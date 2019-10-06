__filename__ = "follow.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.0.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import json
import commentjson
from pprint import pprint
import os
import sys
from utils import validNickname
from utils import domainPermitted
from utils import getDomainFromActor
from utils import getNicknameFromActor
from utils import getStatusNumber
from utils import followPerson
from posts import sendSignedJson
from posts import getPersonBox
from acceptreject import createAccept
from acceptreject import createReject
from webfinger import webfingerHandle
from auth import createBasicAuthHeader
from auth import createPassword
from session import postJson

def removeFromFollowBase(baseDir: str, \
                         nickname: str,domain: str, \
                         acceptOrDenyHandle: str,followFile: str) -> None:
    """Removes a handle from follow requests or rejects file
    """
    handle=nickname+'@'+domain
    accountsDir=baseDir+'/accounts/'+handle
    approveFollowsFilename=accountsDir+'/'+followFile+'.txt'
    if not os.path.isfile(approveFollowsFilename):
        if debug:
            print('WARN: Follow requests file '+approveFollowsFilename+' not found')
        return
    if acceptOrDenyHandle not in open(approveFollowsFilename).read():
        return
    approvefilenew = open(approveFollowsFilename+'.new', 'w+')
    with open(approveFollowsFilename, 'r') as approvefile:
        for approveHandle in approvefile:
            if not approveHandle.startswith(acceptOrDenyHandle):
                approvefilenew.write(approveHandle)
    approvefilenew.close()
    os.rename(approveFollowsFilename+'.new',approveFollowsFilename)

def removeFromFollowRequests(baseDir: str, \
                             nickname: str,domain: str, \
                             denyHandle: str) -> None:
    """Removes a handle from follow requests
    """
    removeFromFollowBase(baseDir,nickname,domain, \
                         denyHandle,'followrequests')

def removeFromFollowRejects(baseDir: str, \
                            nickname: str,domain: str, \
                            acceptHandle: str) -> None:
    """Removes a handle from follow rejects
    """
    removeFromFollowBase(baseDir,nickname,domain, \
                         acceptHandle,'followrejects')

def isFollowingActor(baseDir: str,nickname: str,domain: str,actor: str) -> bool:
    """Is the given actor a follower of the given nickname?
    """
    if ':' in domain:
        domain=domain.split(':')[0]
    handle=nickname+'@'+domain
    if not os.path.isdir(baseDir+'/accounts/'+handle):
        return False
    followingFile=baseDir+'/accounts/'+handle+'/following.txt'    
    if not os.path.isfile(followingFile):
        return False
    if actor in open(followingFile).read():
        return True
    followingNickname=getNicknameFromActor(actor)
    if not followingNickname:
        print('WARN: unable to find nickname in '+actor)
        return False
    followingDomain,followingPort=getDomainFromActor(actor)
    followingHandle=followingNickname+'@'+followingDomain
    if followingPort:
        if followingPort!=80 and followingPort!=443:
            if ':' not in followingHandle:
                followingHandle+=':'+str(followingPort)
    if followingHandle in open(followingFile).read():
        return True
    return False

def getFollowersOfPerson(baseDir: str, \
                         nickname: str,domain: str, \
                         followFile='following.txt') -> []:
    """Returns a list containing the followers of the given person
    Used by the shared inbox to know who to send incoming mail to
    """
    followers=[]
    if ':' in domain:
        domain=domain.split(':')[0]
    handle=nickname+'@'+domain
    if not os.path.isdir(baseDir+'/accounts/'+handle):
        return followers
    for subdir, dirs, files in os.walk(baseDir+'/accounts'):
        for account in dirs:
            filename = os.path.join(subdir, account)+'/'+followFile
            if account == handle or account.startswith('inbox@'):
                continue
            if not os.path.isfile(filename):
                continue
            with open(filename, 'r') as followingfile:
                for followingHandle in followingfile:
                    if followingHandle.replace('\n','')==handle:
                        if account not in followers:
                            followers.append(account)
                        break
    return followers

