__filename__ = "blocking.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "0.0.1"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import os

def addBlock(baseDir: str,nickname: str,domain: str, \
             blockNickname: str,blockDomain: str) -> None:
    """Block the given account
    """
    blockingFilename=baseDir+'/accounts/'+nickname+'@'+domain+'/blocking.txt'
    blockHandle=blockNickName+'@'+blockDomain
    if os.path.isfile(blockingFilename):
        if blockHandle in open(blockingFilename).read():
            return
    blockFile=open(blockingFilename, "a+")
    blockFile.write(blockHandle+'\n')
    blockFile.close()

def removeBlock(baseDir: str,nickname: str,domain: str, \
                unblockNickname: str,unblockDomain: str) -> None:
    """Unblock the given account
    """
    unblockingFilename=baseDir+'/accounts/'+nickname+'@'+domain+'/blocking.txt'
    unblockHandle=unblockNickName+'@'+unblockDomain
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
                    
def isBlocked(baseDir: str,nickname: str,domain: str, \
              blockNickname: str,blockDomain: str) -> bool:
    """Is the given nickname blocked?
    """
    blockingFilename=baseDir+'/accounts/'+nickname+'@'+domain+'/blocking.txt'
    blockHandle=blockNickName+'@'+blockDomain
    if os.path.isfile(blockingFilename):
        if blockHandle in open(blockingFilename).read():
            return True
    return False

