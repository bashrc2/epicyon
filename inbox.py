__filename__ = "inbox.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.0.0"
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
from utils import removeModerationPostFromIndex
from httpsig import verifyPostHeaders
from session import createSession
from session import getJson
from follow import receiveFollowRequest
from follow import getFollowersOfActor
from follow import unfollowerOfPerson
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
from announce import updateAnnounceCollection
from httpsig import messageContentDigest

def validInbox(baseDir: str,nickname: str,domain: str) -> bool:
    """Checks whether files were correctly saved to the inbox
    """
    if ':' in domain:
        domain=domain.split(':')[0]
    inboxDir=baseDir+'/accounts/'+nickname+'@'+domain+'/inbox'
    if not os.path.isdir(inboxDir):
        return True
    for subdir, dirs, files in os.walk(inboxDir):
        for f in files:
            filename = os.path.join(subdir, f)
            if not os.path.isfile(filename):
                print('filename: '+filename)
                return False
            if 'postNickname' in open(filename).read():
                print('queue file incorrectly saved to '+filename)
                return False
    return True    

def validInboxFilenames(baseDir: str,nickname: str,domain: str, \
                        expectedDomain: str,expectedPort: int) -> bool:
    """Used by unit tests to check that the port number gets appended to
    domain names within saved post filenames
    """
    if ':' in domain:
        domain=domain.split(':')[0]
    inboxDir=baseDir+'/accounts/'+nickname+'@'+domain+'/inbox'
    if not os.path.isdir(inboxDir):
        return True
    expectedStr=expectedDomain+':'+str(expectedPort)
    for subdir, dirs, files in os.walk(inboxDir):
        for f in files:
            filename = os.path.join(subdir, f)
            if not os.path.isfile(filename):
                print('filename: '+filename)
                return False
            if not expectedStr in filename:
                print('Expected: '+expectedStr)
                print('Invalid filename: '+filename)
                return False
    return True    

def getPersonPubKey(baseDir: str,session,personUrl: str, \
                    personCache: {},debug: bool, \
                    projectVersion: str,httpPrefix: str,domain: str) -> str:
    if not personUrl:
        return None
    personUrl=personUrl.replace('#main-key','')
    if personUrl.endswith('/users/inbox'):
        if debug:
            print('DEBUG: Obtaining public key for shared inbox')
        personUrl=personUrl.replace('/users/inbox','/inbox')        
    personJson = getPersonFromCache(baseDir,personUrl,personCache)
    if not personJson:
        if debug:
            print('DEBUG: Obtaining public key for '+personUrl)
        asHeader = {'Accept': 'application/activity+json; profile="https://www.w3.org/ns/activitystreams"'}
        personJson = getJson(session,personUrl,asHeader,None,projectVersion,httpPrefix,domain)
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

    storePersonInCache(baseDir,personUrl,personJson,personCache)
    return pubKey

def inboxMessageHasParams(messageJson: {}) -> bool:
    """Checks whether an incoming message contains expected parameters
    """
    expectedParams=['type','actor','object']
    for param in expectedParams:
        if not messageJson.get(param):
            return False
    if not messageJson.get('to'):
        allowedWithoutToParam=['Like','Follow','Request','Accept','Capability','Undo']
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
                if not urlPermitted(inReplyTo,federationList,"inbox:write"):
                    return False

    return True

def validPublishedDate(published) -> bool:
    currTime=datetime.datetime.utcnow()
    pubDate=datetime.datetime.strptime(published,"%Y-%m-%dT%H:%M:%SZ")
    daysSincePublished = (currTime - pubTime).days
    if daysSincePublished>30:
        return False
    return True

