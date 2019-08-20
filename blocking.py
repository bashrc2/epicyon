__filename__ = "blocking.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "0.0.1"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import os

def addGlobalBlock(baseDir: str, \
                   blockNickname: str,blockDomain: str) -> bool:
    """Global block which applies to all accounts
    """
    blockingFilename=baseDir+'/accounts/blocking.txt'
    if not blockNickname.startswith('#'):        
        blockHandle=blockNickname+'@'+blockDomain
        if os.path.isfile(blockingFilename):
            if blockHandle in open(blockingFilename).read():
                return False
        blockFile=open(blockingFilename, "a+")
        blockFile.write(blockHandle+'\n')
        blockFile.close()
    else:
        blockHashtag=blockNickname
        if os.path.isfile(blockingFilename):
            if blockHashtag+'\n' in open(blockingFilename).read():
                return False
        blockFile=open(blockingFilename, "a+")
        blockFile.write(blockHashtag+'\n')
        blockFile.close()
    return True

def addBlock(baseDir: str,nickname: str,domain: str, \
             blockNickname: str,blockDomain: str) -> bool:
    """Block the given account
    """
    if ':' in domain:
        domain=domain.split(':')[0]
    blockingFilename=baseDir+'/accounts/'+nickname+'@'+domain+'/blocking.txt'
    blockHandle=blockNickname+'@'+blockDomain
    if os.path.isfile(blockingFilename):
        if blockHandle in open(blockingFilename).read():
            return False
    blockFile=open(blockingFilename, "a+")
    blockFile.write(blockHandle+'\n')
    blockFile.close()
    return True

def removeGlobalBlock(baseDir: str, \
                      unblockNickname: str, \
                      unblockDomain: str) -> bool:
    """Unblock the given global block
    """
    unblockingFilename=baseDir+'/accounts/blocking.txt'
    if not unblockNickname.startswith('#'):        
        unblockHandle=unblockNickname+'@'+unblockDomain
        if os.path.isfile(unblockingFilename):
            if unblockHandle in open(unblockingFilename).read():
                with open(unblockingFilename, 'r') as fp:
                    with open(unblockingFilename+'.new', 'w') as fpnew:
                        for line in fp:
                            handle=line.replace('\n','')
                            if unblockHandle not in line:
                                fpnew.write(handle+'\n')
                if os.path.isfile(unblockingFilename+'.new'):
                    os.rename(unblockingFilename+'.new',unblockingFilename)
                    return True
    else:
        unblockHashtag=unblockNickname
        if os.path.isfile(unblockingFilename):
            if unblockHashtag+'\n' in open(unblockingFilename).read():
                with open(unblockingFilename, 'r') as fp:
                    with open(unblockingFilename+'.new', 'w') as fpnew:
                        for line in fp:
                            blockLine=line.replace('\n','')
                            if unblockHashtag not in line:
                                fpnew.write(blockLine+'\n')
                if os.path.isfile(unblockingFilename+'.new'):
                    os.rename(unblockingFilename+'.new',unblockingFilename)
                    return True
    return False

def removeBlock(baseDir: str,nickname: str,domain: str, \
                unblockNickname: str,unblockDomain: str) -> bool:
    """Unblock the given account
    """
    if ':' in domain:
        domain=domain.split(':')[0]
    unblockingFilename=baseDir+'/accounts/'+nickname+'@'+domain+'/blocking.txt'
    unblockHandle=unblockNickname+'@'+unblockDomain
    if os.path.isfile(unblockingFilename):
        if unblockHandle in open(unblockingFilename).read():
            with open(unblockingFilename, 'r') as fp:
                with open(unblockingFilename+'.new', 'w') as fpnew:
                    for line in fp:
                        handle=line.replace('\n','')
                        if unblockHandle not in line:
                            fpnew.write(handle+'\n')
            if os.path.isfile(unblockingFilename+'.new'):
                os.rename(unblockingFilename+'.new',unblockingFilename)
                return True
    return False

def isBlockedHashtag(baseDir: str,hashtag: str) -> bool:
    """Is the given hashtag blocked?
    """
    globalBlockingFilename=baseDir+'/accounts/blocking.txt'
    if os.path.isfile(globalBlockingFilename):
        hashtag=hashtag.strip('\n')
        if hashtag+'\n' in open(globalBlockingFilename).read():
            return True
    return False