def followerOfPerson(baseDir: str,nickname: str, domain: str, \
                     followerNickname: str, followerDomain: str, \
                     federationList: [],debug :bool) -> bool:
    """Adds a follower of the given person
    """
    return followPerson(baseDir,nickname,domain, \
                        followerNickname,followerDomain, \
                        federationList,debug,'followers.txt')

def isFollowerOfPerson(baseDir: str,nickname: str, domain: str, \
                       followerNickname: str, followerDomain: str) -> bool:
    """is the given nickname a follower of followerNickname?
    """
    if ':' in domain:
        domain=domain.split(':')[0]
    followersFile=baseDir+'/accounts/'+nickname+'@'+domain+'/followers.txt'
    if not os.path.isfile(followersFile):
        return False
    return followerNickname+'@'+followerDomain in open(followersFile).read()

def unfollowPerson(baseDir: str,nickname: str, domain: str, \
                   followNickname: str, followDomain: str, \
                   followFile='following.txt', \
                   debug=False) -> bool:
    """Removes a person to the follow list
    """
    if ':' in domain:
        domain=domain.split(':')[0]
    handle=nickname.lower()+'@'+domain.lower()
    handleToUnfollow=followNickname.lower()+'@'+followDomain.lower()
    if not os.path.isdir(baseDir+'/accounts'):
        os.mkdir(baseDir+'/accounts')
    if not os.path.isdir(baseDir+'/accounts/'+handle):
        os.mkdir(baseDir+'/accounts/'+handle)
    filename=baseDir+'/accounts/'+handle+'/'+followFile
    if not os.path.isfile(filename):
        if debug:
            print('DEBUG: follow file '+filename+' was not found')
        return False
    if handleToUnfollow not in open(filename).read():
        if debug:
            print('DEBUG: handle to unfollow '+handleToUnfollow+' is not in '+filename)
        return
    with open(filename, "r") as f:
        lines = f.readlines()
    with open(filename, "w") as f:
        for line in lines:
            if line.strip("\n") != handleToUnfollow:
                f.write(line)

def unfollowerOfPerson(baseDir: str,nickname: str,domain: str, \
                       followerNickname: str,followerDomain: str, \
                       debug=False) -> bool:
    """Remove a follower of a person
    """
    return unfollowPerson(baseDir,nickname,domain, \
                          followerNickname,followerDomain, \
                          'followers.txt',debug)

def clearFollows(baseDir: str,nickname: str,domain: str, \
                 followFile='following.txt') -> None:
    """Removes all follows
    """
    handle=nickname.lower()+'@'+domain.lower()
    if not os.path.isdir(baseDir+'/accounts'):
        os.mkdir(baseDir+'/accounts')
    if not os.path.isdir(baseDir+'/accounts/'+handle):
        os.mkdir(baseDir+'/accounts/'+handle)
    filename=baseDir+'/accounts/'+handle+'/'+followFile
    if os.path.isfile(filename):
        os.remove(filename)

def clearFollowers(baseDir: str,nickname: str,domain: str) -> None:
    """Removes all followers
    """
    clearFollows(baseDir,nickname, domain,'followers.txt')

def getNoOfFollows(baseDir: str,nickname: str,domain: str, \
                   authenticated: bool, \
                   followFile='following.txt') -> int:
    """Returns the number of follows or followers
    """
    # only show number of followers to authenticated
    # account holders
    #if not authenticated:
    #    return 9999
    handle=nickname.lower()+'@'+domain.lower()
    filename=baseDir+'/accounts/'+handle+'/'+followFile
    if not os.path.isfile(filename):
        return 0
    ctr = 0
    with open(filename, "r") as f:
        lines = f.readlines()
        for line in lines:
            if '#' not in line:
                if '@' in line and '.' in line and not line.startswith('http'):
                    ctr += 1
                elif line.startswith('http') and '/users/' in line:
                    ctr += 1
    return ctr

def getNoOfFollowers(baseDir: str,nickname: str,domain: str,authenticated: bool) -> int:
    """Returns the number of followers of the given person
    """
    return getNoOfFollows(baseDir,nickname,domain,authenticated,'followers.txt')

