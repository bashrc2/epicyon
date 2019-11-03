__filename__ = "announce.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.0.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import json
import commentjson
from pprint import pprint
from utils import getStatusNumber
from utils import createOutboxDir
from utils import urlPermitted
from utils import getNicknameFromActor
from utils import getDomainFromActor
from utils import locatePost
from posts import sendSignedJson
from posts import getPersonBox
from session import postJson
from webfinger import webfingerHandle
from auth import createBasicAuthHeader

def outboxAnnounce(baseDir: str,messageJson: {},debug: bool) -> bool:
    """ Adds or removes announce entries from the shares collection
    within a given post
    """
    if not messageJson.get('actor'):
        return False
    if not messageJson.get('type'):
        return False
    if not messageJson.get('object'):
        return False
    if messageJson['type']=='Announce':
        if not isinstance(messageJson['object'], str):
            return False
        nickname=getNicknameFromActor(messageJson['actor'])
        if not nickname:
            print('WARN: no nickname found in '+messageJson['actor'])
            return False
        domain,port=getDomainFromActor(messageJson['actor'])
        postFilename=locatePost(baseDir,nickname,domain,messageJson['object'])
        if postFilename:
            updateAnnounceCollection(postFilename,messageJson['actor'],debug)
            return True
    if messageJson['type']=='Undo':
        if not isinstance(messageJson['object'], dict):
            return False
        if not messageJson['object'].get('type'):
            return False
        if messageJson['object']['type']=='Announce':
            if not isinstance(messageJson['object']['object'], str):
                return False
            nickname=getNicknameFromActor(messageJson['actor'])
            if not nickname:
                print('WARN: no nickname found in '+messageJson['actor'])
                return False
            domain,port=getDomainFromActor(messageJson['actor'])
            postFilename=locatePost(baseDir,nickname,domain,messageJson['object']['object'])
            if postFilename:
                undoAnnounceCollectionEntry(postFilename,messageJson['actor'],debug)
                return True
    return False

def undoAnnounceCollectionEntry(postFilename: str,actor: str, \
                                debug: bool) -> None:
    """Undoes an announce for a particular actor by removing it from the "shares"
    collection within a post. Note that the "shares" collection has no relation
    to shared items in shares.py. It's shares of posts, not shares of physical objects.
    """
    with open(postFilename, 'r') as fp:
        postJsonObject=commentjson.load(fp)
        if not postJsonObject.get('type'):
            return
        if postJsonObject['type']!='Create':
            return
        if not postJsonObject.get('object'):
            if debug:
                pprint(postJsonObject)
                print('DEBUG: post has no object')
            return
        if not isinstance(postJsonObject['object'], dict):
            return
        if not postJsonObject['object'].get('shares'):
            return
        if not postJsonObject['object']['shares'].get('items'):
            return
        totalItems=0
        if postJsonObject['object']['shares'].get('totalItems'):
            totalItems=postJsonObject['object']['shares']['totalItems']
        itemFound=False
        for announceItem in postJsonObject['object']['shares']['items']:
            if announceItem.get('actor'):
                if announceItem['actor']==actor:
                    if debug:
                        print('DEBUG: Announce was removed for '+actor)
                    postJsonObject['object']['shares']['items'].remove(announceItem)
                    itemFound=True
                    break
        if itemFound:
            if totalItems==1:
                if debug:
                    print('DEBUG: shares (announcements) was removed from post')
                del postJsonObject['object']['shares']
            else:
                postJsonObject['object']['shares']['totalItems']= \
                    len(postJsonObject['object']['shares']['items'])
            with open(postFilename, 'w') as fp:
                commentjson.dump(postJsonObject, fp, indent=4, sort_keys=True)            

