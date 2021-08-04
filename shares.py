__filename__ = "shares.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"
__module_group__ = "Timeline"

import os
import re
import secrets
import time
import datetime
from pprint import pprint
from session import getJson
from webfinger import webfingerHandle
from auth import createBasicAuthHeader
from auth import constantTimeStringCheck
from posts import getPersonBox
from session import postJson
from session import postImage
from session import createSession
from utils import dateStringToSeconds
from utils import dateSecondsToString
from utils import getConfigParam
from utils import getFullDomain
from utils import validNickname
from utils import loadJson
from utils import saveJson
from utils import getImageExtensions
from utils import hasObjectDict
from utils import removeDomainPort
from utils import isAccountDir
from utils import acctDir
from utils import isfloat
from media import processMetaData
from filters import isFilteredGlobally
from siteactive import siteIsActive


def _dfcProductTypes() -> []:
    # this list should match the ontology json files
    # eg. ontology/foodTypes.json
    return ['food', 'tool', 'clothes']


def _loadDfcIds(baseDir: str, systemLanguage: str,
                productType: str) -> {}:
    """Loads the product types ontology
    This is used to add an id to shared items
    """
    productTypesFilename = \
        baseDir + '/ontology/custom' + productType.title() + 'Types.json'
    if not os.path.isfile(productTypesFilename):
        productTypesFilename = \
            baseDir + '/ontology/' + productType + 'Types.json'
    productTypes = loadJson(productTypesFilename)
    if not productTypes:
        return None
    if not productTypes.get('@graph'):
        return None
    if len(productTypes['@graph']) == 0:
        return None
    if not productTypes['@graph'][0].get('rdfs:label'):
        return None
    languageExists = False
    for label in productTypes['@graph'][0]['rdfs:label']:
        if not label.get('@language'):
            continue
        if label['@language'] == systemLanguage:
            languageExists = True
            break
    if not languageExists:
        print('productTypes ontology does not contain the language ' +
              systemLanguage)
        return None
    dfcIds = {}
    for item in productTypes['@graph']:
        if not item.get('@id'):
            continue
        if not item.get('rdfs:label'):
            continue
        for label in item['rdfs:label']:
            if not label.get('@language'):
                continue
            if not label.get('@value'):
                continue
            if label['@language'] == systemLanguage:
                dfcIds[label['@value'].lower()] = item['@id']
                break
    return dfcIds


def _getValidSharedItemID(actor: str, displayName: str) -> str:
    """Removes any invalid characters from the display name to
    produce an item ID
    """
    removeChars = (' ', '\n', '\r', '#')
    for ch in removeChars:
        displayName = displayName.replace(ch, '')
    removeChars2 = ('+', '/', '\\', '?', '&')
    for ch in removeChars2:
        displayName = displayName.replace(ch, '-')
    displayName = displayName.replace('.', '_')
    displayName = displayName.replace("’", "'")
    actor = actor.replace('://', '___')
    actor = actor.replace('/', '--')
    return actor + '--shareditems--' + displayName


def removeSharedItem(baseDir: str, nickname: str, domain: str,
                     itemID: str,
                     httpPrefix: str, domainFull: str) -> None:
    """Removes a share for a person
    """
    sharesFilename = acctDir(baseDir, nickname, domain) + '/shares.json'
    if not os.path.isfile(sharesFilename):
        print('ERROR: missing shares.json ' + sharesFilename)
        return

    sharesJson = loadJson(sharesFilename)
    if not sharesJson:
        print('ERROR: shares.json could not be loaded from ' + sharesFilename)
        return

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


def _addShareDurationSec(duration: str, published: int) -> int:
    """Returns the duration for the shared item in seconds
    """
    if ' ' not in duration:
        return 0
    durationList = duration.split(' ')
    if not durationList[0].isdigit():
        return 0
    if 'hour' in durationList[1]:
        return published + (int(durationList[0]) * 60 * 60)
    if 'day' in durationList[1]:
        return published + (int(durationList[0]) * 60 * 60 * 24)
    if 'week' in durationList[1]:
        return published + (int(durationList[0]) * 60 * 60 * 24 * 7)
    if 'month' in durationList[1]:
        return published + (int(durationList[0]) * 60 * 60 * 24 * 30)
    if 'year' in durationList[1]:
        return published + (int(durationList[0]) * 60 * 60 * 24 * 365)
    return 0


def _dfcProductTypeFromCategory(itemCategory: str, translate: {}) -> str:
    """Does the shared item category match a DFC product type?
    If so then return the product type.
    This will be used to select an appropriate ontology file
    such as ontology/foodTypes.json
    """
    productTypesList = _dfcProductTypes()
    categoryLower = itemCategory.lower()
    for productType in productTypesList:
        if translate.get(productType):
            if translate[productType] in categoryLower:
                return productType
        else:
            if productType in categoryLower:
                return productType
    return None


