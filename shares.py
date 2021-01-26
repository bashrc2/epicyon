__filename__ = "shares.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import os
import time
from webfinger import webfingerHandle
from auth import createBasicAuthHeader
from posts import getPersonBox
from session import postJson
from session import postImage
from utils import getFullDomain
from utils import validNickname
from utils import loadJson
from utils import saveJson
from utils import getImageExtensions
from media import removeMetaData


def getValidSharedItemID(displayName: str) -> str:
    """Removes any invalid characters from the display name to
    produce an item ID
    """
    removeChars = (' ', '\n', '\r')
    for ch in removeChars:
        displayName = displayName.replace(ch, '')
    removeChars2 = ('+', '/', '\\', '?', '&')
    for ch in removeChars2:
        displayName = displayName.replace(ch, '-')
    displayName = displayName.replace('.', '_')
    displayName = displayName.replace("’", "'")
    return displayName


def removeShare(baseDir: str, nickname: str, domain: str,
                displayName: str) -> None:
    """Removes a share for a person
    """
    sharesFilename = baseDir + '/accounts/' + \
        nickname + '@' + domain + '/shares.json'
    if not os.path.isfile(sharesFilename):
        print('ERROR: missing shares.json ' + sharesFilename)
        return

    sharesJson = loadJson(sharesFilename)
    if not sharesJson:
        print('ERROR: shares.json could not be loaded from ' + sharesFilename)
        return

    itemID = getValidSharedItemID(displayName)
    if sharesJson.get(itemID):
        # remove any image for the item
        itemIDfile = baseDir + '/sharefiles/' + nickname + '/' + itemID
        if sharesJson[itemID]['imageUrl']:
            formats = getImageExtensions()
            for ext in formats:
                if sharesJson[itemID]['imageUrl'].endswith('.' + ext):
                    if os.path.isfile(itemIDfile + '.' + ext):
                        os.remove(itemIDfile + '.' + ext)
        # remove the item itself
        del sharesJson[itemID]
        saveJson(sharesJson, sharesFilename)
    else:
        print('ERROR: share index "' + itemID +
              '" does not exist in ' + sharesFilename)


def addShare(baseDir: str,
             httpPrefix: str, nickname: str, domain: str, port: int,
             displayName: str, summary: str, imageFilename: str,
             itemType: str, itemCategory: str, location: str,
             duration: str, debug: bool) -> None:
    """Adds a new share
    """
    sharesFilename = baseDir + '/accounts/' + \
        nickname + '@' + domain + '/shares.json'
    sharesJson = {}
    if os.path.isfile(sharesFilename):
        sharesJson = loadJson(sharesFilename)

    duration = duration.lower()
    durationSec = 0
    published = int(time.time())
    if ' ' in duration:
        durationList = duration.split(' ')
        if durationList[0].isdigit():
            if 'hour' in durationList[1]:
                durationSec = published + (int(durationList[0]) * 60 * 60)
            if 'day' in durationList[1]:
                durationSec = published + (int(durationList[0]) * 60 * 60 * 24)
            if 'week' in durationList[1]:
                durationSec = \
                    published + (int(durationList[0]) * 60 * 60 * 24 * 7)
            if 'month' in durationList[1]:
                durationSec = \
                    published + (int(durationList[0]) * 60 * 60 * 24 * 30)
            if 'year' in durationList[1]:
                durationSec = \
                    published + (int(durationList[0]) * 60 * 60 * 24 * 365)

    itemID = getValidSharedItemID(displayName)

    # has an image for this share been uploaded?
    imageUrl = None
    moveImage = False
    if not imageFilename:
        sharesImageFilename = \
            baseDir + '/accounts/' + nickname + '@' + domain + '/upload'
        formats = getImageExtensions()
        for ext in formats:
            if os.path.isfile(sharesImageFilename + '.' + ext):
                imageFilename = sharesImageFilename + '.' + ext
                moveImage = True

    domainFull = getFullDomain(domain, port)

    # copy or move the image for the shared item to its destination
    if imageFilename:
        if os.path.isfile(imageFilename):
            if not os.path.isdir(baseDir + '/sharefiles'):
                os.mkdir(baseDir + '/sharefiles')
            if not os.path.isdir(baseDir + '/sharefiles/' + nickname):
                os.mkdir(baseDir + '/sharefiles/' + nickname)
            itemIDfile = baseDir + '/sharefiles/' + nickname + '/' + itemID
            formats = getImageExtensions()
            for ext in formats:
                if imageFilename.endswith('.' + ext):
                    removeMetaData(imageFilename, itemIDfile + '.' + ext)
                    if moveImage:
                        os.remove(imageFilename)
                    imageUrl = \
                        httpPrefix + '://' + domainFull + \
                        '/sharefiles/' + nickname + '/' + itemID + '.' + ext

    sharesJson[itemID] = {
        "displayName": displayName,
        "summary": summary,
        "imageUrl": imageUrl,
        "itemType": itemType,
        "category": itemCategory,
        "location": location,
        "published": published,
        "expire": durationSec
    }

    saveJson(sharesJson, sharesFilename)

    # indicate that a new share is available
    for subdir, dirs, files in os.walk(baseDir + '/accounts'):
        for handle in dirs:
            if '@' not in handle:
                continue
            accountDir = baseDir + '/accounts/' + handle
            newShareFile = accountDir + '/.newShare'
            if not os.path.isfile(newShareFile):
                nickname = handle.split('@')[0]
                try:
                    with open(newShareFile, 'w+') as fp:
                        fp.write(httpPrefix + '://' + domainFull +
                                 '/users/' + nickname + '/tlshares')
                except BaseException:
                    pass
        break