def updateAnnounceCollection(postFilename: str,actor: str,debug: bool) -> None:
    """Updates the announcements collection within a post
    Confusingly this is known as "shares", but isn't the same as shared
    items within shares.py. It's shares of posts, not shares of physical objects.
    """
    with open(postFilename, 'r') as fp:
        postJsonObject=commentjson.load(fp)
        if not postJsonObject.get('object'):
            if debug:
                pprint(postJsonObject)
                print('DEBUG: post '+announceUrl+' has no object')
            return
        if not isinstance(postJsonObject['object'], dict):
            return
        postUrl=postJsonObject['id'].replace('/activity','')+'/shares'
        if not postJsonObject['object'].get('shares'):
            if debug:
                print('DEBUG: Adding initial shares (announcements) to '+postUrl)
            announcementsJson = {
                "@context": "https://www.w3.org/ns/activitystreams",
                'id': postUrl,
                'type': 'Collection',
                "totalItems": 1,
                'items': [{
                    'type': 'Announce',
                    'actor': actor                    
                }]
            }
            postJsonObject['object']['shares']=announcementsJson
        else:
            if postJsonObject['object']['shares'].get('items'):
                for announceItem in postJsonObject['object']['shares']['items']:
                    if announceItem.get('actor'):
                        if announceItem['actor']==actor:
                            return
                newAnnounce={
                    'type': 'Announce',
                    'actor': actor
                }
                postJsonObject['object']['shares']['items'].append(newAnnounce)
                postJsonObject['object']['shares']['totalItems']= \
                    len(postJsonObject['object']['shares']['items'])
            else:
                if debug:
                    print('DEBUG: shares (announcements) section of post has no items list')

        if debug:
            print('DEBUG: saving post with shares (announcements) added')
            pprint(postJsonObject)
        with open(postFilename, 'w') as fp:
            commentjson.dump(postJsonObject, fp, indent=4, sort_keys=True)

def announcedByPerson(postJsonObject: {}, nickname: str,domain: str) -> bool:
    """Returns True if the given post is announced by the given person
    """
    if not postJsonObject.get('object'):
        return False
    if not isinstance(postJsonObject['object'], dict):
        return False
    # not to be confused with shared items
    if not postJsonObject['object'].get('shares'):
        return False
    actorMatch=domain+'/users/'+nickname
    for item in postJsonObject['object']['shares']['items']:
        if item['actor'].endswith(actorMatch):
            return True
    return False

def createAnnounce(session,baseDir: str,federationList: [], \
                   nickname: str, domain: str, port: int, \
                   toUrl: str, ccUrl: str, httpPrefix: str, \
                   objectUrl: str, saveToFile: bool, \
                   clientToServer: bool, \
                   sendThreads: [],postLog: [], \
                   personCache: {},cachedWebfingers: {}, \
                   debug: bool,projectVersion: str) -> {}:
    """Creates an announce message
    Typically toUrl will be https://www.w3.org/ns/activitystreams#Public
    and ccUrl might be a specific person favorited or repeated and the
    followers url objectUrl is typically the url of the message,
    corresponding to url or atomUri in createPostBase
    """
    if not urlPermitted(objectUrl,federationList,"inbox:write"):
        return None

    if ':' in domain:
        domain=domain.split(':')[0]
    fullDomain=domain
    if port:
        if port!=80 and port!=443:
            if ':' not in domain:
                fullDomain=domain+':'+str(port)

    statusNumber,published = getStatusNumber()
    newAnnounceId= \
        httpPrefix+'://'+fullDomain+'/users/'+nickname+'/statuses/'+statusNumber
    newAnnounce = {
        "@context": "https://www.w3.org/ns/activitystreams",
        'actor': httpPrefix+'://'+fullDomain+'/users/'+nickname,
        'atomUri': httpPrefix+'://'+fullDomain+'/users/'+nickname+'/statuses/'+statusNumber,
        'cc': [],
        'id': newAnnounceId+'/activity',
        'object': objectUrl,
        'published': published,
        'to': [toUrl],
        'type': 'Announce'
    }
    if ccUrl:
        if len(ccUrl)>0:
            newAnnounce['cc']=[ccUrl]
    if saveToFile:
        outboxDir = createOutboxDir(nickname,domain,baseDir)
        filename=outboxDir+'/'+newAnnounceId.replace('/','#')+'.json'
        with open(filename, 'w') as fp:
            commentjson.dump(newAnnounce, fp, indent=4, sort_keys=False)

    announceNickname=None
    announceDomain=None
    announcePort=None
    if '/users/' in objectUrl or '/profile/' in objectUrl:
        announceNickname=getNicknameFromActor(objectUrl)
        announceDomain,announcePort=getDomainFromActor(objectUrl)

    if announceNickname and announceDomain:
        sendSignedJson(newAnnounce,session,baseDir, \
                       nickname,domain,port, \
                       announceNickname,announceDomain,announcePort, \
                       'https://www.w3.org/ns/activitystreams#Public', \
                       httpPrefix,True,clientToServer,federationList, \
                       sendThreads,postLog,cachedWebfingers,personCache, \
                       debug,projectVersion)
            
    return newAnnounce

