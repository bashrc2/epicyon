import sys
from .base import BaseStore, GetStore, PutStore, CatalogStore, DeleteStore

class MemoryStore(BaseStore, GetStore,
                  PutStore, CatalogStore):
    """BasicStore is a basic datashards store with a memory backend.

    This is more of an example than anything you'd use
    """
    def __init__(self):
        """Create a new MemoryStore instance

        returns:
            A new `MemoryStore` object
        """
        self._store = {}
    
    def __repr__(self):
        return "memory://"

    def get(self, xt):
        self.__doc__ = GetStore.get.__doc__
        digest = super().validate_xt(xt)[2]
        return self._store[digest]

    def put(self, data):
        self.__doc__ = PutStore.put.__doc__
        super().validate_data(data)

        digest = super().sha256d_data(data)
        str_digest = d = str(digest, 'utf-8')
        self._store[str_digest] = data
        return self.xt_from_digest(digest)

    def delete(self, *xts):
        self.__doc__ = DeleteStore.delete.__doc__
        digests = [self.validate_xt(xt)[2] for xt in xts]
        for d in digests:
            del(self._store[d])

    def catalog(self):
        self.__doc__ = CatalogStore.catalog.__doc__
        return [self.xt_from_digest(digest) for digest in self._store.keys()]
