import hashlib
import base64
import random

notimplemented = "This method is inherited from an abastract base class"


class StoreError(Exception):
    pass


class BaseStore():
    """This is the core abstract base store that offers validation"""
    # Currently only sha256 is supported
    _hash_algorithms = ('sha256d')
    _shard_size = 32768

    def validate_xt(self, xt):
        """Validate the XT

        Args:
            xt (str): The shard in XT form ``urn:<algorith>:<hash>``
        Returns:
            tuple(str): The urn, algorithm and digest
        Raises:
            ValueError: Raised if the XT is invalid
        """
        try:
            scheme, algorithm, digest = xt.split(':')
        except ValueError:
            raise ValueError(f"XT must be in the form urn:<algorithm>:<hash>. Instead we have {xt}")
        if scheme != 'urn':
            raise ValueError("XTs must begin with 'urn'")
        if algorithm not in self._hash_algorithms:
            raise ValueError(f"Hashing algorithm {algorithm} not supported")
        return scheme, algorithm, digest

    def validate_data(self, data, sizes=(32768,)):
        """Validate data that will be stored

        Args:
            data (bytes): The data
        Returns:
            bool: True if valid
        Raises:
            ValueError: Raised if the data is invalid (wrong type or size)
        """
        if not isinstance(data, bytes):
            raise ValueError("Data must of type bytes")
        if not len(data) in sizes:
            raise ValueError("Data must be of supported size")
        return True

    def sha256d_data(self, data):
        digest = hashlib.sha256(data).digest()
        digest2 = hashlib.sha256(digest).digest()
        encoded_digest = base64.urlsafe_b64encode(digest2)
        return encoded_digest

    def xt_from_digest(self, digest, algorithm='sha256d'):
        if isinstance(digest, bytes):
            digest = str(digest, 'utf-8')
        return f"urn:{algorithm}:{digest}"


class GetStore():
    """This is the abstract base class for stores that have the "get" method"""
    def get(self, xt):
        """Get a shard from the store by XT

        Args:
            xt (string): ID of the shard in XT form ``urn:<algorithm>:<hash>``
        Returns:
            bytes: The requested data as a bytearray
        Raises:
            KeyError: Raised when the requested XT is not found
            ValueError: Raised when the XT is improperly formatted
            NotImplementedError: Raised if XT uses an unsupported algorithm
            StoreError: Raised if the store has an unknown internal error

        """
        raise NotImplementedError(notimplemented)


class PutStore():
    def put(self, data):
        """Place the data in the store

        Args:
            data (bytearray): The data to store

            Currently this must be a 32k long byte array

        Returns:
            string: The URN of the data in XT form ``urn:<algorithm>:<hash>``

            If the store supports multiple hashing algorithms, it will select
            its preferred algorithm

        Raises:
            ValueError: Raised if data is of the wrong type or unsupported size
            StoreError: Raised if the store has an unknown internal error

        """
        raise NotImplementedError(notimplemented)


class DeleteStore():
    def delete(self, *shard):
        """Delete a shard from the store

        Args:
            shards: Shard(s) to delete from the store
        Raises:
            KeyError: Raised when the requested shard is not found
            ValueError: Raised when the XT is improperly formatted
            StoreError: Raised if the store has an unknown internal error
        """
        raise NotImplementedError(notimplemented)


class CatalogStore():
    def catalog(self):
        """Get a listing of all the shards in the store

            Returns:
                list (string): A list of shards in the store in XT form

            Raises:
                StoreError: Raised if the store has an unknown internal error
        """
        raise NotImplementedError(notimplemented)

    def _random_shards(self, n=1):
        """Get a selection of random shards in the store

        Args:
            n (int): Number of random shards to retrieve
        Returns:
            list (string): A list of shards in XT form
        Raises:
            StoreError: Raised if the store has an unknown internal error
        """
        return random.choices(self.catalog(), k=n)


class UsedStore(BaseStore, CatalogStore):
    def used(self):
        """Get the storage used by the store in bytes

        Returns:
            int: The number of bytes used by the store

        Raises:
            StoreError: Raised if the store has an unknown internal error
        """
        return len(self.catalog()) * self._shard_size


class FreeupStore(CatalogStore, DeleteStore):
    def freeup(self, count=1):
        """Free up space in the store

        This method will free up space in the store
        and return the list of shards it has deleted

        Args:
            count (int); The number of items to delete from the store
        Returns:
            list (string): The list of deleted shards in XT form
        Raises:
            StoreError: Raised if the store has an unknown internal error
        """
        # This may not work due to inheritance!
        shards = random.choices(self.catalog(), k=count)
        self.deletes(shards)
        return shards
