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
import time
import json
import commentjson
from shutil import copyfile
from utils import urlPermitted
from utils import createInboxQueueDir
from utils import getStatusNumber
from utils import getDomainFromActor
from utils import getNicknameFromActor
from utils import domainPermitted
from utils import locatePost
from utils import deletePost
from utils import removeAttachment
from httpsig import verifyPostHeaders
from session import createSession
from session import getJson
from follow import receiveFollowRequest
from follow import getFollowersOfActor
from pprint import pprint
from cache import getPersonFromCache
from cache import storePersonInCache
from acceptreject import receiveAcceptReject
from capabilities import getOcapFilename
from capabilities import CapablePost
from capabilities import capabilitiesReceiveUpdate
from like import updateLikesCollection
from like import undoLikesCollectionEntry
from blocking import isBlocked
from filters import isFiltered

def getPersonPubKey(session,personUrl: str,personCache: {},debug: bool) -> str:
    if not personUrl:
        return None
    personUrl=personUrl.replace('#main-key','')
    personJson = getPersonFromCache(personUrl,personCache)
    if not personJson:
        if debug:
            print('DEBUG: Obtaining public key for '+personUrl)
        asHeader = {'Accept': 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"'}
        personJson = getJson(session,personUrl,asHeader,None)
        if not personJson:
            return None
    pubKey=None
    if personJson.get('publicKey'):
        if personJson['publicKey'].get('publicKeyPem'):
            pubKey=personJson['publicKey']['publicKeyPem']
    else:
        if personJson.get('publicKeyPem'):
            pubKey=personJson['publicKeyPem']

    if not pubKey:
        if debug:
            print('DEBUG: Public key not found for '+personUrl)

    storePersonInCache(personUrl,personJson,personCache)
    return pubKey

def inboxMessageHasParams(messageJson: {}) -> bool:
    """Checks whether an incoming message contains expected parameters
    """
    expectedParams=['type','actor','object']
    for param in expectedParams:
        if not messageJson.get(param):
            return False
    if not messageJson.get('to'):
        allowedWithoutToParam=['Follow','Request','Capability']
        if messageJson['type'] not in allowedWithoutToParam:
            return False
    return True

def inboxPermittedMessage(domain: str,messageJson: {},federationList: []) -> bool:
    """ check that we are receiving from a permitted domain
    """
    testParam='actor'
    if not messageJson.get(testParam):
        return False
    actor=messageJson[testParam]
    # always allow the local domain
    if domain in actor:
        return True

    if not urlPermitted(actor,federationList,"inbox:write"):
        return False

    if messageJson['type']!='Follow' and \
       messageJson['type']!='Like' and \
       messageJson['type']!='Delete' and \
       messageJson['type']!='Announce':
        if messageJson.get('object'):
            if not isinstance(messageJson['object'], dict):
                return False
            if messageJson['object'].get('inReplyTo'):
                inReplyTo=messageJson['object']['inReplyTo']
                if not urlPermitted(inReplyTo,federationList):
                    return False

    return True

def validPublishedDate(published) -> bool:
    currTime=datetime.datetime.utcnow()
    pubDate=datetime.datetime.strptime(published,"%Y-%m-%dT%H:%M:%SZ")
    daysSincePublished = (currTime - pubTime).days
    if daysSincePublished>30:
        return False
    return True

def savePostToInboxQueue(baseDir: str,httpPrefix: str,nickname: str, domain: str,postJsonObject: {},host: str,headers: str,postPath: str,debug: bool) -> str:
    """Saves the give json to the inbox queue for the person
    keyId specifies the actor sending the post
    """
    if ':' in domain:
        domain=domain.split(':')[0]

    # block at the ealiest stage possible, which means the data
    # isn't written to file
    postNickname=None
    postDomain=None
    if postJsonObject.get('actor'):
        postNickname=getNicknameFromActor(postJsonObject['actor'])
        postDomain,postPort=getDomainFromActor(postJsonObject['actor'])
        if isBlocked(baseDir,nickname,domain,postNickname,postDomain):            
            return None
        if postPort:
            if postPort!=80 and postPort!=443:
                postDomain=postDomain+':'+str(postPort)

        if postJsonObject.get('object'):
            if isinstance(postJsonObject['object'], dict):
                if postJsonObject['object'].get('content'):
                    if isinstance(postJsonObject['object']['content'], str):
                        if isFiltered(baseDir,nickname,domain,postJsonObject['object']['content']):
                            return None

    if postJsonObject.get('id'):
        postId=postJsonObject['id'].replace('/activity','')
    else:
        statusNumber,published = getStatusNumber()
        postId=httpPrefix+'://'+domain+'/users/'+nickname+'/statuses/'+statusNumber
    
    currTime=datetime.datetime.utcnow()
    published=currTime.strftime("%Y-%m-%dT%H:%M:%SZ")

    inboxQueueDir=createInboxQueueDir(nickname,domain,baseDir)

    handle=nickname+'@'+domain
    destination=baseDir+'/accounts/'+handle+'/inbox/'+postId.replace('/','#')+'.json'
    if os.path.isfile(destination):
        if debug:
            print('DEBUG: inbox item already exists')
        return None
    filename=inboxQueueDir+'/'+postId.replace('/','#')+'.json'

    sharedInboxItem=False
    if nickname=='inbox':
        sharedInboxItem=True
        
    newQueueItem = {
        'id': postId,
        'nickname': nickname,
        'domain': domain,
        'postNickname': postNickname,
        'postDomain': postDomain,
        'sharedInbox': sharedInboxItem,
        'published': published,
        'host': host,
        'headers': headers,
        'path': postPath,
        'post': postJsonObject,
        'filename': filename,
        'destination': destination
    }

    if debug:
        print('Inbox queue item created')
        pprint(newQueueItem)
    
    with open(filename, 'w') as fp:
        commentjson.dump(newQueueItem, fp, indent=4, sort_keys=False)
    return filename

def inboxCheckCapabilities(baseDir :str,nickname :str,domain :str, \
                           actor: str,queue: [],queueJson: {}, \
                           capabilityId: str,debug : bool) -> bool:
    if nickname=='inbox':
        return True

    ocapFilename= \
        getOcapFilename(baseDir, \
                        queueJson['nickname'],queueJson['domain'], \
                        actor,'accept')
    if not os.path.isfile(ocapFilename):
        if debug:
            print('DEBUG: capabilities for '+ \
                  actor+' do not exist')
            os.remove(queueFilename)
            queue.pop(0)
            return False

    with open(ocapFilename, 'r') as fp:
        oc=commentjson.load(fp)

    if not oc.get('id'):
        if debug:
            print('DEBUG: capabilities for '+actor+' do not contain an id')
        os.remove(queueFilename)
        queue.pop(0)
        return False

    if oc['id']!=capabilityId:
        if debug:
            print('DEBUG: capability id mismatch')
        os.remove(queueFilename)
        queue.pop(0)
        return False

    if not oc.get('capability'):
        if debug:
            print('DEBUG: missing capability list')
        os.remove(queueFilename)
        queue.pop(0)
        return False

    if not CapablePost(queueJson['post'],oc['capability'],debug):
        if debug:
            print('DEBUG: insufficient capabilities to write to inbox from '+actor)
        os.remove(queueFilename)
        queue.pop(0)
        return False

    if debug:
        print('DEBUG: object capabilities check success')
    return True

def inboxPostRecipientsAdd(baseDir :str,httpPrefix :str,toList :[], \
                           recipientsDict :{}, \
                           domainMatch: str,domain :str, \
                           actor :str,debug: bool) -> bool:
    """Given a list of post recipients (toList) from 'to' or 'cc' parameters
    populate a recipientsDict with the handle and capabilities id for each
    """
    followerRecipients=False
    for recipient in toList:
        # is this a to a local account?
        if domainMatch in recipient:
            # get the handle for the local account
            nickname=recipient.split(domainMatch)[1]
            handle=nickname+'@'+domain
            if os.path.isdir(baseDir+'/accounts/'+handle):
                # are capabilities granted for this account to the
                # sender (actor) of the post?
                ocapFilename=baseDir+'/accounts/'+handle+'/ocap/accept/'+actor.replace('/','#')+'.json'
                if os.path.isfile(ocapFilename):
                    # read the granted capabilities and obtain the id
                    with open(ocapFilename, 'r') as fp:
                        ocapJson=commentjson.load(fp)
                        if ocapJson.get('id'):
                            # append with the capabilities id
                            recipientsDict[handle]=ocapJson['id']
                        else:
                            recipientsDict[handle]=None
                else:
                    if debug:
                        print('DEBUG: '+ocapFilename+' not found')
                    recipientsDict[handle]=None
            else:
                if debug:
                    print('DEBUG: '+baseDir+'/accounts/'+handle+' does not exist')
        else:
            if debug:
                print('DEBUG: '+recipient+' is not local to '+domainMatch)
                print(str(toList))
        if recipient.endswith('followers'):
            if debug:
                print('DEBUG: followers detected as post recipients')
            followerRecipients=True
    return followerRecipients,recipientsDict

def inboxPostRecipients(baseDir :str,postJsonObject :{},httpPrefix :str,domain : str,port :int, debug :bool) -> ([],[]):
    """Returns dictionaries containing the recipients of the given post
    The shared dictionary contains followers
    """
    recipientsDict={}
    recipientsDictFollowers={}

    if not postJsonObject.get('actor'):
        if debug:
            pprint(postJsonObject)
            print('WARNING: inbox post has no actor')
        return recipientsDict,recipientsDictFollowers

    if ':' in domain:
        domain=domain.split(':')[0]
    domainBase=domain
    if port!=80 and port!=443:
        domain=domain+':'+str(port)
    domainMatch='/'+domain+'/users/'

    actor = postJsonObject['actor']
    # first get any specific people which the post is addressed to
    
    followerRecipients=False
    if postJsonObject.get('object'):
        if isinstance(postJsonObject['object'], dict):
            if postJsonObject['object'].get('to'):
                if debug:
                    print('DEBUG: resolving "to"')
                includesFollowers,recipientsDict= \
                    inboxPostRecipientsAdd(baseDir,httpPrefix, \
                                           postJsonObject['object']['to'], \
                                           recipientsDict, \
                                           domainMatch,domainBase, \
                                           actor,debug)
                if includesFollowers:
                    followerRecipients=True
            else:
                if debug:
                    print('DEBUG: inbox post has no "to"')

            if postJsonObject['object'].get('cc'):
                includesFollowers,recipientsDict= \
                    inboxPostRecipientsAdd(baseDir,httpPrefix, \
                                           postJsonObject['object']['cc'], \
                                           recipientsDict, \
                                           domainMatch,domainBase, \
                                           actor,debug)
                if includesFollowers:
                    followerRecipients=True
            else:
                if debug:
                    print('DEBUG: inbox post has no cc')
        else:
            if debug:
                if isinstance(postJsonObject['object'], str):
                    if '/statuses/' in postJsonObject['object']:
                        print('DEBUG: inbox item is a link to a post')
                    else:
                        if '/users/' in postJsonObject['object']:
                            print('DEBUG: inbox item is a link to an actor')

    if postJsonObject.get('to'):
        includesFollowers,recipientsDict= \
            inboxPostRecipientsAdd(baseDir,httpPrefix, \
                                   postJsonObject['to'], \
                                   recipientsDict, \
                                   domainMatch,domainBase, \
                                   actor,debug)
        if includesFollowers:
            followerRecipients=True

    if postJsonObject.get('cc'):
        includesFollowers,recipientsDict= \
            inboxPostRecipientsAdd(baseDir,httpPrefix, \
                                   postJsonObject['cc'], \
                                   recipientsDict, \
                                   domainMatch,domainBase, \
                                   actor,debug)
        if includesFollowers:
            followerRecipients=True

    if not followerRecipients:
        if debug:
            print('DEBUG: no followers were resolved')
        return recipientsDict,recipientsDictFollowers

    # now resolve the followers
    recipientsDictFollowers= \
        getFollowersOfActor(baseDir,actor,debug)

    return recipientsDict,recipientsDictFollowers

def receiveUpdate(session,baseDir: str, \
                  httpPrefix: str,domain :str,port: int, \
                  sendThreads: [],postLog: [],cachedWebfingers: {}, \
                  personCache: {},messageJson: {},federationList: [], \
                  debug : bool) -> bool:
    """Receives an Update activity within the POST section of HTTPServer
    """
    if messageJson['type']!='Update':
        return False
    if not messageJson.get('actor'):
        if debug:
            print('DEBUG: '+messageJson['type']+' has no actor')
        return False
    if not messageJson.get('object'):
        if debug:
            print('DEBUG: '+messageJson['type']+' has no object')
        return False
    if not isinstance(messageJson['object'], dict):
        if debug:
            print('DEBUG: '+messageJson['type']+' object is not a dict')
        return False
    if not messageJson['object'].get('type'):
        if debug:
            print('DEBUG: '+messageJson['type']+' object has no type')
        return False
    if '/users/' not in messageJson['actor']:
        if debug:
            print('DEBUG: "users" missing from actor in '+messageJson['type'])
        return False
    if messageJson['object'].get('capability') and messageJson['object'].get('scope'):
        domain,tempPort=getDomainFromActor(messageJson['object']['scope'])
        nickname=getNicknameFromActor(messageJson['object']['scope'])
        
        if messageJson['object']['type']=='Capability':
            if capabilitiesReceiveUpdate(baseDir,nickname,domain,port,
                                         messageJson['actor'], \
                                         messageJson['object']['id'], \
                                         messageJson['object']['capability'], \
                                         debug):
                if debug:
                    print('DEBUG: An update was received')
                return True            
    return False

def receiveLike(session,handle: str,baseDir: str, \
                httpPrefix: str,domain :str,port: int, \
                sendThreads: [],postLog: [],cachedWebfingers: {}, \
                personCache: {},messageJson: {},federationList: [], \
                debug : bool) -> bool:
    """Receives a Like activity within the POST section of HTTPServer
    """
    if messageJson['type']!='Like':
        return False
    if not messageJson.get('actor'):
        if debug:
            print('DEBUG: '+messageJson['type']+' has no actor')
        return False
    if not messageJson.get('object'):
        if debug:
            print('DEBUG: '+messageJson['type']+' has no object')
        return False
    if not isinstance(messageJson['object'], str):
        if debug:
            print('DEBUG: '+messageJson['type']+' object is not a string')
        return False
    if not messageJson.get('to'):
        if debug:
            print('DEBUG: '+messageJson['type']+' has no "to" list')
        return False
    if '/users/' not in messageJson['actor']:
        if debug:
            print('DEBUG: "users" missing from actor in '+messageJson['type'])
        return False
    if '/statuses/' not in messageJson['object']:
        if debug:
            print('DEBUG: "statuses" missing from object in '+messageJson['type'])
        return False
    if not os.path.isdir(baseDir+'/accounts/'+handle):
        print('DEBUG: unknown recipient of like - '+handle)
    # if this post in the outbox of the person?
    postFilename=locatePost(baseDir,handle.split('@')[0],handle.split('@')[1],messageJson['object'])
    if not postFilename:
        if debug:
            print('DEBUG: post not found in inbox or outbox')
            print(messageJson['object'])
        return True
    if debug:
        print('DEBUG: liked post found in inbox')
    updateLikesCollection(postFilename,messageJson['object'],messageJson['actor'],debug)
    return True

def receiveUndoLike(session,handle: str,baseDir: str, \
                    httpPrefix: str,domain :str,port: int, \
                    sendThreads: [],postLog: [],cachedWebfingers: {}, \
                    personCache: {},messageJson: {},federationList: [], \
                    debug : bool) -> bool:
    """Receives an undo like activity within the POST section of HTTPServer
    """
    if messageJson['type']!='Undo':
        return False
    if not messageJson.get('actor'):
        return False
    if not messageJson.get('object'):
        return False
    if not isinstance(messageJson['object'], dict):
        return False
    if not messageJson['object'].get('type'):
        return False
    if messageJson['object']['type']!='Like':
        return False
    if not messageJson['object'].get('object'):
        if debug:
            print('DEBUG: '+messageJson['type']+' like has no object')
        return False
    if not isinstance(messageJson['object']['object'], str):
        if debug:
            print('DEBUG: '+messageJson['type']+' like object is not a string')
        return False
    if '/users/' not in messageJson['actor']:
        if debug:
            print('DEBUG: "users" missing from actor in '+messageJson['type']+' like')
        return False
    if '/statuses/' not in messageJson['object']['object']:
        if debug:
            print('DEBUG: "statuses" missing from like object in '+messageJson['type'])
        return False
    if not os.path.isdir(baseDir+'/accounts/'+handle):
        print('DEBUG: unknown recipient of undo like - '+handle)
    # if this post in the outbox of the person?
    postFilename=locatePost(baseDir,handle.split('@')[0],handle.split('@')[1],messageJson['object']['object'])
    if not postFilename:
        if debug:
            print('DEBUG: unliked post not found in inbox or outbox')
            print(messageJson['object']['object'])
        return True
    if debug:
        print('DEBUG: liked post found in inbox. Now undoing.')
    undoLikesCollectionEntry(postFilename,messageJson['object'],messageJson['actor'],debug)
    return True

def receiveDelete(session,handle: str,baseDir: str, \
                  httpPrefix: str,domain :str,port: int, \
                  sendThreads: [],postLog: [],cachedWebfingers: {}, \
                  personCache: {},messageJson: {},federationList: [], \
                  debug : bool) -> bool:
    """Receives a Delete activity within the POST section of HTTPServer
    """
    if messageJson['type']!='Delete':
        return False
    if not messageJson.get('actor'):
        if debug:
            print('DEBUG: '+messageJson['type']+' has no actor')
        return False
    if not messageJson.get('object'):
        if debug:
            print('DEBUG: '+messageJson['type']+' has no object')
        return False
    if not isinstance(messageJson['object'], str):
        if debug:
            print('DEBUG: '+messageJson['type']+' object is not a string')
        return False
    if not messageJson.get('to'):
        if debug:
            print('DEBUG: '+messageJson['type']+' has no "to" list')
        return False
    if '/users/' not in messageJson['actor']:
        if debug:
            print('DEBUG: "users" missing from actor in '+messageJson['type'])
        return False
    if '/statuses/' not in messageJson['object']:
        if debug:
            print('DEBUG: "statuses" missing from object in '+messageJson['type'])
        return False
    if messageJson['actor'] not in messageJson['object']:
        if debug:
            print('DEBUG: actor is not the owner of the post to be deleted')    
    if not os.path.isdir(baseDir+'/accounts/'+handle):
        print('DEBUG: unknown recipient of like - '+handle)
    # if this post in the outbox of the person?
    postFilename=locatePost(baseDir,handle.split('@')[0],handle.split('@')[1],messageJson['object'])
    if not postFilename:
        if debug:
            print('DEBUG: delete post not found in inbox or outbox')
            print(messageJson['object'])
        return True
    deletePost(baseDir,httpPrefix,handle.split('@')[0],handle.split('@')[1],postFilename,debug)
    if debug:
        print('DEBUG: post deleted - '+postFilename)
    return True

def receiveAnnounce(session,handle: str,baseDir: str, \
                    httpPrefix: str,domain :str,port: int, \
                    sendThreads: [],postLog: [],cachedWebfingers: {}, \
                    personCache: {},messageJson: {},federationList: [], \
                    debug : bool) -> bool:
    """Receives an announce activity within the POST section of HTTPServer
    """
    if messageJson['type']!='Announce':
        return False
    if not messageJson.get('actor'):
        if debug:
            print('DEBUG: '+messageJson['type']+' has no actor')
        return False
    if not messageJson.get('object'):
        if debug:
            print('DEBUG: '+messageJson['type']+' has no object')
        return False
    if not isinstance(messageJson['object'], str):
        if debug:
            print('DEBUG: '+messageJson['type']+' object is not a string')
        return False
    if not messageJson.get('to'):
        if debug:
            print('DEBUG: '+messageJson['type']+' has no "to" list')
        return False
    if '/users/' not in messageJson['actor']:
        if debug:
            print('DEBUG: "users" missing from actor in '+messageJson['type'])
        return False
    if '/statuses/' not in messageJson['object']:
        if debug:
            print('DEBUG: "statuses" missing from object in '+messageJson['type'])
        return False
    if not os.path.isdir(baseDir+'/accounts/'+handle):
        print('DEBUG: unknown recipient of announce - '+handle)
    # if this post in the outbox of the person?
    postFilename=locatePost(baseDir,handle.split('@')[0],handle.split('@')[1],messageJson['object'])
    if not postFilename:
        if debug:
            print('DEBUG: announce post not found in inbox or outbox')
            print(messageJson['object'])
        return True
    if debug:
        print('DEBUG: announced/repeated post found in inbox')
    return True

def receiveUndoAnnounce(session,handle: str,baseDir: str, \
                        httpPrefix: str,domain :str,port: int, \
                        sendThreads: [],postLog: [],cachedWebfingers: {}, \
                        personCache: {},messageJson: {},federationList: [], \
                        debug : bool) -> bool:
    """Receives an undo announce activity within the POST section of HTTPServer
    """
    if messageJson['type']!='Undo':
        return False
    if not messageJson.get('actor'):
        return False
    if not messageJson.get('object'):
        return False
    if not isinstance(messageJson['object'], dict):
        return False
    if not messageJson['object'].get('object'):
        return False
    if not isinstance(messageJson['object']['object'], str):
        return False
    if messageJson['object']['type']!='Announce':
        return False    
    if '/users/' not in messageJson['actor']:
        if debug:
            print('DEBUG: "users" missing from actor in '+messageJson['type']+' announce')
        return False
    if '/statuses/' not in messageJson['object']:
        if debug:
            print('DEBUG: "statuses" missing from object in '+messageJson['type']+' announce')
        return False
    if not os.path.isdir(baseDir+'/accounts/'+handle):
        print('DEBUG: unknown recipient of undo announce - '+handle)
    # if this post in the outbox of the person?
    postFilename=locatePost(baseDir,handle.split('@')[0],handle.split('@')[1],messageJson['object'])
    if not postFilename:
        if debug:
            print('DEBUG: undo announce post not found in inbox or outbox')
            print(messageJson['object']['object'])
        return True
    if debug:
        print('DEBUG: announced/repeated post to be undone found in inbox')
    with open(postFilename, 'r') as fp:
        postJsonObject=commentjson.load(fp)
        if not postJsonObject.get('type'):
            if postJsonObject['type']!='Announce':
                if debug:
                    print("DEBUG: Attenpt to undo something which isn't an announcement")
                return False        
    os.remove(postFilename)
    return True

def populateReplies(baseDir :str,httpPrefix :str,domain :str, \
                    messageJson :{},maxReplies: int,debug :bool) -> bool:
    """Updates the list of replies for a post on this domain if 
    a reply to it arrives
    """
    if not messageJson.get('id'):
        return False
    if not messageJson.get('object'):
        return False
    if not isinstance(messageJson['object'], dict):
        return False
    if not messageJson['object'].get('inReplyTo'):
        return False
    if not messageJson['object'].get('to'):
        return False
    replyTo=messageJson['object']['inReplyTo']
    if debug:
        print('DEBUG: post contains a reply')
    # is this a reply to a post on this domain?
    if not replyTo.startswith(httpPrefix+'://'+domain+'/'):
        if debug:
            print('DEBUG: post is a reply to another not on this domain')
        return False
    replyToNickname=getNicknameFromActor(replyTo)
    if not replyToNickname:
        if debug:
            print('DEBUG: no nickname found for '+replyTo)
        return False
    replyToDomain,replyToPort=getDomainFromActor(replyTo)
    if not replyToDomain:
        if debug:
            print('DEBUG: no domain found for '+replyTo)
        return False
    postFilename=locatePost(baseDir,replyToNickname,replyToDomain,replyTo)
    if not postFilename:
        if debug:
            print('DEBUG: post may have expired - '+replyTo)
        return False    
    # populate a text file containing the ids of replies
    postRepliesFilename=postFilename.replace('.json','.replies')
    messageId=messageJson['id'].replace('/activity','')
    if os.path.isfile(postRepliesFilename):
        numLines = sum(1 for line in open(postRepliesFilename))
        if numlines>maxReplies:
            return False
        if messageId not in open(postRepliesFilename).read():
            repliesFile=open(postRepliesFilename, "a")
            repliesFile.write(messageId+'\n')
            repliesFile.close()
    else:
        repliesFile=open(postRepliesFilename, "w")
        repliesFile.write(messageId+'\n')
        repliesFile.close()
    return True
                
def inboxAfterCapabilities(session,keyId: str,handle: str,messageJson: {}, \
                           baseDir: str,httpPrefix: str,sendThreads: [], \
                           postLog: [],cachedWebfingers: {},personCache: {}, \
                           queue: [],domain: str,port: int,useTor: bool, \
                           federationList: [],ocapAlways: bool,debug: bool, \
                           acceptedCaps: [],
                           queueFilename :str,destinationFilename :str,
                           maxReplies: int) -> bool:
    """ Anything which needs to be done after capabilities checks have passed
    """
    if receiveLike(session,handle, \
                   baseDir,httpPrefix, \
                   domain,port, \
                   sendThreads,postLog, \
                   cachedWebfingers, \
                   personCache, \
                   messageJson, \
                   federationList, \
                   debug):
        if debug:
            print('DEBUG: Like accepted from '+keyId)
        return False

    if receiveUndoLike(session,handle, \
                       baseDir,httpPrefix, \
                       domain,port, \
                       sendThreads,postLog, \
                       cachedWebfingers, \
                       personCache, \
                       messageJson, \
                       federationList, \
                       debug):
        if debug:
            print('DEBUG: Undo like accepted from '+keyId)
        return False

    if receiveAnnounce(session,handle, \
                       baseDir,httpPrefix, \
                       domain,port, \
                       sendThreads,postLog, \
                       cachedWebfingers, \
                       personCache, \
                       messageJson, \
                       federationList, \
                       debug):
        if debug:
            print('DEBUG: Announce accepted from '+keyId)

    if receiveUndoAnnounce(session,handle, \
                           baseDir,httpPrefix, \
                           domain,port, \
                           sendThreads,postLog, \
                           cachedWebfingers, \
                           personCache, \
                           messageJson, \
                           federationList, \
                           debug):
        if debug:
            print('DEBUG: Undo announce accepted from '+keyId)
        return False

    if receiveDelete(session,handle, \
                     baseDir,httpPrefix, \
                     domain,port, \
                     sendThreads,postLog, \
                     cachedWebfingers, \
                     personCache, \
                     messageJson, \
                     federationList, \
                     debug):
        if debug:
            print('DEBUG: Delete accepted from '+keyId)
        return False
            
    populateReplies(baseDir,httpPrefix,domain,messageJson,maxReplies,debug)
    
    if debug:
        print('DEBUG: object capabilities passed')
        print('copy from '+queueFilename+' to '+destinationFilename)
    copyfile(queueFilename,destinationFilename)
    return True

def restoreQueueItems(baseDir: str,queue: []) -> None:
    """Checks the queue for each account and appends filenames
    """
    queue=[]
    for subdir,dirs,files in os.walk(baseDir+'/accounts'):
        for account in dirs:
            queueDir=baseDir+'/accounts/'+account+'/queue'
            if os.path.isdir(queueDir):
                for queuesubdir,queuedirs,queuefiles in os.walk(queueDir):
                    for qfile in queuefiles:
                        queue.append(os.path.join(queueDir, qfile))

def runInboxQueue(baseDir: str,httpPrefix: str,sendThreads: [],postLog: [], \
                  cachedWebfingers: {},personCache: {},queue: [], \
                  domain: str,port: int,useTor: bool,federationList: [], \
                  ocapAlways: bool,maxReplies: int, \
                  domainMaxPostsPerDay: int,accountMaxPostsPerDay: int, \
                  debug: bool, \
                  acceptedCaps=["inbox:write","objects:read"]) -> None:
    """Processes received items and moves them to
    the appropriate directories
    """
    currSessionTime=int(time.time())
    sessionLastUpdate=currSessionTime
    session=createSession(domain,port,useTor)
    inboxHandle='inbox@'+domain
    if debug:
        print('DEBUG: Inbox queue running')

    # if queue processing was interrupted (eg server crash)
    # then this loads any outstanding items back into the queue
    restoreQueueItems(baseDir,queue)

    # keep track of numbers of incoming posts per unit of time
    quotasLastUpdate=int(time.time())
    quotas={
        'domains': {},
        'accounts': {}
    }
    
    while True:
        time.sleep(1)
        if len(queue)>0:
            currTime=int(time.time())

            # recreate the session periodically
            if currTime-sessionLastUpdate>1200:
                session=createSession(domain,port,useTor)
                sessionLastUpdate=currTime            

            # oldest item first
            queue.sort()
            queueFilename=queue[0]
            if not os.path.isfile(queueFilename):
                if debug:
                    print("DEBUG: queue item rejected becase it has no file: "+queueFilename)
                queue.pop(0)
                continue

            # Load the queue json
            with open(queueFilename, 'r') as fp:
                queueJson=commentjson.load(fp)

            # clear the daily quotas for maximum numbers of received posts
            if currTime-quotasLastUpdate>60*60*24:
                quotas={
                    'domains': {},
                    'accounts': {}
                }
                quotasLastUpdate=currTime            

            # limit the number of posts which can arrive per domain per day
            postDomain=queueJson['postDomain']
            if postDomain:
                if domainMaxPostsPerDay>0:
                    if quotas['domains'].get(postDomain):
                        if quotas['domains'][postDomain]>domainMaxPostsPerDay:
                            queue.pop(0)
                            continue
                        quotas['domains'][postDomain]+=1
                    else:
                        quotas['domains'][postDomain]=1

                if accountMaxPostsPerDay>0:
                    postHandle=queueJson['postNickname']+'@'+postDomain
                    if quotas['accounts'].get(postHandle):
                        if quotas['accounts'][postHandle]>accountMaxPostsPerDay:
                            queue.pop(0)
                            continue
                        quotas['accounts'][postHandle]+=1
                    else:
                        quotas['accounts'][postHandle]=1

                if debug:
                    if accountMaxPostsPerDay>0 or domainMaxPostsPerDay>0:
                        pprint(quotas)

            # Try a few times to obtain the public key
            pubKey=None
            keyId=None
            for tries in range(8):
                keyId=None
                signatureParams=queueJson['headers'].split(',')
                for signatureItem in signatureParams:
                    if signatureItem.startswith('keyId='):
                        if '"' in signatureItem:
                            keyId=signatureItem.split('"')[1]
                            break
                if not keyId:
                    if debug:
                        print('DEBUG: No keyId in signature: '+queueJson['headers']['signature'])
                    os.remove(queueFilename)
                    queue.pop(0)
                    continue

                pubKey=getPersonPubKey(session,keyId,personCache,debug)
                if pubKey:
                    print('DEBUG: public key: '+str(pubKey))
                    break
                    
                if debug:
                    print('DEBUG: Retry '+str(tries+1)+' obtaining public key for '+keyId)
                time.sleep(5)

            if not pubKey:
                if debug:
                    print('DEBUG: public key could not be obtained from '+keyId)
                os.remove(queueFilename)
                queue.pop(0)
                continue

            # check the signature
            verifyHeaders={
                'host': queueJson['host'],
                'signature': queueJson['headers']
            }            
            if not verifyPostHeaders(httpPrefix, \
                                     pubKey, verifyHeaders, \
                                     queueJson['path'], False, \
                                     json.dumps(queueJson['post'])):
                if debug:
                    print('DEBUG: Header signature check failed')
                os.remove(queueFilename)
                queue.pop(0)
                continue

            if debug:
                print('DEBUG: Signature check success')

            if receiveFollowRequest(session, \
                                    baseDir,httpPrefix,port, \
                                    sendThreads,postLog, \
                                    cachedWebfingers,
                                    personCache,
                                    queueJson['post'], \
                                    federationList, \
                                    debug, \
                                    acceptedCaps=["inbox:write","objects:read"]):
                if debug:
                    print('DEBUG: Follow accepted from '+keyId)
                os.remove(queueFilename)
                queue.pop(0)
                continue

            if receiveAcceptReject(session, \
                                   baseDir,httpPrefix,domain,port, \
                                   sendThreads,postLog, \
                                   cachedWebfingers,
                                   personCache,
                                   queueJson['post'], \
                                   federationList, \
                                   debug):
                if debug:
                    print('DEBUG: Accept/Reject received from '+keyId)
                os.remove(queueFilename)
                queue.pop(0)
                continue

            if receiveUpdate(session, \
                             baseDir,httpPrefix, \
                             domain,port, \
                             sendThreads,postLog, \
                             cachedWebfingers,
                             personCache,
                             queueJson['post'], \
                             federationList, \
                             debug):
                if debug:
                    print('DEBUG: Update accepted from '+keyId)
                os.remove(queueFilename)
                queue.pop(0)
                continue

            # get recipients list
            recipientsDict,recipientsDictFollowers= \
                inboxPostRecipients(baseDir,queueJson['post'],httpPrefix,domain,port,debug)
            if len(recipientsDict.items())==0 and \
               len(recipientsDictFollowers.items())==0:
                if debug:
                    pprint(queueJson['post'])
                    print('DEBUG: no recipients were resolved for post arriving in inbox')
                os.remove(queueFilename)
                queue.pop(0)
                continue

            # if there are only a small number of followers then process them as if they
            # were specifically addresses to particular accounts
            noOfFollowItems=len(recipientsDictFollowers.items())
            if noOfFollowItems>0:
                if noOfFollowItems<5:
                    if debug:
                        print('DEBUG: moving '+str(noOfFollowItems)+' inbox posts addressed to followers')
                    for handle,postItem in recipientsDictFollowers.items():
                        recipientsDict[handle]=postItem
                    recipientsDictFollowers={}
                recipientsList=[recipientsDict,recipientsDictFollowers]

            if debug:
                print('*************************************')
                print('Resolved recipients list:')
                pprint(recipientsDict)
                print('Resolved followers list:')
                pprint(recipientsDictFollowers)
                print('*************************************')

            if queueJson['post'].get('capability'):
                if not isinstance(queueJson['post']['capability'], list):
                    if debug:
                        print('DEBUG: capability on post should be a list')
                    os.remove(queueFilename)
                    queue.pop(0)
                    continue

            # Copy any posts addressed to followers into the shared inbox
            # this avoid copying file multiple times to potentially many
            # individual inboxes
            # This obviously bypasses object capabilities and so
            # any checking will needs to be handled at the time when inbox
            # GET happens on individual accounts.
            # See posts.py/createBoxBase
            if len(recipientsDictFollowers)>0:
                copyfile(queueFilename, \
                         queueJson['destination'].replace(inboxHandle,inboxHandle))

            # for posts addressed to specific accounts
            for handle,capsId in recipientsDict.items():              
                destination=queueJson['destination'].replace(inboxHandle,handle)
                # check that capabilities are accepted
                if queueJson['post'].get('capability'):
                    capabilityIdList=queueJson['post']['capability']
                    # does the capability id list within the post contain the id
                    # of the recipient with this handle?
                    # Here the capability id begins with the handle, so this could also
                    # be matched separately, but it's probably not necessary
                    if capsId in capabilityIdList:
                        inboxAfterCapabilities(session,keyId,handle, \
                                               queueJson['post'], \
                                               baseDir,httpPrefix, \
                                               sendThreads,postLog, \
                                               cachedWebfingers, \
                                               personCache,queue,domain, \
                                               port,useTor, \
                                               federationList,ocapAlways, \
                                               debug,acceptedCaps, \
                                               queueFilename,destination, \
                                               maxReplies)
                    else:
                        if debug:
                            print('DEBUG: object capabilities check failed')
                            pprint(queueJson['post'])
                else:
                    if not ocapAlways:
                        inboxAfterCapabilities(session,keyId,handle, \
                                               queueJson['post'], \
                                               baseDir,httpPrefix, \
                                               sendThreads,postLog, \
                                               cachedWebfingers, \
                                               personCache,queue,domain, \
                                               port,useTor, \
                                               federationList,ocapAlways, \
                                               debug,acceptedCaps, \
                                               queueFilename,destination, \
                                               maxReplies)
                    if debug:
                        print('DEBUG: object capabilities check failed')
            
                if debug:
                    print('DEBUG: Queue post accepted')
            os.remove(queueFilename)
            queue.pop(0)
