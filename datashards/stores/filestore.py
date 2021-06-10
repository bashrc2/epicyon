import os
from .base import BaseStore, GetStore, PutStore, \
    FreeupStore, UsedStore, StoreError, CatalogStore

class FileStore(BaseStore, GetStore, PutStore, FreeupStore):
    """A datashards store with a file backend
    """
    def __init__(self, directory=None, create_dir=False):
        """Instantiate the store

        Args:
            directory: The directory where the data should be stored
        Returns:
            A new FileStore isinstance
        """
        if not os.path.isdir(directory):
            if create_dir:
                os.mkdir(directory)
            else:
                raise ValueError(f"Store directory {directory} does not exist")
        self._dir = directory

    def __repr__(self):
        dir = os.path.abspath(self._dir)
        return f"file://{dir}"

    def get(self, xt):
        self.__doc__ = GetStore.get.__doc__
        digest = self.validate_xt(xt)[2]
        path = os.path.join(self._dir, digest)
        if os.path.exists(path):
            try:
                with open(path, 'rb') as fd:
                    return fd.read()
            except OSError:
                raise StoreError()

    def put(self, data):
        self.__doc__ = PutStore.put.__doc__
        self.validate_data(data)
        digest = str(self.sha256d_data(data), 'utf-8')
        path = os.path.join(self._dir, digest)
        if not os.path.exists(path):
            try:
                with open(path, 'wb') as fd:
                    fd.write(data)
            except OSError:
                raise StoreError()
        xt = f"urn:sha256d:{digest}"
        return xt

    def catalog(self):
        self.__doc__ = CatalogStore.catalog.__doc__
        # We'll assume the store directory does not contain other files
        return [self.xt_from_digest(f) for f in os.listdir(self._dir) 
                if os.path.isfile(os.path.join(self._dir, f))]

    def delete(self, xts):
        self.__doc__ = DeleteStore.deletes.__doc__

        digests = [self.validate_data[xt][2] for xt in l]
        for digest in digests:
            path = os.path.join(self._dir, digest)
            try:
                os.remove(path)
            except OSError:
                raise StoreError()
        return digests
