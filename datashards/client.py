__filename__ = "client.py"
__author__ = "Serge Wroclawski"
__author_email__ = 'serge@wroclawski.org'
__license__ = "Apache 2.0"
__version__ = "0.1"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

from base64 import urlsafe_b64decode, urlsafe_b64encode
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import os
import secrets
import hashlib
import datashards.usexp

# The size of the IV in Python Cryptdome should be 32 bytes
IV_SIZE = 16
CHUNK_SIZE = 32768
MAX_RAW_SIZE = CHUNK_SIZE - 13  # 13 is the number of bits for sexp
KEY_SIZE = 32

BACKEND = default_backend()


def generate_key(length=KEY_SIZE):
    """Generate a random key of length

    Args:
        length (int): The size of the key
    Returns:
        string: The random key
    """
    return secrets.token_bytes(length)


def make_iv(key, prefix, count=0):
    """Make the initiaization vector for encryption/decryption

    Args:
       key (bytes): The symmetrical key
       prefix (str): The prefix to use ("entry" or "content")
       count (int): The counter (defaults to 0)

    Returns:
       bytes: The initialization vector in bytes
    """
    # TODO: This needs to switch to appending together bytes
    c = str(count).encode('latin-1')
    raw = prefix + c + key
    return hashlib.sha256(raw).digest()[:IV_SIZE]


def encrypt_shard_entry(data, key):
    """Encrypt a raw file

    Args:
       data (bytes): The data to be encrypted
       key (bytes): The symmetrical key

    Returns:
       bytes: The encrypted data
    """
    iv = make_iv(key, b'entry-point')
    cipher = Cipher(algorithms.AES(key), modes.CTR(iv), backend=BACKEND)
    encryptor = cipher.encryptor()
    return encryptor.update(data) + encryptor.finalize()


def decrypt_shard_entry(data, key):
    """Decrypt an entry shard file

    Args:
        data (bytes): The bytes to be decrypted
        key (bytes): The symmetical key

    Returns:
        bytes: The decrypted data
    """
    iv = make_iv(key, b'entry-point')
    cipher = Cipher(algorithms.AES(key), modes.CTR(iv), backend=BACKEND)
    decryptor = cipher.decryptor()
    return decryptor.update(data) + decryptor.finalize()


def encrypt_shard_chunk(data, key, count):
    """Encrypt a file chunk

    Args:
       data (bytes): The data to be encrypted
       key (bytes): The symmetrical key
       count (int): The block count

    Returns:
       bytes: The encrypted data
    """
    iv = make_iv(key, b'content', count)
    cipher = Cipher(algorithms.AES(key), modes.CTR(iv), backend=BACKEND)
    encryptor = cipher.encryptor()
    return encryptor.update(data) + encryptor.finalize()


def decrypt_shard_chunk(data, key, count):
    """Decrypt a file chunk

    Args:
       data (bytes): The data to be decrypted
       key (bytes): The symmetrical key
       count (int): The block count

    Returns:
       bytes: The decrypted data
    """
    iv = make_iv(key, b'content', count)
    cipher = Cipher(algorithms.AES(key), modes.CTR(iv), backend=BACKEND)
    decryptor = cipher.decryptor()
    return decryptor.update(data) + decryptor.finalize()


def make_manifest(xts, size):
    """Create a manifest

    Args:
        urns (list): A list of the URNS for the chunks

    Returns:
        bytes: The raw (unencrypted) manifest
    """
    manifest_data = ["manifest", size] + xts
    manifest = usexp.dumpb(manifest_data)
    size = len(manifest)
    if size > MAX_RAW_SIZE:
        raise NotImplementedError("Manifest too large")
    return manifest


def pad(data, size=CHUNK_SIZE):
    """Pad data to 32k

    Args:
        data (bytes): The data to pad
        size (int): The size of the destination
    Returns:
        bytes: The padded data
    """
    data_size = len(data)
    return data + (b'\0' * (size - data_size))