def getFollowingFeed(baseDir: str,domain: str,port: int,path: str, \
                     httpPrefix: str, authenticated: bool,
                     followsPerPage=12, \
                     followFile='following') -> {}:
    """Returns the following and followers feeds from GET requests
    """
    # Show a small number of follows to non-authenticated viewers
    if not authenticated:
        followsPerPage=6

    if '/'+followFile not in path:
        return None
    # handle page numbers
    headerOnly=True
    pageNumber=None    
    if '?page=' in path:
        pageNumber=path.split('?page=')[1]
        if pageNumber=='true' or not authenticated:
            pageNumber=1
        else:
            try:
                pageNumber=int(pageNumber)
            except:
                pass
        path=path.split('?page=')[0]
        headerOnly=False
    
    if not path.endswith('/'+followFile):
        return None
    nickname=None
    if path.startswith('/users/'):
        nickname=path.replace('/users/','',1).replace('/'+followFile,'')
    if path.startswith('/@'):
        nickname=path.replace('/@','',1).replace('/'+followFile,'')
    if not nickname:
        return None
    if not validNickname(domain,nickname):
        return None

    if port:
        if port!=80 and port!=443:
            if ':' not in domain:
                domain=domain+':'+str(port)

    if headerOnly:
        following = {
            '@context': 'https://www.w3.org/ns/activitystreams',
            'first': httpPrefix+'://'+domain+'/users/'+nickname+'/'+followFile+'?page=1',
            'id': httpPrefix+'://'+domain+'/users/'+nickname+'/'+followFile,
            'totalItems': getNoOfFollows(baseDir,nickname,domain,authenticated),
            'type': 'OrderedCollection'}
        return following

    if not pageNumber:
        pageNumber=1

    nextPageNumber=int(pageNumber+1)
    following = {
        '@context': 'https://www.w3.org/ns/activitystreams',
        'id': httpPrefix+'://'+domain+'/users/'+nickname+'/'+followFile+'?page='+str(pageNumber),
        'orderedItems': [],
        'partOf': httpPrefix+'://'+domain+'/users/'+nickname+'/'+followFile,
        'totalItems': 0,
        'type': 'OrderedCollectionPage'}        

    handleDomain=domain
    if ':' in handleDomain:
        handleDomain=domain.split(':')[0]
    handle=nickname.lower()+'@'+handleDomain.lower()
    filename=baseDir+'/accounts/'+handle+'/'+followFile+'.txt'
    if not os.path.isfile(filename):
        return following
    currPage=1
    pageCtr=0
    totalCtr=0
    with open(filename, "r") as f:
        lines = f.readlines()
        for line in lines:
            if '#' not in line:
                if '@' in line and not line.startswith('http'):
                    pageCtr += 1
                    totalCtr += 1
                    if currPage==pageNumber:
                        url = httpPrefix + '://' + line.lower().replace('\n','').split('@')[1] + \
                            '/users/' + line.lower().replace('\n','').split('@')[0]
                        following['orderedItems'].append(url)
                elif (line.startswith('http') or line.startswith('dat')) and '/users/' in line:
                    pageCtr += 1
                    totalCtr += 1
                    if currPage==pageNumber:
                        following['orderedItems'].append(line.lower().replace('\n',''))
            if pageCtr>=followsPerPage:
                pageCtr=0
                currPage += 1
    following['totalItems']=totalCtr
    lastPage=int(totalCtr/followsPerPage)
    if lastPage<1:
        lastPage=1
    if nextPageNumber>lastPage:
        following['next']=httpPrefix+'://'+domain+'/users/'+nickname+'/'+followFile+'?page='+str(lastPage)
    return following

def followApprovalRequired(baseDir: str,nicknameToFollow: str, \
                           domainToFollow: str,debug: bool) -> bool:
    """ Returns the policy for follower approvals
    """
    manuallyApproveFollows=False
    if ':' in domainToFollow:
        domainToFollow=domainToFollow.split(':')[0]
    actorFilename=baseDir+'/accounts/'+nicknameToFollow+'@'+domainToFollow+'.json'
    if os.path.isfile(actorFilename):
        actor=None
        try:
            with open(actorFilename, 'r') as fp:
                actor=commentjson.load(fp)
        except Exception as e:
            print(e)
        if actor:
            if actor.get('manuallyApprovesFollowers'):
                manuallyApproveFollows=actor['manuallyApprovesFollowers']
            else:
                if debug:
                    print('manuallyApprovesFollowers is missing from '+actorFilename)
    else:
        if debug:
            print('DEBUG: Actor file not found: '+actorFilename)
    return manuallyApproveFollows