def _getshareDfcId(baseDir: str, systemLanguage: str,
                   itemType: str, itemCategory: str,
                   translate: {}, dfcIds: {} = None) -> str:
    """Attempts to obtain a DFC Id for the shared item,
    based upon productTypes ontology.
    See https://github.com/datafoodconsortium/ontology
    """
    # does the category field match any prodyct type ontology
    # files in the ontology subdirectory?
    matchedProductType = _dfcProductTypeFromCategory(itemCategory, translate)
    if not matchedProductType:
        itemType = itemType.replace(' ', '_')
        itemType = itemType.replace('.', '')
        return 'epicyon#' + itemType
    if not dfcIds:
        dfcIds = _loadDfcIds(baseDir, systemLanguage, matchedProductType)
        if not dfcIds:
            return ''
    itemTypeLower = itemType.lower()
    matchName = ''
    matchId = ''
    for name, uri in dfcIds.items():
        if name not in itemTypeLower:
            continue
        if len(name) > len(matchName):
            matchName = name
            matchId = uri
    if not matchId:
        # bag of words match
        maxMatchedWords = 0
        for name, uri in dfcIds.items():
            words = name.split(' ')
            score = 0
            for wrd in words:
                if wrd in itemTypeLower:
                    score += 1
            if score > maxMatchedWords:
                maxMatchedWords = score
                matchId = uri
    return matchId


def _getshareTypeFromDfcId(dfcUri: str, dfcIds: {}) -> str:
    """Attempts to obtain a share item type from its DFC Id,
    based upon productTypes ontology.
    See https://github.com/datafoodconsortium/ontology
    """
    if dfcUri.startswith('epicyon#'):
        itemType = dfcUri.split('#')[1]
        itemType = itemType.replace('_', ' ')
        return itemType

    for name, uri in dfcIds.items():
        if uri.endswith('#' + dfcUri):
            return name
        elif uri == dfcUri:
            return name
    return None


def _indicateNewShareAvailable(baseDir: str, httpPrefix: str,
                               domainFull: str) -> None:
    """Indicate to each account that a new share is available
    """
    for subdir, dirs, files in os.walk(baseDir + '/accounts'):
        for handle in dirs:
            if not isAccountDir(handle):
                continue
            accountDir = baseDir + '/accounts/' + handle
            newShareFile = accountDir + '/.newShare'
            if os.path.isfile(newShareFile):
                continue
            nickname = handle.split('@')[0]
            try:
                with open(newShareFile, 'w+') as fp:
                    fp.write(httpPrefix + '://' + domainFull +
                             '/users/' + nickname + '/tlshares')
            except BaseException:
                pass
        break


def addShare(baseDir: str,
             httpPrefix: str, nickname: str, domain: str, port: int,
             displayName: str, summary: str, imageFilename: str,
             itemQty: float, itemType: str, itemCategory: str, location: str,
             duration: str, debug: bool, city: str,
             price: str, currency: str,
             systemLanguage: str, translate: {}) -> None:
    """Adds a new share
    """
    if isFilteredGlobally(baseDir,
                          displayName + ' ' + summary + ' ' +
                          itemType + ' ' + itemCategory):
        print('Shared item was filtered due to content')
        return
    sharesFilename = acctDir(baseDir, nickname, domain) + '/shares.json'
    sharesJson = {}
    if os.path.isfile(sharesFilename):
        sharesJson = loadJson(sharesFilename, 1, 2)

    duration = duration.lower()
    published = int(time.time())
    durationSec = _addShareDurationSec(duration, published)

    domainFull = getFullDomain(domain, port)
    actor = httpPrefix + '://' + domainFull + '/users/' + nickname
    itemID = _getValidSharedItemID(actor, displayName)
    dfcId = _getshareDfcId(baseDir, systemLanguage,
                           itemType, itemCategory, translate)

    # has an image for this share been uploaded?
    imageUrl = None
    moveImage = False
    if not imageFilename:
        sharesImageFilename = \
            acctDir(baseDir, nickname, domain) + '/upload'
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
                if not imageFilename.endswith('.' + ext):
                    continue
                processMetaData(baseDir, nickname, domain,
                                imageFilename, itemIDfile + '.' + ext,
                                city)
                if moveImage:
                    os.remove(imageFilename)
                imageUrl = \
                    httpPrefix + '://' + domainFull + \
                    '/sharefiles/' + nickname + '/' + itemID + '.' + ext

    sharesJson[itemID] = {
        "displayName": displayName,
        "summary": summary,
        "imageUrl": imageUrl,
        "itemQty": float(itemQty),
        "dfcId": dfcId,
        "itemType": itemType,
        "category": itemCategory,
        "location": location,
        "published": published,
        "expire": durationSec,
        "itemPrice": price,
        "itemCurrency": currency
    }

    saveJson(sharesJson, sharesFilename)

    _indicateNewShareAvailable(baseDir, httpPrefix, domainFull)


