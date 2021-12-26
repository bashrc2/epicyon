__filename__ = "shares.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Timeline"

import os
import re
import secrets
import time
import datetime
from random import randint
from pprint import pprint
from session import getJson
from webfinger import webfingerHandle
from auth import createBasicAuthHeader
from auth import constantTimeStringCheck
from posts import getPersonBox
from session import postJson
from session import postImage
from session import createSession
from utils import has_object_stringType
from utils import date_string_to_seconds
from utils import date_seconds_to_string
from utils import get_config_param
from utils import get_full_domain
from utils import validNickname
from utils import load_json
from utils import save_json
from utils import get_image_extensions
from utils import remove_domain_port
from utils import isAccountDir
from utils import acct_dir
from utils import is_float
from utils import get_category_types
from utils import get_shares_files_list
from utils import local_actor_url
from media import processMetaData
from media import convertImageToLowBandwidth
from filters import isFilteredGlobally
from siteactive import siteIsActive
from content import getPriceFromString
from blocking import isBlocked


def _loadDfcIds(base_dir: str, system_language: str,
                productType: str,
                http_prefix: str, domain_full: str) -> {}:
    """Loads the product types ontology
    This is used to add an id to shared items
    """
    productTypesFilename = \
        base_dir + '/ontology/custom' + productType.title() + 'Types.json'
    if not os.path.isfile(productTypesFilename):
        productTypesFilename = \
            base_dir + '/ontology/' + productType + 'Types.json'
    productTypes = load_json(productTypesFilename)
    if not productTypes:
        print('Unable to load ontology: ' + productTypesFilename)
        return None
    if not productTypes.get('@graph'):
        print('No @graph list within ontology')
        return None
    if len(productTypes['@graph']) == 0:
        print('@graph list has no contents')
        return None
    if not productTypes['@graph'][0].get('rdfs:label'):
        print('@graph list entry has no rdfs:label')
        return None
    languageExists = False
    for label in productTypes['@graph'][0]['rdfs:label']:
        if not label.get('@language'):
            continue
        if label['@language'] == system_language:
            languageExists = True
            break
    if not languageExists:
        print('productTypes ontology does not contain the language ' +
              system_language)
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
            if label['@language'] == system_language:
                itemId = \
                    item['@id'].replace('http://static.datafoodconsortium.org',
                                        http_prefix + '://' + domain_full)
                dfcIds[label['@value'].lower()] = itemId
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


def removeSharedItem(base_dir: str, nickname: str, domain: str,
                     itemID: str,
                     http_prefix: str, domain_full: str,
                     sharesFileType: str) -> None:
    """Removes a share for a person
    """
    sharesFilename = \
        acct_dir(base_dir, nickname, domain) + '/' + sharesFileType + '.json'
    if not os.path.isfile(sharesFilename):
        print('ERROR: remove shared item, missing ' +
              sharesFileType + '.json ' + sharesFilename)
        return

    sharesJson = load_json(sharesFilename)
    if not sharesJson:
        print('ERROR: remove shared item, ' +
              sharesFileType + '.json could not be loaded from ' +
              sharesFilename)
        return

    if sharesJson.get(itemID):
        # remove any image for the item
        itemIDfile = base_dir + '/sharefiles/' + nickname + '/' + itemID
        if sharesJson[itemID]['imageUrl']:
            formats = get_image_extensions()
            for ext in formats:
                if sharesJson[itemID]['imageUrl'].endswith('.' + ext):
                    if os.path.isfile(itemIDfile + '.' + ext):
                        try:
                            os.remove(itemIDfile + '.' + ext)
                        except OSError:
                            print('EX: removeSharedItem unable to delete ' +
                                  itemIDfile + '.' + ext)
        # remove the item itself
        del sharesJson[itemID]
        save_json(sharesJson, sharesFilename)
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


def _dfcProductTypeFromCategory(base_dir: str,
                                itemCategory: str, translate: {}) -> str:
    """Does the shared item category match a DFC product type?
    If so then return the product type.
    This will be used to select an appropriate ontology file
    such as ontology/foodTypes.json
    """
    productTypesList = get_category_types(base_dir)
    categoryLower = itemCategory.lower()
    for productType in productTypesList:
        if translate.get(productType):
            if translate[productType] in categoryLower:
                return productType
        else:
            if productType in categoryLower:
                return productType
    return None


def _getshareDfcId(base_dir: str, system_language: str,
                   itemType: str, itemCategory: str,
                   translate: {},
                   http_prefix: str, domain_full: str,
                   dfcIds: {} = None) -> str:
    """Attempts to obtain a DFC Id for the shared item,
    based upon productTypes ontology.
    See https://github.com/datafoodconsortium/ontology
    """
    # does the category field match any prodyct type ontology
    # files in the ontology subdirectory?
    matchedProductType = \
        _dfcProductTypeFromCategory(base_dir, itemCategory, translate)
    if not matchedProductType:
        itemType = itemType.replace(' ', '_')
        itemType = itemType.replace('.', '')
        return 'epicyon#' + itemType
    if not dfcIds:
        dfcIds = _loadDfcIds(base_dir, system_language, matchedProductType,
                             http_prefix, domain_full)
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
            name = name.replace('-', ' ')
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


def _indicateNewShareAvailable(base_dir: str, http_prefix: str,
                               nickname: str, domain: str,
                               domain_full: str, sharesFileType: str) -> None:
    """Indicate to each account that a new share is available
    """
    for subdir, dirs, files in os.walk(base_dir + '/accounts'):
        for handle in dirs:
            if not isAccountDir(handle):
                continue
            accountDir = base_dir + '/accounts/' + handle
            if sharesFileType == 'shares':
                newShareFile = accountDir + '/.newShare'
            else:
                newShareFile = accountDir + '/.newWanted'
            if os.path.isfile(newShareFile):
                continue
            accountNickname = handle.split('@')[0]
            # does this account block you?
            if accountNickname != nickname:
                if isBlocked(base_dir, accountNickname, domain,
                             nickname, domain, None):
                    continue
            localActor = \
                local_actor_url(http_prefix, accountNickname, domain_full)
            try:
                with open(newShareFile, 'w+') as fp:
                    if sharesFileType == 'shares':
                        fp.write(localActor + '/tlshares')
                    else:
                        fp.write(localActor + '/tlwanted')
            except OSError:
                print('EX: _indicateNewShareAvailable unable to write ' +
                      str(newShareFile))
        break


