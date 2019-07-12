__filename__ = "announce.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "0.0.1"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import json
import commentjson
from utils import getStatusNumber
from utils import createOutboxDir
from utils import urlPermitted
from utils import getNicknameFromActor
from utils import getDomainFromActor
from posts import sendSignedJson

def createAnnounce(session,baseDir: str,federationList: [], \
                   nickname: str, domain: str, port: int, \
                   toUrl: str, ccUrl: str, httpPrefix: str, \
                   objectUrl: str, saveToFile: bool, \
                   clientToServer: bool, \
                   sendThreads: [],postLog: [], \
                   personCache: {},cachedWebfingers: {}, \
                   debug: bool) -> {}:
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
    if port!=80 and port!=443:
        fullDomain=domain+':'+str(port)

    statusNumber,published = getStatusNumber()
    newAnnounceId= \
        httpPrefix+'://'+fullDomain+'/users/'+nickname+'/statuses/'+statusNumber
    newAnnounce = {
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
    if '/users/' in objectUrl:
        announceNickname=getNicknameFromActor(objectUrl)
        announceDomain,announcePort=getDomainFromActor(objectUrl)

    if announceNickname and announceDomain:
        sendSignedJson(newAnnounce,session,baseDir, \
                       nickname,domain,port, \
                       announceNickname,announceDomain,announcePort, \
                       'https://www.w3.org/ns/activitystreams#Public', \
                       httpPrefix,True,clientToServer,federationList, \
                       sendThreads,postLog,cachedWebfingers,personCache,debug)
            
    return newAnnounce

def announcePublic(session,baseDir: str,federationList: [], \
                   nickname: str, domain: str, port: int, httpPrefix: str, \
                   objectUrl: str,clientToServer: bool, \
                   sendThreads: [],postLog: [], \
                   personCache: {},cachedWebfingers: {}, \
                   debug: bool) -> {}:
    """Makes a public announcement
    """
    fromDomain=domain
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
                          debug)

def repeatPost(session,baseDir: str,federationList: [], \
               nickname: str, domain: str, port: int, httpPrefix: str, \
               announceNickname: str, announceDomain: str, \
               announcePort: int, announceHttpsPrefix: str, \
               announceStatusNumber: int,clientToServer: bool, \
               sendThreads: [],postLog: [], \
               personCache: {},cachedWebfingers: {}, \
               debug: bool) -> {}:
    """Repeats a given status post
    """
    announcedDomain=announceDomain
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
                          debug)

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
    if port!=80 and port!=443:
        fullDomain=domain+':'+str(port)

    newUndoAnnounce = {
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
    if '/users/' in objectUrl:
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