def expireShares(baseDir: str) -> None:
    """Removes expired items from shares
    """
    for subdir, dirs, files in os.walk(baseDir + '/accounts'):
        for account in dirs:
            if not isAccountDir(account):
                continue
            nickname = account.split('@')[0]
            domain = account.split('@')[1]
            _expireSharesForAccount(baseDir, nickname, domain)
        break


def _expireSharesForAccount(baseDir: str, nickname: str, domain: str) -> None:
    """Removes expired items from shares for a particular account
    """
    handleDomain = removeDomainPort(domain)
    handle = nickname + '@' + handleDomain
    sharesFilename = baseDir + '/accounts/' + handle + '/shares.json'
    if not os.path.isfile(sharesFilename):
        return
    sharesJson = loadJson(sharesFilename, 1, 2)
    if not sharesJson:
        return
    currTime = int(time.time())
    deleteItemID = []
    for itemID, item in sharesJson.items():
        if currTime > item['expire']:
            deleteItemID.append(itemID)
    if not deleteItemID:
        return
    for itemID in deleteItemID:
        del sharesJson[itemID]
        # remove any associated images
        itemIDfile = baseDir + '/sharefiles/' + nickname + '/' + itemID
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

    handleDomain = removeDomainPort(domain)
    sharesFilename = acctDir(baseDir, nickname, handleDomain) + '/shares.json'

    if headerOnly:
        noOfShares = 0
        if os.path.isfile(sharesFilename):
            sharesJson = loadJson(sharesFilename)
            if sharesJson:
                noOfShares = len(sharesJson.items())
        idStr = httpPrefix + '://' + domain + '/users/' + nickname
        shares = {
            '@context': 'https://www.w3.org/ns/activitystreams',
            'first': idStr + '/shares?page=1',
            'id': idStr + '/shares',
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
        'id': idStr + '/shares?page=' + str(pageNumber),
        'orderedItems': [],
        'partOf': idStr + '/shares',
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
                item['shareId'] = itemID
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
                       itemQty: float, itemType: str, itemCategory: str,
                       location: str, duration: str,
                       cachedWebfingers: {}, personCache: {},
                       debug: bool, projectVersion: str,
                       itemPrice: str, itemCurrency: str) -> {}:
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
        'target': actor + '/shares',
        'object': {
            "type": "Offer",
            "displayName": displayName,
            "summary": summary,
            "itemQty": float(itemQty),
            "itemType": itemType,
            "category": itemCategory,
            "location": location,
            "duration": duration,
            "itemPrice": itemPrice,
            "itemCurrency": itemCurrency,
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
                        fromDomain, projectVersion, debug, False)
    if not wfRequest:
        if debug:
            print('DEBUG: share webfinger failed for ' + handle)
        return 1
    if not isinstance(wfRequest, dict):
        print('WARN: share webfinger for ' + handle +
              ' did not return a dict. ' + str(wfRequest))
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
            print('DEBUG: share no ' + postToBox +
                  ' was found for ' + handle)
        return 3
    if not fromPersonId:
        if debug:
            print('DEBUG: share no actor was found for ' + handle)
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
        postJson(httpPrefix, fromDomainFull,
                 session, newShareJson, [], inboxUrl, headers, 30, True)
    if not postResult:
        if debug:
            print('DEBUG: POST share failed for c2s to ' + inboxUrl)
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
                        fromDomain, projectVersion, debug, False)
    if not wfRequest:
        if debug:
            print('DEBUG: unshare webfinger failed for ' + handle)
        return 1
    if not isinstance(wfRequest, dict):
        print('WARN: unshare webfinger for ' + handle +
              ' did not return a dict. ' + str(wfRequest))
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
            print('DEBUG: unshare no ' + postToBox +
                  ' was found for ' + handle)
        return 3
    if not fromPersonId:
        if debug:
            print('DEBUG: unshare no actor was found for ' + handle)
        return 4

    authHeader = createBasicAuthHeader(fromNickname, password)

    headers = {
        'host': fromDomain,
        'Content-type': 'application/json',
        'Authorization': authHeader
    }
    postResult = \
        postJson(httpPrefix, fromDomainFull,
                 session, undoShareJson, [], inboxUrl,
                 headers, 30, True)
    if not postResult:
        if debug:
            print('DEBUG: POST unshare failed for c2s to ' + inboxUrl)
#        return 5

    if debug:
        print('DEBUG: c2s POST unshare success')

    return undoShareJson