def addShare(base_dir: str,
             http_prefix: str, nickname: str, domain: str, port: int,
             displayName: str, summary: str, image_filename: str,
             itemQty: float, itemType: str, itemCategory: str, location: str,
             duration: str, debug: bool, city: str,
             price: str, currency: str,
             system_language: str, translate: {},
             sharesFileType: str, low_bandwidth: bool,
             content_license_url: str) -> None:
    """Adds a new share
    """
    if isFilteredGlobally(base_dir,
                          displayName + ' ' + summary + ' ' +
                          itemType + ' ' + itemCategory):
        print('Shared item was filtered due to content')
        return
    sharesFilename = \
        acct_dir(base_dir, nickname, domain) + '/' + sharesFileType + '.json'
    sharesJson = {}
    if os.path.isfile(sharesFilename):
        sharesJson = load_json(sharesFilename, 1, 2)

    duration = duration.lower()
    published = int(time.time())
    durationSec = _addShareDurationSec(duration, published)

    domain_full = get_full_domain(domain, port)
    actor = local_actor_url(http_prefix, nickname, domain_full)
    itemID = _getValidSharedItemID(actor, displayName)
    dfcId = _getshareDfcId(base_dir, system_language,
                           itemType, itemCategory, translate,
                           http_prefix, domain_full)

    # has an image for this share been uploaded?
    imageUrl = None
    moveImage = False
    if not image_filename:
        sharesImageFilename = \
            acct_dir(base_dir, nickname, domain) + '/upload'
        formats = get_image_extensions()
        for ext in formats:
            if os.path.isfile(sharesImageFilename + '.' + ext):
                image_filename = sharesImageFilename + '.' + ext
                moveImage = True

    domain_full = get_full_domain(domain, port)

    # copy or move the image for the shared item to its destination
    if image_filename:
        if os.path.isfile(image_filename):
            if not os.path.isdir(base_dir + '/sharefiles'):
                os.mkdir(base_dir + '/sharefiles')
            if not os.path.isdir(base_dir + '/sharefiles/' + nickname):
                os.mkdir(base_dir + '/sharefiles/' + nickname)
            itemIDfile = base_dir + '/sharefiles/' + nickname + '/' + itemID
            formats = get_image_extensions()
            for ext in formats:
                if not image_filename.endswith('.' + ext):
                    continue
                if low_bandwidth:
                    convertImageToLowBandwidth(image_filename)
                processMetaData(base_dir, nickname, domain,
                                image_filename, itemIDfile + '.' + ext,
                                city, content_license_url)
                if moveImage:
                    try:
                        os.remove(image_filename)
                    except OSError:
                        print('EX: addShare unable to delete ' +
                              str(image_filename))
                imageUrl = \
                    http_prefix + '://' + domain_full + \
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

    save_json(sharesJson, sharesFilename)

    _indicateNewShareAvailable(base_dir, http_prefix,
                               nickname, domain, domain_full,
                               sharesFileType)


def expireShares(base_dir: str) -> None:
    """Removes expired items from shares
    """
    for subdir, dirs, files in os.walk(base_dir + '/accounts'):
        for account in dirs:
            if not isAccountDir(account):
                continue
            nickname = account.split('@')[0]
            domain = account.split('@')[1]
            for sharesFileType in get_shares_files_list():
                _expireSharesForAccount(base_dir, nickname, domain,
                                        sharesFileType)
        break


def _expireSharesForAccount(base_dir: str, nickname: str, domain: str,
                            sharesFileType: str) -> None:
    """Removes expired items from shares for a particular account
    """
    handleDomain = remove_domain_port(domain)
    handle = nickname + '@' + handleDomain
    sharesFilename = \
        base_dir + '/accounts/' + handle + '/' + sharesFileType + '.json'
    if not os.path.isfile(sharesFilename):
        return
    sharesJson = load_json(sharesFilename, 1, 2)
    if not sharesJson:
        return
    curr_time = int(time.time())
    deleteItemID = []
    for itemID, item in sharesJson.items():
        if curr_time > item['expire']:
            deleteItemID.append(itemID)
    if not deleteItemID:
        return
    for itemID in deleteItemID:
        del sharesJson[itemID]
        # remove any associated images
        itemIDfile = base_dir + '/sharefiles/' + nickname + '/' + itemID
        formats = get_image_extensions()
        for ext in formats:
            if os.path.isfile(itemIDfile + '.' + ext):
                try:
                    os.remove(itemIDfile + '.' + ext)
                except OSError:
                    print('EX: _expireSharesForAccount unable to delete ' +
                          itemIDfile + '.' + ext)
    save_json(sharesJson, sharesFilename)


