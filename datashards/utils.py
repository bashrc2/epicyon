from urllib.parse import urlparse, urlunparse
from .stores import MemoryStore, RemoteMagencStore, FileStore, RemoteFizzgigStore
from .client import Client

def filestore(u):
    """Take results of store and return FileStore object"""
    # We only care about the path for this
    return FileStore(u.path)

def memorystore(u):
    return MemoryStore()

def magencstore(u):
    # Remove magenc from the scheme and reassemble
    l = list(u)
    l[0] = l[0][7:]
    return RemoteMagencStore(urlunparse(l))

def fizzgigstore(u):
    l = list(u)
    l[0] = l[0].lstrip('fizz+')
    return RemoteFizzgigStore(urlunparse(l))

def store(uri):
    """Takes in a Datashards URI and returns the appropriate store for it

    Args:
      uri (string): The URI representation of the store
    Returns:
      Object: A datashards store
    """
    scheme_map = {
        'file': filestore,
        'memory': memorystore,
        'magenc': magencstore,
        'fizz': fizzgigstore,
    }

    parsed = urlparse(uri)
    scheme = parsed.scheme.split('+')[0]
    if scheme in scheme_map:
        return scheme_map[scheme](parsed)
    else:
        raise ValueError(f"Unsupported scheme for store {scheme}")


def client(uri):
    """Create a client tied to the store sent by uri

    Args:
       uri (string): The URI representation of the store
    Returns:
       Client: A datashards client
    """
    st = store(uri)
    return Client(st)