def savePostToInboxQueue(baseDir: str,httpPrefix: str, \
                         nickname: str, domain: str, \
                         postJsonObject: {}, \
                         messageBytes: str, \
                         httpHeaders: {}, \
                         postPath: str,debug: bool) -> str:
    """Saves the give json to the inbox queue for the person
    keyId specifies the actor sending the post
    """
    originalDomain=domain
    if ':' in domain:
        domain=domain.split(':')[0]

    # block at the ealiest stage possible, which means the data
    # isn't written to file
    postNickname=None
    postDomain=None
    actor=None
    if postJsonObject.get('actor'):
        actor=postJsonObject['actor']
        postNickname=getNicknameFromActor(postJsonObject['actor'])
        postDomain,postPort=getDomainFromActor(postJsonObject['actor'])
        if not postNickname:
            pprint(postJsonObject)
            print('No post Nickname in actor')
            return None
        if not postDomain:
            pprint(postJsonObject)
            print('No post Domain in actor')
            return None
        if isBlocked(baseDir,nickname,domain,postNickname,postDomain):
            if debug:
                print('DEBUG: post from '+postNickname+' blocked')
            return None
        if postPort:
            if postPort!=80 and postPort!=443:
                if ':' not in postDomain:
                    postDomain=postDomain+':'+str(postPort)

    if postJsonObject.get('object'):
        if isinstance(postJsonObject['object'], dict):
            if postJsonObject['object'].get('inReplyTo'):
                if isinstance(postJsonObject['object']['inReplyTo'], str):
                    replyNickname=getNicknameFromActor(postJsonObject['object']['inReplyTo'])
                    replyDomain,replyPort=getDomainFromActor(postJsonObject['object']['inReplyTo'])
                    if replyNickname and replyDomain:
                        if isBlocked(baseDir,nickname,domain,postNickname,postDomain):
                            print('WARN: post contains reply from a blocked domain: '+replyDomain)
                            return None                        
            if postJsonObject['object'].get('content'):
                if isinstance(postJsonObject['object']['content'], str):
                    if isFiltered(baseDir,nickname,domain,postJsonObject['object']['content']):
                        if debug:
                            print('DEBUG: post was filtered out due to content')
                        return None
    originalPostId=None
    if postJsonObject.get('id'):
        originalPostId=postJsonObject['id'].replace('/activity','').replace('/undo','')

    currTime=datetime.datetime.utcnow()

    postId=None
    if postJsonObject.get('id'):
        #if '/statuses/' not in postJsonObject['id']:
        postId=postJsonObject['id'].replace('/activity','').replace('/undo','')
        published=currTime.strftime("%Y-%m-%dT%H:%M:%SZ")
    if not postId:
        statusNumber,published = getStatusNumber()
        if actor:
            postId=actor+'/statuses/'+statusNumber
        else:
            postId=httpPrefix+'://'+originalDomain+'/users/'+nickname+'/statuses/'+statusNumber
    
    # NOTE: don't change postJsonObject['id'] before signature check
    
    inboxQueueDir=createInboxQueueDir(nickname,domain,baseDir)

    handle=nickname+'@'+domain
    destination=baseDir+'/accounts/'+handle+'/inbox/'+postId.replace('/','#')+'.json'
    #if os.path.isfile(destination):
    #    if debug:
    #        print(destination)
    #        print('DEBUG: inbox item already exists')
    #    return None
    filename=inboxQueueDir+'/'+postId.replace('/','#')+'.json'

    sharedInboxItem=False
    if nickname=='inbox':
        nickname=originalDomain
        sharedInboxItem=True
        
    newQueueItem = {
        'originalId': originalPostId,
        'id': postId,
        'actor': actor,
        'nickname': nickname,
        'domain': domain,
        'postNickname': postNickname,
        'postDomain': postDomain,
        'sharedInbox': sharedInboxItem,
        'published': published,
        'httpHeaders': httpHeaders,
        'path': postPath,
        'post': postJsonObject,
        'digest': messageContentDigest(messageBytes),
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
    if not ocapFilename:
        return False
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
    if port:
        if port!=80 and port!=443:
            if ':' not in domain:
                domain=domain+':'+str(port)
    domainMatch='/'+domain+'/users/'

    actor = postJsonObject['actor']
    # first get any specific people which the post is addressed to
    
    followerRecipients=False
    if postJsonObject.get('object'):
        if isinstance(postJsonObject['object'], dict):
            if postJsonObject['object'].get('to'):
                if isinstance(postJsonObject['object']['to'], list):
                    recipientsList=postJsonObject['object']['to']
                else:
                    recipientsList=[postJsonObject['object']['to']]
                if debug:
                    print('DEBUG: resolving "to"')
                includesFollowers,recipientsDict= \
                    inboxPostRecipientsAdd(baseDir,httpPrefix, \
                                           recipientsList, \
                                           recipientsDict, \
                                           domainMatch,domainBase, \
                                           actor,debug)
                if includesFollowers:
                    followerRecipients=True
            else:
                if debug:
                    print('DEBUG: inbox post has no "to"')

            if postJsonObject['object'].get('cc'):
                if isinstance(postJsonObject['object']['cc'], list):
                    recipientsList=postJsonObject['object']['cc']
                else:
                    recipientsList=[postJsonObject['object']['cc']]
                includesFollowers,recipientsDict= \
                    inboxPostRecipientsAdd(baseDir,httpPrefix, \
                                           recipientsList, \
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
        if isinstance(postJsonObject['to'], list):
            recipientsList=postJsonObject['to']
        else:
            recipientsList=[postJsonObject['to']]
        includesFollowers,recipientsDict= \
            inboxPostRecipientsAdd(baseDir,httpPrefix, \
                                   recipientsList, \
                                   recipientsDict, \
                                   domainMatch,domainBase, \
                                   actor,debug)
        if includesFollowers:
            followerRecipients=True

    if postJsonObject.get('cc'):
        if isinstance(postJsonObject['cc'], list):
            recipientsList=postJsonObject['cc']
        else:
            recipientsList=[postJsonObject['cc']]
        includesFollowers,recipientsDict= \
            inboxPostRecipientsAdd(baseDir,httpPrefix, \
                                   recipientsList, \
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

def receiveUndoFollow(session,baseDir: str,httpPrefix: str, \
                      port: int,messageJson: {}, \
                      federationList: [], \
                      debug : bool) -> bool:
    if not messageJson['object'].get('actor'):
        if debug:
            print('DEBUG: follow request has no actor within object')
        return False
    if '/users/' not in messageJson['object']['actor']:
        if debug:
            print('DEBUG: "users" missing from actor within object')
        return False
    if messageJson['object']['actor'] != messageJson['actor']:
        if debug:
            print('DEBUG: actors do not match')
        return False

    nicknameFollower=getNicknameFromActor(messageJson['object']['actor'])
    domainFollower,portFollower=getDomainFromActor(messageJson['object']['actor'])
    domainFollowerFull=domainFollower
    if portFollower:
        if portFollower!=80 and portFollower!=443:
            if ':' not in domainFollower:
                domainFollowerFull=domainFollower+':'+str(portFollower)
    
    nicknameFollowing=getNicknameFromActor(messageJson['object']['object'])
    domainFollowing,portFollowing=getDomainFromActor(messageJson['object']['object'])
    domainFollowingFull=domainFollowing
    if portFollowing:
        if portFollowing!=80 and portFollowing!=443:
            if ':' not in domainFollowing:
                domainFollowingFull=domainFollowing+':'+str(portFollowing)

    if unfollowerOfPerson(baseDir, \
                          nicknameFollowing,domainFollowingFull, \
                          nicknameFollower,domainFollowerFull, \
                          debug):
        if debug:
            print('DEBUG: Follower '+nicknameFollower+'@'+domainFollowerFull+' was removed')
        return True
    
    if debug:
        print('DEBUG: Follower '+nicknameFollower+'@'+domainFollowerFull+' was not removed')
    return False

def receiveUndo(session,baseDir: str,httpPrefix: str, \
                port: int,sendThreads: [],postLog: [], \
                cachedWebfingers: {},personCache: {}, \
                messageJson: {},federationList: [], \
                debug : bool, \
                acceptedCaps=["inbox:write","objects:read"]) -> bool:
    """Receives an undo request within the POST section of HTTPServer
    """
    if not messageJson['type'].startswith('Undo'):
        return False
    if debug:
        print('DEBUG: Undo activity received')
    if not messageJson.get('actor'):
        if debug:
            print('DEBUG: follow request has no actor')
        return False
    if '/users/' not in messageJson['actor']:
        if debug:
            print('DEBUG: "users" missing from actor')            
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
            print('DEBUG: '+messageJson['type']+' has no object type')
        return False
    if not messageJson['object'].get('object'):
        if debug:
            print('DEBUG: '+messageJson['type']+' has no object within object')
        return False
    if not isinstance(messageJson['object']['object'], str):
        if debug:
            print('DEBUG: '+messageJson['type']+' object within object is not a string')
        return False
    if messageJson['object']['type']=='Follow':
        return receiveUndoFollow(session,baseDir,httpPrefix, \
                                 port,messageJson, \
                                 federationList, \
                                 debug)
    return False

def personReceiveUpdate(baseDir: str, \
                        domain: str,port: int, \
                        updateNickname: str,updateDomain: str,updatePort: int, \
                        personJson: {},personCache: {},debug: bool) -> bool:
    """Changes an actor. eg: avatar or display name change
    """
    if debug:
        print('DEBUG: receiving actor update for '+personJson['url'])
    domainFull=domain
    if port:
        if port!=80 and port!=443:
            domainFull=domain+':'+str(port)
    updateDomainFull=updateDomain
    if updatePort:
        if updatePort!=80 and updatePort!=443:
            updateDomainFull=updateDomain+':'+str(updatePort)
    actor=updateDomainFull+'/users/'+updateNickname
    if actor not in personJson['id']:
        if debug:
            print('actor: '+actor)
            print('id: '+personJson['id'])
            print('DEBUG: Actor does not match id')
        return False
    if updateDomainFull==domainFull:
        if debug:
            print('DEBUG: You can only receive actor updates for domains other than your own')
        return False
    if not personJson.get('publicKey'):
        if debug:
            print('DEBUG: actor update does not contain a public key')        
        return False
    if not personJson['publicKey'].get('publicKeyPem'):
        if debug:
            print('DEBUG: actor update does not contain a public key Pem')        
        return False
    actorFilename=baseDir+'/cache/actors/'+personJson['id'].replace('/','#')+'.json'
    # check that the public keys match.
    # If they don't then this may be a nefarious attempt to hack an account
    if personCache.get(personJson['id']):
        if personCache[personJson['id']]['actor']['publicKey']['publicKeyPem']!=personJson['publicKey']['publicKeyPem']:
            if debug:
                print('WARN: Public key does not match when updating actor')
            return False
    else:
        if os.path.isfile(actorFilename):
            with open(actorFilename, 'r') as fp:
                existingPersonJson=commentjson.load(fp)
                if existingPersonJson['publicKey']['publicKeyPem']!=personJson['publicKey']['publicKeyPem']:
                    if debug:
                        print('WARN: Public key does not match cached actor when updating')
                    return False
    # save to cache in memory
    storePersonInCache(baseDir,personJson['id'],personJson,personCache)
    # save to cache on file
    with open(actorFilename, 'w') as fp:
        commentjson.dump(personJson, fp, indent=4, sort_keys=False)
        print('actor updated for '+personJson['id'])
    return True

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

    if messageJson['object']['type']=='Person' or \
       messageJson['object']['type']=='Application' or \
       messageJson['object']['type']=='Service':
        if messageJson['object'].get('url') and messageJson['object'].get('id'):
            print('Request to update actor: '+messageJson['actor'])
            updateDomain,updatePort=getDomainFromActor(messageJson['actor'])
            updateNickname=getNicknameFromActor(messageJson['actor'])            
            if personReceiveUpdate(baseDir, \
                                   domain,port, \
                                   updateNickname,updateDomain,updatePort, \
                                   messageJson['object'], \
                                   personCache,debug):
                if debug:
                    print('DEBUG: Profile update was received for '+messageJson['object']['url'])
                    return True

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
                  debug : bool,allowDeletion: bool) -> bool:
    """Receives a Delete activity within the POST section of HTTPServer
    """
    if messageJson['type']!='Delete':
        return False
    if not messageJson.get('actor'):
        if debug:
            print('DEBUG: '+messageJson['type']+' has no actor')
        return False
    if debug:
        print('DEBUG: Delete activity arrived')
    if not messageJson.get('object'):
        if debug:
            print('DEBUG: '+messageJson['type']+' has no object')
        return False
    if not isinstance(messageJson['object'], str):
        if debug:
            print('DEBUG: '+messageJson['type']+' object is not a string')
        return False
    domainFull=domain
    if port:
        if port!=80 and port!=443:
            if ':' not in domain:
                domainFull=domain+':'+str(port)
    deletePrefix=httpPrefix+'://'+domainFull+'/'
    if not allowDeletion and \
       (not messageJson['object'].startswith(deletePrefix) or \
        not messageJson['actor'].startswith(deletePrefix)):
        if debug:
            print('DEBUG: delete not permitted from other instances')
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
    messageId=messageJson['object'].replace('/activity','').replace('/undo','')
    removeModerationPostFromIndex(baseDir,messageId,debug)
    postFilename=locatePost(baseDir,handle.split('@')[0],handle.split('@')[1],messageId)
    if not postFilename:
        if debug:
            print('DEBUG: delete post not found in inbox or outbox')
            print(messageId)
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
    if debug:
        print('DEBUG: receiving announce on '+handle)
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
    # is this post in the outbox of the person?
    postFilename=locatePost(baseDir,handle.split('@')[0],handle.split('@')[1],messageJson['object'])
    if not postFilename:
        if debug:
            print('DEBUG: announce post not found in inbox or outbox')
            print(messageJson['object'])
        return True
    updateAnnounceCollection(postFilename,messageJson['actor'],debug)
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
                    print("DEBUG: Attempt to undo something which isn't an announcement")
                return False        
    undoAnnounceCollectionEntry(postFilename,messageJson['actor'],debug)
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
            print(replyTo)
            print('Expected: '+httpPrefix+'://'+domain+'/')
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
    messageId=messageJson['id'].replace('/activity','').replace('/undo','')
    if os.path.isfile(postRepliesFilename):
        numLines = sum(1 for line in open(postRepliesFilename))
        if numLines>maxReplies:
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
                           maxReplies: int,allowDeletion: bool) -> bool:
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
                     debug,allowDeletion):
        if debug:
            print('DEBUG: Delete accepted from '+keyId)
        return False

    populateReplies(baseDir,httpPrefix,domain,messageJson,maxReplies,debug)

    if debug:
        print('DEBUG: object capabilities passed')
        print('copy queue file from '+queueFilename+' to '+destinationFilename)

    if messageJson.get('postNickname'):
        with open(destinationFilename, 'w+') as fp:
            commentjson.dump(messageJson['post'], fp, indent=4, sort_keys=False)
    else:
        with open(destinationFilename, 'w+') as fp:
            commentjson.dump(messageJson, fp, indent=4, sort_keys=False)

    if not os.path.isfile(destinationFilename):
        return False

    return True