def isBlocked(baseDir: str,nickname: str,domain: str, \
              blockNickname: str,blockDomain: str) -> bool:
    """Is the given nickname blocked?
    """
    globalBlockingFilename=baseDir+'/accounts/blocking.txt'
    if os.path.isfile(globalBlockingFilename):
        if '*@'+blockDomain in open(globalBlockingFilename).read():
            return True
        blockHandle=blockNickname+'@'+blockDomain
        if blockHandle in open(globalBlockingFilename).read():
            return True
    allowFilename=baseDir+'/accounts/'+nickname+'@'+domain+'/allowedinstances.txt'
    if os.path.isfile(allowFilename):
        if blockDomain not in open(allowFilename).read():
            return True
    blockingFilename=baseDir+'/accounts/'+nickname+'@'+domain+'/blocking.txt'
    if os.path.isfile(blockingFilename):
        if '*@'+blockDomain in open(blockingFilename).read():
            return True
        blockHandle=blockNickname+'@'+blockDomain
        if blockHandle in open(blockingFilename).read():
            return True
    return False

def sendBlockViaServer(baseDir: str,session, \
                       fromNickname: str,password: str, \
                       fromDomain: str,fromPort: int, \
                       httpPrefix: str,blockedUrl: str, \
                       cachedWebfingers: {},personCache: {}, \
                       debug: bool,projectVersion: str) -> {}:
    """Creates a block via c2s
    """
    if not session:
        print('WARN: No session for sendBlockViaServer')
        return 6

    fromDomainFull=fromDomain
    if fromPort:
        if fromPort!=80 and fromPort!=443:
            if ':' not in fromDomain:
                fromDomainFull=fromDomain+':'+str(fromPort)

    toUrl = 'https://www.w3.org/ns/activitystreams#Public'
    ccUrl = httpPrefix + '://'+fromDomainFull+'/users/'+fromNickname+'/followers'

    blockActor=httpPrefix+'://'+fromDomainFull+'/users/'+fromNickname
    newBlockJson = {
        "@context": "https://www.w3.org/ns/activitystreams",
        'type': 'Block',
        'actor': blockActor,
        'object': blockedUrl,
        'to': [toUrl],
        'cc': [ccUrl]
    }

    handle=httpPrefix+'://'+fromDomainFull+'/@'+fromNickname

    # lookup the inbox for the To handle
    wfRequest = webfingerHandle(session,handle,httpPrefix,cachedWebfingers, \
                                fromDomain,projectVersion)
    if not wfRequest:
        if debug:
            print('DEBUG: announce webfinger failed for '+handle)
        return 1

    postToBox='outbox'

    # get the actor inbox for the To handle
    inboxUrl,pubKeyId,pubKey,fromPersonId,sharedInbox,capabilityAcquisition,avatarUrl,preferredName = \
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
        postJson(session,newBlockJson,[],inboxUrl,headers,"inbox:write")
    #if not postResult:
    #    if debug:
    #        print('DEBUG: POST announce failed for c2s to '+inboxUrl)
    #    return 5

    if debug:
        print('DEBUG: c2s POST block success')

    return newBlockJson

def sendUndoBlockViaServer(baseDir: str,session, \
                           fromNickname: str,password: str, \
                           fromDomain: str,fromPort: int, \
                           httpPrefix: str,blockedUrl: str, \
                           cachedWebfingers: {},personCache: {}, \
                           debug: bool,projectVersion: str) -> {}:
    """Creates a block via c2s
    """
    if not session:
        print('WARN: No session for sendBlockViaServer')
        return 6

    fromDomainFull=fromDomain
    if fromPort:
        if fromPort!=80 and fromPort!=443:
            if ':' not in fromDomain:
                fromDomainFull=fromDomain+':'+str(fromPort)

    toUrl = 'https://www.w3.org/ns/activitystreams#Public'
    ccUrl = httpPrefix + '://'+fromDomainFull+'/users/'+fromNickname+'/followers'

    blockActor=httpPrefix+'://'+fromDomainFull+'/users/'+fromNickname
    newBlockJson = {
        "@context": "https://www.w3.org/ns/activitystreams",
        'type': 'Undo',
        'actor': blockActor,
        'object': {
            'type': 'Block',
            'actor': blockActor,
            'object': blockedUrl,
            'to': [toUrl],
            'cc': [ccUrl]
        }
    }

    handle=httpPrefix+'://'+fromDomainFull+'/@'+fromNickname

    # lookup the inbox for the To handle
    wfRequest = webfingerHandle(session,handle,httpPrefix,cachedWebfingers, \
                                fromDomain,projectVersion)
    if not wfRequest:
        if debug:
            print('DEBUG: announce webfinger failed for '+handle)
        return 1

    postToBox='outbox'

    # get the actor inbox for the To handle
    inboxUrl,pubKeyId,pubKey,fromPersonId,sharedInbox,capabilityAcquisition,avatarUrl,preferredName = \
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
        postJson(session,newBlockJson,[],inboxUrl,headers,"inbox:write")
    #if not postResult:
    #    if debug:
    #        print('DEBUG: POST announce failed for c2s to '+inboxUrl)
    #    return 5

    if debug:
        print('DEBUG: c2s POST block success')

    return newBlockJson