def getSharedItemsCatalogViaServer(baseDir, session,
                                   nickname: str, password: str,
                                   domain: str, port: int,
                                   httpPrefix: str, debug: bool) -> {}:
    """Returns the shared items catalog via c2s
    """
    if not session:
        print('WARN: No session for getSharedItemsCatalogViaServer')
        return 6

    authHeader = createBasicAuthHeader(nickname, password)

    headers = {
        'host': domain,
        'Content-type': 'application/json',
        'Authorization': authHeader,
        'Accept': 'application/json'
    }
    domainFull = getFullDomain(domain, port)
    url = httpPrefix + '://' + domainFull + '/users/' + nickname + '/catalog'
    if debug:
        print('Shared items catalog request to: ' + url)
    catalogJson = getJson(session, url, headers, None, debug,
                          __version__, httpPrefix, None)
    if not catalogJson:
        if debug:
            print('DEBUG: GET shared items catalog failed for c2s to ' + url)
#        return 5

    if debug:
        print('DEBUG: c2s GET shared items catalog success')

    return catalogJson


def outboxShareUpload(baseDir: str, httpPrefix: str,
                      nickname: str, domain: str, port: int,
                      messageJson: {}, debug: bool, city: str,
                      systemLanguage: str, translate: {}) -> None:
    """ When a shared item is received by the outbox from c2s
    """
    if not messageJson.get('type'):
        return
    if not messageJson['type'] == 'Add':
        return
    if not hasObjectDict(messageJson):
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
    if not messageJson['object'].get('itemQty'):
        if debug:
            print('DEBUG: itemQty missing from Offer')
        return
    if not messageJson['object'].get('itemType'):
        if debug:
            print('DEBUG: itemType missing from Offer')
        return
    if not messageJson['object'].get('category'):
        if debug:
            print('DEBUG: category missing from Offer')
        return
    if not messageJson['object'].get('duration'):
        if debug:
            print('DEBUG: duration missing from Offer')
        return
    itemQty = float(messageJson['object']['itemQty'])
    location = ''
    if messageJson['object'].get('location'):
        location = messageJson['object']['location']
    imageFilename = None
    if messageJson['object'].get('imageFilename'):
        imageFilename = messageJson['object']['imageFilename']
    if debug:
        print('Adding shared item')
        pprint(messageJson)

    addShare(baseDir,
             httpPrefix, nickname, domain, port,
             messageJson['object']['displayName'],
             messageJson['object']['summary'],
             imageFilename,
             itemQty,
             messageJson['object']['itemType'],
             messageJson['object']['category'],
             location,
             messageJson['object']['duration'],
             debug, city,
             messageJson['object']['itemPrice'],
             messageJson['object']['itemCurrency'],
             systemLanguage, translate)
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
    if not hasObjectDict(messageJson):
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
    domainFull = getFullDomain(domain, port)
    removeSharedItem(baseDir, nickname, domain,
                     messageJson['object']['displayName'],
                     httpPrefix, domainFull)
    if debug:
        print('DEBUG: shared item removed via c2s')


def _sharesCatalogParams(path: str) -> (bool, float, float, str):
    """Returns parameters when accessing the shares catalog
    """
    today = False
    minPrice = 0
    maxPrice = 9999999
    matchPattern = None
    if '?' not in path:
        return today, minPrice, maxPrice, matchPattern
    args = path.split('?', 1)[1]
    argList = args.split(';')
    for arg in argList:
        if '=' not in arg:
            continue
        key = arg.split('=')[0].lower()
        value = arg.split('=')[1]
        if key == 'today':
            value = value.lower()
            if 't' in value or 'y' in value or '1' in value:
                today = True
        elif key.startswith('min'):
            if isfloat(value):
                minPrice = float(value)
        elif key.startswith('max'):
            if isfloat(value):
                maxPrice = float(value)
        elif key.startswith('match'):
            matchPattern = value
    return today, minPrice, maxPrice, matchPattern


