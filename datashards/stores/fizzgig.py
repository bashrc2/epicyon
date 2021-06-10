import requests
from .base import BaseStore, GetStore, PutStore, StoreError

class RemoteFizzgigStore(BaseStore, GetStore, PutStore):
    """A remote Fizzgig store"""


    def __init__(self, url):
        """Create a RemoteFizzgigStore

        Args:
            url (string): The location of the store
        Returns:
            RemoteFizzgigStore
        """
        self.url = url

    def __repr__(self):
        return f"fizz+{self.url}"
    
    def get(self, xt):
        self.__doc__ = GetStore.get.__doc__
        self.validate_xt(xt)
        url = self.url + '/get'
        payload = {'xt': xt}
        r = requests.get(url, params=payload)
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
        url = self.url + '/put'
        r = requests.put(url=url, data=data)
        if r.status_code == 400:
            raise ValueError(r.content.decode('utf-8'))
            return
        elif r.status_code == 500:
            raise StoreError(r.content.decode('utf-8'))
            return
        parsed = r.json()
        return parsed['xt']
