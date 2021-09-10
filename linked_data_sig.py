__filename__ = "linked_data_sig.py"
__author__ = "Bob Mottram"
__credits__ = ['Based on ' +
               'https://github.com/tsileo/little-boxes']
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Security"

import base64
import hashlib
from datetime import datetime
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import utils as hazutils
from pyjsonld import normalize
from context import hasValidContext
from utils import getSHA256


def _options_hash(doc: {}) -> str:
    """Returns a hash of the signature, with a few fields removed
    """
    docSig = dict(doc["signature"])

    # remove fields from signature
    for k in ["type", "id", "signatureValue"]:
        if k in docSig:
            del docSig[k]

    docSig["@context"] = "https://w3id.org/identity/v1"
    options = {
        "algorithm": "URDNA2015",
        "format": "application/nquads"
    }

    normalized = normalize(docSig, options)
    h = hashlib.new("sha256")
    h.update(normalized.encode("utf-8"))
    return h.hexdigest()


def _doc_hash(doc: {}) -> str:
    """Returns a hash of the ActivityPub post
    """
    doc = dict(doc)

    # remove the signature
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


def verifyJsonSignature(doc: {}, publicKeyPem: str) -> bool:
    """Returns True if the given ActivityPub post was sent
    by an actor having the given public key
    """
    if not hasValidContext(doc):
        return False
    pubkey = load_pem_public_key(publicKeyPem.encode('utf-8'),
                                 backend=default_backend())
    to_be_signed = _options_hash(doc) + _doc_hash(doc)
    signature = doc["signature"]["signatureValue"]

    digest = getSHA256(to_be_signed.encode("utf-8"))
    base64sig = base64.b64decode(signature)

    try:
        pubkey.verify(
            base64sig,
            digest,
            padding.PKCS1v15(),
            hazutils.Prehashed(hashes.SHA256()))
        return True
    except BaseException:
        return False


def generateJsonSignature(doc: {}, privateKeyPem: str) -> None:
    """Adds a json signature to the given ActivityPub post
    """
    if not doc.get('actor'):
        return
    if not hasValidContext(doc):
        return
    options = {
        "type": "RsaSignature2017",
        "creator": doc["actor"] + "#main-key",
        "created": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
    }
    doc["signature"] = options
    to_be_signed = _options_hash(doc) + _doc_hash(doc)

    key = load_pem_private_key(privateKeyPem.encode('utf-8'),
                               None, backend=default_backend())
    digest = getSHA256(to_be_signed.encode("utf-8"))
    signature = key.sign(digest,
                         padding.PKCS1v15(),
                         hazutils.Prehashed(hashes.SHA256()))
    sig = base64.b64encode(signature)
    options["signatureValue"] = sig.decode("utf-8")
