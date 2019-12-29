__filename__ = "manualapprove.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.1.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import os
import json
import time
from follow import followedAccountAccepts
from follow import followedAccountRejects
from follow import removeFromFollowRequests
from utils import loadJson
from utils import saveJson

def manualDenyFollowRequest(session,baseDir: str, \
                            httpPrefix: str,
                            nickname: str,domain: str,port: int, \
                            denyHandle: str, \
                            federationList: [], \
                            sendThreads: [],postLog: [], \
                            cachedWebfingers: {},personCache: {}, \
                            debug: bool, \
                            projectVersion: str) -> None:
    """Manually deny a follow request
    """
    handle=nickname+'@'+domain
    accountsDir=baseDir+'/accounts/'+handle

    # has this handle already been rejected?
    rejectedFollowsFilename=accountsDir+'/followrejects.txt'
    if os.path.isfile(rejectedFollowsFilename):
        if denyHandle in open(rejectedFollowsFilename).read():
            removeFromFollowRequests(baseDir,nickname,domain,denyHandle,debug)        
            print(denyHandle+' has already been rejected as a follower of '+nickname)
            return

    removeFromFollowRequests(baseDir,nickname,domain,denyHandle,debug)        

    # Store rejected follows
    rejectsFile=open(rejectedFollowsFilename, "a+")
    rejectsFile.write(denyHandle+'\n')
    rejectsFile.close()
    
    denyNickname=denyHandle.split('@')[0]
    denyDomain=denyHandle.split('@')[1].replace('\n','')
    denyPort=port
    if ':' in denyDomain:
        denyPort=denyDomain.split(':')[1]
        denyDomain=denyDomain.split(':')[0]
    followedAccountRejects(session,baseDir,httpPrefix, \
                           nickname,domain,port, \
                           denyNickname,denyDomain,denyPort, \
                           federationList, \
                           sendThreads,postLog, \
                           cachedWebfingers,personCache, \
                           debug,projectVersion)

    print('Follow request from '+denyHandle+' was denied.')
    
def manualApproveFollowRequest(session,baseDir: str, \
                               httpPrefix: str,
                               nickname: str,domain: str,port: int, \
                               approveHandle: str, \
                               federationList: [], \
                               sendThreads: [],postLog: [], \
                               cachedWebfingers: {},personCache: {}, \
                               acceptedCaps: [], \
                               debug: bool, \
                               projectVersion: str) -> None:
    """Manually approve a follow request
    """
    handle=nickname+'@'+domain
    print('Manual follow accept: '+handle+' approving follow request from '+approveHandle)
    accountDir=baseDir+'/accounts/'+handle
    approveFollowsFilename=accountDir+'/followrequests.txt'
    if not os.path.isfile(approveFollowsFilename):
        print('Manual follow accept: follow requests file '+approveFollowsFilename+' not found')
        return
    # is the handle in the requests file?
    if approveHandle not in open(approveFollowsFilename).read():
        print('Manual follow accept: '+approveHandle+' not in requests file '+approveFollowsFilename)
        return
    
    approvefilenew = open(approveFollowsFilename+'.new', 'w+')
    updateApprovedFollowers=False
    with open(approveFollowsFilename, 'r') as approvefile:
        for handleOfFollowRequester in approvefile:
            # is this the approved follow?
            if handleOfFollowRequester.startswith(approveHandle):
                handleOfFollowRequester=handleOfFollowRequester.replace('\n','')
                port2=port
                if ':' in handleOfFollowRequester:
                    port2=int(handleOfFollowRequester.split(':')[1])
                requestsDir=accountDir+'/requests'
                followActivityfilename=requestsDir+'/'+handleOfFollowRequester+'.follow'
                if os.path.isfile(followActivityfilename):
                    followJson=loadJson(followActivityfilename)
                    if followJson:
                        approveNickname=approveHandle.split('@')[0]
                        approveDomain=approveHandle.split('@')[1].replace('\n','')
                        approvePort=port2
                        if ':' in approveDomain:
                            approvePort=approveDomain.split(':')[1]
                            approveDomain=approveDomain.split(':')[0]
                        print('Manual follow accept: Sending Accept for '+handle+' follow request from '+approveNickname+'@'+approveDomain)
                        followedAccountAccepts(session,baseDir,httpPrefix, \
                                               nickname,domain,port, \
                                               approveNickname,approveDomain,approvePort, \
                                               followJson['actor'],federationList, \
                                               followJson,acceptedCaps, \
                                               sendThreads,postLog, \
                                               cachedWebfingers,personCache, \
                                               debug,projectVersion)
                        updateApprovedFollowers=True
            else:
                # this isn't the approved follow so it will remain
                # in the requests file
                approvefilenew.write(handleOfFollowRequester)
    approvefilenew.close()

    followersFilename=accountDir+'/followers.txt'
    if updateApprovedFollowers:
        # update the followers
        print('Manual follow accept: updating '+followersFilename)
        if os.path.isfile(followersFilename):
            if approveHandle not in open(followersFilename).read():
                try:
                    with open(followersFilename, 'r+') as followersFile:
                        content = followersFile.read()
                        followersFile.seek(0, 0)
                        followersFile.write(approveHandle+'\n'+content)
                except Exception as e:
                    print('WARN: Manual follow accept. Failed to write entry to followers file '+str(e))
            else:
                print('WARN: Manual follow accept: '+approveHandle+' already exists in '+followersFilename)
        else:
            print('Manual follow accept: first follower accepted for '+handle+' is '+approveHandle)
            followersFile=open(followersFilename, "w+")
            followersFile.write(approveHandle+'\n')
            followersFile.close()

    # only update the follow requests file if the follow is confirmed to be
    # in followers.txt
    if approveHandle in open(followersFilename).read():
        # update the follow requests with the handles not yet approved
        os.rename(approveFollowsFilename+'.new',approveFollowsFilename)
    else:
        os.remove(approveFollowsFilename+'.new')
