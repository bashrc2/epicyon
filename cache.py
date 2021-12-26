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
from utils import load_json
from utils import save_json
from utils import getFileCaseInsensitive
from utils import get_user_paths


def _removePersonFromCache(base_dir: str, personUrl: str,
                           person_cache: {}) -> bool:
    """Removes an actor from the cache
    """
    cacheFilename = base_dir + '/cache/actors/' + \
        personUrl.replace('/', '#') + '.json'
    if os.path.isfile(cacheFilename):
        try:
            os.remove(cacheFilename)
        except OSError:
            print('EX: unable to delete cached actor ' + str(cacheFilename))
    if person_cache.get(personUrl):
        del person_cache[personUrl]


def checkForChangedActor(session, base_dir: str,
                         http_prefix: str, domain_full: str,
                         personUrl: str, avatarUrl: str, person_cache: {},
                         timeoutSec: int):
    """Checks if the avatar url exists and if not then
    the actor has probably changed without receiving an actor/Person Update.
    So clear the actor from the cache and it will be refreshed when the next
    post from them is sent
    """
    if not session or not avatarUrl:
        return
    if domain_full in avatarUrl:
        return
    if urlExists(session, avatarUrl, timeoutSec, http_prefix, domain_full):
        return
    _removePersonFromCache(base_dir, personUrl, person_cache)


def storePersonInCache(base_dir: str, personUrl: str,
                       personJson: {}, person_cache: {},
                       allowWriteToFile: bool) -> None:
    """Store an actor in the cache
    """
    if 'statuses' in personUrl or personUrl.endswith('/actor'):
        # This is not an actor or person account
        return

    curr_time = datetime.datetime.utcnow()
    person_cache[personUrl] = {
        "actor": personJson,
        "timestamp": curr_time.strftime("%Y-%m-%dT%H:%M:%SZ")
    }
    if not base_dir:
        return

    # store to file
    if not allowWriteToFile:
        return
    if os.path.isdir(base_dir + '/cache/actors'):
        cacheFilename = base_dir + '/cache/actors/' + \
            personUrl.replace('/', '#') + '.json'
        if not os.path.isfile(cacheFilename):
            save_json(personJson, cacheFilename)


def getPersonFromCache(base_dir: str, personUrl: str, person_cache: {},
                       allowWriteToFile: bool) -> {}:
    """Get an actor from the cache
    """
    # if the actor is not in memory then try to load it from file
    loadedFromFile = False
    if not person_cache.get(personUrl):
        # does the person exist as a cached file?
        cacheFilename = base_dir + '/cache/actors/' + \
            personUrl.replace('/', '#') + '.json'
        actorFilename = getFileCaseInsensitive(cacheFilename)
        if actorFilename:
            personJson = load_json(actorFilename)
            if personJson:
                storePersonInCache(base_dir, personUrl, personJson,
                                   person_cache, False)
                loadedFromFile = True

    if person_cache.get(personUrl):
        if not loadedFromFile:
            # update the timestamp for the last time the actor was retrieved
            curr_time = datetime.datetime.utcnow()
            curr_timeStr = curr_time.strftime("%Y-%m-%dT%H:%M:%SZ")
            person_cache[personUrl]['timestamp'] = curr_timeStr
        return person_cache[personUrl]['actor']
    return None


def expirePersonCache(person_cache: {}):
    """Expires old entries from the cache in memory
    """
    curr_time = datetime.datetime.utcnow()
    removals = []
    for personUrl, cacheJson in person_cache.items():
        cacheTime = datetime.datetime.strptime(cacheJson['timestamp'],
                                               "%Y-%m-%dT%H:%M:%SZ")
        daysSinceCached = (curr_time - cacheTime).days
        if daysSinceCached > 2:
            removals.append(personUrl)
    if len(removals) > 0:
        for personUrl in removals:
            del person_cache[personUrl]
        print(str(len(removals)) + ' actors were expired from the cache')


def storeWebfingerInCache(handle: str, wf, cached_webfingers: {}) -> None:
    """Store a webfinger endpoint in the cache
    """
    cached_webfingers[handle] = wf


def getWebfingerFromCache(handle: str, cached_webfingers: {}) -> {}:
    """Get webfinger endpoint from the cache
    """
    if cached_webfingers.get(handle):
        return cached_webfingers[handle]
    return None


def getPersonPubKey(base_dir: str, session, personUrl: str,
                    person_cache: {}, debug: bool,
                    project_version: str, http_prefix: str,
                    domain: str, onion_domain: str,
                    signing_priv_key_pem: str) -> str:
    if not personUrl:
        return None
    personUrl = personUrl.replace('#main-key', '')
    usersPaths = get_user_paths()
    for possibleUsersPath in usersPaths:
        if personUrl.endswith(possibleUsersPath + 'inbox'):
            if debug:
                print('DEBUG: Obtaining public key for shared inbox')
            personUrl = \
                personUrl.replace(possibleUsersPath + 'inbox', '/inbox')
            break
    personJson = \
        getPersonFromCache(base_dir, personUrl, person_cache, True)
    if not personJson:
        if debug:
            print('DEBUG: Obtaining public key for ' + personUrl)
        personDomain = domain
        if onion_domain:
            if '.onion/' in personUrl:
                personDomain = onion_domain
        profileStr = 'https://www.w3.org/ns/activitystreams'
        asHeader = {
            'Accept': 'application/activity+json; profile="' + profileStr + '"'
        }
        personJson = \
            getJson(signing_priv_key_pem,
                    session, personUrl, asHeader, None, debug,
                    project_version, http_prefix, personDomain)
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

    storePersonInCache(base_dir, personUrl, personJson, person_cache, True)
    return pubKey