def storeFollowRequest(baseDir: str, \
                       nicknameToFollow: str,domainToFollow: str,port: int, \
                       nickname: str,domain: str,fromPort: int, \
                       followJson: {}, \
                       debug: bool) -> bool:
    """Stores the follow request for later use
    """
    accountsDir=baseDir+'/accounts/'+nicknameToFollow+'@'+domainToFollow
    if not os.path.isdir(accountsDir):
        return False

    approveHandle=nickname+'@'+domain
    if fromPort:
        if fromPort!=80 and fromPort!=443:
            if ':' not in domain:
                approveHandle=nickname+'@'+domain+':'+str(fromPort)

    followersFilename=accountsDir+'/followers.txt'
    if os.path.isfile(followersFilename):
        if approveHandle in open(followersFilename).read():
            if debug:
                print('DEBUG: '+ \
                      nicknameToFollow+'@'+domainToFollow+ \
                      ' already following '+approveHandle)
            return True

    # should this follow be denied?
    denyFollowsFilename=accountsDir+'/followrejects.txt'
    if os.path.isfile(denyFollowsFilename):
        if approveHandle in open(denyFollowsFilename).read():
            removeFromFollowRequests(baseDir,nicknameToFollow,domainToFollow,approveHandle)
            print(approveHandle+' was already denied as a follower of '+nicknameToFollow)
            return True

    # add to a file which contains a list of requests
    approveFollowsFilename=accountsDir+'/followrequests.txt'
    if os.path.isfile(approveFollowsFilename):
        if approveHandle not in open(approveFollowsFilename).read():
            with open(approveFollowsFilename, "a") as fp:
                fp.write(approveHandle+'\n')
        else:
            if debug:
                print('DEBUG: '+approveHandle+' is already awaiting approval')
    else:
        with open(approveFollowsFilename, "w") as fp:
            fp.write(approveHandle+'\n')

    # store the follow request in its own directory
    # We don't rely upon the inbox because items in there could expire
    requestsDir=accountsDir+'/requests'
    if not os.path.isdir(requestsDir):
        os.mkdir(requestsDir)
    followActivityfilename=requestsDir+'/'+approveHandle+'.follow'
    try:
        with open(followActivityfilename, 'w') as fp:
            commentjson.dump(followJson, fp, indent=4, sort_keys=False)
            return True
    except Exception as e:
        print(e)
    return False