def expireShares(baseDir: str) -> None:
    """Removes expired items from shares
    """
    for subdir, dirs, files in os.walk(baseDir + '/accounts'):
        for account in dirs:
            if '@' not in account:
                continue
            nickname = account.split('@')[0]
            domain = account.split('@')[1]
            _expireSharesForAccount(baseDir, nickname, domain)
        break


def _expireSharesForAccount(baseDir: str, nickname: str, domain: str) -> None:
    """Removes expired items from shares for a particular account
    """
    handleDomain = domain
    if ':' in handleDomain:
        handleDomain = domain.split(':')[0]
    handle = nickname + '@' + handleDomain
    sharesFilename = baseDir + '/accounts/' + handle + '/shares.json'
    if os.path.isfile(sharesFilename):
        sharesJson = loadJson(sharesFilename)
        if sharesJson:
            currTime = int(time.time())
            deleteItemID = []
            for itemID, item in sharesJson.items():
                if currTime > item['expire']:
                    deleteItemID.append(itemID)
            if deleteItemID:
                for itemID in deleteItemID:
                    del sharesJson[itemID]
                    # remove any associated images
                    itemIDfile = \
                        baseDir + '/sharefiles/' + nickname + '/' + itemID
                    formats = getImageExtensions()
                    for ext in formats:
                        if os.path.isfile(itemIDfile + '.' + ext):
                            os.remove(itemIDfile + '.' + ext)
                saveJson(sharesJson, sharesFilename)


def getSharesFeedForPerson(baseDir: str,
                           domain: str, port: int,
                           path: str, httpPrefix: str,
                           sharesPerPage=12) -> {}:
    """Returns the shares for an account from GET requests
    """
    if '/shares' not in path:
        return None
    # handle page numbers
    headerOnly = True
    pageNumber = None
    if '?page=' in path:
        pageNumber = path.split('?page=')[1]
        if pageNumber == 'true':
            pageNumber = 1
        else:
            try:
                pageNumber = int(pageNumber)
            except BaseException:
                pass
        path = path.split('?page=')[0]
        headerOnly = False

    if not path.endswith('/shares'):
        return None
    nickname = None
    if path.startswith('/users/'):
        nickname = path.replace('/users/', '', 1).replace('/shares', '')
    if path.startswith('/@'):
        nickname = path.replace('/@', '', 1).replace('/shares', '')
    if not nickname:
        return None
    if not validNickname(domain, nickname):
        return None

    domain = getFullDomain(domain, port)

    handleDomain = domain
    if ':' in handleDomain:
        handleDomain = domain.split(':')[0]
    handle = nickname + '@' + handleDomain
    sharesFilename = baseDir + '/accounts/' + handle + '/shares.json'

    if headerOnly:
        noOfShares = 0
        if os.path.isfile(sharesFilename):
            sharesJson = loadJson(sharesFilename)
            if sharesJson:
                noOfShares = len(sharesJson.items())
        idStr = httpPrefix + '://' + domain + '/users/' + nickname
        shares = {
            '@context': 'https://www.w3.org/ns/activitystreams',
            'first': idStr+'/shares?page=1',
            'id': idStr+'/shares',
            'totalItems': str(noOfShares),
            'type': 'OrderedCollection'
        }
        return shares

    if not pageNumber:
        pageNumber = 1

    nextPageNumber = int(pageNumber + 1)
    idStr = httpPrefix + '://' + domain + '/users/' + nickname
    shares = {
        '@context': 'https://www.w3.org/ns/activitystreams',
        'id': idStr+'/shares?page='+str(pageNumber),
        'orderedItems': [],
        'partOf': idStr+'/shares',
        'totalItems': 0,
        'type': 'OrderedCollectionPage'
    }

    if not os.path.isfile(sharesFilename):
        print("test5")
        return shares
    currPage = 1
    pageCtr = 0
    totalCtr = 0

    sharesJson = loadJson(sharesFilename)
    if sharesJson:
        for itemID, item in sharesJson.items():
            pageCtr += 1
            totalCtr += 1
            if currPage == pageNumber:
                shares['orderedItems'].append(item)
            if pageCtr >= sharesPerPage:
                pageCtr = 0
                currPage += 1
    shares['totalItems'] = totalCtr
    lastPage = int(totalCtr / sharesPerPage)
    if lastPage < 1:
        lastPage = 1
    if nextPageNumber > lastPage:
        shares['next'] = \
            httpPrefix + '://' + domain + '/users/' + nickname + \
            '/shares?page=' + str(lastPage)
    return shares