def getSharesFeedForPerson(base_dir: str,
                           domain: str, port: int,
                           path: str, http_prefix: str,
                           sharesFileType: str,
                           sharesPerPage: int) -> {}:
    """Returns the shares for an account from GET requests
    """
    if '/' + sharesFileType not in path:
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
                print('EX: getSharesFeedForPerson unable to convert to int ' +
                      str(pageNumber))
                pass
        path = path.split('?page=')[0]
        headerOnly = False

    if not path.endswith('/' + sharesFileType):
        return None
    nickname = None
    if path.startswith('/users/'):
        nickname = \
            path.replace('/users/', '', 1).replace('/' + sharesFileType, '')
    if path.startswith('/@'):
        nickname = \
            path.replace('/@', '', 1).replace('/' + sharesFileType, '')
    if not nickname:
        return None
    if not validNickname(domain, nickname):
        return None

    domain = get_full_domain(domain, port)

    handleDomain = remove_domain_port(domain)
    sharesFilename = \
        acct_dir(base_dir, nickname, handleDomain) + '/' + \
        sharesFileType + '.json'

    if headerOnly:
        noOfShares = 0
        if os.path.isfile(sharesFilename):
            sharesJson = load_json(sharesFilename)
            if sharesJson:
                noOfShares = len(sharesJson.items())
        idStr = local_actor_url(http_prefix, nickname, domain)
        shares = {
            '@context': 'https://www.w3.org/ns/activitystreams',
            'first': idStr + '/' + sharesFileType + '?page=1',
            'id': idStr + '/' + sharesFileType,
            'totalItems': str(noOfShares),
            'type': 'OrderedCollection'
        }
        return shares

    if not pageNumber:
        pageNumber = 1

    nextPageNumber = int(pageNumber + 1)
    idStr = local_actor_url(http_prefix, nickname, domain)
    shares = {
        '@context': 'https://www.w3.org/ns/activitystreams',
        'id': idStr + '/' + sharesFileType + '?page=' + str(pageNumber),
        'orderedItems': [],
        'partOf': idStr + '/' + sharesFileType,
        'totalItems': 0,
        'type': 'OrderedCollectionPage'
    }

    if not os.path.isfile(sharesFilename):
        return shares
    currPage = 1
    pageCtr = 0
    totalCtr = 0

    sharesJson = load_json(sharesFilename)
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
            local_actor_url(http_prefix, nickname, domain) + \
            '/' + sharesFileType + '?page=' + str(lastPage)
    return shares


