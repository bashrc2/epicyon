__filename__ = "cache.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "0.0.1"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

# cache of actor json
# If there are repeated lookups then this helps prevent a lot
# of needless network traffic
personCache = {}

# cached webfinger endpoints
cachedWebfingers = {}

def storePersonInCache(personUrl: str,personJson) -> None:
    """Store an actor in the cache
    """
    personCache[personUrl]=personJson

def storeWebfingerInCache(handle: str,wf) -> None:
    """Store a webfinger endpoint in the cache
    """
    cachedWebfingers[handle]=wf

def getPersonFromCache(personUrl: str):
    """Get an actor from the cache
    """
    if personCache.get(personUrl):
        return personCache[personUrl]
    return None

def getWebfingerFromCache(handle: str):
    """Get webfinger endpoint from the cache
    """
    if cachedWebfingers.get(handle):
        return cachedWebfingers[handle]
    return None
