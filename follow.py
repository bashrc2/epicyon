__filename__ = "follow.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "0.0.1"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import json
from pprint import pprint
import os
import sys
from person import validUsername
from utils import domainPermitted

def followPerson(baseDir: str,username: str, domain: str, followUsername: str, followDomain: str, federationList: [], followFile='following.txt') -> bool:
    """Adds a person to the follow list
    """
    if not domainPermitted(followDomain.lower().replace('\n',''), federationList):
        return False
    handle=username.lower()+'@'+domain.lower()
    handleToFollow=followUsername.lower()+'@'+followDomain.lower()
    if not os.path.isdir(baseDir+'/accounts'):
        os.mkdir(baseDir+'/accounts')
    if not os.path.isdir(baseDir+'/accounts/'+handle):
        os.mkdir(baseDir+'/accounts/'+handle)
    filename=baseDir+'/accounts/'+handle+'/'+followFile
    if os.path.isfile(filename):
        if handleToFollow in open(filename).read():
            return True
        with open(filename, "a") as followfile:
            followfile.write(handleToFollow+'\n')
            return True
    with open(filename, "w") as followfile:
        followfile.write(handleToFollow+'\n')
    return True

def followerOfPerson(baseDir: str,username: str, domain: str, followerUsername: str, followerDomain: str, federationList: []) -> bool:
    """Adds a follower of the given person
    """
    return followPerson(baseDir,username, domain, followerUsername, followerDomain, federationList, 'followers.txt')

def unfollowPerson(baseDir: str,username: str, domain: str, followUsername: str, followDomain: str,followFile='following.txt') -> None:
    """Removes a person to the follow list
    """
    handle=username.lower()+'@'+domain.lower()
    handleToUnfollow=followUsername.lower()+'@'+followDomain.lower()
    if not os.path.isdir(baseDir+'/accounts'):
        os.mkdir(baseDir+'/accounts')
    if not os.path.isdir(baseDir+'/accounts/'+handle):
        os.mkdir(baseDir+'/accounts/'+handle)
    filename=baseDir+'/accounts/'+handle+'/'+followFile
    if os.path.isfile(filename):
        if handleToUnfollow not in open(filename).read():
            return
        with open(filename, "r") as f:
            lines = f.readlines()
        with open(filename, "w") as f:
            for line in lines:
                if line.strip("\n") != handleToUnfollow:
                    f.write(line)

def unfollowerOfPerson(username: str, domain: str, followerUsername: str, followerDomain: str) -> None:
    """Remove a follower of a person
    """
    unfollowPerson(username, domain, followerUsername, followerDomain,'followers.txt')

def clearFollows(baseDir: str,username: str, domain: str,followFile='following.txt') -> None:
    """Removes all follows
    """
    handle=username.lower()+'@'+domain.lower()
    if not os.path.isdir(baseDir+'/accounts'):
        os.mkdir(baseDir+'/accounts')
    if not os.path.isdir(baseDir+'/accounts/'+handle):
        os.mkdir(baseDir+'/accounts/'+handle)
    filename=baseDir+'/accounts/'+handle+'/'+followFile
    if os.path.isfile(filename):
        os.remove(filename)

def clearFollowers(baseDir: str,username: str, domain: str) -> None:
    """Removes all followers
    """
    clearFollows(baseDir,username, domain,'followers.txt')

def getNoOfFollows(baseDir: str,username: str,domain: str, followFile='following.txt') -> int:
    """Returns the number of follows or followers
    """
    handle=username.lower()+'@'+domain.lower()
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

def getNoOfFollowers(username: str,domain: str) -> int:
    """Returns the number of followers of the given person
    """
    return getNoOfFollows(username,domain,'followers.txt')

def getFollowingFeed(baseDir: str,domain: str,port: int,path: str,https: bool,followsPerPage=12,followFile='following') -> {}:
    """Returns the following and followers feeds from GET requests
    """
    if '/'+followFile not in path:
        return None
    # handle page numbers
    headerOnly=True
    pageNumber=None    
    if '?page=' in path:
        pageNumber=path.split('?page=')[1]
        if pageNumber=='true':
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
    username=None
    if path.startswith('/users/'):
        username=path.replace('/users/','',1).replace('/'+followFile,'')
    if path.startswith('/@'):
        username=path.replace('/@','',1).replace('/'+followFile,'')
    if not username:
        return None
    if not validUsername(username):
        return None
            
    prefix='https'
    if not https:
        prefix='http'

    if port!=80 and port!=443:
        domain=domain+':'+str(port)

    if headerOnly:
        following = {
            '@context': 'https://www.w3.org/ns/activitystreams',
            'first': prefix+'://'+domain+'/users/'+username+'/'+followFile+'?page=1',
            'id': prefix+'://'+domain+'/users/'+username+'/'+followFile,
            'totalItems': getNoOfFollows(username,domain),
            'type': 'OrderedCollection'}
        return following

    if not pageNumber:
        pageNumber=1

    nextPageNumber=int(pageNumber+1)
    following = {
        '@context': 'https://www.w3.org/ns/activitystreams',
        'id': prefix+'://'+domain+'/users/'+username+'/'+followFile+'?page='+str(pageNumber),
        'orderedItems': [],
        'partOf': prefix+'://'+domain+'/users/'+username+'/'+followFile,
        'totalItems': 0,
        'type': 'OrderedCollectionPage'}        

    handle=username.lower()+'@'+domain.lower()
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
                if '@' in line and '.' in line and not line.startswith('http'):
                    pageCtr += 1
                    totalCtr += 1
                    if currPage==pageNumber:
                        url = prefix + '://' + line.lower().replace('\n','').split('@')[1] + \
                            '/users/' + line.lower().replace('\n','').split('@')[0]
                        following['orderedItems'].append(url)
                elif line.startswith('http') and '/users/' in line:
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
        following['next']=prefix+'://'+domain+'/users/'+username+'/'+followFile+'?page='+str(lastPage)
    return following