def read_manifest(mlist):
    """Takes in a manifest list and coerces the correct data structures from it

    Args:
        mlist (list): The manifest in list form
    Returns:
        list: A usable manifest list
    """
    manifest = [mlist[0].decode(), int(mlist[1])]
    xts = [i.decode() for i in mlist[2:]]
    manifest = manifest + xts
    return manifest


def make_raw_shard(data):
    """Create a raw shard

    Args:
        data (bytes): The data
    Returns
        bytes: The data as a Data Shard raw entity
    """
    raw = ['raw', data]
    return usexp.dumpb(raw)


class Client():
    def __init__(self, store):
        self.store = store

    def upload(self, fd, keyfun=generate_key):
        """Upload a file to a store

        Args:
            fd (file-like object): The file to send
            keyfun (function): Function to generate the key (used for testing)
        Raises:
            NotImplementedError: If the store does not support the 'put' method
        """
        if not hasattr(self.store, 'put'):
            raise NotImplementedError("Store doesn't support the 'put' method")

        size = os.fstat(fd.fileno()).st_size
        key = keyfun()
        if size <= MAX_RAW_SIZE:
            # If file is smaller than max raw file size, create a "raw" entity
            data = fd.read()
            sexp = make_raw_shard(data)
            padded = pad(sexp)
            encrypted_data = encrypt_shard_entry(padded, key)
            xt_urn = self.store.put(encrypted_data)
            xt = xt_urn.split(':')[2]
            b64key = urlsafe_b64encode(key).rstrip(b'=').decode()
            return f"idsc:p0.{xt}.{b64key}"
        else:
            xts = []
            count = 0
            current_size = 0
            while current_size <= size:
                raw_data = fd.read(CHUNK_SIZE)
                if len(raw_data) < CHUNK_SIZE:
                    raw_data = pad(raw_data)
                data = encrypt_shard_chunk(raw_data, key, count)
                xt_urn = self.store.put(data)
                xts.append(xt_urn)
                count += 1
                current_size += CHUNK_SIZE
            # Finally generate the manifest
            manifest = make_manifest(xts, size)
            padded_manifest = pad(manifest)
            encrypted_manifest = encrypt_shard_entry(padded_manifest, key)
            xt_urn = self.store.put(encrypted_manifest)
            xt = xt_urn.split(':')[2]
            b64key = urlsafe_b64encode(key).rstrip(b'=').decode()
            return f"idsc:p0.{xt}.{b64key}"

    def download(self, urn, fd):
        """Download a file from a store

        Takes a URN and writes the data to the file descriptor

        Args:
            urn (string): The URN of the file
            fd (file-like object): A file object to write the file to
        Raises:
            NotImplementedError: If the store does not support 'get'
        """
        if not hasattr(self.store, 'get'):
            raise NotImplementedError("Store does not support 'get' method")
        scheme, payload = urn.split(':')
        if scheme != 'idsc':
            raise NotImplementedError("Client can only handle IDSCs")
        enc_suite, xt, b64key_prepad = payload.split('.')
        pad = "=" * (4 - (len(b64key_prepad) % 4))
        b64key = b64key_prepad + pad
        key = urlsafe_b64decode(b64key)
        xt_urn = f"urn:sha256d:{xt}"
        encrypted_data = self.store.get(xt_urn)
        decrypted_data = decrypt_shard_entry(encrypted_data, key)
        data = usexp.loadb(decrypted_data)
        if data[0] == b'raw':
            fd.write(data[1])
            fd.flush()
            return
        elif data[0] == b'manifest':
            manifest = read_manifest(data)
            size, chunks = manifest[1], manifest[2:]
            # We need to assemble the pieces
            i = 0
            current_size = 0
            for chunk in chunks:
                encrypted_data = self.store.get(chunk)
                data = decrypt_shard_chunk(encrypted_data, key, i)
                current_size += CHUNK_SIZE
                if current_size > size:
                    fd.write(data[:size % CHUNK_SIZE])
                    fd.flush()
                else:
                    fd.write(data)
                    fd.flush()
                i += 1