def announcePublic(session,baseDir: str,federationList: [], \
                   nickname: str, domain: str, port: int, httpPrefix: str, \
                   objectUrl: str,clientToServer: bool, \
                   sendThreads: [],postLog: [], \
                   personCache: {},cachedWebfingers: {}, \
                   debug: bool,projectVersion: str) -> {}:
    """Makes a public announcement
    """
    fromDomain=domain
    if port:
        if port!=80 and port!=443:
            if ':' not in domain:
                fromDomain=domain+':'+str(port)

    toUrl = 'https://www.w3.org/ns/activitystreams#Public'
    ccUrl = httpPrefix + '://'+fromDomain+'/users/'+nickname+'/followers'
    return createAnnounce(session,baseDir,federationList, \
                          nickname,domain,port, \
                          toUrl,ccUrl,httpPrefix, \
                          objectUrl,True,clientToServer, \
                          sendThreads,postLog, \
                          personCache,cachedWebfingers, \
                          debug,projectVersion)

def repeatPost(session,baseDir: str,federationList: [], \
               nickname: str, domain: str, port: int, httpPrefix: str, \
               announceNickname: str, announceDomain: str, \
               announcePort: int, announceHttpsPrefix: str, \
               announceStatusNumber: int,clientToServer: bool, \
               sendThreads: [],postLog: [], \
               personCache: {},cachedWebfingers: {}, \
               debug: bool,projectVersion: str) -> {}:
    """Repeats a given status post
    """
    announcedDomain=announceDomain
    if announcePort:
        if announcePort!=80 and announcePort!=443:
            if ':' not in announcedDomain:
                announcedDomain=announcedDomain+':'+str(announcePort)

    objectUrl = announceHttpsPrefix + '://'+announcedDomain+'/users/'+ \
        announceNickname+'/statuses/'+str(announceStatusNumber)

    return announcePublic(session,baseDir,federationList, \
                          nickname,domain,port,httpPrefix, \
                          objectUrl,clientToServer, \
                          sendThreads,postLog, \
                          personCache,cachedWebfingers, \
                          debug,projectVersion)

def undoAnnounce(session,baseDir: str,federationList: [], \
                 nickname: str, domain: str, port: int, \
                 toUrl: str, ccUrl: str, httpPrefix: str, \
                 objectUrl: str, saveToFile: bool, \
                 clientToServer: bool, \
                 sendThreads: [],postLog: [], \
                 personCache: {},cachedWebfingers: {}, \
                 debug: bool) -> {}:
    """Undoes an announce message
    Typically toUrl will be https://www.w3.org/ns/activitystreams#Public
    and ccUrl might be a specific person whose post was repeated and the
    objectUrl is typically the url of the message which was repeated,
    corresponding to url or atomUri in createPostBase
    """
    if not urlPermitted(objectUrl,federationList,"inbox:write"):
        return None

    if ':' in domain:
        domain=domain.split(':')[0]
    fullDomain=domain
    if port:
        if port!=80 and port!=443:
            if ':' not in domain:
                fullDomain=domain+':'+str(port)

    newUndoAnnounce = {
        "@context": "https://www.w3.org/ns/activitystreams",
        'actor': httpPrefix+'://'+fullDomain+'/users/'+nickname,
        'type': 'Undo',
        'cc': [],
        'to': [toUrl],
        'object': {
            'actor': httpPrefix+'://'+fullDomain+'/users/'+nickname,
            'cc': [],
            'object': objectUrl,
            'to': [toUrl],
            'type': 'Announce'
        }
    }
    if ccUrl:
        if len(ccUrl)>0:
            newUndoAnnounce['object']['cc']=[ccUrl]

    announceNickname=None
    announceDomain=None
    announcePort=None
    if '/users/' in objectUrl or '/profile/' in objectUrl:
        announceNickname=getNicknameFromActor(objectUrl)
        announceDomain,announcePort=getDomainFromActor(objectUrl)

    if announceNickname and announceDomain:
        sendSignedJson(newUndoAnnounce,session,baseDir, \
                       nickname,domain,port, \
                       announceNickname,announceDomain,announcePort, \
                       'https://www.w3.org/ns/activitystreams#Public', \
                       httpPrefix,True,clientToServer,federationList, \
                       sendThreads,postLog,cachedWebfingers,personCache,debug)
            
    return newUndoAnnounce

