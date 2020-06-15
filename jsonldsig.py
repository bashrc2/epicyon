__filename__ = "jsonldsig.py"
__author__ = "Bob Mottram"
__credits__ = ['Based on ' +
               'https://github.com/WebOfTrustInfo/ld-signatures-python']
__license__ = "AGPL3+"
__version__ = "1.1.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

from copy import deepcopy
from datetime import datetime

import pytz

try:
    from Cryptodome.PublicKey import RSA
    from Cryptodome.Hash import SHA256
    from Cryptodome.Signature import pkcs1_5 as PKCS1_v1_5
except ImportError:
    from Crypto.PublicKey import RSA
    from Crypto.Hash import SHA256
    from Crypto.Signature import PKCS1_v1_5

from pyld import jsonld

import base64
import json


def b64safeEncode(payload: {}) -> str:
    """
    b64 url safe encoding with the padding removed.
    """
    return base64.urlsafe_b64encode(payload).rstrip(b'=')


def b64safeDecode(payload: {}) -> str:
    """
    b64 url safe decoding with the padding added.
    """
    return base64.urlsafe_b64decode(payload + b'=' * (4 - len(payload) % 4))


def normalizeJson(payload: {}) -> str:
    return json.dumps(payload, separators=(',', ':'),
                      sort_keys=True).encode('utf-8')


def signRs256(payload: {}, privateKey: str) -> str:
    """
    Produce a RS256 signature of the payload
    """
    key = RSA.importKey(privateKey)
    signer = PKCS1_v1_5.new(key)
    signature = signer.sign(SHA256.new(payload))
    return signature


def verifyRs256(payload: {}, signature: str, publicKeyPem: str) -> bool:
    """
    Verifies a RS256 signature
    """
    key = RSA.importKey(publicKeyPem)
    verifier = PKCS1_v1_5.new(key)
    return verifier.verify(SHA256.new(payload), signature)


def signJws(payload: {}, privateKey: str) -> str:
    """ Prepare payload to sign
    """
    header = {
        'alg': 'RS256',
        'b64': False,
        'crit': ['b64']
    }
    normalizedJson = normalizeJson(header)
    encodedHeader = b64safeEncode(normalizedJson)
    preparedPayload = b'.'.join([encodedHeader, payload])

    signature = signRs256(preparedPayload, privateKey)
    encodedSignature = b64safeEncode(signature)
    jwsSignature = b'..'.join([encodedHeader, encodedSignature])

    return jwsSignature


def verifyJws(payload: {}, jwsSignature: str, publicKeyPem: str) -> bool:
    # remove the encoded header from the signature
    encodedHeader, encodedSignature = jwsSignature.split(b'..')
    signature = b64safeDecode(encodedSignature)
    payload = b'.'.join([encodedHeader, payload])
    return verifyRs256(payload, signature, publicKeyPem)


def jsonldNormalize(jldDocument: str):
    """
    Normalize and hash the json-ld document
    """
    options = {
        'algorithm': 'URDNA2015',
        'format': 'application/nquads'
    }
    normalized = jsonld.normalize(jldDocument, options=options)
    normalizedHash = SHA256.new(data=normalized.encode('utf-8')).digest()
    return normalizedHash


def jsonldSign(jldDocument: {}, privateKeyPem: str) -> {}:
    """
    Produces a signed JSON-LD document with a Json Web Signature
    """
    jldDocument = deepcopy(jldDocument)
    normalizedJldHash = jsonldNormalize(jldDocument)
    jwsSignature = signJws(normalizedJldHash, privateKeyPem)

    # construct the signature document and add it to jsonld
    signature = {
        'type': 'RsaSignatureSuite2017',
        'created': datetime.now(tz=pytz.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'signatureValue': jwsSignature.decode('utf-8')
    }
    jldDocument.update({'signature': signature})

    return jldDocument


def jsonldVerify(signedJldDocument: {}, publicKeyPem: str) -> bool:
    """
    Verifies the Json Web Signature of a signed JSON-LD Document
    """
    signedJldDocument = deepcopy(signedJldDocument)
    signature = signedJldDocument.pop('signature')
    jwsSignature = signature['signatureValue'].encode('utf-8')
    normalizedJldHash = jsonldNormalize(signedJldDocument)

    return verifyJws(normalizedJldHash, jwsSignature, publicKeyPem)


def testSignJsonld(jldDocument: {}, privateKeyPem: str) -> {}:
    """Creates a test signature
    """
    signedJldDocument = jsonldSign(jldDocument, privateKeyPem)

    # pop the created time key since its dynamic
    signedJldDocument['signature'].pop('created')

    return signedJldDocument
