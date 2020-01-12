__filename__ = "posts.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.1.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import requests
import json
import html
import datetime
import os
import shutil
import threading
import sys
import trace
import time
from time import gmtime, strftime
from collections import OrderedDict
from threads import threadWithTrace
from cache import storePersonInCache
from cache import getPersonFromCache
from cache import expirePersonCache
from pprint import pprint
from random import randint
from session import createSession
from session import getJson
from session import postJsonString
from session import postImage
from webfinger import webfingerHandle
from httpsig import createSignedHeader
from utils import removePostFromCache
from utils import getCachedPostFilename
from utils import getStatusNumber
from utils import createPersonDir
from utils import urlPermitted
from utils import getNicknameFromActor
from utils import getDomainFromActor
from utils import deletePost
from utils import validNickname
from utils import locatePost
from utils import loadJson
from utils import saveJson
from capabilities import getOcapFilename
from capabilities import capabilitiesUpdate
from media import attachMedia
from content import addHtmlTags
from content import replaceEmojiFromTags
from auth import createBasicAuthHeader
from config import getConfigParam
from blocking import isBlocked
from schedule import addSchedulePost
try: 
    from BeautifulSoup import BeautifulSoup
except ImportError:
    from bs4 import BeautifulSoup

def isModerator(baseDir: str,nickname: str) -> bool:
    """Returns true if the given nickname is a moderator
    """
    moderatorsFile=baseDir+'/accounts/moderators.txt'

    if not os.path.isfile(moderatorsFile):
        if getConfigParam(baseDir,'admin')==nickname:
            return True
        return False

    with open(moderatorsFile, "r") as f:
        lines = f.readlines()
        if len(lines)==0:
            if getConfigParam(baseDir,'admin')==nickname:
                return True
        for moderator in lines:
            moderator=moderator.strip('\n')
            if moderator==nickname:
                return True
    return False

def noOfFollowersOnDomain(baseDir: str,handle: str, \
                          domain: str, followFile='followers.txt') -> int:
    """Returns the number of followers of the given handle from the given domain
    """
    filename=baseDir+'/accounts/'+handle+'/'+followFile
    if not os.path.isfile(filename):
        return 0

    ctr=0
    with open(filename, "r") as followersFilename:
        for followerHandle in followersFilename:
            if '@' in followerHandle:
                followerDomain= \
                    followerHandle.split('@')[1].replace('\n','')
                if domain==followerDomain:
                    ctr+=1
    return ctr

def getPersonKey(nickname: str,domain: str,baseDir: str,keyType='public', \
                 debug=False):
    """Returns the public or private key of a person
    """
    handle=nickname+'@'+domain
    keyFilename=baseDir+'/keys/'+keyType+'/'+handle.lower()+'.key'
    if not os.path.isfile(keyFilename):
        if debug:
            print('DEBUG: private key file not found: '+keyFilename)
        return ''
    keyPem=''
    with open(keyFilename, "r") as pemFile:
        keyPem=pemFile.read()
    if len(keyPem)<20:
        if debug:
            print('DEBUG: private key was too short: '+keyPem)
        return ''
    return keyPem
    
def cleanHtml(rawHtml: str) -> str:
    text = BeautifulSoup(rawHtml, 'html.parser').get_text()
    return html.unescape(text)

def getUserUrl(wfRequest: {}) -> str:
    if wfRequest.get('links'):
        for link in wfRequest['links']:
            if link.get('type') and link.get('href'):
                if link['type'] == 'application/activity+json':
                    if not ('/users/' in link['href'] or \
                            '/profile/' in link['href'] or \
                            '/channel/' in link['href']):
                        print('Webfinger activity+json contains single user instance actor')
                    return link['href']
    return None

def parseUserFeed(session,feedUrl: str,asHeader: {}, \
                  projectVersion: str,httpPrefix: str,domain: str) -> None:
    feedJson = getJson(session,feedUrl,asHeader,None, \
                       projectVersion,httpPrefix,domain)
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
        if isinstance(nextUrl, str):
            userFeed=parseUserFeed(session,nextUrl,asHeader, \
                                   projectVersion,httpPrefix,domain)
            for item in userFeed:
                yield item
        elif isinstance(nextUrl, dict):
            userFeed=nextUrl
            if userFeed.get('orderedItems'):
                for item in userFeed['orderedItems']:
                    yield item        
    
