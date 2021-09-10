__filename__ = "cache.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Core"

import os
import datetime
from session import urlExists
from session import getJson
from utils import loadJson
from utils import saveJson
from utils import getFileCaseInsensitive
from utils import getUserPaths


def _removePersonFromCache(baseDir: str, personUrl: str,
                           personCache: {}) -> bool:
    """Removes an actor from the cache
    """
    cacheFilename = baseDir + '/cache/actors/' + \
        personUrl.replace('/', '#') + '.json'
    if os.path.isfile(cacheFilename):
        try:
            os.remove(cacheFilename)
        except BaseException:
            pass
    if personCache.get(personUrl):
        del personCache[personUrl]


def checkForChangedActor(session, baseDir: str,
                         httpPrefix: str, domainFull: str,
                         personUrl: str, avatarUrl: str, personCache: {},
                         timeoutSec: int):
    """Checks if the avatar url exists and if not then
    the actor has probably changed without receiving an actor/Person Update.
    So clear the actor from the cache and it will be refreshed when the next
    post from them is sent
    """
    if not session or not avatarUrl:
        return
    if domainFull in avatarUrl:
        return
    if urlExists(session, avatarUrl, timeoutSec, httpPrefix, domainFull):
        return
    _removePersonFromCache(baseDir, personUrl, personCache)


def storePersonInCache(baseDir: str, personUrl: str,
                       personJson: {}, personCache: {},
                       allowWriteToFile: bool) -> None:
    """Store an actor in the cache
    """
    if 'statuses' in personUrl or personUrl.endswith('/actor'):
        # This is not an actor or person account
        return

    currTime = datetime.datetime.utcnow()
    personCache[personUrl] = {
        "actor": personJson,
        "timestamp": currTime.strftime("%Y-%m-%dT%H:%M:%SZ")
    }
    if not baseDir:
        return

    # store to file
    if not allowWriteToFile:
        return
    if os.path.isdir(baseDir + '/cache/actors'):
        cacheFilename = baseDir + '/cache/actors/' + \
            personUrl.replace('/', '#') + '.json'
        if not os.path.isfile(cacheFilename):
            saveJson(personJson, cacheFilename)


def getPersonFromCache(baseDir: str, personUrl: str, personCache: {},
                       allowWriteToFile: bool) -> {}:
    """Get an actor from the cache
    """
    # if the actor is not in memory then try to load it from file
    loadedFromFile = False
    if not personCache.get(personUrl):
        # does the person exist as a cached file?
        cacheFilename = baseDir + '/cache/actors/' + \
            personUrl.replace('/', '#') + '.json'
        actorFilename = getFileCaseInsensitive(cacheFilename)
        if actorFilename:
            personJson = loadJson(actorFilename)
            if personJson:
                storePersonInCache(baseDir, personUrl, personJson,
                                   personCache, False)
                loadedFromFile = True

    if personCache.get(personUrl):
        if not loadedFromFile:
            # update the timestamp for the last time the actor was retrieved
            currTime = datetime.datetime.utcnow()
            currTimeStr = currTime.strftime("%Y-%m-%dT%H:%M:%SZ")
            personCache[personUrl]['timestamp'] = currTimeStr
        return personCache[personUrl]['actor']
    return None


def expirePersonCache(personCache: {}):
    """Expires old entries from the cache in memory
    """
    currTime = datetime.datetime.utcnow()
    removals = []
    for personUrl, cacheJson in personCache.items():
        cacheTime = datetime.datetime.strptime(cacheJson['timestamp'],
                                               "%Y-%m-%dT%H:%M:%SZ")
        daysSinceCached = (currTime - cacheTime).days
        if daysSinceCached > 2:
            removals.append(personUrl)
    if len(removals) > 0:
        for personUrl in removals:
            del personCache[personUrl]
        print(str(len(removals)) + ' actors were expired from the cache')


def storeWebfingerInCache(handle: str, wf, cachedWebfingers: {}) -> None:
    """Store a webfinger endpoint in the cache
    """
    cachedWebfingers[handle] = wf


def getWebfingerFromCache(handle: str, cachedWebfingers: {}) -> {}:
    """Get webfinger endpoint from the cache
    """
    if cachedWebfingers.get(handle):
        return cachedWebfingers[handle]
    return None


def getPersonPubKey(baseDir: str, session, personUrl: str,
                    personCache: {}, debug: bool,
                    projectVersion: str, httpPrefix: str,
                    domain: str, onionDomain: str,
                    signingPrivateKeyPem: str) -> str:
    if not personUrl:
        return None
    personUrl = personUrl.replace('#main-key', '')
    usersPaths = getUserPaths()
    for possibleUsersPath in usersPaths:
        if personUrl.endswith(possibleUsersPath + 'inbox'):
            if debug:
                print('DEBUG: Obtaining public key for shared inbox')
            personUrl = \
                personUrl.replace(possibleUsersPath + 'inbox', '/inbox')
            break
    personJson = \
        getPersonFromCache(baseDir, personUrl, personCache, True)
    if not personJson:
        if debug:
            print('DEBUG: Obtaining public key for ' + personUrl)
        personDomain = domain
        if onionDomain:
            if '.onion/' in personUrl:
                personDomain = onionDomain
        profileStr = 'https://www.w3.org/ns/activitystreams'
        asHeader = {
            'Accept': 'application/activity+json; profile="' + profileStr + '"'
        }
        personJson = \
            getJson(signingPrivateKeyPem,
                    session, personUrl, asHeader, None, debug,
                    projectVersion, httpPrefix, personDomain)
        if not personJson:
            return None
    pubKey = None
    if personJson.get('publicKey'):
        if personJson['publicKey'].get('publicKeyPem'):
            pubKey = personJson['publicKey']['publicKeyPem']
    else:
        if personJson.get('publicKeyPem'):
            pubKey = personJson['publicKeyPem']

    if not pubKey:
        if debug:
            print('DEBUG: Public key not found for ' + personUrl)

    storePersonInCache(baseDir, personUrl, personJson, personCache, True)
    return pubKey
