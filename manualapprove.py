__filename__ = "manualapprove.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "0.0.1"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import os
import json
import commentjson

from follow import followedAccountAccepts

def manualDenyFollowRequest(baseDir: str,nickname: str,domain: str,denyHandle: str) -> None:
    """Manually deny a follow request
    """
    handle=nickname+'@'+domain
    accountsDir=baseDir+'/accounts/'+handle
    approveFollowsFilename=accountsDir+'/followrequests.txt'
    if not os.path.isfile(approveFollowsFilename):
        if debug:
            print('WARN: Follow requests file '+approveFollowsFilename+' not found')
        return
    if denyHandle not in open(approveFollowsFilename).read():
        return
    approvefilenew = open(approveFollowsFilename+'.new', 'w+')
    with open(approveFollowsFilename, 'r') as approvefile:
        for approveHandle in approvefile:
            if not approveHandle.startswith(denyHandle):
                approvefilenew.write(approveHandle)
    approvefilenew.close()
    os.rename(approveFollowsFilename+'.new',approveFollowsFilename)
    print('Follow request from '+denyHandle+' was denied.')
    
def manualApproveFollowRequest(session,baseDir: str, \
                               httpPrefix: str,
                               nickname: str,domain: str,port: int, \
                               approveHandle: str, \
                               federationList: [], \
                               sendThreads: [],postLog: [], \
                               cachedWebfingers: {},personCache: {}, \
                               acceptedCaps: [], \
                               debug: bool) -> None:
    """Manually approve a follow request
    """
    print('Test3')
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
    print('Test4')
    approvefilenew = open(approveFollowsFilename+'.new', 'w+')
    with open(approveFollowsFilename, 'r') as approvefile:
        for handle in approvefile:
            if handle.startswith(approveHandle):
                print('Test5: '+handle)
                port2=port
                if ':' in handle:
                    port2=int(handle.split(':')[1].replace('\n',''))
                requestsDir=accountsDir+'/requests'
                followActivityfilename=requestsDir+'/'+handle+'.follow'
                print('Test6: '+followActivityfilename)
                if os.path.isfile(followActivityfilename):
                    print('Test6')
                    with open(followActivityfilename, 'r') as fp:
                        print('Test7')
                        followJson=commentjson.load(fp)
                        approveNickname=approveHandle.split('@')[0]
                        approveDomain=approveHandle.split('@')[1].replace('\n','')
                        approvePort=port2
                        if ':' in approveDomain:
                            approvePort=approveDomain.split(':')[1]
                            approveDomain=approveDomain.split(':')[0]
                        print('Test8: '+approveNickname+' '+approveDomain+' '+approvePort+' '+followJson['actor'])
                        followedAccountAccepts(session,baseDir,httpPrefix, \
                                               nickname,domain,port, \
                                               approveNickname,approveDomain,approvePort, \
                                               followJson['actor'],federationList, \
                                               followJson,acceptedCaps, \
                                               sendThreads,postLog, \
                                               cachedWebfingers,personCache, \
                                               debug)
                        print("Test9")
                        os.remove(followActivityfilename)
            else:
                approvefilenew.write(handle)
    approvefilenew.close()
    os.rename(approveFollowsFilename+'.new',approveFollowsFilename)