def getPersonBox(baseDir: str,session,wfRequest: {},personCache: {}, \
                 projectVersion: str,httpPrefix: str, \
                 nickname: str,domain: str, \
                 boxName='inbox') -> (str,str,str,str,str,str,str,str):
    asHeader = {'Accept': 'application/activity+json; profile="https://www.w3.org/ns/activitystreams"'}
    if not wfRequest.get('errors'):
        personUrl = getUserUrl(wfRequest)
    else:
        if nickname=='dev':
            # try single user instance
            print('getPersonBox: Trying single user instance with ld+json')
            personUrl = httpPrefix+'://'+domain
            asHeader = {'Accept': 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"'}
        else:
            personUrl = httpPrefix+'://'+domain+'/users/'+nickname
    if not personUrl:
        return None,None,None,None,None,None,None,None
    personJson = getPersonFromCache(baseDir,personUrl,personCache)
    if not personJson:
        if '/channel/' in personUrl:
            asHeader = {'Accept': 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"'}
        personJson = getJson(session,personUrl,asHeader,None, \
                             projectVersion,httpPrefix,domain)
        if not personJson:
            asHeader = {'Accept': 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"'}
            personJson = getJson(session,personUrl,asHeader,None, \
                                 projectVersion,httpPrefix,domain)
            if not personJson:
                print('Unable to get actor')
                return None,None,None,None,None,None,None,None
    boxJson=None
    if not personJson.get(boxName):
        if personJson.get('endpoints'):
            if personJson['endpoints'].get(boxName):
                boxJson=personJson['endpoints'][boxName]
    else:
        boxJson=personJson[boxName]

    if not boxJson:
        return None,None,None,None,None,None,None,None

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
    sharedInbox=None
    if personJson.get('sharedInbox'):
        sharedInbox=personJson['sharedInbox']
    else:
        if personJson.get('endpoints'):
            if personJson['endpoints'].get('sharedInbox'):
                sharedInbox=personJson['endpoints']['sharedInbox']
    capabilityAcquisition=None
    if personJson.get('capabilityAcquisitionEndpoint'):
        capabilityAcquisition=personJson['capabilityAcquisitionEndpoint']
    avatarUrl=None
    if personJson.get('icon'):
        if personJson['icon'].get('url'):
            avatarUrl=personJson['icon']['url']
    displayName=None
    if personJson.get('name'):
        displayName=personJson['name']

    storePersonInCache(baseDir,personUrl,personJson,personCache)

    return boxJson,pubKeyId,pubKey,personId,sharedInbox,capabilityAcquisition,avatarUrl,displayName

def getPosts(session,outboxUrl: str,maxPosts: int, \
             maxMentions: int, \
             maxEmoji: int,maxAttachments: int, \
             federationList: [], \
             personCache: {},raw: bool, \
             simple: bool,debug: bool, \
             projectVersion: str,httpPrefix: str,domain: str) -> {}:
    """Gets public posts from an outbox
    """
    personPosts={}    
    if not outboxUrl:
        return personPosts
    asHeader = {'Accept': 'application/activity+json; profile="https://www.w3.org/ns/activitystreams"'}
    if '/outbox/' in outboxUrl:
        asHeader = {'Accept': 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"'}
    if raw:
        result = []
        i = 0
        userFeed=parseUserFeed(session,outboxUrl,asHeader, \
                               projectVersion,httpPrefix,domain)
        for item in userFeed:
            result.append(item)
            i += 1
            if i == maxPosts:
                break
        pprint(result)
        return None

    i = 0
    userFeed=parseUserFeed(session,outboxUrl,asHeader, \
                           projectVersion,httpPrefix,domain)
    for item in userFeed:
        if not item.get('id'):
            if debug:
                print('No id')
            continue
        if not item.get('type'):
            if debug:
                print('No type')
            continue
        if item['type'] != 'Create':
            if debug:
                print('Not Create type')
            continue
        if not item.get('object'):
            if debug:
                print('No object')
            continue
        if not isinstance(item['object'], dict):
            if debug:
                print('item object is not a dict')
            continue
        if not item['object'].get('published'):
            if debug:
                print('No published attribute')
            continue
        #pprint(item)
        published = item['object']['published']
        if not personPosts.get(item['id']):
            # check that this is a public post
            # #Public should appear in the "to" list
            if item['object'].get('to'):
                isPublic=False
                for recipient in item['object']['to']:
                    if recipient.endswith('#Public'):
                        isPublic=True
                        break
                if not isPublic:
                    continue
            
            content = item['object']['content'].replace('&apos;',"'")

            mentions=[]
            emoji={}
            if item['object'].get('tag'):
                for tagItem in item['object']['tag']:
                    tagType=tagItem['type'].lower()
                    if tagType=='emoji':
                        if tagItem.get('name') and tagItem.get('icon'):
                            if tagItem['icon'].get('url'):
                                # No emoji from non-permitted domains
                                if urlPermitted(tagItem['icon']['url'], \
                                                federationList, \
                                                "objects:read"):
                                    emojiName=tagItem['name']
                                    emojiIcon=tagItem['icon']['url']
                                    emoji[emojiName]=emojiIcon
                                else:
                                    if debug:
                                        print('url not permitted '+tagItem['icon']['url'])
                    if tagType=='mention':
                        if tagItem.get('name'):
                            if tagItem['name'] not in mentions:
                                mentions.append(tagItem['name'])
            if len(mentions)>maxMentions:
                if debug:
                    print('max mentions reached')
                continue
            if len(emoji)>maxEmoji:
                if debug:
                    print('max emojis reached')
                continue

            summary = ''
            if item['object'].get('summary'):
                if item['object']['summary']:
                    summary = item['object']['summary']

            inReplyTo = ''
            if item['object'].get('inReplyTo'):
                if item['object']['inReplyTo']:
                    # No replies to non-permitted domains
                    if not urlPermitted(item['object']['inReplyTo'], \
                                        federationList, \
                                        "objects:read"):
                        if debug:
                            print('url not permitted '+item['object']['inReplyTo'])
                        continue
                    inReplyTo = item['object']['inReplyTo']

            conversation = ''
            if item['object'].get('conversation'):
                if item['object']['conversation']:
                    # no conversations originated in non-permitted domains
                    if urlPermitted(item['object']['conversation'], \
                                    federationList,"objects:read"):  
                        conversation = item['object']['conversation']

            attachment = []
            if item['object'].get('attachment'):
                if item['object']['attachment']:
                    for attach in item['object']['attachment']:
                        if attach.get('name') and attach.get('url'):
                            # no attachments from non-permitted domains
                            if urlPermitted(attach['url'], \
                                            federationList, \
                                            "objects:read"):
                                attachment.append([attach['name'],attach['url']])
                            else:
                                if debug:
                                    print('url not permitted '+attach['url'])

            sensitive = False
            if item['object'].get('sensitive'):
                sensitive = item['object']['sensitive']

            if simple:
                print(cleanHtml(content)+'\n')
            else:
                pprint(item)
                personPosts[item['id']] = {
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

def deleteAllPosts(baseDir: str,nickname: str, domain: str,boxname: str) -> None:
    """Deletes all posts for a person from inbox or outbox
    """
    if boxname!='inbox' and boxname!='outbox':
        return
    boxDir = createPersonDir(nickname,domain,baseDir,boxname)
    for deleteFilename in os.scandir(boxDir):
        deleteFilename=deleteFilename.name
        filePath = os.path.join(boxDir, deleteFilename)
        try:
            if os.path.isfile(filePath):
                os.unlink(filePath)
            elif os.path.isdir(filePath): shutil.rmtree(filePath)
        except Exception as e:
            print(e)

def savePostToBox(baseDir: str,httpPrefix: str,postId: str, \
                  nickname: str, domain: str,postJsonObject: {}, \
                  boxname: str) -> str:
    """Saves the give json to the give box
    Returns the filename
    """
    if boxname!='inbox' and boxname!='outbox' and boxname!='scheduled':
        return None
    originalDomain=domain    
    if ':' in domain:
        domain=domain.split(':')[0]

    if not postId:
        statusNumber,published = getStatusNumber()
        postId=httpPrefix+'://'+originalDomain+'/users/'+nickname+'/statuses/'+statusNumber
        postJsonObject['id']=postId+'/activity'
    if postJsonObject.get('object'):
        if isinstance(postJsonObject['object'], dict):
            postJsonObject['object']['id']=postId
            postJsonObject['object']['atomUri']=postId
         
    boxDir = createPersonDir(nickname,domain,baseDir,boxname)
    filename=boxDir+'/'+postId.replace('/','#')+'.json'
    saveJson(postJsonObject,filename)
    return filename

def updateHashtagsIndex(baseDir: str,tag: {},newPostId: str) -> None:
    """Writes the post url for hashtags to a file
    This allows posts for a hashtag to be quickly looked up
    """
    if tag['type']!='Hashtag':
        return

    # create hashtags directory    
    tagsDir=baseDir+'/tags'
    if not os.path.isdir(tagsDir):
        os.mkdir(tagsDir)
    tagName=tag['name']
    tagsFilename=tagsDir+'/'+tagName[1:]+'.txt'
    tagline=newPostId+'\n'

    if not os.path.isfile(tagsFilename):
        # create a new tags index file
        tagsFile=open(tagsFilename, "w+")
        if tagsFile:
            tagsFile.write(tagline)
            tagsFile.close()
    else:
        # prepend to tags index file
        if tagline not in open(tagsFilename).read():
            try:
                with open(tagsFilename, 'r+') as tagsFile:
                    content = tagsFile.read()
                    tagsFile.seek(0, 0)
                    tagsFile.write(tagline+content)
            except Exception as e:
                print('WARN: Failed to write entry to tags file '+ \
                      tagsFilename+' '+str(e))

def createPostBase(baseDir: str,nickname: str,domain: str,port: int, \
                   toUrl: str,ccUrl: str,httpPrefix: str,content: str, \
                   followersOnly: bool,saveToFile: bool,clientToServer: bool, \
                   attachImageFilename: str, \
                   mediaType: str,imageDescription: str, \
                   useBlurhash: bool,isModerationReport: bool,inReplyTo=None, \
                   inReplyToAtomUri=None,subject=None, \
                   schedulePost=False, \
                   eventDate=None,eventTime=None,location=None) -> {}:
    """Creates a message
    """
    mentionedRecipients= \
        getMentionedPeople(baseDir,httpPrefix,content,domain,False)

    tags=[]
    hashtagsDict={}

    if port:
        if port!=80 and port!=443:
            if ':' not in domain:
                domain=domain+':'+str(port)

    # convert content to html
    emojisDict={}

    # replace 's
    content=content.replace("\ufffd\ufffd\ufffds","'s").replace("’","'")

    # add tags
    content= \
        addHtmlTags(baseDir,httpPrefix, \
                    nickname,domain,content, \
                    mentionedRecipients, \
                    hashtagsDict,True)
    
    statusNumber,published = getStatusNumber()
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

    toRecipients=[]
    toCC=[]
    if toUrl:
        if not isinstance(toUrl, str):
            print('ERROR: toUrl is not a string')
            return None
        toRecipients=[toUrl]        

    # who to send to
    if mentionedRecipients:
        for mention in mentionedRecipients:
            if mention not in toCC:
                toCC.append(mention)

    # create a list of hashtags
    # Only posts which are #Public are searchable by hashtag
    if hashtagsDict:
        isPublic=False
        for recipient in toRecipients:
            if recipient.endswith('#Public'):
                isPublic=True
                break
        for tagName,tag in hashtagsDict.items():
            tags.append(tag)
            if isPublic:
                updateHashtagsIndex(baseDir,tag,newPostId)
        print('Content tags: '+str(tags))

    if inReplyTo and not sensitive:
        # locate the post which this is a reply to and check if
        # it has a content warning. If it does then reproduce
        # the same warning
        replyPostFilename=locatePost(baseDir,nickname,domain,inReplyTo)
        if replyPostFilename:
            replyToJson=loadJson(replyPostFilename)
            if replyToJson:
                if replyToJson.get('object'):
                    if replyToJson['object'].get('sensitive'):
                        if replyToJson['object']['sensitive']:
                            sensitive=True
                            if replyToJson['object'].get('summary'):
                                summary=replyToJson['object']['summary']
    eventDateStr=None
    if eventDate:
        eventName=summary
        if not eventName:
            eventName=content
        eventDateStr=eventDate
        if eventTime:
            if eventTime.endswith('Z'):
                eventDateStr=eventDate+'T'+eventTime
            else:
                eventDateStr=eventDate+'T'+eventTime+':00'+strftime("%z", gmtime())
        else:
            eventDateStr=eventDate+'T12:00:00Z'
        if not schedulePost:
            tags.append({
                "@context": "https://www.w3.org/ns/activitystreams",
                "type": "Event",
                "name": eventName,
                "startTime": eventDateStr,
                "endTime": eventDateStr
            })
    if location:
        tags.append({
            "@context": "https://www.w3.org/ns/activitystreams",
            "type": "Place",
            "name": location
        })

    postContext=[
        'https://www.w3.org/ns/activitystreams',
        {
            'Hashtag': 'as:Hashtag',
            'sensitive': 'as:sensitive',
            'toot': 'http://joinmastodon.org/ns#',
            'votersCount': 'toot:votersCount'
        }
    ]
            
    if not clientToServer:
        actorUrl=httpPrefix+'://'+domain+'/users/'+nickname

        # if capabilities have been granted for this actor
        # then get the corresponding id
        capabilityId=None
        capabilityIdList=[]
        ocapFilename=getOcapFilename(baseDir,nickname,domain,toUrl,'granted')
        if ocapFilename:
            if os.path.isfile(ocapFilename):
                oc=loadJson(ocapFilename)
                if oc:
                    if oc.get('id'):
                        capabilityIdList=[oc['id']]
        newPost = {
            "@context": postContext,
            'id': newPostId+'/activity',
            'capability': capabilityIdList,
            'type': 'Create',
            'actor': actorUrl,
            'published': published,
            'to': toRecipients,
            'cc': toCC,
            'object': {
                'id': newPostId,
                'type': 'Note',
                'summary': summary,
                'inReplyTo': inReplyTo,
                'published': published,
                'url': httpPrefix+'://'+domain+'/@'+nickname+'/'+statusNumber,
                'attributedTo': httpPrefix+'://'+domain+'/users/'+nickname,
                'to': toRecipients,
                'cc': toCC,
                'sensitive': sensitive,
                'atomUri': newPostId,
                'inReplyToAtomUri': inReplyToAtomUri,
                'content': content,
                'contentMap': {
                    'en': content
                },
                'attachment': [],
                'tag': tags,
                'replies': {
                    'id': 'https://'+domain+'/users/'+nickname+'/statuses/'+statusNumber+'/replies',
                    'type': 'Collection',
                    'first': {
                        'type': 'CollectionPage',
                        'partOf': 'https://'+domain+'/users/'+nickname+'/statuses/'+statusNumber+'/replies',
                        'items': []
                    }
                }
            }
        }
        if attachImageFilename:
            newPost['object']= \
                attachMedia(baseDir,httpPrefix,domain,port, \
                            newPost['object'],attachImageFilename, \
                            mediaType,imageDescription,useBlurhash)            
    else:
        newPost = {
            "@context": postContext,
            'id': newPostId,
            'type': 'Note',
            'summary': summary,
            'inReplyTo': inReplyTo,
            'published': published,
            'url': httpPrefix+'://'+domain+'/@'+nickname+'/'+statusNumber,
            'attributedTo': httpPrefix+'://'+domain+'/users/'+nickname,
            'to': toRecipients,
            'cc': toCC,
            'sensitive': sensitive,
            'atomUri': newPostId,
            'inReplyToAtomUri': inReplyToAtomUri,
            'content': content,
            'contentMap': {
                'en': content
            },
            'attachment': [],
            'tag': tags,
            'replies': {
                'id': 'https://'+domain+'/users/'+nickname+'/statuses/'+statusNumber+'/replies',
                'type': 'Collection',
                'first': {
                    'type': 'CollectionPage',
                    'partOf': 'https://'+domain+'/users/'+nickname+'/statuses/'+statusNumber+'/replies',
                    'items': []
                }
            }
        }
        if attachImageFilename:
            newPost= \
                attachMedia(baseDir,httpPrefix,domain,port, \
                            newPost,attachImageFilename, \
                            mediaType,imageDescription,useBlurhash)            
    if ccUrl:
        if len(ccUrl)>0:
            newPost['cc']=[ccUrl]
            if newPost.get('object'):
                newPost['object']['cc']=[ccUrl]

    # if this is a moderation report then add a status
    if isModerationReport:
        # add status
        if newPost.get('object'):
            newPost['object']['moderationStatus']='pending'
        else:
            newPost['moderationStatus']='pending'
        # save to index file
        moderationIndexFile=baseDir+'/accounts/moderation.txt'
        modFile=open(moderationIndexFile, "a+")
        if modFile:
            modFile.write(newPostId+'\n')
            modFile.close()

    if schedulePost:
        if eventDate and eventTime:    
            # add an item to the scheduled post index file
            addSchedulePost(baseDir,nickname,domain,eventDateStr,postId)
            savePostToBox(baseDir,httpPrefix,newPostId, \
                          nickname,domain,newPost,'scheduled')
        else:
            print('Unable to create scheduled post without date and time values')
            return newPost
    elif saveToFile:
        savePostToBox(baseDir,httpPrefix,newPostId, \
                      nickname,domain,newPost,'outbox')
    return newPost

def outboxMessageCreateWrap(httpPrefix: str, \
                            nickname: str,domain: str,port: int, \
                            messageJson: {}) -> {}:
    """Wraps a received message in a Create
    https://www.w3.org/TR/activitypub/#object-without-create
    """

    if port:
        if port!=80 and port!=443:
            if ':' not in domain:
                domain=domain+':'+str(port)
    statusNumber,published = getStatusNumber()
    if messageJson.get('published'):
        published = messageJson['published']
    newPostId=httpPrefix+'://'+domain+'/users/'+nickname+'/statuses/'+statusNumber
    cc=[]
    if messageJson.get('cc'):
        cc=messageJson['cc']
    # TODO
    capabilityUrl=[]
    newPost = {
        "@context": "https://www.w3.org/ns/activitystreams",
        'id': newPostId+'/activity',
        'capability': capabilityUrl,
        'type': 'Create',
        'actor': httpPrefix+'://'+domain+'/users/'+nickname,
        'published': published,
        'to': messageJson['to'],
        'cc': cc,
        'object': messageJson
    }
    newPost['object']['id']=newPost['id']
    newPost['object']['url']= \
        httpPrefix+'://'+domain+'/@'+nickname+'/'+statusNumber
    newPost['object']['atomUri']= \
        httpPrefix+'://'+domain+'/users/'+nickname+'/statuses/'+statusNumber
    return newPost

def postIsAddressedToFollowers(baseDir: str,
                               nickname: str,domain: str,port: int, \
                               httpPrefix: str,
                               postJsonObject: {}) -> bool:
    """Returns true if the given post is addressed to followers of the nickname
    """
    if port:
        if port!=80 and port!=443:
            if ':' not in domain:
                domain=domain+':'+str(port)

    if not postJsonObject.get('object'):
        return False
    toList=[]
    ccList=[]
    if postJsonObject['type']!='Update' and \
       isinstance(postJsonObject['object'], dict):
        if postJsonObject['object'].get('to'):
            toList=postJsonObject['object']['to']
        if postJsonObject['object'].get('cc'):
            ccList=postJsonObject['object']['cc']
    else:
        if postJsonObject.get('to'):
            toList=postJsonObject['to']
        if postJsonObject.get('cc'):
            ccList=postJsonObject['cc']
        
    followersUrl=httpPrefix+'://'+domain+'/users/'+nickname+'/followers'

    # does the followers url exist in 'to' or 'cc' lists?
    addressedToFollowers=False
    if followersUrl in toList:
        addressedToFollowers=True
    elif followersUrl in ccList:
        addressedToFollowers=True
    return addressedToFollowers

def postIsAddressedToPublic(baseDir: str,postJsonObject: {}) -> bool:
    """Returns true if the given post is addressed to public
    """
    if not postJsonObject.get('object'):
        return False
    if not postJsonObject['object'].get('to'):
        return False
        
    publicUrl='https://www.w3.org/ns/activitystreams#Public'

    # does the public url exist in 'to' or 'cc' lists?
    addressedToPublic=False
    if publicUrl in postJsonObject['object']['to']:
        addressedToPublic=True
    if not addressedToPublic:
        if not postJsonObject['object'].get('cc'):
            return False
        if publicUrl in postJsonObject['object']['cc']:
            addressedToPublic=True
    return addressedToPublic

def createPublicPost(baseDir: str, \
                     nickname: str,domain: str,port: int,httpPrefix: str, \
                     content: str,followersOnly: bool,saveToFile: bool,
                     clientToServer: bool,\
                     attachImageFilename: str,mediaType: str, \
                     imageDescription: str,useBlurhash: bool, \
                     inReplyTo=None,inReplyToAtomUri=None,subject=None, \
                     schedulePost=False, \
                     eventDate=None,eventTime=None,location=None) -> {}:
    """Public post
    """
    domainFull=domain
    if port:
        if port!=80 and port!=443:
            if ':' not in domain:
                domainFull=domain+':'+str(port)
    return createPostBase(baseDir,nickname,domain,port, \
                          'https://www.w3.org/ns/activitystreams#Public', \
                          httpPrefix+'://'+domainFull+'/users/'+nickname+'/followers', \
                          httpPrefix,content,followersOnly,saveToFile, \
                          clientToServer, \
                          attachImageFilename,mediaType, \
                          imageDescription,useBlurhash, \
                          False,inReplyTo,inReplyToAtomUri,subject, \
                          schedulePost,eventDate,eventTime,location)

def createQuestionPost(baseDir: str,
                       nickname: str,domain: str,port: int,httpPrefix: str, \
                       content: str,qOptions: [], \
                       followersOnly: bool,saveToFile: bool,
                       clientToServer: bool,\
                       attachImageFilename: str,mediaType: str, \
                       imageDescription: str,useBlurhash: bool, \
                       subject: str,durationDays: int) -> {}:
    """Question post with multiple choice options
    """
    domainFull=domain
    if port:
        if port!=80 and port!=443:
            if ':' not in domain:
                domainFull=domain+':'+str(port)
    messageJson= \
        createPostBase(baseDir,nickname,domain,port, \
                       'https://www.w3.org/ns/activitystreams#Public', \
                       httpPrefix+'://'+domainFull+'/users/'+nickname+'/followers', \
                       httpPrefix,content,followersOnly,saveToFile, \
                       clientToServer, \
                       attachImageFilename,mediaType, \
                       imageDescription,useBlurhash, \
                       False,None,None,subject, \
                       False,None,None,None)
    messageJson['object']['type']='Question'
    messageJson['object']['oneOf']=[]
    messageJson['object']['votersCount']=0
    currTime=datetime.datetime.utcnow()
    daysSinceEpoch=int((currTime - datetime.datetime(1970,1,1)).days + durationDays)
    endTime=datetime.datetime(1970,1,1) + datetime.timedelta(daysSinceEpoch)
    messageJson['object']['endTime']=endTime.strftime("%Y-%m-%dT%H:%M:%SZ")
    for questionOption in qOptions:
        messageJson['object']['oneOf'].append({
            "type": "Note",
            "name": questionOption,
            "replies": {
                "type": "Collection",
                "totalItems": 0
            }
        })
    return messageJson

def createUnlistedPost(baseDir: str,
                       nickname: str,domain: str,port: int,httpPrefix: str, \
                       content: str,followersOnly: bool,saveToFile: bool,
                       clientToServer: bool,\
                       attachImageFilename: str,mediaType: str, \
                       imageDescription: str,useBlurhash: bool, \
                       inReplyTo=None,inReplyToAtomUri=None,subject=None, \
                       schedulePost=False, \
                       eventDate=None,eventTime=None,location=None) -> {}:
    """Unlisted post. This has the #Public and followers links inverted.
    """
    domainFull=domain
    if port:
        if port!=80 and port!=443:
            if ':' not in domain:
                domainFull=domain+':'+str(port)
    return createPostBase(baseDir,nickname,domain,port, \
                          httpPrefix+'://'+domainFull+'/users/'+nickname+'/followers', \
                          'https://www.w3.org/ns/activitystreams#Public', \
                          httpPrefix,content,followersOnly,saveToFile, \
                          clientToServer, \
                          attachImageFilename,mediaType, \
                          imageDescription,useBlurhash, \
                          False,inReplyTo, inReplyToAtomUri, subject, \
                          schedulePost,eventDate,eventTime,location)

def createFollowersOnlyPost(baseDir: str,
                            nickname: str,domain: str,port: int,httpPrefix: str, \
                            content: str,followersOnly: bool,saveToFile: bool,
                            clientToServer: bool,\
                            attachImageFilename: str,mediaType: str, \
                            imageDescription: str,useBlurhash: bool, \
                            inReplyTo=None,inReplyToAtomUri=None,subject=None, \
                            schedulePost=False, \
                            eventDate=None,eventTime=None,location=None) -> {}:
    """Followers only post
    """
    domainFull=domain
    if port:
        if port!=80 and port!=443: 
            if ':' not in domain:
                domainFull=domain+':'+str(port)
    return createPostBase(baseDir,nickname,domain,port, \
                          httpPrefix+'://'+domainFull+'/users/'+nickname+'/followers', \
                          None,
                          httpPrefix,content,followersOnly,saveToFile, \
                          clientToServer, \
                          attachImageFilename,mediaType, \
                          imageDescription,useBlurhash, \
                          False,inReplyTo, inReplyToAtomUri, subject, \
                          schedulePost,eventDate,eventTime,location)

def getMentionedPeople(baseDir: str,httpPrefix: str, \
                       content: str,domain: str,debug: bool) -> []:
    """Extracts a list of mentioned actors from the given message content
    """
    if '@' not in content:
        return None
    mentions=[]
    words=content.split(' ')
    for wrd in words:
        if wrd.startswith('@'):
            handle=wrd[1:]
            if debug:
                print('DEBUG: mentioned handle '+handle)
            if '@' not in handle:
                handle=handle+'@'+domain
                if not os.path.isdir(baseDir+'/accounts/'+handle):
                    continue
            else:
                externalDomain=handle.split('@')[1]
                if not ('.' in externalDomain or externalDomain=='localhost'):
                    continue
            mentionedNickname=handle.split('@')[0]
            mentionedDomain=handle.split('@')[1].strip('\n')
            if ':' in mentionedDomain:
                mentionedDomain=mentionedDomain.split(':')[0]
            if not validNickname(mentionedDomain,mentionedNickname):
                continue
            actor= \
                httpPrefix+'://'+handle.split('@')[1]+ \
                '/users/'+mentionedNickname
            mentions.append(actor)
    return mentions

def createDirectMessagePost(baseDir: str,
                            nickname: str,domain: str,port: int,httpPrefix: str, \
                            content: str,followersOnly: bool,saveToFile: bool,
                            clientToServer: bool,\
                            attachImageFilename: str,mediaType: str, \
                            imageDescription: str,useBlurhash: bool, \
                            inReplyTo=None,inReplyToAtomUri=None, \
                            subject=None,debug=False, \
                            schedulePost=False, \
                            eventDate=None,eventTime=None,location=None) -> {}:
    """Direct Message post
    """
    mentionedPeople=getMentionedPeople(baseDir,httpPrefix,content,domain,debug)
    if debug:
        print('mentionedPeople: '+str(mentionedPeople))
    if not mentionedPeople:
        return None
    postTo=None
    postCc=None
    messageJson= \
        createPostBase(baseDir,nickname,domain,port, \
                       postTo,postCc, \
                       httpPrefix,content,followersOnly,saveToFile, \
                       clientToServer, \
                       attachImageFilename,mediaType, \
                       imageDescription,useBlurhash, \
                       False,inReplyTo,inReplyToAtomUri,subject, \
                       schedulePost,eventDate,eventTime,location)
    # mentioned recipients go into To rather than Cc
    messageJson['to']=messageJson['object']['cc']
    messageJson['object']['to']=messageJson['to']
    messageJson['cc']=[]
    messageJson['object']['cc']=[]
    return messageJson

def createReportPost(baseDir: str,
                     nickname: str, domain: str, port: int,httpPrefix: str, \
                     content: str, followersOnly: bool, saveToFile: bool,
                     clientToServer: bool,\
                     attachImageFilename: str,mediaType: str, \
                     imageDescription: str,useBlurhash: bool, \
                     debug: bool,subject=None) -> {}:
    """Send a report to moderators
    """
    domainFull=domain
    if port:
        if port!=80 and port!=443:
            if ':' not in domain:
                domainFull=domain+':'+str(port)

    # add a title to distinguish moderation reports from other posts
    reportTitle='Moderation Report'
    if not subject:
        subject=reportTitle
    else:
        if not subject.startswith(reportTitle):
            subject=reportTitle+': '+subject

    # create the list of moderators from the moderators file
    moderatorsList=[]
    moderatorsFile=baseDir+'/accounts/moderators.txt'
    if os.path.isfile(moderatorsFile):
        with open (moderatorsFile, "r") as fileHandler:
            for line in fileHandler:
                line=line.strip('\n')
                if line.startswith('#'):
                    continue
                if line.startswith('/users/'):
                    line=line.replace('users','')
                if line.startswith('@'):
                    line=line[1:]
                if '@' in line:
                    moderatorActor=httpPrefix+'://'+domainFull+'/users/'+line.split('@')[0]
                    if moderatorActor not in moderatorList:
                        moderatorsList.append(moderatorActor)
                    continue
                if line.startswith('http') or line.startswith('dat'):
                    # must be a local address - no remote moderators
                    if '://'+domainFull+'/' in line:
                        if line not in moderatorsList:
                            moderatorsList.append(line)
                else:
                    if '/' not in line:
                        moderatorActor=httpPrefix+'://'+domainFull+'/users/'+line
                        if moderatorActor not in moderatorsList:
                            moderatorsList.append(moderatorActor)
    if len(moderatorsList)==0:
        # if there are no moderators then the admin becomes the moderator
        adminNickname=getConfigParam(baseDir,'admin')
        if adminNickname:
            moderatorsList.append(httpPrefix+'://'+domainFull+ \
                                  '/users/'+adminNickname)
    if not moderatorsList:
        return None
    if debug:
        print('DEBUG: Sending report to moderators')
        print(str(moderatorsList))
    postTo=moderatorsList
    postCc=None
    postJsonObject=None
    for toUrl in postTo:        
        # who is this report going to?
        toNickname=toUrl.split('/users/')[1]
        handle=toNickname+'@'+domain

        postJsonObject= \
            createPostBase(baseDir,nickname,domain,port, \
                           toUrl,postCc, \
                           httpPrefix,content,followersOnly,saveToFile, \
                           clientToServer, \
                           attachImageFilename,mediaType, \
                           imageDescription,useBlurhash, \
                           True,None,None,subject, \
                           False,None,None,None)
        if not postJsonObject:
            continue

        # update the inbox index with the report filename
        #indexFilename=baseDir+'/accounts/'+handle+'/inbox.index'
        #indexEntry=postJsonObject['id'].replace('/activity','').replace('/','#')+'.json'
        #if indexEntry not in open(indexFilename).read():        
        #    try:
        #        with open(indexFilename, 'a+') as fp:
        #            fp.write(indexEntry)
        #    except:
        #        pass

        # save a notification file so that the moderator
        # knows something new has appeared
        newReportFile=baseDir+'/accounts/'+handle+'/.newReport'
        if os.path.isfile(newReportFile):
            continue
        try:
            with open(newReportFile, 'w') as fp:
                fp.write(toUrl+'/moderation')
        except:
            pass

    return postJsonObject

def threadSendPost(session,postJsonStr: str,federationList: [],\
                   inboxUrl: str, baseDir: str, \
                   signatureHeaderJson: {},postLog: [], \
                   debug :bool) -> None:
    """Sends a with retries
    """
    tries=0
    sendIntervalSec=30
    for attempt in range(20):
        postResult=None
        unauthorized=False
        try:
            postResult,unauthorized = \
                postJsonString(session,postJsonStr,federationList, \
                               inboxUrl,signatureHeaderJson, \
                               "inbox:write",debug)
        except Exception as e:
            print('ERROR: postJsonString failed '+str(e))
        if unauthorized==True:
            print(postJsonStr)
            print('threadSendPost: Post is unauthorized')
            break
        if postResult:
            logStr='Success on try '+str(tries)+': '+postJsonStr
        else:
            logStr='Retry '+str(tries)+': '+postJsonStr
        postLog.append(logStr)
        # keep the length of the log finite
        # Don't accumulate massive files on systems with limited resources
        while len(postLog)>16:
            postLog.pop(0)
        if debug:
            # save the log file
            postLogFilename=baseDir+'/post.log'
            with open(postLogFilename, "a+") as logFile:
                logFile.write(logStr+'\n')

        if postResult:
            if debug:
                print('DEBUG: successful json post to '+inboxUrl)
            # our work here is done
            break
        if debug:
            print(postJsonStr)
            print('DEBUG: json post to '+inboxUrl+' failed. Waiting for '+ \
                  str(sendIntervalSec)+' seconds.')
        time.sleep(sendIntervalSec)
        tries+=1
        
def sendPost(projectVersion: str, \
             session,baseDir: str,nickname: str, domain: str, port: int, \
             toNickname: str, toDomain: str, toPort: int, cc: str, \
             httpPrefix: str, content: str, followersOnly: bool, \
             saveToFile: bool, clientToServer: bool, \
             attachImageFilename: str,mediaType: str, \
             imageDescription: str,useBlurhash: bool, \
             federationList: [],\
             sendThreads: [], postLog: [], cachedWebfingers: {},personCache: {}, \
             debug=False,inReplyTo=None,inReplyToAtomUri=None,subject=None) -> int:
    """Post to another inbox
    """
    withDigest=True

    if toNickname=='inbox':
        # shared inbox actor on @domain@domain
        toNickname=toDomain

    toDomainOriginal=toDomain
    if toPort:
        if toPort!=80 and toPort!=443:
            if ':' not in toDomain:
                toDomain=toDomain+':'+str(toPort)        

    handle=httpPrefix+'://'+toDomain+'/@'+toNickname

    # lookup the inbox for the To handle
    wfRequest = webfingerHandle(session,handle,httpPrefix,cachedWebfingers, \
                                domain,projectVersion)
    if not wfRequest:
        return 1

    if not clientToServer:
        postToBox='inbox'
    else:
        postToBox='outbox'

    # get the actor inbox for the To handle
    inboxUrl,pubKeyId,pubKey,toPersonId,sharedInbox,capabilityAcquisition,avatarUrl,displayName = \
        getPersonBox(baseDir,session,wfRequest,personCache, \
                     projectVersion,httpPrefix, \
                     nickname,domain,postToBox)

    # If there are more than one followers on the target domain
    # then send to the shared inbox indead of the individual inbox
    if nickname=='capabilities':
        inboxUrl=capabilityAcquisition
        if not capabilityAcquisition:
            return 2
                     
    if not inboxUrl:
        return 3
    if not pubKey:
        return 4
    if not toPersonId:
        return 5
    # sharedInbox and capabilities are optional

    postJsonObject = \
            createPostBase(baseDir,nickname,domain,port, \
                           toPersonId,cc,httpPrefix,content, \
                           followersOnly,saveToFile,clientToServer, \
                           attachImageFilename,mediaType, \
                           imageDescription,useBlurhash, \
                           False,inReplyTo,inReplyToAtomUri,subject, \
                           False,None,None,None)

    # get the senders private key
    privateKeyPem=getPersonKey(nickname,domain,baseDir,'private')
    if len(privateKeyPem)==0:
        return 6

    if toDomain not in inboxUrl:
        return 7
    postPath=inboxUrl.split(toDomain,1)[1]

    # convert json to string so that there are no
    # subsequent conversions after creating message body digest
    postJsonStr=json.dumps(postJsonObject)

    # construct the http header, including the message body digest
    signatureHeaderJson = \
        createSignedHeader(privateKeyPem,nickname,domain,port, \
                           toDomain,toPort, \
                           postPath,httpPrefix,withDigest,postJsonStr)

    # Keep the number of threads being used small
    while len(sendThreads)>1000:
        print('WARN: Maximum threads reached - killing send thread')
        sendThreads[0].kill()
        sendThreads.pop(0)
        print('WARN: thread killed')
    thr = \
        threadWithTrace(target=threadSendPost, \
                        args=(session, \
                              postJsonStr, \
                              federationList, \
                              inboxUrl,baseDir, \
                              signatureHeaderJson.copy(), \
                              postLog,
                              debug),daemon=True)
    sendThreads.append(thr)
    thr.start()
    return 0

def sendPostViaServer(projectVersion: str, \
                      baseDir: str,session,fromNickname: str,password: str, \
                      fromDomain: str, fromPort: int, \
                      toNickname: str, toDomain: str, toPort: int, cc: str, \
                      httpPrefix: str, content: str, followersOnly: bool, \
                      attachImageFilename: str,mediaType: str, \
                      imageDescription: str,useBlurhash: bool, \
                      cachedWebfingers: {},personCache: {}, \
                      debug=False,inReplyTo=None, \
                      inReplyToAtomUri=None,subject=None) -> int:
    """Send a post via a proxy (c2s)
    """
    if not session:
        print('WARN: No session for sendPostViaServer')
        return 6
    withDigest=True

    if toPort:
        if toPort!=80 and toPort!=443:
            if ':' not in fromDomain:
                fromDomain=fromDomain+':'+str(fromPort)

    handle=httpPrefix+'://'+fromDomain+'/@'+fromNickname

    # lookup the inbox for the To handle
    wfRequest = \
        webfingerHandle(session,handle,httpPrefix,cachedWebfingers, \
                        fromDomain,projectVersion)
    if not wfRequest:
        if debug:
            print('DEBUG: webfinger failed for '+handle)
        return 1

    postToBox='outbox'

    # get the actor inbox for the To handle
    inboxUrl,pubKeyId,pubKey,fromPersonId,sharedInbox,capabilityAcquisition,avatarUrl,displayName = \
        getPersonBox(baseDir,session,wfRequest,personCache, \
                     projectVersion,httpPrefix,fromNickname, \
                     fromDomain,postToBox)
                     
    if not inboxUrl:
        if debug:
            print('DEBUG: No '+postToBox+' was found for '+handle)
        return 3
    if not fromPersonId:
        if debug:
            print('DEBUG: No actor was found for '+handle)
        return 4

    # Get the json for the c2s post, not saving anything to file
    # Note that baseDir is set to None
    saveToFile=False
    clientToServer=True
    if toDomain.lower().endswith('public'):
        toPersonId='https://www.w3.org/ns/activitystreams#Public'
        fromDomainFull=fromDomain
        if fromPort:
            if fromPort!=80 and fromPort!=443:
                if ':' not in fromDomain:
                    fromDomainFull=fromDomain+':'+str(fromPort)                
        cc=httpPrefix+'://'+fromDomainFull+'/users/'+fromNickname+'/followers'
    else:
        if toDomain.lower().endswith('followers') or \
           toDomain.lower().endswith('followersonly'):
            toPersonId= \
                httpPrefix+'://'+ \
                fromDomainFull+'/users/'+fromNickname+'/followers'
        else:
            toDomainFull=toDomain
            if toPort:
                if toPort!=80 and toPort!=443:
                    if ':' not in toDomain:
                        toDomainFull=toDomain+':'+str(toPort)        
            toPersonId=httpPrefix+'://'+toDomainFull+'/users/'+toNickname
    postJsonObject = \
            createPostBase(baseDir, \
                           fromNickname,fromDomain,fromPort, \
                           toPersonId,cc,httpPrefix,content, \
                           followersOnly,saveToFile,clientToServer, \
                           attachImageFilename,mediaType, \
                           imageDescription,useBlurhash, \
                           False,inReplyTo,inReplyToAtomUri,subject, \
                           False,None,None,None)
    
    authHeader=createBasicAuthHeader(fromNickname,password)

    if attachImageFilename:
        headers = {'host': fromDomain, \
                   'Authorization': authHeader}
        postResult = \
            postImage(session,attachImageFilename,[], \
                      inboxUrl,headers,"inbox:write")
        #if not postResult:
        #    if debug:
        #        print('DEBUG: Failed to upload image')
        #    return 9
     
    headers = {'host': fromDomain, \
               'Content-type': 'application/json', \
               'Authorization': authHeader}
    postResult = \
        postJsonString(session,json.dumps(postJsonObject),[], \
                       inboxUrl,headers,"inbox:write",debug)
    #if not postResult:
    #    if debug:
    #        print('DEBUG: POST failed for c2s to '+inboxUrl)
    #    return 5

    if debug:
        print('DEBUG: c2s POST success')
    return 0

def groupFollowersByDomain(baseDir :str,nickname :str,domain :str) -> {}:
    """Returns a dictionary with followers grouped by domain
    """
    handle=nickname+'@'+domain
    followersFilename=baseDir+'/accounts/'+handle+'/followers.txt'
    if not os.path.isfile(followersFilename):
        return None
    grouped={}
    with open(followersFilename, "r") as f:
        for followerHandle in f:
            if '@' in followerHandle:
                fHandle=followerHandle.strip().replace('\n','')
                followerDomain=fHandle.split('@')[1]
                if not grouped.get(followerDomain):
                    grouped[followerDomain]=[fHandle]
                else:
                    grouped[followerDomain].append(fHandle)
    return grouped

def addFollowersToPublicPost(postJsonObject: {}) -> None:
    """Adds followers entry to cc if it doesn't exist
    """
    if not postJsonObject.get('actor'):
        return

    if isinstance(postJsonObject['object'], str):
        if not postJsonObject.get('to'):
            return
        if len(postJsonObject['to'])>1:
            return
        if len(postJsonObject['to'])==0:
            return
        if not postJsonObject['to'][0].endswith('#Public'):
            return
        if postJsonObject.get('cc'):
            return
        postJsonObject['cc']=postJsonObject['actor']+'/followers'
    elif isinstance(postJsonObject['object'], dict):
        if not postJsonObject['object'].get('to'):
            return
        if len(postJsonObject['object']['to'])>1:
            return
        if len(postJsonObject['object']['to'])==0:
            return
        if not postJsonObject['object']['to'][0].endswith('#Public'):
            return
        if postJsonObject['object'].get('cc'):
            return
        postJsonObject['object']['cc']=postJsonObject['actor']+'/followers'

def sendSignedJson(postJsonObject: {},session,baseDir: str, \
                   nickname: str, domain: str, port: int, \
                   toNickname: str, toDomain: str, toPort: int, cc: str, \
                   httpPrefix: str, saveToFile: bool, clientToServer: bool, \
                   federationList: [], \
                   sendThreads: [], postLog: [], cachedWebfingers: {}, \
                   personCache: {}, debug: bool,projectVersion: str) -> int:
    """Sends a signed json object to an inbox/outbox
    """
    if debug:
        print('DEBUG: sendSignedJson start')
    if not session:
        print('WARN: No session specified for sendSignedJson')
        return 8
    withDigest=True

    sharedInbox=False
    if toNickname=='inbox':
        # shared inbox actor on @domain@domain
        toNickname=toDomain
        sharedInbox=True

    toDomainOriginal=toDomain
    if toPort:
        if toPort!=80 and toPort!=443:
            if ':' not in toDomain:
                toDomain=toDomain+':'+str(toPort)        

    handleBase=httpPrefix+'://'+toDomain+'/@'
    if toNickname:
        handle=handleBase+toNickname
    else:
        singleUserInstanceNickname='dev'
        handle=handleBase+singleUserInstanceNickname
        
    if debug:
        print('DEBUG: handle - '+handle+' toPort '+str(toPort))

    # lookup the inbox for the To handle
    wfRequest=webfingerHandle(session,handle,httpPrefix,cachedWebfingers, \
                              domain,projectVersion)
    if not wfRequest:
        if debug:
            print('DEBUG: webfinger for '+handle+' failed')
        return 1

    if wfRequest.get('errors'):
        if debug:
            print('DEBUG: webfinger for '+handle+' failed with errors '+str(wfRequest['errors']))
    
    if not clientToServer:
        postToBox='inbox'
    else:
        postToBox='outbox'

    # get the actor inbox/outbox/capabilities for the To handle
    inboxUrl,pubKeyId,pubKey,toPersonId,sharedInboxUrl,capabilityAcquisition,avatarUrl,displayName = \
        getPersonBox(baseDir,session,wfRequest,personCache, \
                     projectVersion,httpPrefix,nickname,domain,postToBox)

    if nickname=='capabilities':
        inboxUrl=capabilityAcquisition
        if not capabilityAcquisition:
            return 2
    else:
        print("inboxUrl: "+str(inboxUrl))
        print("toPersonId: "+str(toPersonId))
        print("sharedInboxUrl: "+str(sharedInboxUrl))
        if inboxUrl:
            if inboxUrl.endswith('/actor/inbox'):
                inboxUrl=sharedInboxUrl

    if not inboxUrl:
        if debug:
            print('DEBUG: missing inboxUrl')
        return 3

    if debug:
        print('DEBUG: Sending to endpoint '+inboxUrl)
                     
    if not pubKey:
        if debug:
            print('DEBUG: missing pubkey')
        return 4
    if not toPersonId:
        if debug:
            print('DEBUG: missing personId')
        return 5
    # sharedInbox and capabilities are optional

    # get the senders private key
    privateKeyPem=getPersonKey(nickname,domain,baseDir,'private',debug)
    if len(privateKeyPem)==0:
        if debug:
            print('DEBUG: Private key not found for '+ \
                  nickname+'@'+domain+' in '+baseDir+'/keys/private')
        return 6

    if toDomain not in inboxUrl:
        if debug:
            print('DEBUG: '+toDomain+' is not in '+inboxUrl)
        return 7
    postPath=inboxUrl.split(toDomain,1)[1]

    addFollowersToPublicPost(postJsonObject)
    
    # convert json to string so that there are no
    # subsequent conversions after creating message body digest
    postJsonStr=json.dumps(postJsonObject)

    # construct the http header, including the message body digest
    signatureHeaderJson = \
        createSignedHeader(privateKeyPem,nickname,domain,port, \
                           toDomain,toPort, \
                           postPath,httpPrefix,withDigest,postJsonStr)
    
    # Keep the number of threads being used small
    while len(sendThreads)>1000:
        print('WARN: Maximum threads reached - killing send thread')
        sendThreads[0].kill()
        sendThreads.pop(0)
        print('WARN: thread killed')

    if debug:
        print('DEBUG: starting thread to send post')
        pprint(postJsonObject)
    thr = threadWithTrace(target=threadSendPost, \
                          args=(session, \
                                postJsonStr, \
                                federationList, \
                                inboxUrl,baseDir, \
                                signatureHeaderJson.copy(), \
                                postLog,
                                debug),daemon=True)
    sendThreads.append(thr)
    #thr.start()
    return 0

def addToField(activityType: str,postJsonObject: {},debug: bool) -> ({},bool):
    """The Follow activity doesn't have a 'to' field and so one
    needs to be added so that activity distribution happens in a consistent way
    Returns true if a 'to' field exists or was added
    """
    if postJsonObject.get('to'):
        return postJsonObject,True
    
    if debug:
        pprint(postJsonObject)
        print('DEBUG: no "to" field when sending to named addresses 2')

    isSameType=False
    toFieldAdded=False
    if postJsonObject.get('object'):
        if isinstance(postJsonObject['object'], str):
            if postJsonObject.get('type'):
                if postJsonObject['type']==activityType:
                    isSameType=True
                    if debug:
                        print('DEBUG: "to" field assigned to Follow')
                    toAddress=postJsonObject['object']
                    if '/statuses/' in toAddress:
                        toAddress=toAddress.split('/statuses/')[0]
                    postJsonObject['to']=[toAddress]
                    toFieldAdded=True
        elif isinstance(postJsonObject['object'], dict):
            if postJsonObject['object'].get('type'):
                if postJsonObject['object']['type']==activityType:
                    isSameType=True
                    if isinstance(postJsonObject['object']['object'], str):
                        if debug:
                            print('DEBUG: "to" field assigned to Follow')
                        toAddress=postJsonObject['object']['object']
                        if '/statuses/' in toAddress:
                            toAddress=toAddress.split('/statuses/')[0]
                        postJsonObject['object']['to']=[toAddress]
                        postJsonObject['to']= \
                            [postJsonObject['object']['object']]
                        toFieldAdded=True

    if not isSameType:
        return postJsonObject,True
    if toFieldAdded:
        return postJsonObject,True
    return postJsonObject,False

def sendToNamedAddresses(session,baseDir: str, \
                         nickname: str, domain: str, port: int, \
                         httpPrefix: str,federationList: [], \
                         sendThreads: [],postLog: [], \
                         cachedWebfingers: {},personCache: {}, \
                         postJsonObject: {},debug: bool, \
                         projectVersion: str) -> None:
    """sends a post to the specific named addresses in to/cc
    """
    if not session:
        print('WARN: No session for sendToNamedAddresses')
        return
    if not postJsonObject.get('object'):
        return
    if isinstance(postJsonObject['object'], dict):
        isProfileUpdate=False
        # for actor updates there is no 'to' within the object
        if postJsonObject['object'].get('type') and postJsonObject.get('type'):
            if postJsonObject['type']=='Update' and \
               (postJsonObject['object']['type']=='Person' or \
                postJsonObject['object']['type']=='Application' or \
                postJsonObject['object']['type']=='Group' or \
                postJsonObject['object']['type']=='Service'):
                # use the original object, which has a 'to'
                recipientsObject=postJsonObject
                isProfileUpdate=True
        
        if not isProfileUpdate:
            if not postJsonObject['object'].get('to'):
                if debug:
                    pprint(postJsonObject)
                    print('DEBUG: no "to" field when sending to named addresses')
                if postJsonObject['object'].get('type'):                    
                    if postJsonObject['object']['type']=='Follow':
                        if isinstance(postJsonObject['object']['object'], str):
                            if debug:
                                print('DEBUG: "to" field assigned to Follow')
                            postJsonObject['object']['to']= \
                                [postJsonObject['object']['object']]
                if not postJsonObject['object'].get('to'):
                    return
            recipientsObject=postJsonObject['object']
    else: 
        postJsonObject,fieldAdded=addToField('Follow',postJsonObject,debug)
        if not fieldAdded:
            return
        postJsonObject,fieldAdded=addToField('Like',postJsonObject,debug)
        if not fieldAdded:
            return
        recipientsObject=postJsonObject

    recipients=[]
    recipientType=['to','cc']
    for rType in recipientType:
        if not recipientsObject.get(rType):
            continue
        if isinstance(recipientsObject[rType], list):
            if debug:
                pprint(recipientsObject)
                print('recipientsObject: '+str(recipientsObject[rType]))
            for address in recipientsObject[rType]:
                if not address:
                    continue
                if '/' not in address:
                    continue
                if address.endswith('#Public'):
                    continue
                if address.endswith('/followers'):
                    continue
                recipients.append(address)
        elif isinstance(recipientsObject[rType], str):
            address=recipientsObject[rType]
            if address:
                if '/' in address:
                    if address.endswith('#Public'):
                        continue
                    if address.endswith('/followers'):
                        continue
                    recipients.append(address)
    if not recipients:
        if debug:
            print('DEBUG: no individual recipients')
        return
    if debug:
        print('DEBUG: Sending individually addressed posts: '+str(recipients))
    # this is after the message has arrived at the server
    clientToServer=False
    for address in recipients:
        toNickname=getNicknameFromActor(address)
        if not toNickname:
            continue
        toDomain,toPort=getDomainFromActor(address)
        if not toDomain:
            continue
        if debug:
            domainFull=domain
            if port:
                if port!=80 and port!=443:
                    if ':' not in domain:
                        domainFull=domain+':'+str(port)
            toDomainFull=toDomain
            if toPort:
                if toPort!=80 and toPort!=443:
                    if ':' not in toDomain:
                        toDomainFull=toDomain+':'+str(toPort)
            print('DEBUG: Post sending s2s: '+nickname+'@'+domainFull+ \
                  ' to '+toNickname+'@'+toDomainFull)
        cc=[]
        sendSignedJson(postJsonObject,session,baseDir, \
                       nickname,domain,port, \
                       toNickname,toDomain,toPort, \
                       cc,httpPrefix,True,clientToServer, \
                       federationList, \
                       sendThreads,postLog,cachedWebfingers, \
                       personCache,debug,projectVersion)

def hasSharedInbox(session,httpPrefix: str,domain: str) -> bool:
    """Returns true if the given domain has a shared inbox
    """
    wfRequest=webfingerHandle(session,domain+'@'+domain,httpPrefix,{}, \
                              None,__version__)
    if wfRequest:
        if not wfRequest.get('errors'):
            return True
    return False

def sendToFollowers(session,baseDir: str, \
                    nickname: str, domain: str, port: int, \
                    httpPrefix: str,federationList: [], \
                    sendThreads: [],postLog: [], \
                    cachedWebfingers: {},personCache: {}, \
                    postJsonObject: {},debug: bool, \
                    projectVersion: str) -> None:
    """sends a post to the followers of the given nickname
    """
    print('sendToFollowers')
    if not session:
        print('WARN: No session for sendToFollowers')
        return
    if not postIsAddressedToFollowers(baseDir,nickname,domain, \
                                      port,httpPrefix,postJsonObject):
        if debug:
            print('Post is not addressed to followers')
        return
    print('Post is addressed to followers')
    
    grouped=groupFollowersByDomain(baseDir,nickname,domain)
    if not grouped:
        if debug:
            print('Post to followers did not resolve any domains')
        return
    print('Post to followers resolved domains')
    print(str(grouped))

    # this is after the message has arrived at the server
    clientToServer=False

    # for each instance
    for followerDomain,followerHandles in grouped.items():
        if debug:
            print('DEBUG: follower handles for '+followerDomain)
            pprint(followerHandles)
        withSharedInbox=hasSharedInbox(session,httpPrefix,followerDomain)
        if debug:
            if withSharedInbox:
                print(followerDomain+' has shared inbox')
            else:
                print(followerDomain+' does not have a shared inbox')

        toPort=port
        index=0
        toDomain=followerHandles[index].split('@')[1]
        if ':' in toDomain:
            toPort=toDomain.split(':')[1]
            toDomain=toDomain.split(':')[0]

        cc=''

        if withSharedInbox:
            toNickname=followerHandles[index].split('@')[0]

            # if there are more than one followers on the domain
            # then send the post to the shared inbox
            if len(followerHandles)>1:
                toNickname='inbox'

            if toNickname!='inbox' and postJsonObject.get('type'):
                if postJsonObject['type']=='Update':
                    if postJsonObject.get('object'):
                        if isinstance(postJsonObject['object'], dict):
                            if postJsonObject['object'].get('type'):
                                if postJsonObject['object']['type']=='Person' or \
                                   postJsonObject['object']['type']=='Application' or \
                                   postJsonObject['object']['type']=='Group' or \
                                   postJsonObject['object']['type']=='Service':
                                    print('Sending profile update to shared inbox of '+toDomain)
                                    toNickname='inbox'
            
            if debug:
                print('DEBUG: Sending from '+nickname+'@'+domain+ \
                      ' to '+toNickname+'@'+toDomain)
            sendSignedJson(postJsonObject,session,baseDir, \
                           nickname,domain,port, \
                           toNickname,toDomain,toPort, \
                           cc,httpPrefix,True,clientToServer, \
                           federationList, \
                           sendThreads,postLog,cachedWebfingers, \
                           personCache,debug,projectVersion)
        else:
            # send to individual followers without using a shared inbox
            for handle in followerHandles:
                if debug:
                    print('DEBUG: Sending to '+handle)
                toNickname=handle.split('@')[0]
                
                if debug:
                    if postJsonObject['type']!='Update':
                        print('DEBUG: Sending from '+ \
                              nickname+'@'+domain+' to '+ \
                              toNickname+'@'+toDomain)
                    else:
                        print('DEBUG: Sending profile update from '+ \
                              nickname+'@'+domain+' to '+ \
                              toNickname+'@'+toDomain)

                sendSignedJson(postJsonObject,session,baseDir, \
                               nickname,domain,port, \
                               toNickname,toDomain,toPort, \
                               cc,httpPrefix,True,clientToServer, \
                               federationList, \
                               sendThreads,postLog,cachedWebfingers, \
                               personCache,debug,projectVersion)
                
        time.sleep(4)

    if debug:
        print('DEBUG: End of sendToFollowers')

def sendToFollowersThread(session,baseDir: str, \
                          nickname: str,domain: str,port: int, \
                          httpPrefix: str,federationList: [], \
                          sendThreads: [],postLog: [], \
                          cachedWebfingers: {},personCache: {}, \
                          postJsonObject: {},debug: bool, \
                          projectVersion: str):
    """Returns a thread used to send a post to followers
    """
    sendThread= \
        threadWithTrace(target=sendToFollowers, \
                        args=(session,baseDir, \
                              nickname,domain,port, \
                              httpPrefix,federationList, \
                              sendThreads,postLog, \
                              cachedWebfingers,personCache, \
                              postJsonObject.copy(),debug, \
                              projectVersion),daemon=True)
    sendThread.start()
    return sendThread

def createInbox(recentPostsCache: {}, \
                session,baseDir: str,nickname: str,domain: str,port: int,httpPrefix: str, \
                itemsPerPage: int,headerOnly: bool,ocapAlways: bool,pageNumber=None) -> {}:
    return createBoxIndexed(recentPostsCache, \
                            session,baseDir,'inbox',nickname,domain,port,httpPrefix, \
                            itemsPerPage,headerOnly,True,ocapAlways,pageNumber)

def createBookmarksTimeline(session,baseDir: str,nickname: str,domain: str,port: int,httpPrefix: str, \
                            itemsPerPage: int,headerOnly: bool,ocapAlways: bool,pageNumber=None) -> {}:
    return createBoxIndexed({},session,baseDir,'tlbookmarks',nickname,domain,port,httpPrefix, \
                            itemsPerPage,headerOnly,True,ocapAlways,pageNumber)

def createDMTimeline(session,baseDir: str,nickname: str,domain: str,port: int,httpPrefix: str, \
                 itemsPerPage: int,headerOnly: bool,ocapAlways: bool,pageNumber=None) -> {}:
    return createBoxIndexed({},session,baseDir,'dm',nickname,domain,port,httpPrefix, \
                            itemsPerPage,headerOnly,True,ocapAlways,pageNumber)

def createRepliesTimeline(session,baseDir: str,nickname: str,domain: str,port: int,httpPrefix: str, \
                          itemsPerPage: int,headerOnly: bool,ocapAlways: bool,pageNumber=None) -> {}:
    return createBoxIndexed({},session,baseDir,'tlreplies',nickname,domain,port,httpPrefix, \
                            itemsPerPage,headerOnly,True,ocapAlways,pageNumber)

def createMediaTimeline(session,baseDir: str,nickname: str,domain: str,port: int,httpPrefix: str, \
                        itemsPerPage: int,headerOnly: bool,ocapAlways: bool,pageNumber=None) -> {}:
    return createBoxIndexed({},session,baseDir,'tlmedia',nickname,domain,port,httpPrefix, \
                            itemsPerPage,headerOnly,True,ocapAlways,pageNumber)

def createOutbox(session,baseDir: str,nickname: str,domain: str,port: int,httpPrefix: str, \
                 itemsPerPage: int,headerOnly: bool,authorized: bool,pageNumber=None) -> {}:
    return createBoxIndexed({},session,baseDir,'outbox',nickname,domain,port,httpPrefix, \
                            itemsPerPage,headerOnly,authorized,False,pageNumber)

def createModeration(baseDir: str,nickname: str,domain: str,port: int, \
                     httpPrefix: str, \
                     itemsPerPage: int,headerOnly: bool, \
                     ocapAlways: bool,pageNumber=None) -> {}:
    boxDir = createPersonDir(nickname,domain,baseDir,'inbox')
    boxname='moderation'

    if port:
        if port!=80 and port!=443:
            if ':' not in domain:
                domain=domain+':'+str(port)

    if not pageNumber:
        pageNumber=1

    pageStr='?page='+str(pageNumber)
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

    if isModerator(baseDir,nickname):
        moderationIndexFile=baseDir+'/accounts/moderation.txt'
        if os.path.isfile(moderationIndexFile):
            with open(moderationIndexFile, "r") as f:
                lines = f.readlines()
            boxHeader['totalItems']=len(lines)
            if headerOnly:
                return boxHeader

            pageLines=[]
            if len(lines)>0:
                endLineNumber=len(lines)-1-int(itemsPerPage*pageNumber)
                if endLineNumber<0:
                    endLineNumber=0
                startLineNumber=len(lines)-1-int(itemsPerPage*(pageNumber-1))
                if startLineNumber<0:
                    startLineNumber=0
                lineNumber=startLineNumber
                while lineNumber>=endLineNumber:
                    pageLines.append(lines[lineNumber].strip('\n'))
                    lineNumber-=1

            for postUrl in pageLines:
                postFilename=boxDir+'/'+postUrl.replace('/','#')+'.json'
                if os.path.isfile(postFilename):
                    postJsonObject=loadJson(postFilename)
                    if postJsonObject:
                        boxItems['orderedItems'].append(postJsonObject)

    if headerOnly:
        return boxHeader
    return boxItems

def getStatusNumberFromPostFilename(filename) -> int:
    """Gets the status number from a post filename
    eg. https:##testdomain.com:8085#users#testuser567#statuses#1562958506952068.json
    returns 156295850695206
    """
    if '#statuses#' not in filename:
        return None
    return int(filename.split('#')[-1].replace('.json',''))

def isDM(postJsonObject: {}) -> bool:
    """Returns true if the given post is a DM
    """
    if postJsonObject['type']!='Create':
        return False
    if not postJsonObject.get('object'):
        return False
    if not isinstance(postJsonObject['object'], dict):
        return False
    if postJsonObject['object']['type']!='Note':
        return False
    if postJsonObject['object'].get('moderationStatus'):
        return False
    fields=['to','cc']
    for f in fields:        
        if not postJsonObject['object'].get(f):
            continue
        for toAddress in postJsonObject['object'][f]:
            if toAddress.endswith('#Public'):
                return False
            if toAddress.endswith('followers'):
                return False
    return True

def isImageMedia(session,baseDir: str,httpPrefix: str, \
                 nickname: str,domain: str,postJsonObject: {}) -> bool:
    """Returns true if the given post has attached image media
    """
    if postJsonObject['type']=='Announce':
        postJsonAnnounce= \
            downloadAnnounce(session,baseDir,httpPrefix, \
                             nickname,domain,postJsonObject,__version__)
        if postJsonAnnounce:
            postJsonObject=postJsonAnnounce
    if postJsonObject['type']!='Create':
        return False
    if not postJsonObject.get('object'):
        return False
    if not isinstance(postJsonObject['object'], dict):
        return False
    if postJsonObject['object'].get('moderationStatus'):
        return False
    if postJsonObject['object']['type']!='Note':
        return False
    if not postJsonObject['object'].get('attachment'):
        return False
    if not isinstance(postJsonObject['object']['attachment'], list):
        return False
    for attach in postJsonObject['object']['attachment']:
        if attach.get('mediaType') and attach.get('url'):
            if attach['mediaType'].startswith('image/') or \
               attach['mediaType'].startswith('audio/') or \
               attach['mediaType'].startswith('video/'):
                return True
    return False

def isReply(postJsonObject: {},actor: str) -> bool:
    """Returns true if the given post is a reply to the given actor
    """
    if postJsonObject['type']!='Create':
        return False
    if not postJsonObject.get('object'):
        return False
    if not isinstance(postJsonObject['object'], dict):
        return False
    if postJsonObject['object'].get('moderationStatus'):
        return False
    if postJsonObject['object']['type']!='Note':
        return False
    if postJsonObject['object'].get('inReplyTo'):
        if postJsonObject['object']['inReplyTo'].startswith(actor):
            return True        
    if not postJsonObject['object'].get('tag'):
        return False
    if not isinstance(postJsonObject['object']['tag'], list):
        return False
    for tag in postJsonObject['object']['tag']:
        if not tag.get('type'):
            continue
        if tag['type']=='Mention':
            if not tag.get('href'):
                continue
            if actor in tag['href']:
                return True
    return False

def createBoxIndex(boxDir: str,postsInBoxDict: {}) -> int:
    """ Creates an index for the given box
    """
    postsCtr=0
    postsInPersonInbox=os.scandir(boxDir)
    for postFilename in postsInPersonInbox:
        postFilename=postFilename.name
        if not postFilename.endswith('.json'):
            continue
        # extract the status number
        statusNumber=getStatusNumberFromPostFilename(postFilename)
        if statusNumber:
            postsInBoxDict[statusNumber]=os.path.join(boxDir, postFilename)
            postsCtr+=1
    return postsCtr

def createSharedInboxIndex(baseDir: str,sharedBoxDir: str, \
                           postsInBoxDict: {},postsCtr: int, \
                           nickname: str,domain: str, \
                           ocapAlways: bool) -> int:
    """ Creates an index for the given shared inbox
    """
    handle=nickname+'@'+domain
    followingFilename=baseDir+'/accounts/'+handle+'/following.txt'
    postsInSharedInbox=os.scandir(sharedBoxDir)
    followingHandles=None
    for postFilename in postsInSharedInbox:        
        postFilename=postFilename.name
        if not postFilename.endswith('.json'):
            continue
        statusNumber=getStatusNumberFromPostFilename(postFilename)
        if not statusNumber:
            continue
                
        sharedInboxFilename=os.path.join(sharedBoxDir, postFilename)
        # get the actor from the shared post
        postJsonObject=loadJson(sharedInboxFilename,0)
        if not postJsonObject:
            print('WARN: json load exception createSharedInboxIndex')
            continue

        actorNickname=getNicknameFromActor(postJsonObject['actor'])
        if not actorNickname:
            continue
        actorDomain,actorPort=getDomainFromActor(postJsonObject['actor'])
        if not actorDomain:
            continue

        # is the actor followed by this account?
        if not followingHandles:
            with open(followingFilename, 'r') as followingFile:
                followingHandles = followingFile.read()
        if actorNickname+'@'+actorDomain not in followingHandles:
            continue

        if ocapAlways:
            capsList=None
            # Note: should this be in the Create or the object of a post?
            if postJsonObject.get('capability'):
                if isinstance(postJsonObject['capability'], list):                                
                    capsList=postJsonObject['capability']

            # Have capabilities been granted for the sender?
            ocapFilename= \
                baseDir+'/accounts/'+handle+'/ocap/granted/'+ \
                postJsonObject['actor'].replace('/','#')+'.json'
            if not os.path.isfile(ocapFilename):
                continue

            # read the capabilities id
            ocapJson=loadJson(ocapFilename,0)
            if not ocapJson:
                print('WARN: json load exception createSharedInboxIndex')
            else:
                if ocapJson.get('id'):
                    if ocapJson['id'] in capsList:                                    
                        postsInBoxDict[statusNumber]=sharedInboxFilename
                        postsCtr+=1
        else:
            postsInBoxDict[statusNumber]=sharedInboxFilename
            postsCtr+=1
    return postsCtr

def addPostStringToTimeline(postStr: str,boxname: str, \
                            postsInBox: [],boxActor: str) -> bool:
    """ is this a valid timeline post?
    """
    # must be a "Note" or "Announce" type
    if '"Note"' in postStr or '"Announce"' in postStr or \
       ('"Question"' in postStr and ('"Create"' in postStr or '"Update"' in postStr)):

        if boxname=='dm':
            if '#Public' in postStr or '/followers' in postStr:
                return False
        elif boxname=='tlreplies':
            if boxActor not in postStr:
                return False
        elif boxname=='tlmedia':
            if '"Create"' in postStr:
                if 'mediaType' not in postStr or 'image/' not in postStr:
                    return False
        # add the post to the dictionary
        postsInBox.append(postStr)
        return True
    return False

def addPostToTimeline(filePath: str,boxname: str, \
                      postsInBox: [],boxActor: str) -> bool:
    """ Reads a post from file and decides whether it is valid
    """
    with open(filePath, 'r') as postFile:
        postStr = postFile.read()
        return addPostStringToTimeline(postStr,boxname,postsInBox,boxActor)
    return False

def createBoxIndexed(recentPostsCache: {}, \
                     session,baseDir: str,boxname: str, \
                     nickname: str,domain: str,port: int,httpPrefix: str, \
                     itemsPerPage: int,headerOnly: bool,authorized :bool, \
                     ocapAlways: bool,pageNumber=None) -> {}:
    """Constructs the box feed for a person with the given nickname
    """
    if not authorized or not pageNumber:
        pageNumber=1

    if boxname!='inbox' and boxname!='dm' and \
       boxname!='tlreplies' and boxname!='tlmedia' and \
       boxname!='outbox' and boxname!='tlbookmarks':
        return None

    if boxname!='dm' and boxname!='tlreplies' and \
       boxname!='tlmedia' and boxname!='tlbookmarks':
        boxDir = createPersonDir(nickname,domain,baseDir,boxname)
    else:
        # extract DMs or replies or media from the inbox
        boxDir = createPersonDir(nickname,domain,baseDir,'inbox')

    announceCacheDir=baseDir+'/cache/announce/'+nickname

    sharedBoxDir=None
    if boxname=='inbox' or boxname=='tlreplies' or \
       boxname=='tlmedia':
        sharedBoxDir = createPersonDir('inbox',domain,baseDir,boxname)

    # bookmarks timeline is like the inbox but has its own separate index
    indexBoxName=boxname
    if boxname=='tlbookmarks':
        indexBoxName='bookmarks'
    elif boxname=='dm':
        indexBoxName='dm'
    elif boxname=='tlreplies':
        indexBoxName='tlreplies'
    elif boxname=='tlmedia':
        indexBoxName='tlmedia'

    if port:
        if port!=80 and port!=443:
            if ':' not in domain:
                domain=domain+':'+str(port)

    boxActor=httpPrefix+'://'+domain+'/users/'+nickname
                
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

    postsInBox=[]

    indexFilename=baseDir+'/accounts/'+nickname+'@'+domain+'/'+indexBoxName+'.index'
    postsCtr=0
    if os.path.isfile(indexFilename):
        maxPostCtr=itemsPerPage*pageNumber
        with open(indexFilename, 'r') as indexFile:
            while postsCtr<maxPostCtr:
                postFilename=indexFile.readline()

                if not postFilename:
                    postsCtr+=1
                    continue

                # Skip through any posts previous to the current page
                if postsCtr<int((pageNumber-1)*itemsPerPage):                    
                    postsCtr+=1
                    continue

                # if this is a full path then remove the directories
                if '/' in postFilename:
                    postFilename=postFilename.split('/')[-1]

                # filename of the post without any extension or path
                # This should also correspond to any index entry in the posts cache
                postUrl=postFilename.replace('\n','').replace('.json','').strip()

                postAdded=False
                # is the post cached in memory?
                if recentPostsCache.get('index'):
                    if postUrl in recentPostsCache['index']:
                        if recentPostsCache['json'].get(postUrl):
                            addPostStringToTimeline(recentPostsCache['json'][postUrl], \
                                                    boxname,postsInBox,boxActor)
                            postAdded=True

                if not postAdded:
                    # read the post from file
                    fullPostFilename= \
                        locatePost(baseDir,nickname,domain,postUrl,False)
                    if fullPostFilename:
                        addPostToTimeline(fullPostFilename,boxname,postsInBox,boxActor)
                    else:
                        print('WARN: unable to locate post '+postUrl)

                postsCtr+=1

    # Generate first and last entries within header
    if postsCtr>0:
        lastPage=int(postsCtr/itemsPerPage)
        if lastPage<1:
            lastPage=1
        boxHeader['last']= \
            httpPrefix+'://'+domain+'/users/'+nickname+'/'+boxname+'?page='+str(lastPage)

    if headerOnly:
        boxHeader['totalItems']=len(postsInBox)
        prevPageStr='true'
        if pageNumber>1:
            prevPageStr=str(pageNumber-1)
        boxHeader['prev']= \
            httpPrefix+'://'+domain+'/users/'+nickname+'/'+boxname+'?page='+prevPageStr

        nextPageStr=str(pageNumber+1)
        boxHeader['next']= \
            httpPrefix+'://'+domain+'/users/'+nickname+'/'+boxname+'?page='+nextPageStr
        return boxHeader

    for postStr in postsInBox:
        p=None
        try:
            p=json.loads(postStr)
        except:
            continue

        # remove any capability so that it's not displayed
        if p.get('capability'):
            del p['capability']

        # Don't show likes, replies or shares (announces) to unauthorized viewers
        if not authorized:
            if p.get('object'):
                if isinstance(p['object'], dict):                                
                    if p['object'].get('likes'):
                        p['likes']={'items': []}
                    if p['object'].get('replies'):
                        p['replies']={}
                    if p['object'].get('shares'):
                        p['shares']={}
                    if p['object'].get('bookmarks'):
                        p['bookmarks']={}

        boxItems['orderedItems'].append(p)

    return boxItems

def expireCache(baseDir: str,personCache: {}, \
                httpPrefix: str,archiveDir: str,maxPostsInBox=32000):
    """Thread used to expire actors from the cache and archive old posts
    """
    while True:
        # once per day
        time.sleep(60*60*24)
        expirePersonCache(basedir,personCache)
        archivePosts(baseDir,httpPrefix,archiveDir,maxPostsInBox)

def archivePosts(baseDir: str,httpPrefix: str,archiveDir: str, \
                 maxPostsInBox=32000) -> None:
    """Archives posts for all accounts
    """
    if archiveDir:
        if not os.path.isdir(archiveDir):
            os.mkdir(archiveDir)
    if archiveDir:
        if not os.path.isdir(archiveDir+'/accounts'):
            os.mkdir(archiveDir+'/accounts')

    for subdir, dirs, files in os.walk(baseDir+'/accounts'):
        for handle in dirs:
            if '@' in handle:
                nickname=handle.split('@')[0]
                domain=handle.split('@')[1]
                archiveSubdir=None
                if archiveDir:
                    if not os.path.isdir(archiveDir+'/accounts/'+handle):
                        os.mkdir(archiveDir+'/accounts/'+handle)    
                    if not os.path.isdir(archiveDir+'/accounts/'+handle+'/inbox'):
                        os.mkdir(archiveDir+'/accounts/'+handle+'/inbox')    
                    if not os.path.isdir(archiveDir+'/accounts/'+handle+'/outbox'):
                        os.mkdir(archiveDir+'/accounts/'+handle+'/outbox')
                    archiveSubdir=archiveDir+'/accounts/'+handle+'/inbox'
                archivePostsForPerson(httpPrefix,nickname,domain,baseDir, \
                                      'inbox',archiveSubdir, \
                                      maxPostsInBox)
                if archiveDir:
                    archiveSubdir=archiveDir+'/accounts/'+handle+'/outbox'
                archivePostsForPerson(httpPrefix,nickname,domain,baseDir, \
                                      'outbox',archiveSubdir, \
                                      maxPostsInBox)

def archivePostsForPerson(httpPrefix: str,nickname: str,domain: str,baseDir: str, \
                          boxname: str,archiveDir: str,maxPostsInBox=32000) -> None:
    """Retain a maximum number of posts within the given box
    Move any others to an archive directory
    """
    if boxname!='inbox' and boxname!='outbox':
        return
    if archiveDir:
        if not os.path.isdir(archiveDir):
            os.mkdir(archiveDir)    
    boxDir = createPersonDir(nickname,domain,baseDir,boxname)
    postsInBox=os.scandir(boxDir)
    noOfPosts=0
    for f in postsInBox:
        noOfPosts+=1
    if noOfPosts<=maxPostsInBox:
        return

    # remove entries from the index
    handle=nickname+'@'+domain
    indexFilename=baseDir+'/accounts/'+handle+'/'+boxname+'.index'
    if os.path.isfile(indexFilename):
        indexCtr=0
        # get the existing index entries as a string
        newIndex=''
        with open(indexFilename, 'r') as indexFile:
            for postId in indexFile:
                newIndex+=postId
                indexCtr+=1
                if indexCtr>=maxPostsInBox:
                    break
        # save the new index file
        if len(newIndex)>0:
            indexFile=open(indexFilename,'w+')
            if indexFile:
                indexFile.write(newIndex)
                indexFile.close()

    postsInBoxDict={}
    postsCtr=0
    postsInBox=os.scandir(boxDir)
    for postFilename in postsInBox:
        postFilename=postFilename.name
        if not postFilename.endswith('.json'):
            continue
        # Time of file creation
        fullFilename=os.path.join(boxDir,postFilename)
        if os.path.isfile(fullFilename):
            content=open(fullFilename).read()
            if '"published":' in content:
                publishedStr=content.split('"published":')[1]
                if '"' in publishedStr:
                    publishedStr=publishedStr.split('"')[1]
                    if publishedStr.endswith('Z'):
                        postsInBoxDict[publishedStr]=postFilename
                        postsCtr+=1

    noOfPosts=postsCtr
    if noOfPosts<=maxPostsInBox:
        return

    # sort the list in ascending order of date
    postsInBoxSorted= \
        OrderedDict(sorted(postsInBoxDict.items(),reverse=False))

    # directory containing cached html posts
    postCacheDir=boxDir.replace('/'+boxname,'/postcache')

    for publishedStr,postFilename in postsInBoxSorted.items():
        filePath=os.path.join(boxDir,postFilename)        
        if not os.path.isfile(filePath):
            continue
        if archiveDir:
            repliesPath=filePath.replace('.json','.replies')
            archivePath=os.path.join(archiveDir,postFilename)
            os.rename(filePath,archivePath)
            if os.path.isfile(repliesPath):
                os.rename(repliesPath,archivePath)
        else:
            deletePost(baseDir,httpPrefix,nickname,domain,filePath,False)

        # remove cached html posts
        postCacheFilename= \
            os.path.join(postCacheDir,postFilename).replace('.json','.html')
        if os.path.isfile(postCacheFilename):
            os.remove(postCacheFilename)

        noOfPosts-=1
        if noOfPosts<=maxPostsInBox:
            break

def getPublicPostsOfPerson(baseDir: str,nickname: str,domain: str, \
                           raw: bool,simple: bool,useTor: bool, \
                           port: int,httpPrefix: str, \
                           debug: bool,projectVersion: str) -> None:
    """ This is really just for test purposes
    """
    session = createSession(useTor)
    personCache={}
    cachedWebfingers={}
    federationList=[]

    domainFull=domain
    if port:
        if port!=80 and port!=443:
            if ':' not in domain:
                domainFull=domain+':'+str(port)
    handle=httpPrefix+"://"+domainFull+"/@"+nickname
    wfRequest = \
        webfingerHandle(session,handle,httpPrefix,cachedWebfingers, \
                        domain,projectVersion)
    if not wfRequest:
        sys.exit()

    personUrl,pubKeyId,pubKey,personId,shaedInbox,capabilityAcquisition,avatarUrl,displayName= \
        getPersonBox(baseDir,session,wfRequest,personCache, \
                     projectVersion,httpPrefix,nickname,domain,'outbox')
    wfResult = json.dumps(wfRequest, indent=2, sort_keys=False)

    maxMentions=10
    maxEmoji=10
    maxAttachments=5
    userPosts = \
        getPosts(session,personUrl,30,maxMentions,maxEmoji, \
                 maxAttachments,federationList, \
                 personCache,raw,simple,debug, \
                 projectVersion,httpPrefix,domain)
    #print(str(userPosts))

def sendCapabilitiesUpdate(session,baseDir: str,httpPrefix: str, \
                           nickname: str,domain: str,port: int, \
                           followerUrl,updateCaps: [], \
                           sendThreads: [],postLog: [], \
                           cachedWebfingers: {},personCache: {}, \
                           federationList :[],debug :bool, \
                           projectVersion: str) -> int:
    """When the capabilities for a follower are changed this
    sends out an update. followerUrl is the actor of the follower.
    """
    updateJson=capabilitiesUpdate(baseDir,httpPrefix, \
                                  nickname,domain,port, \
                                  followerUrl, \
                                  updateCaps)

    if not updateJson:
        return 1

    if debug:
        pprint(updateJson)
        print('DEBUG: sending capabilities update from '+ \
              nickname+'@'+domain+' port '+ str(port) + \
              ' to '+followerUrl)

    clientToServer=False
    followerNickname=getNicknameFromActor(followerUrl)
    if not followerNickname:
        print('WARN: unable to find nickname in '+followerUrl)
        return 1
    followerDomain,followerPort=getDomainFromActor(followerUrl)
    return sendSignedJson(updateJson,session,baseDir, \
                          nickname,domain,port, \
                          followerNickname,followerDomain,followerPort, '', \
                          httpPrefix,True,clientToServer, \
                          federationList, \
                          sendThreads,postLog,cachedWebfingers, \
                          personCache,debug,projectVersion)

def populateRepliesJson(baseDir: str,nickname: str,domain: str, \
                        postRepliesFilename: str,authorized: bool, \
                        repliesJson: {}) -> None:
    # populate the items list with replies
    repliesBoxes=['outbox','inbox']
    with open(postRepliesFilename,'r') as repliesFile: 
        for messageId in repliesFile:
            replyFound=False
            # examine inbox and outbox
            for boxname in repliesBoxes:
                searchFilename= \
                    baseDir+ \
                    '/accounts/'+nickname+'@'+ \
                    domain+'/'+ \
                    boxname+'/'+ \
                    messageId.replace('\n','').replace('/','#')+'.json'
                if os.path.isfile(searchFilename):
                    if authorized or \
                       'https://www.w3.org/ns/activitystreams#Public' in open(searchFilename).read():
                        postJsonObject=loadJson(searchFilename)
                        if postJsonObject:
                            if postJsonObject['object'].get('cc'):                                                            
                                if authorized or \
                                   ('https://www.w3.org/ns/activitystreams#Public' in postJsonObject['object']['to'] or \
                                    'https://www.w3.org/ns/activitystreams#Public' in postJsonObject['object']['cc']):
                                    repliesJson['orderedItems'].append(postJsonObject)
                                    replyFound=True
                            else:
                                if authorized or \
                                   'https://www.w3.org/ns/activitystreams#Public' in postJsonObject['object']['to']:
                                    repliesJson['orderedItems'].append(postJsonObject)
                                    replyFound=True
                    break
            # if not in either inbox or outbox then examine the shared inbox
            if not replyFound:
                searchFilename= \
                    baseDir+ \
                    '/accounts/inbox@'+ \
                    domain+'/inbox/'+ \
                    messageId.replace('\n','').replace('/','#')+'.json'
                if os.path.isfile(searchFilename):
                    if authorized or \
                       'https://www.w3.org/ns/activitystreams#Public' in open(searchFilename).read():
                        # get the json of the reply and append it to the collection
                        postJsonObject=loadJson(searchFilename)
                        if postJsonObject:
                            if postJsonObject['object'].get('cc'):                                                            
                                if authorized or \
                                   ('https://www.w3.org/ns/activitystreams#Public' in postJsonObject['object']['to'] or \
                                    'https://www.w3.org/ns/activitystreams#Public' in postJsonObject['object']['cc']):
                                    repliesJson['orderedItems'].append(postJsonObject)
                            else:
                                if authorized or \
                                   'https://www.w3.org/ns/activitystreams#Public' in postJsonObject['object']['to']:
                                    repliesJson['orderedItems'].append(postJsonObject)

def rejectAnnounce(announceFilename: str):
    """Marks an announce as rejected
    """
    if not os.path.isfile(announceFilename+'.reject'):
        rejectAnnounceFile=open(announceFilename+'.reject', "w+")
        rejectAnnounceFile.write('\n')
        rejectAnnounceFile.close()

def downloadAnnounce(session,baseDir: str,httpPrefix: str, \
                     nickname: str,domain: str, \
                     postJsonObject: {},projectVersion: str) -> {}:
    """Download the post referenced by an announce
    """
    if not postJsonObject.get('object'):
        return None
    if not isinstance(postJsonObject['object'], str):
        return None

    # get the announced post
    announceCacheDir=baseDir+'/cache/announce/'+nickname
    if not os.path.isdir(announceCacheDir):
        os.mkdir(announceCacheDir)
    announceFilename= \
        announceCacheDir+'/'+postJsonObject['object'].replace('/','#')+'.json'
    print('announceFilename: '+announceFilename)

    if os.path.isfile(announceFilename+'.reject'):
        return None

    if os.path.isfile(announceFilename):
        print('Reading cached Announce content for '+postJsonObject['object'])
        postJsonObject=loadJson(announceFilename)
        if postJsonObject:
            return postJsonObject
    else:
        print('Downloading Announce content for '+postJsonObject['object'])
        asHeader={'Accept': 'application/activity+json; profile="https://www.w3.org/ns/activitystreams"'}
        if '/channel/' in postJsonObject['actor']:
            asHeader={'Accept': 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"'}
        actorNickname=getNicknameFromActor(postJsonObject['actor'])
        actorDomain,actorPort=getDomainFromActor(postJsonObject['actor'])
        announcedJson= \
            getJson(session,postJsonObject['object'],asHeader, \
                    None,projectVersion,httpPrefix,domain)
                        
        if not announcedJson:
            return None

        if not isinstance(announcedJson, dict):
            print('WARN: announce json is not a dict - '+postJsonObject['object'])
            rejectAnnounce(announceFilename)
            return None        
        if not announcedJson.get('id'):
            rejectAnnounce(announceFilename)
            return None
        if '/statuses/' not in announcedJson['id']:
            rejectAnnounce(announceFilename)
            return None
        if '/users/' not in announcedJson['id'] and \
           '/channel/' not in announcedJson['id'] and \
           '/profile/' not in announcedJson['id']:
            rejectAnnounce(announceFilename)
            return None
        if not announcedJson.get('type'):
            rejectAnnounce(announceFilename)
            #pprint(announcedJson)
            return None
        if announcedJson['type']!='Note':
            rejectAnnounce(announceFilename)
            #pprint(announcedJson)
            return None
                            
        # wrap in create to be consistent with other posts
        announcedJson= \
            outboxMessageCreateWrap(httpPrefix, \
                                    actorNickname,actorDomain,actorPort, \
                                    announcedJson)
        if announcedJson['type']!='Create':
            rejectAnnounce(announceFilename)
            #pprint(announcedJson)
            return None

        # set the id to the original status
        announcedJson['id']=postJsonObject['object']
        announcedJson['object']['id']=postJsonObject['object']
        # check that the repeat isn't for a blocked account
        attributedNickname= \
            getNicknameFromActor(announcedJson['object']['id'])
        attributedDomain,attributedPort= \
            getDomainFromActor(announcedJson['object']['id'])
        if attributedNickname and attributedDomain:
            if attributedPort:
                if attributedPort!=80 and attributedPort!=443:
                    attributedDomain=attributedDomain+':'+str(attributedPort)
            if isBlocked(baseDir,nickname,domain, \
                         attributedNickname,attributedDomain):
                rejectAnnounce(announceFilename)
                return None
        postJsonObject=announcedJson
        if saveJson(postJsonObject,announceFilename):
            return postJsonObject
    return None

def mutePost(baseDir: str,nickname: str,domain: str,postId: str, \
             recentPostsCache: {}) -> None:
    """ Mutes the given post
    """
    postFilename=locatePost(baseDir,nickname,domain,postId)
    if not postFilename:
        return
    postJsonObject=loadJson(postFilename)
    if not postJsonObject:
        return

    print('MUTE: '+postFilename)
    muteFile=open(postFilename+'.muted', "w")
    if muteFile:
        muteFile.write('\n')
        muteFile.close()

    # remove cached posts so that the muted version gets created
    cachedPostFilename= \
        getCachedPostFilename(baseDir,nickname,domain,postJsonObject)
    if cachedPostFilename:
        if os.path.isfile(cachedPostFilename):
            os.remove(cachedPostFilename)

    # if the post is in the recent posts cache then mark it as muted
    if recentPostsCache.get('index'):
        postId=postJsonObject['id'].replace('/activity','').replace('/','#')
        if postId in recentPostsCache['index']:
            print('MUTE: '+postId+' is in recent posts cache')
            if recentPostsCache['json'].get(postId):
                postJsonObject['muted']=True
                recentPostsCache['json'][postId]=json.dumps(postJsonObject)
                print('MUTE: '+postId+' marked as muted in recent posts cache')

def unmutePost(baseDir: str,nickname: str,domain: str,postId: str, \
               recentPostsCache: {}) -> None:
    """ Unmutes the given post
    """
    postFilename=locatePost(baseDir,nickname,domain,postId)
    if not postFilename:
        return
    postJsonObject=loadJson(postFilename)
    if not postJsonObject:
        return

    print('UNMUTE: '+postFilename)
    muteFilename=postFilename+'.muted'
    if os.path.isfile(muteFilename):
        os.remove(muteFilename)

    # remove cached posts so that it gets recreated
    cachedPostFilename= \
        getCachedPostFilename(baseDir,nickname,domain,postJsonObject)
    if cachedPostFilename:
        if os.path.isfile(cachedPostFilename):
            os.remove(cachedPostFilename)
    removePostFromCache(postJsonObject,recentPostsCache)