def outboxBlock(baseDir: str,httpPrefix: str, \
                nickname: str,domain: str,port: int, \
                messageJson: {},debug: bool) -> None:
    """ When a block request is received by the outbox from c2s
    """
    if not messageJson.get('type'):
        if debug:
            print('DEBUG: block - no type')
        return
    if not messageJson['type']=='Block':
        if debug:
            print('DEBUG: not a block')
        return
    if not messageJson.get('object'):
        if debug:
            print('DEBUG: no object in block')
        return
    if not isinstance(messageJson['object'], str):
        if debug:
            print('DEBUG: block object is not string')
        return
    if debug:
        print('DEBUG: c2s block request arrived in outbox')

    messageId=messageJson['object'].replace('/activity','')
    if '/statuses/' not in messageId:
        if debug:
            print('DEBUG: c2s block object is not a status')
        return
    if '/users/' not in messageId:
        if debug:
            print('DEBUG: c2s block object has no nickname')
        return
    if ':' in domain:
        domain=domain.split(':')[0]
    postFilename=locatePost(baseDir,nickname,domain,messageId)
    if not postFilename:
        if debug:
            print('DEBUG: c2s block post not found in inbox or outbox')
            print(messageId)
        return True
    nicknameBlocked=getNicknameFromActor(messageJson['object'])
    domainBlocked,portBlocked=getDomainFromActor(messageJson['object'])
    domainBlockedFull=domainBlocked
    if portBlocked:
        if portBlocked!=80 and portBlocked!=443:
            if ':' not in domainBlocked:
                domainBlockedFull=domainBlocked+':'+str(portBlocked)

    addBlock(baseDir,nickname,domain, \
             nicknameBlocked,domainBlockedFull)
    
    if debug:
        print('DEBUG: post blocked via c2s - '+postFilename)

def outboxUndoBlock(baseDir: str,httpPrefix: str, \
                    nickname: str,domain: str,port: int, \
                    messageJson: {},debug: bool) -> None:
    """ When an undo block request is received by the outbox from c2s
    """
    if not messageJson.get('type'):
        if debug:
            print('DEBUG: undo block - no type')
        return
    if not messageJson['type']=='Undo':
        if debug:
            print('DEBUG: not an undo block')
        return
    if not messageJson.get('object'):
        if debug:
            print('DEBUG: no object in undo block')
        return
    if not isinstance(messageJson['object'], dict):
        if debug:
            print('DEBUG: undo block object is not string')
        return

    if not messageJson['object'].get('type'):
        if debug:
            print('DEBUG: undo block - no type')
        return
    if not messageJson['object']['type']=='Block':
        if debug:
            print('DEBUG: not an undo block')
        return
    if not messageJson['object'].get('object'):
        if debug:
            print('DEBUG: no object in undo block')
        return
    if not isinstance(messageJson['object']['object'], str):
        if debug:
            print('DEBUG: undo block object is not string')
        return
    if debug:
        print('DEBUG: c2s undo block request arrived in outbox')

    messageId=messageJson['object']['object'].replace('/activity','')
    if '/statuses/' not in messageId:
        if debug:
            print('DEBUG: c2s undo block object is not a status')
        return
    if '/users/' not in messageId:
        if debug:
            print('DEBUG: c2s undo block object has no nickname')
        return
    if ':' in domain:
        domain=domain.split(':')[0]
    postFilename=locatePost(baseDir,nickname,domain,messageId)
    if not postFilename:
        if debug:
            print('DEBUG: c2s undo block post not found in inbox or outbox')
            print(messageId)
        return True
    nicknameBlocked=getNicknameFromActor(messageJson['object']['object'])
    domainBlocked,portBlocked=getDomainFromActor(messageJson['object']['object'])
    domainBlockedFull=domainBlocked
    if portBlocked:
        if portBlocked!=80 and portBlocked!=443:
            if ':' not in domainBlocked:
                domainBlockedFull=domainBlocked+':'+str(portBlocked)

    removeBlock(baseDir,nickname,domain, \
                nicknameBlocked,domainBlockedFull)
    if debug:
        print('DEBUG: post undo blocked via c2s - '+postFilename)
