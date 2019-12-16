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
    print('Manually approving follow request from '+approveHandle)
    handle=nickname+'@'+domain
    accountsDir=baseDir+'/accounts/'+handle
    approveFollowsFilename=accountsDir+'/followrequests.txt'
    if not os.path.isfile(approveFollowsFilename):
        if debug:
            print('WARN: Follow requests file '+approveFollowsFilename+' not found')
        return
    if approveHandle not in open(approveFollowsFilename).read():
        if debug:
            print(handle+' not in '+approveFollowsFilename)
        return
    
    approvefilenew = open(approveFollowsFilename+'.new', 'w+')
    updateApprovedFollowers=False
    with open(approveFollowsFilename, 'r') as approvefile:
        for handle in approvefile:
            if handle.startswith(approveHandle):
                handle=handle.replace('\n','')
                port2=port
                if ':' in handle:
                    port2=int(handle.split(':')[1])
                requestsDir=accountsDir+'/requests'
                followActivityfilename=requestsDir+'/'+handle+'.follow'
                if os.path.isfile(followActivityfilename):
                    followJson=loadJson(followActivityfilename)
                    if followJson:
                        approveNickname=approveHandle.split('@')[0]
                        approveDomain=approveHandle.split('@')[1].replace('\n','')
                        approvePort=port2
                        if ':' in approveDomain:
                            approvePort=approveDomain.split(':')[1]
                            approveDomain=approveDomain.split(':')[0]
                        print('Sending Accept for '+handle+' follow request from '+approveHandle)
                        followedAccountAccepts(session,baseDir,httpPrefix, \
                                               nickname,domain,port, \
                                               approveNickname,approveDomain,approvePort, \
                                               followJson['actor'],federationList, \
                                               followJson,acceptedCaps, \
                                               sendThreads,postLog, \
                                               cachedWebfingers,personCache, \
                                               debug,projectVersion)
                        os.remove(followActivityfilename)
                        updateApprovedFollowers=True
            else:
                approvefilenew.write(handle)
    approvefilenew.close()
    os.rename(approveFollowsFilename+'.new',approveFollowsFilename)

    if updateApprovedFollowers:
        # update the followers
        followersFilename=accountsDir+'/followers.txt'
        if os.path.isfile(followersFilename):
            if approveHandle not in open(followersFilename).read():
                try:
                    with open(followersFilename, 'r+') as followersFile:
                        content = followersFile.read()
                        followersFile.seek(0, 0)
                        followersFile.write(approveHandle+'\n'+content)
                except Exception as e:
                    print('WARN: Failed to write entry to followers file '+str(e))
        else:
            followersFile=open(followersFilename, "w+")
            followersFile.write(approveHandle+'\n')
            followersFile.close()
