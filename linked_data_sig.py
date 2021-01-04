__filename__ = "linked_data_sig.py"
__author__ = "Bob Mottram"
__credits__ = ['Based on ' +
               'https://github.com/tsileo/little-boxes']
__license__ = "AGPL3+"
__version__ = "1.1.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import base64
import hashlib
from datetime import datetime

try:
    from Cryptodome.PublicKey import RSA
    from Cryptodome.Hash import SHA256
    from Cryptodome.Signature import pkcs1_5 as PKCS1_v1_5
except ImportError:
    from Crypto.PublicKey import RSA
    from Crypto.Hash import SHA256
    from Crypto.Signature import PKCS1_v1_5

from pyjsonld import normalize


def _options_hash(doc):
    doc = dict(doc["signature"])
    for k in ["type", "id", "signatureValue"]:
        if k in doc:
            del doc[k]
    doc["@context"] = "https://w3id.org/identity/v1"
    options = {
        "algorithm": "URDNA2015",
        "format": "application/nquads"
    }
    normalized = normalize(doc, options)
    h = hashlib.new("sha256")
    h.update(normalized.encode("utf-8"))
    return h.hexdigest()


def _doc_hash(doc):
    doc = dict(doc)
    if "signature" in doc:
        del doc["signature"]
    options = {
        "algorithm": "URDNA2015",
        "format": "application/nquads"
    }
    normalized = normalize(doc, options)
    h = hashlib.new("sha256")
    h.update(normalized.encode("utf-8"))
    return h.hexdigest()


def verifyJsonSignature(doc: {}, publicKeyPem: str):
    key = RSA.importKey(publicKeyPem)
    to_be_signed = _options_hash(doc) + _doc_hash(doc)
    signature = doc["signature"]["signatureValue"]
    signer = PKCS1_v1_5.new(key)  # type: ignore
    digest = SHA256.new()
    digest.update(to_be_signed.encode("utf-8"))
    return signer.verify(digest, base64.b64decode(signature))  # type: ignore


def generateJsonSignature(doc: {}, privateKeyPem: str):
    if not doc.get('actor'):
        return

    options = {
        "type": "RsaSignature2017",
        "creator": doc["actor"] + "#main-key",
        "created": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
    }
    doc["signature"] = options
    to_be_signed = _options_hash(doc) + _doc_hash(doc)

    key = RSA.importKey(privateKeyPem)
    signer = PKCS1_v1_5.new(key)
    digest = SHA256.new()
    digest.update(to_be_signed.encode("utf-8"))
    sig = base64.b64encode(signer.sign(digest))  # type: ignore
    options["signatureValue"] = sig.decode("utf-8")
