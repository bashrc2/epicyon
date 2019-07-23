__filename__ = "shares.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "0.0.1"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import json
import commentjson
import os
import time
from shutil import copyfile
from person import validNickname
from webfinger import webfingerHandle
from auth import createBasicAuthHeader
from posts import getPersonBox
from session import postJson
from utils import getNicknameFromActor
from utils import getDomainFromActor

def removeShare(baseDir: str,nickname: str,domain: str, \
                displayName: str) -> None:
    """Removes a share for a person
    """
    sharesFilename=baseDir+'/accounts/'+nickname+'@'+domain+'/shares.json'
    if os.path.isfile(sharesFilename):    
        with open(sharesFilename, 'r') as fp:
            sharesJson=commentjson.load(fp)

    itemID=displayName.replace(' ','')
    if sharesJson.get(itemID):
        # remove any image for the item
        published=sharesJson[itemID]['published']
        itemIDfile=baseDir+'/sharefiles/'+str(published)+itemID
        if sharesJson[itemID]['imageUrl']:
            if sharesJson[itemID]['imageUrl'].endswith('.png'):
                os.remove(itemIDfile+'.png')
            if sharesJson[itemID]['imageUrl'].endswith('.jpg'):
                os.remove(itemIDfile+'.jpg')
            if sharesJson[itemID]['imageUrl'].endswith('.gif'):
                os.remove(itemIDfile+'.gif')
        # remove the item itself
        del sharesJson[itemID]
        with open(sharesFilename, 'w') as fp:
            commentjson.dump(sharesJson, fp, indent=4, sort_keys=True)

def addShare(baseDir: str,nickname: str,domain: str, \
             displayName: str, \
             summary: str, \
             imageFilename: str, \
             itemType: str, \
             itemCategory: str, \
             location: str, \
             duration: str,
             debug: bool) -> None:
    """Updates the likes collection within a post
    """
    sharesFilename=baseDir+'/accounts/'+nickname+'@'+domain+'/shares.json'
    sharesJson={}
    if os.path.isfile(sharesFilename):    
        with open(sharesFilename, 'r') as fp:
            sharesJson=commentjson.load(fp)

    duration=duration.lower()
    durationSec=0
    published=int(time.time())
    if ' ' in duration:
        durationList=duration.split(' ')
        if durationList[0].isdigit():
            if 'hour' in durationList[1]:
                durationSec=published+(int(durationList[0])*60*60)
            if 'day' in durationList[1]:
                durationSec=published+(int(durationList[0])*60*60*24)
            if 'week' in durationList[1]:
                durationSec=published+(int(durationList[0])*60*60*24*7)
            if 'month' in durationList[1]:
                durationSec=published+(int(durationList[0])*60*60*24*30)
            if 'year' in durationList[1]:
                durationSec=published+(int(durationList[0])*60*60*24*365)

    itemID=displayName.replace(' ','')

    imageUrl=None
    if imageFilename:
        if os.path.isfile(imageFilename):
            if not os.path.isdir(baseDir+'/sharefiles'):
                os.mkdir(baseDir+'/sharefiles')
            itemIDfile=baseDir+'/sharefiles/'+str(published)+itemID
            if imageFilename.endswidth('.png'):
                copyfile(imageFilename,itemIDfile+'.png')
                imageUrl='/sharefiles/'+str(published)+itemID+'.png'
            if imageFilename.endswidth('.jpg'):
                copyfile(imageFilename,itemIDfile+'.jpg')
                imageUrl='/sharefiles/'+str(published)+itemID+'.jpg'
            if imageFilename.endswidth('.gif'):
                copyfile(imageFilename,itemIDfile+'.gif')           
                imageUrl='/sharefiles/'+str(published)+itemID+'.gif'

    sharesJson[itemID] = {
        "displayName": displayName,
        "summary": summary,
        "imageUrl": imageUrl,
        "type": itemType,
        "category": category,
        "location": location,
        "published": published,
        "expire": durationSec
    }

    with open(sharesFilename, 'w') as fp:
        commentjson.dump(sharesJson, fp, indent=4, sort_keys=True)

