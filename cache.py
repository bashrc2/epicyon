__filename__ = "cache.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "0.0.1"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import datetime

def storePersonInCache(personUrl: str,personJson: {},personCache: {}) -> None:
    """Store an actor in the cache
    """
    currTime=datetime.datetime.utcnow()
    personCache[personUrl]={
        "actor": personJson,
        "timestamp": currTime.strftime("%Y-%m-%dT%H:%M:%SZ")
    }

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
