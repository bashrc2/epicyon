import requests
from .base import BaseStore, GetStore, PutStore, StoreError

class RemoteMagencStore(BaseStore, GetStore, PutStore):
    """This is an impelmentation of the original Remote Magenc Store"""

    def __init__(self, url):
        """Create a RemoteMagencStore

        Args:
            url (string): The location of the store
        Returns:
            RemoteMagencStore
        """
        self.url = url

    def __repr__(self):
        return f"magenc+{self.url}"

    def get(self, xt):
        self.__doc__ = GetStore.get.__doc__
        self.validate_xt(xt)
        payload = {'xt': xt}
        r = requests.get(self.url, params=payload)
        if r.status_code == 404:
            raise KeyError("Shard not found")
            return
        elif r.status_code == 400:
            raise ValueError(r.content.decode('utf-8'))
            return
        elif r.status_code == 500:
            raise StoreError(r.content.decode('utf-8'))
            return
        return r.content
    
    def put(self, data):
        self.__doc__ = PutStore.put.__doc__
        self.validate_data(data)
        r = requests.post(url=self.url, data=data)
        if r.status_code == 400:
            raise ValueError(r.content.decode('utf-8'))
            return
        elif r.status_code == 500:
            raise StoreError(r.content.decode('utf-8'))
            return
        return r.text