def receiveFollowRequest(session,baseDir: str,httpPrefix: str, \
                         port: int,sendThreads: [],postLog: [], \
                         cachedWebfingers: {},personCache: {}, \
                         messageJson: {},federationList: [], \
                         debug : bool,projectVersion: str, \
                         acceptedCaps=["inbox:write","objects:read"]) -> bool:
    """Receives a follow request within the POST section of HTTPServer
    """
    if not messageJson['type'].startswith('Follow'):
        return False
    print('Receiving follow request')
    if not messageJson.get('actor'):
        if debug:
            print('DEBUG: follow request has no actor')
        return False
    if '/users/' not in messageJson['actor'] and '/profile/' not in messageJson['actor']:
        if debug:
            print('DEBUG: "users" or "profile" missing from actor')            
        return False
    domain,tempPort=getDomainFromActor(messageJson['actor'])
    fromPort=port
    domainFull=domain
    if tempPort:
        fromPort=tempPort
        if tempPort!=80 and tempPort!=443:
            if ':' not in domain:
                domainFull=domain+':'+str(tempPort)
    if not domainPermitted(domain,federationList):
        if debug:
            print('DEBUG: follower from domain not permitted - '+domain)
        return False
    nickname=getNicknameFromActor(messageJson['actor'])
    if not nickname:
        if debug:
            print('DEBUG: follow request does not contain a nickname')
        return False
    if not messageJson.get('to'):
        messageJson['to']=messageJson['object']
    handle=nickname.lower()+'@'+domain.lower()
    if '/users/' not in messageJson['object'] and '/profile/' not in messageJson['object']:
        if debug:
            print('DEBUG: "users" or "profile" not found within object')
        return False
    domainToFollow,tempPort=getDomainFromActor(messageJson['object'])
    if not domainPermitted(domainToFollow,federationList):
        if debug:
            print('DEBUG: follow domain not permitted '+domainToFollow)
        return True
    domainToFollowFull=domainToFollow
    if tempPort:
        if tempPort!=80 and tempPort!=443:
            if ':' not in domainToFollow:
                domainToFollowFull=domainToFollow+':'+str(tempPort)            
    nicknameToFollow=getNicknameFromActor(messageJson['object'])
    if not nicknameToFollow:
        if debug:
            print('DEBUG: follow request does not contain a nickname for the account followed')
        return True
    handleToFollow=nicknameToFollow+'@'+domainToFollow
    if domainToFollow==domain:
        if not os.path.isdir(baseDir+'/accounts/'+handleToFollow):
            if debug:
                print('DEBUG: followed account not found - '+ \
                      baseDir+'/accounts/'+handleToFollow)
            return True
        
    if isFollowerOfPerson(baseDir, \
                          nicknameToFollow,domainToFollowFull, \
                          nickname,domainFull):
        if debug:
            print('DEBUG: '+nickname+'@'+domain+ \
                  ' is already a follower of '+ \
                  nicknameToFollow+'@'+domainToFollow)
        return True
    
    # what is the followers policy?
    if followApprovalRequired(baseDir,nicknameToFollow, \
                              domainToFollow,debug):
        print('Storing follow request for approval')
        return storeFollowRequest(baseDir, \
                                  nicknameToFollow,domainToFollow,port, \
                                  nickname,domain,fromPort,
                                  messageJson,debug)
    else:
        print('Follow request does not require approval')
        # update the followers
        if os.path.isdir(baseDir+'/accounts/'+nicknameToFollow+'@'+domainToFollow):
            followersFilename=baseDir+'/accounts/'+nicknameToFollow+'@'+domainToFollow+'/followers.txt'
            approveHandle=nickname+'@'+domain
            if fromPort:
                approveHandle=approveHandle+':'+str(fromPort)
            print('Updating followers file: '+followersFilename+' adding '+approveHandle)
            if os.path.isfile(followersFilename):
                if approveHandle not in open(followersFilename).read():
                    followersFile=open(followersFilename, "a+")
                    followersFile.write(approveHandle+'\n')
                    followersFile.close()
            else:
                followersFile=open(followersFilename, "w+")
                followersFile.write(approveHandle+'\n')
                followersFile.close()

    print('Beginning follow accept')
    return followedAccountAccepts(session,baseDir,httpPrefix, \
                                  nicknameToFollow,domainToFollow,port, \
                                  nickname,domain,fromPort, \
                                  messageJson['actor'],federationList,
                                  messageJson,acceptedCaps, \
                                  sendThreads,postLog, \
                                  cachedWebfingers,personCache, \
                                  debug,projectVersion)

def followedAccountAccepts(session,baseDir: str,httpPrefix: str, \
                           nicknameToFollow: str,domainToFollow: str,port: int, \
                           nickname: str,domain: str,fromPort: int, \
                           personUrl: str,federationList: [], \
                           followJson: {},acceptedCaps: [], \
                           sendThreads: [],postLog: [], \
                           cachedWebfingers: {},personCache: {}, \
                           debug: bool,projectVersion: str):
    """The person receiving a follow request accepts the new follower
    and sends back an Accept activity
    """
    # send accept back
    if debug:
        print('DEBUG: sending Accept activity for follow request which arrived at '+ \
              nicknameToFollow+'@'+domainToFollow+' back to '+nickname+'@'+domain)
    acceptJson=createAccept(baseDir,federationList, \
                            nicknameToFollow,domainToFollow,port, \
                            personUrl,'',httpPrefix,followJson,acceptedCaps)
    if debug:
        pprint(acceptJson)
        print('DEBUG: sending follow Accept from '+ \
              nicknameToFollow+'@'+domainToFollow+ \
              ' port '+str(port)+' to '+ \
              nickname+'@'+domain+' port '+ str(fromPort))
    clientToServer=False
    return sendSignedJson(acceptJson,session,baseDir, \
                          nicknameToFollow,domainToFollow,port, \
                          nickname,domain,fromPort, '', \
                          httpPrefix,True,clientToServer, \
                          federationList, \
                          sendThreads,postLog,cachedWebfingers, \
                          personCache,debug,projectVersion)