def sharesCatalogAccountEndpoint(baseDir: str, httpPrefix: str,
                                 nickname: str, domain: str,
                                 domainFull: str,
                                 path: str, debug: bool) -> {}:
    """Returns the endpoint for the shares catalog of a particular account
    See https://github.com/datafoodconsortium/ontology
    """
    today, minPrice, maxPrice, matchPattern = _sharesCatalogParams(path)
    dfcUrl = \
        "http://static.datafoodconsortium.org/ontologies/DFC_FullModel.owl#"
    dfcPtUrl = \
        "http://static.datafoodconsortium.org/data/productTypes.rdf#"
    owner = httpPrefix + '://' + domainFull + '/users/' + nickname
    dfcInstanceId = owner + '/catalog'
    endpoint = {
        "@context": {
            "DFC": dfcUrl,
            "dfc-pt": dfcPtUrl,
            "@base": "http://maPlateformeNationale"
        },
        "@id": dfcInstanceId,
        "@type": "DFC:Entreprise",
        "DFC:supplies": []
    }

    currDate = datetime.datetime.utcnow()
    currDateStr = currDate.strftime("%Y-%m-%d")

    sharesFilename = acctDir(baseDir, nickname, domain) + '/shares.json'
    if not os.path.isfile(sharesFilename):
        if debug:
            print('shares.json file not found: ' + sharesFilename)
        return endpoint
    sharesJson = loadJson(sharesFilename, 1, 2)
    if not sharesJson:
        if debug:
            print('Unable to load json for ' + sharesFilename)
        return endpoint

    for itemID, item in sharesJson.items():
        if not item.get('dfcId'):
            if debug:
                print('Item does not have dfcId: ' + itemID)
            continue
        if '#' not in item['dfcId']:
            continue
        if today:
            if not item['published'].startswith(currDateStr):
                continue
        if minPrice is not None:
            if float(item['itemPrice']) < minPrice:
                continue
        if maxPrice is not None:
            if float(item['itemPrice']) > maxPrice:
                continue
        description = item['displayName'] + ': ' + item['summary']
        if matchPattern:
            if not re.match(matchPattern, description):
                continue

        expireDate = datetime.datetime.fromtimestamp(item['expire'])
        expireDateStr = expireDate.strftime("%Y-%m-%dT%H:%M:%SZ")

        shareId = _getValidSharedItemID(owner, item['displayName'])
        if item['dfcId'].startswith('epicyon#'):
            dfcId = "epicyon:" + item['dfcId'].split('#')[1]
        else:
            dfcId = "dfc-pt:" + item['dfcId'].split('#')[1]
        priceStr = item['itemPrice'] + ' ' + item['itemCurrency']
        catalogItem = {
            "@id": shareId,
            "@type": "DFC:SuppliedProduct",
            "DFC:hasType": dfcId,
            "DFC:startDate": item['published'],
            "DFC:expiryDate": expireDateStr,
            "DFC:quantity": float(item['itemQty']),
            "DFC:price": priceStr,
            "DFC:Image": item['imageUrl'],
            "DFC:description": description
        }
        endpoint['DFC:supplies'].append(catalogItem)

    return endpoint


def sharesCatalogEndpoint(baseDir: str, httpPrefix: str,
                          domainFull: str,
                          path: str) -> {}:
    """Returns the endpoint for the shares catalog for the instance
    See https://github.com/datafoodconsortium/ontology
    """
    today, minPrice, maxPrice, matchPattern = _sharesCatalogParams(path)
    dfcUrl = \
        "http://static.datafoodconsortium.org/ontologies/DFC_FullModel.owl#"
    dfcPtUrl = \
        "http://static.datafoodconsortium.org/data/productTypes.rdf#"
    dfcInstanceId = httpPrefix + '://' + domainFull + '/catalog'
    endpoint = {
        "@context": {
            "DFC": dfcUrl,
            "dfc-pt": dfcPtUrl,
            "@base": "http://maPlateformeNationale"
        },
        "@id": dfcInstanceId,
        "@type": "DFC:Entreprise",
        "DFC:supplies": []
    }

    currDate = datetime.datetime.utcnow()
    currDateStr = currDate.strftime("%Y-%m-%d")

    for subdir, dirs, files in os.walk(baseDir + '/accounts'):
        for acct in dirs:
            if not isAccountDir(acct):
                continue
            nickname = acct.split('@')[0]
            domain = acct.split('@')[1]
            owner = httpPrefix + '://' + domainFull + '/users/' + nickname

            sharesFilename = \
                acctDir(baseDir, nickname, domain) + '/shares.json'
            if not os.path.isfile(sharesFilename):
                continue
            print('Test 78363 ' + sharesFilename)
            sharesJson = loadJson(sharesFilename, 1, 2)
            if not sharesJson:
                continue

            for itemID, item in sharesJson.items():
                if not item.get('dfcId'):
                    continue
                if '#' not in item['dfcId']:
                    continue
                if today:
                    if not item['published'].startswith(currDateStr):
                        continue
                if minPrice is not None:
                    if float(item['itemPrice']) < minPrice:
                        continue
                if maxPrice is not None:
                    if float(item['itemPrice']) > maxPrice:
                        continue
                description = item['displayName'] + ': ' + item['summary']
                if matchPattern:
                    if not re.match(matchPattern, description):
                        continue

                startDateStr = dateSecondsToString(item['published'])
                expireDateStr = dateSecondsToString(item['expire'])
                shareId = _getValidSharedItemID(owner, item['displayName'])
                if item['dfcId'].startswith('epicyon#'):
                    dfcId = "epicyon:" + item['dfcId'].split('#')[1]
                else:
                    dfcId = "dfc-pt:" + item['dfcId'].split('#')[1]
                priceStr = item['itemPrice'] + ' ' + item['itemCurrency']
                catalogItem = {
                    "@id": shareId,
                    "@type": "DFC:SuppliedProduct",
                    "DFC:hasType": dfcId,
                    "DFC:startDate": startDateStr,
                    "DFC:expiryDate": expireDateStr,
                    "DFC:quantity": float(item['itemQty']),
                    "DFC:price": priceStr,
                    "DFC:Image": item['imageUrl'],
                    "DFC:description": description
                }
                endpoint['DFC:supplies'].append(catalogItem)

    return endpoint