def sendShareViaServer(baseDir, session,
                       fromNickname: str, password: str,
                       fromDomain: str, fromPort: int,
                       httpPrefix: str, displayName: str,
                       summary: str, imageFilename: str,
                       itemType: str, itemCategory: str,
                       location: str, duration: str,
                       cachedWebfingers: {}, personCache: {},
                       debug: bool, projectVersion: str) -> {}:
    """Creates an item share via c2s
    """
    if not session:
        print('WARN: No session for sendShareViaServer')
        return 6

    fromDomainFull = getFullDomain(fromDomain, fromPort)

    toUrl = 'https://www.w3.org/ns/activitystreams#Public'
    ccUrl = httpPrefix + '://' + fromDomainFull + \
        '/users/' + fromNickname + '/followers'

    actor = httpPrefix + '://' + fromDomainFull + '/users/' + fromNickname
    newShareJson = {
        "@context": "https://www.w3.org/ns/activitystreams",
        'type': 'Add',
        'actor': actor,
        'target': actor+'/shares',
        'object': {
            "type": "Offer",
            "displayName": displayName,
            "summary": summary,
            "itemType": itemType,
            "category": itemCategory,
            "location": location,
            "duration": duration,
            'to': [toUrl],
            'cc': [ccUrl]
        },
        'to': [toUrl],
        'cc': [ccUrl]
    }

    handle = httpPrefix + '://' + fromDomainFull + '/@' + fromNickname

    # lookup the inbox for the To handle
    wfRequest = \
        webfingerHandle(session, handle, httpPrefix,
                        cachedWebfingers,
                        fromDomain, projectVersion)
    if not wfRequest:
        if debug:
            print('DEBUG: announce webfinger failed for ' + handle)
        return 1
    if not isinstance(wfRequest, dict):
        print('WARN: Webfinger for ' + handle + ' did not return a dict. ' +
              str(wfRequest))
        return 1

    postToBox = 'outbox'

    # get the actor inbox for the To handle
    (inboxUrl, pubKeyId, pubKey,
     fromPersonId, sharedInbox,
     avatarUrl, displayName) = getPersonBox(baseDir, session, wfRequest,
                                            personCache, projectVersion,
                                            httpPrefix, fromNickname,
                                            fromDomain, postToBox,
                                            83653)

    if not inboxUrl:
        if debug:
            print('DEBUG: No ' + postToBox + ' was found for ' + handle)
        return 3
    if not fromPersonId:
        if debug:
            print('DEBUG: No actor was found for ' + handle)
        return 4

    authHeader = createBasicAuthHeader(fromNickname, password)

    if imageFilename:
        headers = {
            'host': fromDomain,
            'Authorization': authHeader
        }
        postResult = \
            postImage(session, imageFilename, [],
                      inboxUrl.replace('/' + postToBox, '/shares'),
                      headers)

    headers = {
        'host': fromDomain,
        'Content-type': 'application/json',
        'Authorization': authHeader
    }
    postResult = \
        postJson(session, newShareJson, [], inboxUrl, headers)
    if not postResult:
        if debug:
            print('DEBUG: POST announce failed for c2s to ' + inboxUrl)
#        return 5

    if debug:
        print('DEBUG: c2s POST share item success')

    return newShareJson