def followedAccountRejects(session,baseDir: str,httpPrefix: str, \
                           nicknameToFollow: str,domainToFollow: str,port: int, \
                           nickname: str,domain: str,fromPort: int, \
                           personUrl: str,federationList: [], \
                           followJson: {}, \
                           sendThreads: [],postLog: [], \
                           cachedWebfingers: {},personCache: {}, \
                           debug: bool,projectVersion: str):
    """The person receiving a follow request rejects the new follower
    and sends back a Reject activity
    """
    # send reject back
    if debug:
        print('DEBUG: sending Reject activity for follow request which arrived at '+ \
              nicknameToFollow+'@'+domainToFollow+' back to '+nickname+'@'+domain)
    rejectJson=createReject(baseDir,federationList, \
                            nicknameToFollow,domainToFollow,port, \
                            personUrl,'',httpPrefix,followJson)
    if debug:
        pprint(rejectJson)
        print('DEBUG: sending follow Reject from '+ \
              nicknameToFollow+'@'+domainToFollow+ \
              ' port '+str(port)+' to '+ \
              nickname+'@'+domain+' port '+ str(fromPort))
    clientToServer=False
    denyHandle=nickname+'@'+domain
    if fromPort:
        if fromPort!=80 and fromPort!=443:
            denyHandle=denyHandle+':'+str(fromPort)
    removeFromFollowRequests(baseDir,nicknameToFollow,domainToFollow,denyHandle)
    return sendSignedJson(rejectJson,session,baseDir, \
                          nicknameToFollow,domainToFollow,port, \
                          nickname,domain,fromPort, '', \
                          httpPrefix,True,clientToServer, \
                          federationList, \
                          sendThreads,postLog,cachedWebfingers, \
                          personCache,debug,projectVersion)

def sendFollowRequest(session,baseDir: str, \
                      nickname: str,domain: str,port: int,httpPrefix: str, \
                      followNickname: str,followDomain: str, \
                      followPort: int,followHttpPrefix: str, \
                      clientToServer: bool,federationList: [], \
                      sendThreads: [],postLog: [],cachedWebfingers: {}, \
                      personCache: {},debug : bool, \
                      projectVersion: str) -> {}:
    """Gets the json object for sending a follow request
    """    
    if not domainPermitted(followDomain,federationList):
        return None

    fullDomain=domain
    followActor=httpPrefix+'://'+domain+'/users/'+nickname
    if port:
        if port!=80 and port!=443:
            if ':' not in domain:
                fullDomain=domain+':'+str(port)
                followActor=httpPrefix+'://'+domain+':'+str(port)+'/users/'+nickname

    requestDomain=followDomain
    if followPort:
        if followPort!=80 and followPort!=443:
            if ':' not in followDomain:
                requestDomain=followDomain+':'+str(followPort)

    statusNumber,published = getStatusNumber()
    
    followedId=followHttpPrefix+'://'+requestDomain+'/users/'+followNickname

    newFollowJson = {
        '@context': 'https://www.w3.org/ns/activitystreams',
        'id': followActor+'/statuses/'+str(statusNumber),
        'type': 'Follow',
        'actor': followActor,
        'object': followedId
    }

    sendSignedJson(newFollowJson,session,baseDir,nickname,domain,port, \
                   followNickname,followDomain,followPort, \
                   'https://www.w3.org/ns/activitystreams#Public', \
                   httpPrefix,True,clientToServer, \
                   federationList, \
                   sendThreads,postLog,cachedWebfingers,personCache, \
                   debug,projectVersion)

    return newFollowJson