def sharesCatalogCSVEndpoint(baseDir: str, httpPrefix: str,
                             domainFull: str,
                             path: str) -> str:
    """Returns a CSV version of the shares catalog
    """
    catalogJson = \
        sharesCatalogEndpoint(baseDir, httpPrefix, domainFull, path)
    if not catalogJson:
        return ''
    if not catalogJson.get('DFC:supplies'):
        return ''
    csvStr = \
        'id,type,hasType,startDate,expiryDate,' + \
        'quantity,price,currency,Image,description,\n'
    for item in catalogJson['DFC:supplies']:
        csvStr += '"' + item['@id'] + '",'
        csvStr += '"' + item['@type'] + '",'
        csvStr += '"' + item['DFC:hasType'] + '",'
        csvStr += '"' + item['DFC:startDate'] + '",'
        csvStr += '"' + item['DFC:expiryDate'] + '",'
        csvStr += str(item['DFC:quantity']) + ','
        csvStr += item['DFC:price'].split(' ')[0] + ','
        csvStr += '"' + item['DFC:price'].split(' ')[1] + '",'
        csvStr += '"' + item['DFC:Image'] + '",'
        description = item['DFC:description'].replace('"', "'")
        csvStr += '"' + description + '",\n'
    return csvStr


def generateSharedItemFederationTokens(sharedItemsFederatedDomains: [],
                                       baseDir: str) -> {}:
    """Generates tokens for shared item federated domains
    """
    if not sharedItemsFederatedDomains:
        return {}

    tokensJson = {}
    if baseDir:
        tokensFilename = \
            baseDir + '/accounts/sharedItemsFederationTokens.json'
        if os.path.isfile(tokensFilename):
            tokensJson = loadJson(tokensFilename, 1, 2)
            if tokensJson is None:
                tokensJson = {}

    tokensAdded = False
    for domain in sharedItemsFederatedDomains:
        if not tokensJson.get(domain):
            tokensJson[domain] = ''
            tokensAdded = True

    if not tokensAdded:
        return tokensJson
    if baseDir:
        saveJson(tokensJson, tokensFilename)
    return tokensJson


def updateSharedItemFederationToken(baseDir: str,
                                    tokenDomain: str, newToken: str,
                                    tokensJson: {} = None) -> {}:
    """Updates an individual token for shared item federation
    """
    if not tokensJson:
        tokensJson = {}
    if baseDir:
        tokensFilename = \
            baseDir + '/accounts/sharedItemsFederationTokens.json'
        if os.path.isfile(tokensFilename):
            tokensJson = loadJson(tokensFilename, 1, 2)
            if tokensJson is None:
                tokensJson = {}
    updateRequired = False
    if tokensJson.get(tokenDomain):
        if tokensJson[tokenDomain] != newToken:
            updateRequired = True
    else:
        updateRequired = True
    if updateRequired:
        tokensJson[tokenDomain] = newToken
        if baseDir:
            saveJson(tokensJson, tokensFilename)
    return tokensJson


def mergeSharedItemTokens(baseDir: str, domain: str,
                          newSharedItemsFederatedDomains: [],
                          tokensJson: {}) -> {}:
    """When the shared item federation domains list has changed, update
    the tokens dict accordingly
    """
    removals = []
    changed = False
    for tokenDomain, tok in tokensJson.items():
        if domain:
            if tokenDomain.startswith(domain):
                continue
        if tokenDomain not in newSharedItemsFederatedDomains:
            removals.append(tokenDomain)
    # remove domains no longer in the federation list
    for tokenDomain in removals:
        del tokensJson[tokenDomain]
        changed = True
    # add new domains from the federation list
    for tokenDomain in newSharedItemsFederatedDomains:
        if tokenDomain not in tokensJson:
            tokensJson[tokenDomain] = ''
            changed = True
    if baseDir and changed:
        tokensFilename = \
            baseDir + '/accounts/sharedItemsFederationTokens.json'
        saveJson(tokensJson, tokensFilename)
    return tokensJson


