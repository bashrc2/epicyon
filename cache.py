__filename__ = "cache.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "0.0.1"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import os
import datetime
import commentjson

def storePersonInCache(baseDir: str,personUrl: str,personJson: {},personCache: {}) -> None:
    """Store an actor in the cache
    """
    currTime=datetime.datetime.utcnow()
    personCache[personUrl]={
        "actor": personJson,
        "timestamp": currTime.strftime("%Y-%m-%dT%H:%M:%SZ")
    }
    if not baseDir:
        return

    # store to file
    if not os.path.isdir(baseDir+'/cache'):
        os.mkdir(baseDir+'/cache')
    if not os.path.isdir(baseDir+'/cache/actors'):
        os.mkdir(baseDir+'/cache/actors')
    cacheFilename=baseDir+'/cache/actors/'+personUrl.replace('/','#')+'.json'
    if not os.path.isfile(cacheFilename):
        with open(cacheFilename, 'w') as fp:
            commentjson.dump(personJson, fp, indent=4, sort_keys=False)

def storeWebfingerInCache(handle: str,wf,cachedWebfingers: {}) -> None:
    """Store a webfinger endpoint in the cache
    """
    cachedWebfingers[handle]=wf

def getPersonFromCache(personUrl: str,personCache: {}) -> {}:
    """Get an actor from the cache
    """
    if personCache.get(personUrl):
        # how old is the cached data?
        currTime=datetime.datetime.utcnow()
        cacheTime= \
            datetime.datetime.strptime(personCache[personUrl]['timestamp'], \
                                       "%Y-%m-%dT%H:%M:%SZ")
        daysSinceCached=(currTime - cacheTime).days
        # return cached value if it has not expired
        if daysSinceCached <= 2:
            return personCache[personUrl]['actor']        
    return None

def getWebfingerFromCache(handle: str,cachedWebfingers: {}) -> {}:
    """Get webfinger endpoint from the cache
    """
    if cachedWebfingers.get(handle):
        return cachedWebfingers[handle]
    return None