def sendFollowRequestViaServer(baseDir: str,session, \
                               fromNickname: str,password: str, \
                               fromDomain: str,fromPort: int, \
                               followNickname: str,followDomain: str,followPort: int, \
                               httpPrefix: str, \
                               cachedWebfingers: {},personCache: {}, \
                               debug: bool,projectVersion: str) -> {}:
    """Creates a follow request via c2s
    """
    if not session:
        print('WARN: No session for sendFollowRequestViaServer')
        return 6

    fromDomainFull=fromDomain
    if fromPort:
        if fromPort!=80 and fromPort!=443:
            if ':' not in fromDomain:
                fromDomainFull=fromDomain+':'+str(fromPort)

    followDomainFull=followDomain
    if followPort:
        if followPort!=80 and followPort!=443:
            if ':' not in followDomain:
                followDomainFull=followDomain+':'+str(followPort)

    followActor=httpPrefix+'://'+fromDomainFull+'/users/'+fromNickname    
    followedId=httpPrefix+'://'+followDomainFull+'/users/'+followNickname

    statusNumber,published = getStatusNumber()
    newFollowJson = {
        '@context': 'https://www.w3.org/ns/activitystreams',
        'id': followActor+'/statuses/'+str(statusNumber),
        'type': 'Follow',
        'actor': followActor,
        'object': followedId
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
        postJson(session,newFollowJson,[],inboxUrl,headers,"inbox:write")
    #if not postResult:
    #    if debug:
    #        print('DEBUG: POST announce failed for c2s to '+inboxUrl)
    #    return 5

    if debug:
        print('DEBUG: c2s POST follow success')

    return newFollowJson

def sendUnfollowRequestViaServer(baseDir: str,session, \
                                 fromNickname: str,password: str, \
                                 fromDomain: str,fromPort: int, \
                                 followNickname: str,followDomain: str,followPort: int, \
                                 httpPrefix: str, \
                                 cachedWebfingers: {},personCache: {}, \
                                 debug: bool,projectVersion: str) -> {}:
    """Creates a unfollow request via c2s
    """
    if not session:
        print('WARN: No session for sendUnfollowRequestViaServer')
        return 6

    fromDomainFull=fromDomain
    if fromPort:
        if fromPort!=80 and fromPort!=443:
            if ':' not in fromDomain:
                fromDomainFull=fromDomain+':'+str(fromPort)
    followDomainFull=followDomain
    if followPort:
        if followPort!=80 and followPort!=443:
            if ':' not in followDomain:
                followDomainFull=followDomain+':'+str(followPort)

    followActor=httpPrefix+'://'+fromDomainFull+'/users/'+fromNickname    
    followedId=httpPrefix+'://'+followDomainFull+'/users/'+followNickname
    statusNumber,published = getStatusNumber()

    unfollowJson = {
        '@context': 'https://www.w3.org/ns/activitystreams',
        'id': followActor+'/statuses/'+str(statusNumber)+'/undo',
        'type': 'Undo',
        'actor': followActor,
        'object': {
            'id': followActor+'/statuses/'+str(statusNumber),
            'type': 'Follow',
            'actor': followActor,
            'object': followedId
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
        postJson(session,unfollowJson,[],inboxUrl,headers,"inbox:write")
    #if not postResult:
    #    if debug:
    #        print('DEBUG: POST announce failed for c2s to '+inboxUrl)
    #    return 5

    if debug:
        print('DEBUG: c2s POST unfollow success')

    return unfollowJson

def getFollowersOfActor(baseDir :str,actor :str,debug: bool) -> {}:
    """In a shared inbox if we receive a post we know who it's from
    and if it's addressed to followers then we need to get a list of those.
    This returns a list of account handles which follow the given actor
    and also the corresponding capability id if it exists
    """
    if debug:
        print('DEBUG: getting followers of '+actor)
    recipientsDict={}
    if ':' not in actor:
        return recipientsDict
    httpPrefix=actor.split(':')[0]
    nickname=getNicknameFromActor(actor)
    if not nickname:
        if debug:
            print('DEBUG: no nickname found in '+actor)
        return recipientsDict
    domain,port=getDomainFromActor(actor)
    if not domain:
        if debug:
            print('DEBUG: no domain found in '+actor)
        return recipientsDict
    actorHandle=nickname+'@'+domain
    if debug:
        print('DEBUG: searching for handle '+actorHandle)
    # for each of the accounts
    for subdir, dirs, files in os.walk(baseDir+'/accounts'):
        for account in dirs:
            if '@' in account and not account.startswith('inbox@'):
                followingFilename = os.path.join(subdir, account)+'/following.txt'
                if debug:
                    print('DEBUG: examining follows of '+account)
                    print(followingFilename)
                if os.path.isfile(followingFilename):
                    # does this account follow the given actor?
                    if debug:
                        print('DEBUG: checking if '+actorHandle+' in '+followingFilename)
                    if actorHandle in open(followingFilename).read():
                        if debug:
                            print('DEBUG: '+account+' follows '+actorHandle)
                        ocapFilename=baseDir+'/accounts/'+account+'/ocap/accept/'+httpPrefix+':##'+domain+':'+str(port)+'#users#'+nickname+'.json'
                        if debug:
                            print('DEBUG: checking capabilities of'+account)
                        if os.path.isfile(ocapFilename):
                            ocapJson=None
                            try:
                                with open(ocapFilename, 'r') as fp:
                                    ocapJson=commentjson.load(fp)
                            except Exception as e:
                                print(e)
                            if ocapJson:
                                if ocapJson.get('id'):
                                    if debug:
                                        print('DEBUG: capabilities id found for '+account)
                
                                    recipientsDict[account]=ocapJson['id']
                                else:
                                    if debug:
                                        print('DEBUG: capabilities has no id attribute')
                                    recipientsDict[account]=None
                        else:
                            if debug:
                                print('DEBUG: No capabilities file found for '+account+' granted by '+actorHandle)
                                print(ocapFilename)
                            recipientsDict[account]=None
    return recipientsDict

def outboxUndoFollow(baseDir: str,messageJson: {},debug: bool) -> None:
    """When an unfollow request is received by the outbox from c2s
    This removes the followed handle from the following.txt file
    of the relevant account
    TODO the unfollow should also be sent to the previously followed account
    """
    if not messageJson.get('type'):
        return
    if not messageJson['type']=='Undo':
        return
    if not messageJson.get('object'):
        return
    if not isinstance(messageJson['object'], dict):
        return
    if not messageJson['object'].get('type'):
        return
    if not messageJson['object']['type']=='Follow':
        return
    if not messageJson['object'].get('object'):
        return
    if not messageJson['object'].get('actor'):
        return
    if not isinstance(messageJson['object']['object'], str):
        return
    if debug:
        print('DEBUG: undo follow arrived in outbox')

    nicknameFollower=getNicknameFromActor(messageJson['object']['actor'])
    if not nicknameFollower:
        print('WARN: unable to find nickname in '+messageJson['object']['actor'])
        return
    domainFollower,portFollower=getDomainFromActor(messageJson['object']['actor'])
    domainFollowerFull=domainFollower
    if portFollower:
        if portFollower!=80 and portFollower!=443:
            if ':' not in domainFollower:
                domainFollowerFull=domainFollower+':'+str(portFollower)
    
    nicknameFollowing=getNicknameFromActor(messageJson['object']['object'])
    if not nicknameFollowing:
        print('WARN: unable to find nickname in '+messageJson['object']['object'])
        return
    domainFollowing,portFollowing=getDomainFromActor(messageJson['object']['object'])
    domainFollowingFull=domainFollowing
    if portFollowing:
        if portFollowing!=80 and portFollowing!=443:
            if ':' not in domainFollowing:
                domainFollowingFull=domainFollowing+':'+str(portFollowing)

    if unfollowPerson(baseDir,nicknameFollower,domainFollowerFull, \
                      nicknameFollowing,domainFollowingFull):
        if debug:
            print('DEBUG: '+nicknameFollower+' unfollowed '+nicknameFollowing+'@'+domainFollowingFull)
    else:
        if debug:
            print('WARN: '+nicknameFollower+' could not unfollow '+nicknameFollowing+'@'+domainFollowingFull)
