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
    handle=args.nickname+'@'+domain
    accountsDir=baseDir+'/accounts/'+handle
    approveFollowsFilename=accountsDir+'/followrequests.txt'
    if handle not in open(approveFollowsFilename).read():
        return
    with open(approveFollowsFilename+'.new', 'w') as approvefilenew:
        with open(approveFollowsFilename, 'r') as approvefile:
            for approveHandle in approvefile:
                if not approveHandle.startswith(denyHandle):
                    approvefilenew.write(approveHandle)
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
    handle=nickname+'@'+domain
    accountsDir=baseDir+'/accounts/'+handle
    approveFollowsFilename=accountsDir+'/followrequests.txt'
    if not os.path.isfile(approveFollowsFilename):
        if debug:
            print('WARN: Follow requests file '+approveFollowsFilename+' not found')
        return
    if handle not in open(approveFollowsFilename).read():
        if debug:
            print(handle+' not in '+approveFollowsFilename)
        return
    with open(approveFollowsFilename+'.new', 'w') as approvefilenew:
        with open(approveFollowsFilename, 'r') as approvefile:
            for handle in approvefile:
                if handle.startswith(approveHandle):
                    if ':' in handle:
                        port=int(handle.split(':')[1].replace('\n',''))
                    requestsDir=accountsDir+'/requests'
                    followActivityfilename=requestsDir+'/'+handle+'.follow'
                    if os.path.isfile(followActivityfilename):
                        with open(followActivityfilename, 'r') as fp:
                            followJson=commentjson.load(fp)
                            approveNickname=approveHandle.split('@')[0]
                            approveDomain=approveHandle.split('@')[1].replace('\n','')
                            approvePort=port
                            if ':' in approveDomain:
                                approvePort=approveDomain.split(':')[1]
                                approveDomain=approveDomain.split(':')[0]
                            followedAccountAccepts(session,baseDir,httpPrefix, \
                                                   nickname,domain,port, \
                                                   approveNickname,approveDomain,approvePort, \
                                                   followJson['actor'],federationList, \
                                                   followJson,acceptedCaps, \
                                                   sendThreads,postLog, \
                                                   cachedWebfingers,personCache, \
                                                   debug)
                            os.remove(followActivityfilename)
                else:
                    approvefilenew.write(handle)
    os.rename(approveFollowsFilename+'.new',approveFollowsFilename)
