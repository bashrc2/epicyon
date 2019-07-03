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
from person import validNickname
from utils import domainPermitted

def followPerson(baseDir: str,nickname: str, domain: str, \
                 followNickname: str, followDomain: str, \
                 federationList: [], followFile='following.txt') -> bool:
    """Adds a person to the follow list
    """
    if not domainPermitted(followDomain.lower().replace('\n',''), federationList):
        return False
    handle=nickname.lower()+'@'+domain.lower()
    handleToFollow=followNickname.lower()+'@'+followDomain.lower()
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

def followerOfPerson(baseDir: str,nickname: str, domain: str, \
                     followerNickname: str, followerDomain: str, \
                     federationList: []) -> bool:
    """Adds a follower of the given person
    """
    return followPerson(baseDir,nickname, domain, \
                        followerNickname, followerDomain, \
                        federationList, 'followers.txt')

def unfollowPerson(baseDir: str,nickname: str, domain: str, \
                   followNickname: str, followDomain: str, \
                   followFile='following.txt') -> None:
    """Removes a person to the follow list
    """
    handle=nickname.lower()+'@'+domain.lower()
    handleToUnfollow=followNickname.lower()+'@'+followDomain.lower()
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

def unfollowerOfPerson(baseDir: str,nickname: str,domain: str, \
                       followerNickname: str,followerDomain: str) -> None:
    """Remove a follower of a person
    """
    unfollowPerson(baseDir,nickname,domain,followerNickname,followerDomain,'followers.txt')

def clearFollows(baseDir: str,nickname: str,domain: str,followFile='following.txt') -> None:
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

def getNoOfFollows(baseDir: str,nickname: str,domain: str,followFile='following.txt') -> int:
    """Returns the number of follows or followers
    """
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

def getNoOfFollowers(baseDir: str,nickname: str,domain: str) -> int:
    """Returns the number of followers of the given person
    """
    return getNoOfFollows(baseDir,nickname,domain,'followers.txt')

def getFollowingFeed(baseDir: str,domain: str,port: int,path: str,httpPrefix: str, \
                     followsPerPage=12,followFile='following') -> {}:
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
    nickname=None
    if path.startswith('/users/'):
        nickname=path.replace('/users/','',1).replace('/'+followFile,'')
    if path.startswith('/@'):
        nickname=path.replace('/@','',1).replace('/'+followFile,'')
    if not nickname:
        return None
    if not validNickname(nickname):
        return None
            
    if port!=80 and port!=443:
        domain=domain+':'+str(port)

    if headerOnly:
        following = {
            '@context': 'https://www.w3.org/ns/activitystreams',
            'first': httpPrefix+'://'+domain+'/users/'+nickname+'/'+followFile+'?page=1',
            'id': httpPrefix+'://'+domain+'/users/'+nickname+'/'+followFile,
            'totalItems': getNoOfFollows(nickname,domain),
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

    handle=nickname.lower()+'@'+domain.lower()
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

def receiveFollowRequest(baseDir: str,messageJson: {},federationList: []) -> bool:
    """Receives a follow request within the POST section of HTTPServer
    """
    if not messageJson['type'].startswith('Follow'):
        return False
    if '/users/' not in messageJson['actor']:
        return False
    domain=messageJson['actor'].split('/users/')[0].replace('https://','').replace('http://','').replace('dat://','')
    if not domainPermitted(domain,federationList):
        return False
    nickname=messageJson['actor'].split('/users/')[1].replace('@','')
    handle=nickname.lower()+'@'+domain.lower()
    if not os.path.isdir(baseDir+'/accounts/'+handle):
        return False
    if '/users/' not in messageJson['object']:
        return False
    domainToFollow=messageJson['object'].split('/users/')[0].replace('https://','').replace('http://','').replace('dat://','')
    if not domainPermitted(domainToFollow,federationList):
        return False
    nicknameToFollow=messageJson['object'].split('/users/')[1].replace('@','')
    handleToFollow=nicknameToFollow.lower()+'@'+domainToFollow.lower()
    if domainToFollow==domain:
        if not os.path.isdir(baseDir+'/accounts/'+handleToFollow):
            return False
    return followerOfPerson(baseDir,nickname,domain,nicknameToFollow,domainToFollow,federationList)

def sendFollowRequest(baseDir: str,nickname: str,domain: str,port: int,httpPrefix: str, \
                      followNickname: str,followDomain: str,followPort: bool,followHttpPrefix: str, \
                      federationList: []) -> {}:
    """Gets the json object for sending a follow request
    """
    if not domainPermitted(followDomain,federationList):
        return None

    if port!=80 and port!=443:
        domain=domain+':'+str(port)

    if followPort!=80 and followPort!=443:
        followDomain=followDomain+':'+str(followPort)

    newFollow = {
        'type': 'Follow',
        'actor': httpPrefix+'://'+domain+'/users/'+nickname,
        'object': followHttpPrefix+'://'+followDomain+'/users/'+followNickname,
        'to': [toUrl],
        'cc': []
    }

    if ccUrl:
        if len(ccUrl)>0:
            newFollow['cc']=ccUrl
    return newFollow