def sendShareViaServer(base_dir, session,
                       fromNickname: str, password: str,
                       fromDomain: str, fromPort: int,
                       http_prefix: str, displayName: str,
                       summary: str, image_filename: str,
                       itemQty: float, itemType: str, itemCategory: str,
                       location: str, duration: str,
                       cached_webfingers: {}, person_cache: {},
                       debug: bool, project_version: str,
                       itemPrice: str, itemCurrency: str,
                       signing_priv_key_pem: str) -> {}:
    """Creates an item share via c2s
    """
    if not session:
        print('WARN: No session for sendShareViaServer')
        return 6

    # convert $4.23 to 4.23 USD
    newItemPrice, newItemCurrency = getPriceFromString(itemPrice)
    if newItemPrice != itemPrice:
        itemPrice = newItemPrice
        if not itemCurrency:
            if newItemCurrency != itemCurrency:
                itemCurrency = newItemCurrency

    fromDomainFull = get_full_domain(fromDomain, fromPort)

    actor = local_actor_url(http_prefix, fromNickname, fromDomainFull)
    toUrl = 'https://www.w3.org/ns/activitystreams#Public'
    ccUrl = actor + '/followers'

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

    handle = http_prefix + '://' + fromDomainFull + '/@' + fromNickname

    # lookup the inbox for the To handle
    wfRequest = \
        webfingerHandle(session, handle, http_prefix,
                        cached_webfingers,
                        fromDomain, project_version, debug, False,
                        signing_priv_key_pem)
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
    originDomain = fromDomain
    (inboxUrl, pubKeyId, pubKey, fromPersonId, sharedInbox, avatarUrl,
     displayName, _) = getPersonBox(signing_priv_key_pem,
                                    originDomain,
                                    base_dir, session, wfRequest,
                                    person_cache, project_version,
                                    http_prefix, fromNickname,
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

    if image_filename:
        headers = {
            'host': fromDomain,
            'Authorization': authHeader
        }
        postResult = \
            postImage(session, image_filename, [],
                      inboxUrl.replace('/' + postToBox, '/shares'),
                      headers)

    headers = {
        'host': fromDomain,
        'Content-type': 'application/json',
        'Authorization': authHeader
    }
    postResult = \
        postJson(http_prefix, fromDomainFull,
                 session, newShareJson, [], inboxUrl, headers, 30, True)
    if not postResult:
        if debug:
            print('DEBUG: POST share failed for c2s to ' + inboxUrl)
#        return 5

    if debug:
        print('DEBUG: c2s POST share item success')

    return newShareJson


def sendUndoShareViaServer(base_dir: str, session,
                           fromNickname: str, password: str,
                           fromDomain: str, fromPort: int,
                           http_prefix: str, displayName: str,
                           cached_webfingers: {}, person_cache: {},
                           debug: bool, project_version: str,
                           signing_priv_key_pem: str) -> {}:
    """Undoes a share via c2s
    """
    if not session:
        print('WARN: No session for sendUndoShareViaServer')
        return 6

    fromDomainFull = get_full_domain(fromDomain, fromPort)

    actor = local_actor_url(http_prefix, fromNickname, fromDomainFull)
    toUrl = 'https://www.w3.org/ns/activitystreams#Public'
    ccUrl = actor + '/followers'

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

    handle = http_prefix + '://' + fromDomainFull + '/@' + fromNickname

    # lookup the inbox for the To handle
    wfRequest = \
        webfingerHandle(session, handle, http_prefix, cached_webfingers,
                        fromDomain, project_version, debug, False,
                        signing_priv_key_pem)
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
    originDomain = fromDomain
    (inboxUrl, pubKeyId, pubKey, fromPersonId, sharedInbox, avatarUrl,
     displayName, _) = getPersonBox(signing_priv_key_pem,
                                    originDomain,
                                    base_dir, session, wfRequest,
                                    person_cache, project_version,
                                    http_prefix, fromNickname,
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
        postJson(http_prefix, fromDomainFull,
                 session, undoShareJson, [], inboxUrl,
                 headers, 30, True)
    if not postResult:
        if debug:
            print('DEBUG: POST unshare failed for c2s to ' + inboxUrl)
#        return 5

    if debug:
        print('DEBUG: c2s POST unshare success')

    return undoShareJson


def sendWantedViaServer(base_dir, session,
                        fromNickname: str, password: str,
                        fromDomain: str, fromPort: int,
                        http_prefix: str, displayName: str,
                        summary: str, image_filename: str,
                        itemQty: float, itemType: str, itemCategory: str,
                        location: str, duration: str,
                        cached_webfingers: {}, person_cache: {},
                        debug: bool, project_version: str,
                        itemMaxPrice: str, itemCurrency: str,
                        signing_priv_key_pem: str) -> {}:
    """Creates a wanted item via c2s
    """
    if not session:
        print('WARN: No session for sendWantedViaServer')
        return 6

    # convert $4.23 to 4.23 USD
    newItemMaxPrice, newItemCurrency = getPriceFromString(itemMaxPrice)
    if newItemMaxPrice != itemMaxPrice:
        itemMaxPrice = newItemMaxPrice
        if not itemCurrency:
            if newItemCurrency != itemCurrency:
                itemCurrency = newItemCurrency

    fromDomainFull = get_full_domain(fromDomain, fromPort)

    actor = local_actor_url(http_prefix, fromNickname, fromDomainFull)
    toUrl = 'https://www.w3.org/ns/activitystreams#Public'
    ccUrl = actor + '/followers'

    newShareJson = {
        "@context": "https://www.w3.org/ns/activitystreams",
        'type': 'Add',
        'actor': actor,
        'target': actor + '/wanted',
        'object': {
            "type": "Offer",
            "displayName": displayName,
            "summary": summary,
            "itemQty": float(itemQty),
            "itemType": itemType,
            "category": itemCategory,
            "location": location,
            "duration": duration,
            "itemPrice": itemMaxPrice,
            "itemCurrency": itemCurrency,
            'to': [toUrl],
            'cc': [ccUrl]
        },
        'to': [toUrl],
        'cc': [ccUrl]
    }

    handle = http_prefix + '://' + fromDomainFull + '/@' + fromNickname

    # lookup the inbox for the To handle
    wfRequest = \
        webfingerHandle(session, handle, http_prefix,
                        cached_webfingers,
                        fromDomain, project_version, debug, False,
                        signing_priv_key_pem)
    if not wfRequest:
        if debug:
            print('DEBUG: share webfinger failed for ' + handle)
        return 1
    if not isinstance(wfRequest, dict):
        print('WARN: wanted webfinger for ' + handle +
              ' did not return a dict. ' + str(wfRequest))
        return 1

    postToBox = 'outbox'

    # get the actor inbox for the To handle
    originDomain = fromDomain
    (inboxUrl, pubKeyId, pubKey, fromPersonId, sharedInbox, avatarUrl,
     displayName, _) = getPersonBox(signing_priv_key_pem,
                                    originDomain,
                                    base_dir, session, wfRequest,
                                    person_cache, project_version,
                                    http_prefix, fromNickname,
                                    fromDomain, postToBox,
                                    23653)

    if not inboxUrl:
        if debug:
            print('DEBUG: wanted no ' + postToBox +
                  ' was found for ' + handle)
        return 3
    if not fromPersonId:
        if debug:
            print('DEBUG: wanted no actor was found for ' + handle)
        return 4

    authHeader = createBasicAuthHeader(fromNickname, password)

    if image_filename:
        headers = {
            'host': fromDomain,
            'Authorization': authHeader
        }
        postResult = \
            postImage(session, image_filename, [],
                      inboxUrl.replace('/' + postToBox, '/wanted'),
                      headers)

    headers = {
        'host': fromDomain,
        'Content-type': 'application/json',
        'Authorization': authHeader
    }
    postResult = \
        postJson(http_prefix, fromDomainFull,
                 session, newShareJson, [], inboxUrl, headers, 30, True)
    if not postResult:
        if debug:
            print('DEBUG: POST wanted failed for c2s to ' + inboxUrl)
#        return 5

    if debug:
        print('DEBUG: c2s POST wanted item success')

    return newShareJson


def sendUndoWantedViaServer(base_dir: str, session,
                            fromNickname: str, password: str,
                            fromDomain: str, fromPort: int,
                            http_prefix: str, displayName: str,
                            cached_webfingers: {}, person_cache: {},
                            debug: bool, project_version: str,
                            signing_priv_key_pem: str) -> {}:
    """Undoes a wanted item via c2s
    """
    if not session:
        print('WARN: No session for sendUndoWantedViaServer')
        return 6

    fromDomainFull = get_full_domain(fromDomain, fromPort)

    actor = local_actor_url(http_prefix, fromNickname, fromDomainFull)
    toUrl = 'https://www.w3.org/ns/activitystreams#Public'
    ccUrl = actor + '/followers'

    undoShareJson = {
        "@context": "https://www.w3.org/ns/activitystreams",
        'type': 'Remove',
        'actor': actor,
        'target': actor + '/wanted',
        'object': {
            "type": "Offer",
            "displayName": displayName,
            'to': [toUrl],
            'cc': [ccUrl]
        },
        'to': [toUrl],
        'cc': [ccUrl]
    }

    handle = http_prefix + '://' + fromDomainFull + '/@' + fromNickname

    # lookup the inbox for the To handle
    wfRequest = \
        webfingerHandle(session, handle, http_prefix, cached_webfingers,
                        fromDomain, project_version, debug, False,
                        signing_priv_key_pem)
    if not wfRequest:
        if debug:
            print('DEBUG: unwant webfinger failed for ' + handle)
        return 1
    if not isinstance(wfRequest, dict):
        print('WARN: unwant webfinger for ' + handle +
              ' did not return a dict. ' + str(wfRequest))
        return 1

    postToBox = 'outbox'

    # get the actor inbox for the To handle
    originDomain = fromDomain
    (inboxUrl, pubKeyId, pubKey, fromPersonId, sharedInbox, avatarUrl,
     displayName, _) = getPersonBox(signing_priv_key_pem,
                                    originDomain,
                                    base_dir, session, wfRequest,
                                    person_cache, project_version,
                                    http_prefix, fromNickname,
                                    fromDomain, postToBox,
                                    12693)

    if not inboxUrl:
        if debug:
            print('DEBUG: unwant no ' + postToBox +
                  ' was found for ' + handle)
        return 3
    if not fromPersonId:
        if debug:
            print('DEBUG: unwant no actor was found for ' + handle)
        return 4

    authHeader = createBasicAuthHeader(fromNickname, password)

    headers = {
        'host': fromDomain,
        'Content-type': 'application/json',
        'Authorization': authHeader
    }
    postResult = \
        postJson(http_prefix, fromDomainFull,
                 session, undoShareJson, [], inboxUrl,
                 headers, 30, True)
    if not postResult:
        if debug:
            print('DEBUG: POST unwant failed for c2s to ' + inboxUrl)
#        return 5

    if debug:
        print('DEBUG: c2s POST unwant success')

    return undoShareJson


def getSharedItemsCatalogViaServer(base_dir, session,
                                   nickname: str, password: str,
                                   domain: str, port: int,
                                   http_prefix: str, debug: bool,
                                   signing_priv_key_pem: str) -> {}:
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
    domain_full = get_full_domain(domain, port)
    url = local_actor_url(http_prefix, nickname, domain_full) + '/catalog'
    if debug:
        print('Shared items catalog request to: ' + url)
    catalogJson = getJson(signing_priv_key_pem, session, url, headers, None,
                          debug, __version__, http_prefix, None)
    if not catalogJson:
        if debug:
            print('DEBUG: GET shared items catalog failed for c2s to ' + url)
#        return 5

    if debug:
        print('DEBUG: c2s GET shared items catalog success')

    return catalogJson


def outboxShareUpload(base_dir: str, http_prefix: str,
                      nickname: str, domain: str, port: int,
                      message_json: {}, debug: bool, city: str,
                      system_language: str, translate: {},
                      low_bandwidth: bool,
                      content_license_url: str) -> None:
    """ When a shared item is received by the outbox from c2s
    """
    if not message_json.get('type'):
        return
    if not message_json['type'] == 'Add':
        return
    if not has_object_stringType(message_json, debug):
        return
    if not message_json['object']['type'] == 'Offer':
        if debug:
            print('DEBUG: not an Offer activity')
        return
    if not message_json['object'].get('displayName'):
        if debug:
            print('DEBUG: displayName missing from Offer')
        return
    if not message_json['object'].get('summary'):
        if debug:
            print('DEBUG: summary missing from Offer')
        return
    if not message_json['object'].get('itemQty'):
        if debug:
            print('DEBUG: itemQty missing from Offer')
        return
    if not message_json['object'].get('itemType'):
        if debug:
            print('DEBUG: itemType missing from Offer')
        return
    if not message_json['object'].get('category'):
        if debug:
            print('DEBUG: category missing from Offer')
        return
    if not message_json['object'].get('duration'):
        if debug:
            print('DEBUG: duration missing from Offer')
        return
    itemQty = float(message_json['object']['itemQty'])
    location = ''
    if message_json['object'].get('location'):
        location = message_json['object']['location']
    image_filename = None
    if message_json['object'].get('image_filename'):
        image_filename = message_json['object']['image_filename']
    if debug:
        print('Adding shared item')
        pprint(message_json)

    addShare(base_dir,
             http_prefix, nickname, domain, port,
             message_json['object']['displayName'],
             message_json['object']['summary'],
             image_filename,
             itemQty,
             message_json['object']['itemType'],
             message_json['object']['category'],
             location,
             message_json['object']['duration'],
             debug, city,
             message_json['object']['itemPrice'],
             message_json['object']['itemCurrency'],
             system_language, translate, 'shares',
             low_bandwidth, content_license_url)
    if debug:
        print('DEBUG: shared item received via c2s')


def outboxUndoShareUpload(base_dir: str, http_prefix: str,
                          nickname: str, domain: str, port: int,
                          message_json: {}, debug: bool) -> None:
    """ When a shared item is removed via c2s
    """
    if not message_json.get('type'):
        return
    if not message_json['type'] == 'Remove':
        return
    if not has_object_stringType(message_json, debug):
        return
    if not message_json['object']['type'] == 'Offer':
        if debug:
            print('DEBUG: not an Offer activity')
        return
    if not message_json['object'].get('displayName'):
        if debug:
            print('DEBUG: displayName missing from Offer')
        return
    domain_full = get_full_domain(domain, port)
    removeSharedItem(base_dir, nickname, domain,
                     message_json['object']['displayName'],
                     http_prefix, domain_full, 'shares')
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
            if is_float(value):
                minPrice = float(value)
        elif key.startswith('max'):
            if is_float(value):
                maxPrice = float(value)
        elif key.startswith('match'):
            matchPattern = value
    return today, minPrice, maxPrice, matchPattern


def sharesCatalogAccountEndpoint(base_dir: str, http_prefix: str,
                                 nickname: str, domain: str,
                                 domain_full: str,
                                 path: str, debug: bool,
                                 sharesFileType: str) -> {}:
    """Returns the endpoint for the shares catalog of a particular account
    See https://github.com/datafoodconsortium/ontology
    Also the subdirectory ontology/DFC
    """
    today, minPrice, maxPrice, matchPattern = _sharesCatalogParams(path)
    dfcUrl = \
        http_prefix + '://' + domain_full + '/ontologies/DFC_FullModel.owl#'
    dfcPtUrl = \
        http_prefix + '://' + domain_full + \
        '/ontologies/DFC_ProductGlossary.rdf#'
    owner = local_actor_url(http_prefix, nickname, domain_full)
    if sharesFileType == 'shares':
        dfcInstanceId = owner + '/catalog'
    else:
        dfcInstanceId = owner + '/wantedItems'
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

    sharesFilename = \
        acct_dir(base_dir, nickname, domain) + '/' + sharesFileType + '.json'
    if not os.path.isfile(sharesFilename):
        if debug:
            print(sharesFileType + '.json file not found: ' + sharesFilename)
        return endpoint
    sharesJson = load_json(sharesFilename, 1, 2)
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


def sharesCatalogEndpoint(base_dir: str, http_prefix: str,
                          domain_full: str,
                          path: str, sharesFileType: str) -> {}:
    """Returns the endpoint for the shares catalog for the instance
    See https://github.com/datafoodconsortium/ontology
    Also the subdirectory ontology/DFC
    """
    today, minPrice, maxPrice, matchPattern = _sharesCatalogParams(path)
    dfcUrl = \
        http_prefix + '://' + domain_full + '/ontologies/DFC_FullModel.owl#'
    dfcPtUrl = \
        http_prefix + '://' + domain_full + \
        '/ontologies/DFC_ProductGlossary.rdf#'
    dfcInstanceId = http_prefix + '://' + domain_full + '/catalog'
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

    for subdir, dirs, files in os.walk(base_dir + '/accounts'):
        for acct in dirs:
            if not isAccountDir(acct):
                continue
            nickname = acct.split('@')[0]
            domain = acct.split('@')[1]
            owner = local_actor_url(http_prefix, nickname, domain_full)

            sharesFilename = \
                acct_dir(base_dir, nickname, domain) + '/' + \
                sharesFileType + '.json'
            if not os.path.isfile(sharesFilename):
                continue
            print('Test 78363 ' + sharesFilename)
            sharesJson = load_json(sharesFilename, 1, 2)
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

                startDateStr = date_seconds_to_string(item['published'])
                expireDateStr = date_seconds_to_string(item['expire'])
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


def sharesCatalogCSVEndpoint(base_dir: str, http_prefix: str,
                             domain_full: str,
                             path: str, sharesFileType: str) -> str:
    """Returns a CSV version of the shares catalog
    """
    catalogJson = \
        sharesCatalogEndpoint(base_dir, http_prefix, domain_full, path,
                              sharesFileType)
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
        if item.get('DFC:Image'):
            csvStr += '"' + item['DFC:Image'] + '",'
        description = item['DFC:description'].replace('"', "'")
        csvStr += '"' + description + '",\n'
    return csvStr


def generateSharedItemFederationTokens(shared_items_federated_domains: [],
                                       base_dir: str) -> {}:
    """Generates tokens for shared item federated domains
    """
    if not shared_items_federated_domains:
        return {}

    tokensJson = {}
    if base_dir:
        tokensFilename = \
            base_dir + '/accounts/sharedItemsFederationTokens.json'
        if os.path.isfile(tokensFilename):
            tokensJson = load_json(tokensFilename, 1, 2)
            if tokensJson is None:
                tokensJson = {}

    tokensAdded = False
    for domain_full in shared_items_federated_domains:
        if not tokensJson.get(domain_full):
            tokensJson[domain_full] = ''
            tokensAdded = True

    if not tokensAdded:
        return tokensJson
    if base_dir:
        save_json(tokensJson, tokensFilename)
    return tokensJson


def updateSharedItemFederationToken(base_dir: str,
                                    tokenDomainFull: str, newToken: str,
                                    debug: bool,
                                    tokensJson: {} = None) -> {}:
    """Updates an individual token for shared item federation
    """
    if debug:
        print('Updating shared items token for ' + tokenDomainFull)
    if not tokensJson:
        tokensJson = {}
    if base_dir:
        tokensFilename = \
            base_dir + '/accounts/sharedItemsFederationTokens.json'
        if os.path.isfile(tokensFilename):
            if debug:
                print('Update loading tokens for ' + tokenDomainFull)
            tokensJson = load_json(tokensFilename, 1, 2)
            if tokensJson is None:
                tokensJson = {}
    updateRequired = False
    if tokensJson.get(tokenDomainFull):
        if tokensJson[tokenDomainFull] != newToken:
            updateRequired = True
    else:
        updateRequired = True
    if updateRequired:
        tokensJson[tokenDomainFull] = newToken
        if base_dir:
            save_json(tokensJson, tokensFilename)
    return tokensJson


def mergeSharedItemTokens(base_dir: str, domain_full: str,
                          newSharedItemsFederatedDomains: [],
                          tokensJson: {}) -> {}:
    """When the shared item federation domains list has changed, update
    the tokens dict accordingly
    """
    removals = []
    changed = False
    for tokenDomainFull, tok in tokensJson.items():
        if domain_full:
            if tokenDomainFull.startswith(domain_full):
                continue
        if tokenDomainFull not in newSharedItemsFederatedDomains:
            removals.append(tokenDomainFull)
    # remove domains no longer in the federation list
    for tokenDomainFull in removals:
        del tokensJson[tokenDomainFull]
        changed = True
    # add new domains from the federation list
    for tokenDomainFull in newSharedItemsFederatedDomains:
        if tokenDomainFull not in tokensJson:
            tokensJson[tokenDomainFull] = ''
            changed = True
    if base_dir and changed:
        tokensFilename = \
            base_dir + '/accounts/sharedItemsFederationTokens.json'
        save_json(tokensJson, tokensFilename)
    return tokensJson


def createSharedItemFederationToken(base_dir: str,
                                    tokenDomainFull: str,
                                    force: bool,
                                    tokensJson: {} = None) -> {}:
    """Updates an individual token for shared item federation
    """
    if not tokensJson:
        tokensJson = {}
    if base_dir:
        tokensFilename = \
            base_dir + '/accounts/sharedItemsFederationTokens.json'
        if os.path.isfile(tokensFilename):
            tokensJson = load_json(tokensFilename, 1, 2)
            if tokensJson is None:
                tokensJson = {}
    if force or not tokensJson.get(tokenDomainFull):
        tokensJson[tokenDomainFull] = secrets.token_urlsafe(64)
        if base_dir:
            save_json(tokensJson, tokensFilename)
    return tokensJson


def authorizeSharedItems(shared_items_federated_domains: [],
                         base_dir: str,
                         originDomainFull: str,
                         calling_domainFull: str,
                         authHeader: str,
                         debug: bool,
                         tokensJson: {} = None) -> bool:
    """HTTP simple token check for shared item federation
    """
    if not shared_items_federated_domains:
        # no shared item federation
        return False
    if originDomainFull not in shared_items_federated_domains:
        if debug:
            print(originDomainFull +
                  ' is not in the shared items federation list ' +
                  str(shared_items_federated_domains))
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
            base_dir + '/accounts/sharedItemsFederationTokens.json'
        if not os.path.isfile(tokensFilename):
            if debug:
                print('DEBUG: shared item federation tokens file missing ' +
                      tokensFilename)
            return False
        tokensJson = load_json(tokensFilename, 1, 2)
    if not tokensJson:
        return False
    if not tokensJson.get(calling_domainFull):
        if debug:
            print('DEBUG: shared item federation token ' +
                  'check failed for ' + calling_domainFull)
        return False
    if not constantTimeStringCheck(tokensJson[calling_domainFull],
                                   providedToken):
        if debug:
            print('DEBUG: shared item federation token ' +
                  'mismatch for ' + calling_domainFull)
        return False
    return True


def _updateFederatedSharesCache(session, shared_items_federated_domains: [],
                                base_dir: str, domain_full: str,
                                http_prefix: str,
                                tokensJson: {}, debug: bool,
                                system_language: str,
                                sharesFileType: str) -> None:
    """Updates the cache of federated shares for the instance.
    This enables shared items to be available even when other instances
    might not be online
    """
    # create directories where catalogs will be stored
    cacheDir = base_dir + '/cache'
    if not os.path.isdir(cacheDir):
        os.mkdir(cacheDir)
    if sharesFileType == 'shares':
        catalogsDir = cacheDir + '/catalogs'
    else:
        catalogsDir = cacheDir + '/wantedItems'
    if not os.path.isdir(catalogsDir):
        os.mkdir(catalogsDir)

    asHeader = {
        "Accept": "application/ld+json",
        "Origin": domain_full
    }
    for federatedDomainFull in shared_items_federated_domains:
        # NOTE: federatedDomain does not have a port extension,
        # so may not work in some situations
        if federatedDomainFull.startswith(domain_full):
            # only download from instances other than this one
            continue
        if not tokensJson.get(federatedDomainFull):
            # token has been obtained for the other domain
            continue
        if not siteIsActive(http_prefix + '://' + federatedDomainFull, 10):
            continue
        if sharesFileType == 'shares':
            url = http_prefix + '://' + federatedDomainFull + '/catalog'
        else:
            url = http_prefix + '://' + federatedDomainFull + '/wantedItems'
        asHeader['Authorization'] = tokensJson[federatedDomainFull]
        catalogJson = getJson(session, url, asHeader, None,
                              debug, __version__, http_prefix, None)
        if not catalogJson:
            print('WARN: failed to download shared items catalog for ' +
                  federatedDomainFull)
            continue
        catalogFilename = catalogsDir + '/' + federatedDomainFull + '.json'
        if save_json(catalogJson, catalogFilename):
            print('Downloaded shared items catalog for ' + federatedDomainFull)
            sharesJson = _dfcToSharesFormat(catalogJson,
                                            base_dir, system_language,
                                            http_prefix, domain_full)
            if sharesJson:
                sharesFilename = \
                    catalogsDir + '/' + federatedDomainFull + '.' + \
                    sharesFileType + '.json'
                save_json(sharesJson, sharesFilename)
                print('Converted shares catalog for ' + federatedDomainFull)
        else:
            time.sleep(2)


def runFederatedSharesWatchdog(project_version: str, httpd) -> None:
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


def _generateNextSharesTokenUpdate(base_dir: str,
                                   minDays: int, maxDays: int) -> None:
    """Creates a file containing the next date when the shared items token
    for this instance will be updated
    """
    tokenUpdateDir = base_dir + '/accounts'
    if not os.path.isdir(base_dir):
        os.mkdir(base_dir)
    if not os.path.isdir(tokenUpdateDir):
        os.mkdir(tokenUpdateDir)
    tokenUpdateFilename = tokenUpdateDir + '/.tokenUpdate'
    nextUpdateSec = None
    if os.path.isfile(tokenUpdateFilename):
        with open(tokenUpdateFilename, 'r') as fp:
            nextUpdateStr = fp.read()
            if nextUpdateStr:
                if nextUpdateStr.isdigit():
                    nextUpdateSec = int(nextUpdateStr)
    curr_time = int(time.time())
    updated = False
    if nextUpdateSec:
        if curr_time > nextUpdateSec:
            nextUpdateDays = randint(minDays, maxDays)
            nextUpdateInterval = int(60 * 60 * 24 * nextUpdateDays)
            nextUpdateSec += nextUpdateInterval
            updated = True
    else:
        nextUpdateDays = randint(minDays, maxDays)
        nextUpdateInterval = int(60 * 60 * 24 * nextUpdateDays)
        nextUpdateSec = curr_time + nextUpdateInterval
        updated = True
    if updated:
        with open(tokenUpdateFilename, 'w+') as fp:
            fp.write(str(nextUpdateSec))


def _regenerateSharesToken(base_dir: str, domain_full: str,
                           minDays: int, maxDays: int, httpd) -> None:
    """Occasionally the shared items token for your instance is updated.
    Scenario:
      - You share items with $FriendlyInstance
      - Some time later under new management
        $FriendlyInstance becomes $HostileInstance
      - You block $HostileInstance and remove them from your
        federated shares domains list
      - $HostileInstance still knows your shared items token,
        and can still have access to your shared items if it presents a
        spoofed Origin header together with the token
    By rotating the token occasionally $HostileInstance will eventually
    lose access to your federated shares. If other instances within your
    federated shares list of domains continue to follow and communicate
    then they will receive the new token automatically
    """
    tokenUpdateFilename = base_dir + '/accounts/.tokenUpdate'
    if not os.path.isfile(tokenUpdateFilename):
        return
    nextUpdateSec = None
    with open(tokenUpdateFilename, 'r') as fp:
        nextUpdateStr = fp.read()
        if nextUpdateStr:
            if nextUpdateStr.isdigit():
                nextUpdateSec = int(nextUpdateStr)
    if not nextUpdateSec:
        return
    curr_time = int(time.time())
    if curr_time <= nextUpdateSec:
        return
    createSharedItemFederationToken(base_dir, domain_full, True, None)
    _generateNextSharesTokenUpdate(base_dir, minDays, maxDays)
    # update the tokens used within the daemon
    shared_fed_domains = httpd.shared_items_federated_domains
    httpd.sharedItemFederationTokens = \
        generateSharedItemFederationTokens(shared_fed_domains,
                                           base_dir)


def runFederatedSharesDaemon(base_dir: str, httpd, http_prefix: str,
                             domain_full: str, proxy_type: str, debug: bool,
                             system_language: str) -> None:
    """Runs the daemon used to update federated shared items
    """
    secondsPerHour = 60 * 60
    fileCheckIntervalSec = 120
    time.sleep(60)
    # the token for this instance will be changed every 7-14 days
    minDays = 7
    maxDays = 14
    _generateNextSharesTokenUpdate(base_dir, minDays, maxDays)
    while True:
        shared_items_federated_domainsStr = \
            get_config_param(base_dir, 'shared_items_federated_domains')
        if not shared_items_federated_domainsStr:
            time.sleep(fileCheckIntervalSec)
            continue

        # occasionally change the federated shared items token
        # for this instance
        _regenerateSharesToken(base_dir, domain_full, minDays, maxDays, httpd)

        # get a list of the domains within the shared items federation
        shared_items_federated_domains = []
        fed_domains_list = \
            shared_items_federated_domainsStr.split(',')
        for shared_fed_domain in fed_domains_list:
            shared_items_federated_domains.append(shared_fed_domain.strip())
        if not shared_items_federated_domains:
            time.sleep(fileCheckIntervalSec)
            continue

        # load the tokens
        tokensFilename = \
            base_dir + '/accounts/sharedItemsFederationTokens.json'
        if not os.path.isfile(tokensFilename):
            time.sleep(fileCheckIntervalSec)
            continue
        tokensJson = load_json(tokensFilename, 1, 2)
        if not tokensJson:
            time.sleep(fileCheckIntervalSec)
            continue

        session = createSession(proxy_type)
        for sharesFileType in get_shares_files_list():
            _updateFederatedSharesCache(session,
                                        shared_items_federated_domains,
                                        base_dir, domain_full, http_prefix,
                                        tokensJson, debug, system_language,
                                        sharesFileType)
        time.sleep(secondsPerHour * 6)


def _dfcToSharesFormat(catalogJson: {},
                       base_dir: str, system_language: str,
                       http_prefix: str, domain_full: str) -> {}:
    """Converts DFC format into the internal formal used to store shared items.
    This simplifies subsequent search and display
    """
    if not catalogJson.get('DFC:supplies'):
        return {}
    sharesJson = {}

    dfcIds = {}
    productTypesList = get_category_types(base_dir)
    for productType in productTypesList:
        dfcIds[productType] = \
            _loadDfcIds(base_dir, system_language, productType,
                        http_prefix, domain_full)

    curr_time = int(time.time())
    for item in catalogJson['DFC:supplies']:
        if not item.get('@id') or \
           not item.get('@type') or \
           not item.get('DFC:hasType') or \
           not item.get('DFC:startDate') or \
           not item.get('DFC:expiryDate') or \
           not item.get('DFC:quantity') or \
           not item.get('DFC:price') or \
           not item.get('DFC:description'):
            continue

        if ' ' not in item['DFC:price']:
            continue
        if ':' not in item['DFC:description']:
            continue
        if ':' not in item['DFC:hasType']:
            continue

        startTimeSec = date_string_to_seconds(item['DFC:startDate'])
        if not startTimeSec:
            continue
        expiryTimeSec = date_string_to_seconds(item['DFC:expiryDate'])
        if not expiryTimeSec:
            continue
        if expiryTimeSec < curr_time:
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
        if isFilteredGlobally(base_dir, allText):
            continue

        dfcId = None
        if productType:
            dfcId = dfcIds[productType][itemType]
        itemID = item['@id']
        description = item['DFC:description'].split(':', 1)[1].strip()

        imageUrl = ''
        if item.get('DFC:Image'):
            imageUrl = item['DFC:Image']
        sharesJson[itemID] = {
            "displayName": item['DFC:description'].split(':')[0],
            "summary": description,
            "imageUrl": imageUrl,
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


def shareCategoryIcon(category: str) -> str:
    """Returns unicode icon for the given category
    """
    categoryIcons = {
        'accommodation': '🏠',
        'clothes':  '👚',
        'tools': '🔧',
        'food': '🍏'
    }
    if categoryIcons.get(category):
        return categoryIcons[category]
    return ''