def expireShares(baseDir: str,nickname: str,domain: str) -> None:
    """Removes expired items from shares
    """
    handleDomain=domain
    if ':' in handleDomain:
        handleDomain=domain.split(':')[0]
    handle=nickname+'@'+handleDomain
    sharesFilename=baseDir+'/accounts/'+handle+'/shares.json'    
    if os.path.isfile(sharesFilename):
        with open(sharesFilename, 'r') as fp:
            sharesJson=commentjson.load(fp)
            currTime=int(time.time())
            deleteItemID=[]
            for itemID,item in sharesJson.items():
                if currTime>item['expire']:
                    deleteItemID.append(itemID)
            if deleteItemID:
                for itemID in deleteItemID:
                    del sharesJson[itemID]
                with open(sharesFilename, 'w') as fp:
                    commentjson.dump(sharesJson, fp, indent=4, sort_keys=True)
        
def getSharesFeedForPerson(baseDir: str, \
                           nickname: str,domain: str,port: int, \
                           path: str,httpPrefix: str, \
                           sharesPerPage=12) -> {}:
    """Returns the shares for an account from GET requests
    """
    if '/shares' not in path:
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
    
    if not path.endswith('/shares'):
        return None
    nickname=None
    if path.startswith('/users/'):
        nickname=path.replace('/users/','',1).replace('/shares','')
    if path.startswith('/@'):
        nickname=path.replace('/@','',1).replace('/shares','')
    if not nickname:
        return None
    if not validNickname(nickname):
        return None
            
    if port!=80 and port!=443:
        domain=domain+':'+str(port)

    handleDomain=domain
    if ':' in handleDomain:
        handleDomain=domain.split(':')[0]
    handle=nickname+'@'+handleDomain
    sharesFilename=baseDir+'/accounts/'+handle+'/shares.json'    

    if headerOnly:
        noOfShares=0
        if os.path.isfile(sharesFilename):
            with open(sharesFilename, 'r') as fp:
                sharesJson=commentjson.load(fp)
                noOfShares=len(sharesJson.items())
        shares = {
            '@context': 'https://www.w3.org/ns/activitystreams',
            'first': httpPrefix+'://'+domain+'/users/'+nickname+'/shares?page=1',
            'id': httpPrefix+'://'+domain+'/users/'+nickname+'/shares',
            'totalItems': str(noOfShares),
            'type': 'OrderedCollection'}
        return shares

    if not pageNumber:
        pageNumber=1

    nextPageNumber=int(pageNumber+1)
    shares = {
        '@context': 'https://www.w3.org/ns/activitystreams',
        'id': httpPrefix+'://'+domain+'/users/'+nickname+'/shares?page='+str(pageNumber),
        'orderedItems': [],
        'partOf': httpPrefix+'://'+domain+'/users/'+nickname+'/shares',
        'totalItems': 0,
        'type': 'OrderedCollectionPage'}        

    if not os.path.isfile(sharesFilename):
        return shares
    currPage=1
    pageCtr=0
    totalCtr=0

    with open(sharesFilename, 'r') as fp:
        sharesJson=commentjson.load(fp)
        for itemID,item in sharesJson.items():
            pageCtr += 1
            totalCtr += 1
            if currPage==pageNumber:
                shares['orderedItems'].append(item)
            if pageCtr>=sharesPerPage:
                pageCtr=0
                currPage += 1
    shares['totalItems']=totalCtr
    lastPage=int(totalCtr/sharesPerPage)
    if lastPage<1:
        lastPage=1
    if nextPageNumber>lastPage:
        shares['next']=httpPrefix+'://'+domain+'/users/'+nickname+'/shares?page='+str(lastPage)
    return shares
