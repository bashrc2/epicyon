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

    if messageJson['type']!='Follow':
        if messageJson.get('object'):
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

def savePostToInboxQueue(baseDir: str,httpPrefix: str,nickname: str, domain: str,postJson: {},host: str,headers: str,postPath: str,debug: bool) -> str:
    """Saves the give json to the inbox queue for the person
    keyId specifies the actor sending the post
    """
    if ':' in domain:
        domain=domain.split(':')[0]
    if postJson.get('id'):
        postId=postJson['id'].replace('/activity','')
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
        'nickname': nickname,
        'domain': domain,
        'sharedInbox': sharedInboxItem,
        'published': published,
        'host': host,
        'headers': headers,
        'path': postPath,
        'post': postJson,
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
                           actor :str) -> bool:
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
                    recipientsDict[handle]=None
        if recipient.endswith('followers'):
            followerRecipients=True
    return followerRecipients,recipientsDict

def inboxPostRecipients(baseDir :str,postJsonObject :{},httpPrefix :str,domain : str,port :int) -> []:
    recipientsDict={}

    if not postJsonObject.get('actor'):
        return recipientsDict

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
                includesFollowers,recipientsDict= \
                    inboxPostRecipientsAdd(baseDir,httpPrefix, \
                                           postJsonObject['object']['to'], \
                                           recipientsDict, \
                                           domainMatch,domainBase,actor)
                if includesFollowers:
                    followerRecipients=True

            if postJsonObject['object'].get('cc'):
                includesFollowers,recipientsDict= \
                    inboxPostRecipientsAdd(baseDir,httpPrefix, \
                                           postJsonObject['object']['cc'], \
                                           recipientsDict, \
                                           domainMatch,domainBase,actor)
                if includesFollowers:
                    followerRecipients=True

    if postJsonObject.get('to'):
        includesFollowers,recipientsDict= \
            inboxPostRecipientsAdd(baseDir,httpPrefix, \
                                   postJsonObject['to'], \
                                   recipientsDict, \
                                   domainMatch,domainBase,actor)
        if includesFollowers:
            followerRecipients=True

    if postJsonObject.get('cc'):
        includesFollowers,recipientsDict= \
            inboxPostRecipientsAdd(baseDir,httpPrefix, \
                                   postJsonObject['cc'], \
                                   recipientsDict, \
                                   domainMatch,domainBase,actor)
        if includesFollowers:
            followerRecipients=True

    if not followerRecipients:
        return recipientsDict

    # now resolve the followers
    recipientsDict= \
        getFollowersOfActor(baseDir,actor,recipientsDict)

    return recipientsDict

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
    domain,tempPort=getDomainFromActor(messageJson['actor'])
    if not domainPermitted(domain,federationList):
        if debug:
            print('DEBUG: '+messageJson['type']+' from domain not permitted - '+domain)
        return False
    nickname=getNicknameFromActor(messageJson['actor'])
    if not nickname:
        if debug:
            print('DEBUG: '+messageJson['type']+' does not contain a nickname')
        return False
    handle=nickname.lower()+'@'+domain.lower()
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

def runInboxQueue(baseDir: str,httpPrefix: str,sendThreads: [],postLog: [],cachedWebfingers: {},personCache: {},queue: [],domain: str,port: int,useTor: bool,federationList: [],ocapAlways: bool,debug: bool) -> None:
    """Processes received items and moves them to
    the appropriate directories
    """
    currSessionTime=int(time.time())
    sessionLastUpdate=currSessionTime
    session=createSession(domain,port,useTor)
    inboxHandle='inbox@'+domain
    if debug:
        print('DEBUG: Inbox queue running')

    while True:
        time.sleep(1)
        if len(queue)>0:
            currSessionTime=int(time.time())
            if currSessionTime-sessionLastUpdate>1200:
                session=createSession(domain,port,useTor)
                sessionLastUpdate=currSessionTime

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
                                    debug):
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
            recipientsDict=inboxPostRecipients(baseDir,queueJson['post'],httpPrefix,domain,port)

            if debug:
                print('*************************************')
                print('Resolved recipients list:')
                pprint(recipientsDict)
                print('*************************************')

            if queueJson['post'].get('capability'):
                if not isinstance(queueJson['post']['capability'], list):
                    if debug:
                        print('DEBUG: capability on post should be a list')
                    os.remove(queueFilename)
                    queue.pop(0)
                    continue
            
            for handle,capsId in recipientsDict.items():
                    
                # check that capabilities are accepted            
                if queueJson['post'].get('capability'):
                    capabilityIdList=queueJson['post']['capability']
                    # does the capability id list within the post contain the id
                    # of the recipient with this handle?
                    # Here the capability id begins with the handle, so this could also
                    # be matched separately, but it's probably not necessary
                    if capsId in capabilityIdList:
                        if debug:
                            print('DEBUG: object capabilities passed')
                            print('copy from '+queueFilename+' to '+queueJson['destination'].replace(inboxHandle,handle))
                        copyfile(queueFilename,queueJson['destination'].replace(inboxHandle,handle))
                    else:
                        if debug:
                            print('DEBUG: object capabilities check failed')
                            pprint(queueJson['post'])
                else:
                    if not ocapAlways:
                        if debug:
                            print('DEBUG: not enforcing object capabilities')
                            print('copy from '+queueFilename+' to '+queueJson['destination'].replace(inboxHandle,handle))
                        copyfile(queueFilename,queueJson['destination'].replace(inboxHandle,handle))
                        continue
                    if debug:
                        print('DEBUG: object capabilities check failed')
            
            if debug:
                print('DEBUG: Queue post accepted')

            os.remove(queueFilename)
            queue.pop(0)