def createSharedItemFederationToken(baseDir: str,
                                    tokenDomain: str,
                                    tokensJson: {} = None) -> {}:
    """Updates an individual token for shared item federation
    """
    if not tokensJson:
        tokensJson = {}
    if baseDir:
        tokensFilename = \
            baseDir + '/accounts/sharedItemsFederationTokens.json'
        if os.path.isfile(tokensFilename):
            tokensJson = loadJson(tokensFilename, 1, 2)
            if tokensJson is None:
                tokensJson = {}
    if not tokensJson.get(tokenDomain):
        tokensJson[tokenDomain] = secrets.token_urlsafe(64)
        if baseDir:
            saveJson(tokensJson, tokensFilename)
    return tokensJson


def authorizeSharedItems(sharedItemsFederatedDomains: [],
                         baseDir: str,
                         callingDomain: str,
                         authHeader: str,
                         debug: bool,
                         tokensJson: {} = None) -> bool:
    """HTTP simple token check for shared item federation
    """
    if not sharedItemsFederatedDomains:
        # no shared item federation
        return False
    if callingDomain not in sharedItemsFederatedDomains:
        if debug:
            print(callingDomain +
                  ' is not in the shared items federation list')
        return False
    if 'Basic ' in authHeader:
        if debug:
            print('DEBUG: shared item federation should not use basic auth')
        return False
    providedToken = authHeader.replace('\n', '').replace('\r', '').strip()
    if not providedToken:
        if debug:
            print('DEBUG: shared item federation token is empty')
        return False
    if len(providedToken) < 60:
        if debug:
            print('DEBUG: shared item federation token is too small ' +
                  providedToken)
        return False
    if not tokensJson:
        tokensFilename = \
            baseDir + '/accounts/sharedItemsFederationTokens.json'
        if not os.path.isfile(tokensFilename):
            if debug:
                print('DEBUG: shared item federation tokens file missing ' +
                      tokensFilename)
            return False
        tokensJson = loadJson(tokensFilename, 1, 2)
    if not tokensJson:
        return False
    if not tokensJson.get(callingDomain):
        if debug:
            print('DEBUG: shared item federation token ' +
                  'check failed for ' + callingDomain)
        return False
    if not constantTimeStringCheck(tokensJson[callingDomain], providedToken):
        if debug:
            print('DEBUG: shared item federation token ' +
                  'mismatch for ' + callingDomain)
        return False
    return True


def _updateFederatedSharesCache(session, sharedItemsFederatedDomains: [],
                                baseDir: str, domain: str,
                                httpPrefix: str,
                                tokensJson: {}, debug: bool,
                                systemLanguage: str) -> None:
    """Updates the cache of federated shares for the instance.
    This enables shared items to be available even when other instances
    might not be online
    """
    # create directories where catalogs will be stored
    cacheDir = baseDir + '/cache'
    if not os.path.isdir(cacheDir):
        os.mkdir(cacheDir)
    catalogsDir = cacheDir + '/catalogs'
    if not os.path.isdir(catalogsDir):
        os.mkdir(catalogsDir)

    asHeader = {
        'Accept': 'application/ld+json'
    }
    for federatedDomain in sharedItemsFederatedDomains:
        # NOTE: federatedDomain does not have a port extension,
        # so may not work in some situations
        if federatedDomain.startswith(domain):
            # only download from instances other than this one
            continue
        if not tokensJson.get(federatedDomain):
            # token has been obtained for the other domain
            continue
        if not siteIsActive(httpPrefix + '://' + federatedDomain):
            continue
        url = httpPrefix + '://' + federatedDomain + '/catalog'
        asHeader['Authorization'] = tokensJson[federatedDomain]
        catalogJson = getJson(session, url, asHeader, None,
                              debug, __version__, httpPrefix, None)
        if not catalogJson:
            print('WARN: failed to download shared items catalog for ' +
                  federatedDomain)
            continue
        catalogFilename = catalogsDir + '/' + federatedDomain + '.json'
        if saveJson(catalogJson, catalogFilename):
            print('Downloaded shared items catalog for ' + federatedDomain)
            sharesJson = _dfcToSharesFormat(catalogJson,
                                            baseDir, systemLanguage)
            if sharesJson:
                sharesFilename = \
                    catalogsDir + '/' + federatedDomain + '.shares.json'
                saveJson(sharesJson, sharesFilename)
                print('Converted shares catalog for ' + federatedDomain)
        else:
            time.sleep(2)


def runFederatedSharesWatchdog(projectVersion: str, httpd) -> None:
    """This tries to keep the federated shares update thread
    running even if it dies
    """
    print('Starting federated shares watchdog')
    federatedSharesOriginal = \
        httpd.thrPostSchedule.clone(runFederatedSharesDaemon)
    httpd.thrFederatedSharesDaemon.start()
    while True:
        time.sleep(55)
        if httpd.thrFederatedSharesDaemon.is_alive():
            continue
        httpd.thrFederatedSharesDaemon.kill()
        httpd.thrFederatedSharesDaemon = \
            federatedSharesOriginal.clone(runFederatedSharesDaemon)
        httpd.thrFederatedSharesDaemon.start()
        print('Restarting federated shares daemon...')