def undoAnnouncePublic(session,baseDir: str,federationList: [], \
                       nickname: str, domain: str, port: int, httpPrefix: str, \
                       objectUrl: str,clientToServer: bool, \
                       sendThreads: [],postLog: [], \
                       personCache: {},cachedWebfingers: {}, \
                       debug: bool) -> {}:
    """Undoes a public announcement
    """
    fromDomain=domain
    if port:
        if port!=80 and port!=443:
            if ':' not in domain:
                fromDomain=domain+':'+str(port)

    toUrl = 'https://www.w3.org/ns/activitystreams#Public'
    ccUrl = httpPrefix + '://'+fromDomain+'/users/'+nickname+'/followers'
    return undoAnnounce(session,baseDir,federationList, \
                        nickname,domain,port, \
                        toUrl,ccUrl,httpPrefix, \
                        objectUrl,True,clientToServer, \
                        sendThreads,postLog, \
                        personCache,cachedWebfingers, \
                        debug)

def undoRepeatPost(session,baseDir: str,federationList: [], \
                   nickname: str, domain: str, port: int, httpPrefix: str, \
                   announceNickname: str, announceDomain: str, \
                   announcePort: int, announceHttpsPrefix: str, \
                   announceStatusNumber: int,clientToServer: bool, \
                   sendThreads: [],postLog: [], \
                   personCache: {},cachedWebfingers: {}, \
                   debug: bool) -> {}:
    """Undoes a status post repeat
    """
    announcedDomain=announceDomain
    if announcePort:
        if announcePort!=80 and announcePort!=443:
            if ':' not in announcedDomain:
                announcedDomain=announcedDomain+':'+str(announcePort)

    objectUrl = announceHttpsPrefix + '://'+announcedDomain+'/users/'+ \
        announceNickname+'/statuses/'+str(announceStatusNumber)

    return undoAnnouncePublic(session,baseDir,federationList, \
                              nickname,domain,port,httpPrefix, \
                              objectUrl,clientToServer, \
                              sendThreads,postLog, \
                              personCache,cachedWebfingers, \
                              debug)

def sendAnnounceViaServer(baseDir: str,session, \
                          fromNickname: str,password: str,
                          fromDomain: str,fromPort: int, \
                          httpPrefix: str,repeatObjectUrl: str, \
                          cachedWebfingers: {},personCache: {}, \
                          debug: bool,projectVersion: str) -> {}:
    """Creates an announce message via c2s
    """
    if not session:
        print('WARN: No session for sendAnnounceViaServer')
        return 6

    withDigest=True

    fromDomainFull=fromDomain
    if fromPort:
        if fromPort!=80 and fromPort!=443:
            if ':' not in fromDomain:
                fromDomainFull=fromDomain+':'+str(fromPort)

    toUrl = 'https://www.w3.org/ns/activitystreams#Public'
    ccUrl = httpPrefix + '://'+fromDomainFull+'/users/'+fromNickname+'/followers'

    statusNumber,published = getStatusNumber()
    newAnnounceId= \
        httpPrefix+'://'+fromDomainFull+'/users/'+fromNickname+'/statuses/'+statusNumber
    newAnnounceJson = {
        "@context": "https://www.w3.org/ns/activitystreams",
        'actor': httpPrefix+'://'+fromDomainFull+'/users/'+fromNickname,
        'atomUri': newAnnounceId,
        'cc': [ccUrl],
        'id': newAnnounceId+'/activity',
        'object': repeatObjectUrl,
        'published': published,
        'to': [toUrl],
        'type': 'Announce'
    }

    handle=httpPrefix+'://'+fromDomainFull+'/@'+fromNickname

    # lookup the inbox for the To handle
    wfRequest = \
        webfingerHandle(session,handle,httpPrefix,cachedWebfingers, \
                        fromDomain,projectVersion)
    if not wfRequest:
        if debug:
            print('DEBUG: announce webfinger failed for '+handle)
        return 1

    postToBox='outbox'

    # get the actor inbox for the To handle
    inboxUrl,pubKeyId,pubKey,fromPersonId,sharedInbox,capabilityAcquisition,avatarUrl,displayName = \
        getPersonBox(baseDir,session,wfRequest,personCache, \
                     projectVersion,httpPrefix,fromDomain,postToBox)
                     
    if not inboxUrl:
        if debug:
            print('DEBUG: No '+postToBox+' was found for '+handle)
        return 3
    if not fromPersonId:
        if debug:
            print('DEBUG: No actor was found for '+handle)
        return 4
    
    authHeader=createBasicAuthHeader(fromNickname,password)
     
    headers = {'host': fromDomain, \
               'Content-type': 'application/json', \
               'Authorization': authHeader}
    postResult = \
        postJson(session,newAnnounceJson,[],inboxUrl,headers,"inbox:write")
    #if not postResult:
    #    if debug:
    #        print('DEBUG: POST announce failed for c2s to '+inboxUrl)
    #    return 5

    if debug:
        print('DEBUG: c2s POST announce success')

    return newAnnounceJson