def restoreQueueItems(baseDir: str,queue: []) -> None:
    """Checks the queue for each account and appends filenames
    """
    queue.clear()
    for subdir,dirs,files in os.walk(baseDir+'/accounts'):
        for account in dirs:
            queueDir=baseDir+'/accounts/'+account+'/queue'
            if os.path.isdir(queueDir):
                for queuesubdir,queuedirs,queuefiles in os.walk(queueDir):
                    for qfile in queuefiles:
                        queue.append(os.path.join(queueDir, qfile))
    if len(queue)>0:
        print('Restored '+str(len(queue))+' inbox queue items')
        
def runInboxQueue(projectVersion: str, \
                  baseDir: str,httpPrefix: str,sendThreads: [],postLog: [], \
                  cachedWebfingers: {},personCache: {},queue: [], \
                  domain: str,port: int,useTor: bool,federationList: [], \
                  ocapAlways: bool,maxReplies: int, \
                  domainMaxPostsPerDay: int,accountMaxPostsPerDay: int, \
                  allowDeletion: bool,debug: bool, \
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

    # keep track of the number of queue item read failures
    # so that if a file is corrupt then it will eventually
    # be ignored rather than endlessly retried
    itemReadFailed=0
    
    while True:
        time.sleep(1)        
        if len(queue)>0:
            currTime=int(time.time())

            # recreate the session periodically
            if not session or currTime-sessionLastUpdate>1200:
                print('Creating inbox session')
                session=createSession(domain,port,useTor)
                sessionLastUpdate=currTime            

            # oldest item first
            queue.sort()
            queueFilename=queue[0]
            if not os.path.isfile(queueFilename):
                if debug:
                    print("DEBUG: queue item rejected because it has no file: "+queueFilename)
                queue.pop(0)
                continue

            print('Loading queue item '+queueFilename)
            
            # Load the queue json
            try:
                with open(queueFilename, 'r') as fp:
                    queueJson=commentjson.load(fp)
            except:
                itemReadFailed+=1
                print('WARN: Failed to load inbox queue item '+queueFilename+' (try '+str(itemReadFailed)+')')
                if itemReadFailed>4:
                    # After a few tries we can assume that the file
                    # is probably corrupt/unreadable
                    queue.pop(0)
                    itemReadFailed=0
                continue
            itemReadFailed=0
            
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
                            if debug:
                                print('DEBUG: Maximum posts for '+postDomain+' reached')
                            queue.pop(0)
                            continue
                        quotas['domains'][postDomain]+=1
                    else:
                        quotas['domains'][postDomain]=1

                if accountMaxPostsPerDay>0:
                    postHandle=queueJson['postNickname']+'@'+postDomain
                    if quotas['accounts'].get(postHandle):
                        if quotas['accounts'][postHandle]>accountMaxPostsPerDay:
                            if debug:
                                print('DEBUG: Maximum posts for '+postHandle+' reached')
                            queue.pop(0)
                            continue
                        quotas['accounts'][postHandle]+=1
                    else:
                        quotas['accounts'][postHandle]=1

                if debug:
                    if accountMaxPostsPerDay>0 or domainMaxPostsPerDay>0:
                        pprint(quotas)

            print('Obtaining public key for actor '+queueJson['actor'])
                        
            # Try a few times to obtain the public key
            pubKey=None
            keyId=None
            for tries in range(8):
                keyId=None
                signatureParams=queueJson['httpHeaders']['signature'].split(',')
                for signatureItem in signatureParams:
                    if signatureItem.startswith('keyId='):
                        if '"' in signatureItem:
                            keyId=signatureItem.split('"')[1]
                            break
                if not keyId:
                    if debug:
                        print('DEBUG: No keyId in signature: '+ \
                              queueJson['httpHeaders']['signature'])
                    os.remove(queueFilename)
                    queue.pop(0)
                    continue

                pubKey= \
                    getPersonPubKey(baseDir,session,keyId, \
                                    personCache,debug, \
                                    projectVersion,httpPrefix,domain)
                if pubKey:
                    print('DEBUG: public key: '+str(pubKey))
                    break
                    
                if debug:
                    print('DEBUG: Retry '+str(tries+1)+ \
                          ' obtaining public key for '+keyId)
                time.sleep(5)

            if not pubKey:
                if debug:
                    print('DEBUG: public key could not be obtained from '+keyId)
                    os.remove(queueFilename)
                    queue.pop(0)
                continue

            # check the signature
            if debug:
                print('DEBUG: checking http headers')
                pprint(queueJson['httpHeaders'])
            if not verifyPostHeaders(httpPrefix, \
                                     pubKey, \
                                     queueJson['httpHeaders'], \
                                     queueJson['path'],False, \
                                     queueJson['digest'], \
                                     json.dumps(queueJson['post'])):
                if debug:
                    print('DEBUG: Header signature check failed')
                    os.remove(queueFilename)
                    queue.pop(0)
                continue

            if debug:
                print('DEBUG: Signature check success')

            # set the id to the same as the post filename
            # This makes the filename and the id consistent
            #if queueJson['post'].get('id'):
            #    queueJson['post']['id']=queueJson['id']
            
            if receiveUndo(session, \
                           baseDir,httpPrefix,port, \
                           sendThreads,postLog, \
                           cachedWebfingers,
                           personCache, \
                           queueJson['post'], \
                           federationList, \
                           debug, \
                           acceptedCaps=["inbox:write","objects:read"]):
                if debug:
                    print('DEBUG: Undo accepted from '+keyId)
                os.remove(queueFilename)
                queue.pop(0)
                continue

            if debug:
                print('DEBUG: checking for follow requests')
            if receiveFollowRequest(session, \
                                    baseDir,httpPrefix,port, \
                                    sendThreads,postLog, \
                                    cachedWebfingers,
                                    personCache, \
                                    queueJson['post'], \
                                    federationList, \
                                    debug,projectVersion, \
                                    acceptedCaps=["inbox:write","objects:read"]):
                os.remove(queueFilename)
                queue.pop(0)
                if debug:
                    print('DEBUG: Follow activity for '+keyId+' removed from accepted from queue')
                continue
            else:
                if debug:
                    print('DEBUG: No follow requests')

            if receiveAcceptReject(session, \
                                   baseDir,httpPrefix,domain,port, \
                                   sendThreads,postLog, \
                                   cachedWebfingers, \
                                   personCache, \
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
                             cachedWebfingers, \
                             personCache, \
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
                inboxPostRecipients(baseDir,queueJson['post'], \
                                    httpPrefix,domain,port,debug)
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
                        print('DEBUG: moving '+str(noOfFollowItems)+ \
                              ' inbox posts addressed to followers')
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
                with open(queueJson['destination'].replace(inboxHandle,inboxHandle), 'w') as fp:
                    commentjson.dump(queueJson['post'],fp,indent=4, \
                                     sort_keys=False)

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
                                               maxReplies,allowDeletion)
                    else:
                        if debug:
                            print('DEBUG: object capabilities check has failed')
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
                                               maxReplies,allowDeletion)
                    if debug:
                        pprint(queueJson['post'])
                        print('No capability list within post')
                        print('ocapAlways: '+str(ocapAlways))
                        print('DEBUG: object capabilities check failed')
            
                if debug:
                    print('DEBUG: Queue post accepted')
            os.remove(queueFilename)
            queue.pop(0)