def runFederatedSharesDaemon(baseDir: str, httpd, httpPrefix: str,
                             domain: str, proxyType: str, debug: bool,
                             systemLanguage: str) -> None:
    """Runs the daemon used to update federated shared items
    """
    secondsPerHour = 60 * 60
    fileCheckIntervalSec = 120
    time.sleep(60)
    while True:
        sharedItemsFederatedDomainsStr = \
            getConfigParam(baseDir, 'sharedItemsFederatedDomains')
        if not sharedItemsFederatedDomainsStr:
            time.sleep(fileCheckIntervalSec)
            continue

        # get a list of the domains within the shared items federation
        sharedItemsFederatedDomains = []
        sharedItemsFederatedDomainsList = \
            sharedItemsFederatedDomainsStr.split(',')
        for sharedFederatedDomain in sharedItemsFederatedDomainsList:
            sharedItemsFederatedDomains.append(sharedFederatedDomain.strip())
        if not sharedItemsFederatedDomains:
            time.sleep(fileCheckIntervalSec)
            continue

        # load the tokens
        tokensFilename = \
            baseDir + '/accounts/sharedItemsFederationTokens.json'
        if not os.path.isfile(tokensFilename):
            time.sleep(fileCheckIntervalSec)
            continue
        tokensJson = loadJson(tokensFilename, 1, 2)
        if not tokensJson:
            time.sleep(fileCheckIntervalSec)
            continue

        session = createSession(proxyType)
        _updateFederatedSharesCache(session, sharedItemsFederatedDomains,
                                    baseDir, domain, httpPrefix, tokensJson,
                                    debug, systemLanguage)
        time.sleep(secondsPerHour * 6)


def _dfcToSharesFormat(catalogJson: {},
                       baseDir: str, systemLanguage: str) -> {}:
    """Converts DFC format into the internal formal used to store shared items.
    This simplifies subsequent search and display
    """
    if not catalogJson.get('DFC:supplies'):
        return {}
    sharesJson = {}

    dfcIds = {}
    productTypesList = _dfcProductTypes()
    for productType in productTypesList:
        dfcIds[productType] = _loadDfcIds(baseDir, systemLanguage, productType)

    currTime = int(time.time())
    for item in catalogJson['DFC:supplies']:
        if not item.get('@id') or \
           not item.get('@type') or \
           not item.get('DFC:hasType') or \
           not item.get('DFC:startDate') or \
           not item.get('DFC:expiryDate') or \
           not item.get('DFC:quantity') or \
           not item.get('DFC:price') or \
           not item.get('DFC:Image') or \
           not item.get('DFC:description'):
            continue

        if ' ' not in item['DFC:price']:
            continue
        if ':' not in item['DFC:description']:
            continue
        if ':' not in item['DFC:hasType']:
            continue

        startTimeSec = dateStringToSeconds(item['DFC:startDate'])
        if not startTimeSec:
            continue
        expiryTimeSec = dateStringToSeconds(item['DFC:expiryDate'])
        if not expiryTimeSec:
            continue
        if expiryTimeSec < currTime:
            # has expired
            continue

        if item['DFC:hasType'].startswith('epicyon:'):
            itemType = item['DFC:hasType'].split(':')[1]
            itemType = itemType.replace('_', ' ')
            itemCategory = 'non-food'
            productType = None
        else:
            hasType = item['DFC:hasType'].split(':')[1]
            itemType = None
            productType = None
            for prodType in productTypesList:
                itemType = _getshareTypeFromDfcId(hasType, dfcIds[prodType])
                if itemType:
                    productType = prodType
                    break
            itemCategory = 'food'
        if not itemType:
            continue

        allText = item['DFC:description'] + ' ' + itemType + ' ' + itemCategory
        if isFilteredGlobally(baseDir, allText):
            continue

        dfcId = None
        if productType:
            dfcId = dfcIds[productType][itemType]
        itemID = item['@id']
        description = item['DFC:description'].split(':', 1)[1].strip()

        sharesJson[itemID] = {
            "displayName": item['DFC:description'].split(':')[0],
            "summary": description,
            "imageUrl": item['DFC:Image'],
            "itemQty": float(item['DFC:quantity']),
            "dfcId": dfcId,
            "itemType": itemType,
            "category": itemCategory,
            "location": "",
            "published": startTimeSec,
            "expire": expiryTimeSec,
            "itemPrice": item['DFC:price'].split(' ')[0],
            "itemCurrency": item['DFC:price'].split(' ')[1]
        }
    return sharesJson