def sendUndoShareViaServer(baseDir: str, session,
                           fromNickname: str, password: str,
                           fromDomain: str, fromPort: int,
                           httpPrefix: str, displayName: str,
                           cachedWebfingers: {}, personCache: {},
                           debug: bool, projectVersion: str) -> {}:
    """Undoes a share via c2s
    """
    if not session:
        print('WARN: No session for sendUndoShareViaServer')
        return 6

    fromDomainFull = getFullDomain(fromDomain, fromPort)

    toUrl = 'https://www.w3.org/ns/activitystreams#Public'
    ccUrl = httpPrefix + '://' + fromDomainFull + \
        '/users/' + fromNickname + '/followers'

    actor = httpPrefix + '://' + fromDomainFull + '/users/' + fromNickname
    undoShareJson = {
        "@context": "https://www.w3.org/ns/activitystreams",
        'type': 'Remove',
        'actor': actor,
        'target': actor + '/shares',
        'object': {
            "type": "Offer",
            "displayName": displayName,
            'to': [toUrl],
            'cc': [ccUrl]
        },
        'to': [toUrl],
        'cc': [ccUrl]
    }

    handle = httpPrefix + '://' + fromDomainFull + '/@' + fromNickname

    # lookup the inbox for the To handle
    wfRequest = \
        webfingerHandle(session, handle, httpPrefix, cachedWebfingers,
                        fromDomain, projectVersion)
    if not wfRequest:
        if debug:
            print('DEBUG: announce webfinger failed for ' + handle)
        return 1
    if not isinstance(wfRequest, dict):
        print('WARN: Webfinger for ' + handle + ' did not return a dict. ' +
              str(wfRequest))
        return 1

    postToBox = 'outbox'

    # get the actor inbox for the To handle
    (inboxUrl, pubKeyId, pubKey,
     fromPersonId, sharedInbox,
     avatarUrl, displayName) = getPersonBox(baseDir, session, wfRequest,
                                            personCache, projectVersion,
                                            httpPrefix, fromNickname,
                                            fromDomain, postToBox,
                                            12663)

    if not inboxUrl:
        if debug:
            print('DEBUG: No '+postToBox+' was found for ' + handle)
        return 3
    if not fromPersonId:
        if debug:
            print('DEBUG: No actor was found for ' + handle)
        return 4

    authHeader = createBasicAuthHeader(fromNickname, password)

    headers = {
        'host': fromDomain,
        'Content-type': 'application/json',
        'Authorization': authHeader
    }
    postResult = \
        postJson(session, undoShareJson, [], inboxUrl, headers)
    if not postResult:
        if debug:
            print('DEBUG: POST announce failed for c2s to ' + inboxUrl)
#        return 5

    if debug:
        print('DEBUG: c2s POST undo share success')

    return undoShareJson


def outboxShareUpload(baseDir: str, httpPrefix: str,
                      nickname: str, domain: str, port: int,
                      messageJson: {}, debug: bool) -> None:
    """ When a shared item is received by the outbox from c2s
    """
    if not messageJson.get('type'):
        return
    if not messageJson['type'] == 'Add':
        return
    if not messageJson.get('object'):
        return
    if not isinstance(messageJson['object'], dict):
        return
    if not messageJson['object'].get('type'):
        if debug:
            print('DEBUG: undo block - no type')
        return
    if not messageJson['object']['type'] == 'Offer':
        if debug:
            print('DEBUG: not an Offer activity')
        return
    if not messageJson['object'].get('displayName'):
        if debug:
            print('DEBUG: displayName missing from Offer')
        return
    if not messageJson['object'].get('summary'):
        if debug:
            print('DEBUG: summary missing from Offer')
        return
    if not messageJson['object'].get('itemType'):
        if debug:
            print('DEBUG: itemType missing from Offer')
        return
    if not messageJson['object'].get('category'):
        if debug:
            print('DEBUG: category missing from Offer')
        return
    if not messageJson['object'].get('location'):
        if debug:
            print('DEBUG: location missing from Offer')
        return
    if not messageJson['object'].get('duration'):
        if debug:
            print('DEBUG: duration missing from Offer')
        return
    addShare(baseDir,
             httpPrefix, nickname, domain, port,
             messageJson['object']['displayName'],
             messageJson['object']['summary'],
             messageJson['object']['imageFilename'],
             messageJson['object']['itemType'],
             messageJson['object']['itemCategory'],
             messageJson['object']['location'],
             messageJson['object']['duration'],
             debug)
    if debug:
        print('DEBUG: shared item received via c2s')


def outboxUndoShareUpload(baseDir: str, httpPrefix: str,
                          nickname: str, domain: str, port: int,
                          messageJson: {}, debug: bool) -> None:
    """ When a shared item is removed via c2s
    """
    if not messageJson.get('type'):
        return
    if not messageJson['type'] == 'Remove':
        return
    if not messageJson.get('object'):
        return
    if not isinstance(messageJson['object'], dict):
        return
    if not messageJson['object'].get('type'):
        if debug:
            print('DEBUG: undo block - no type')
        return
    if not messageJson['object']['type'] == 'Offer':
        if debug:
            print('DEBUG: not an Offer activity')
        return
    if not messageJson['object'].get('displayName'):
        if debug:
            print('DEBUG: displayName missing from Offer')
        return
    removeShare(baseDir, nickname, domain,
                messageJson['object']['displayName'])
    if debug:
        print('DEBUG: shared item removed via c2s')
