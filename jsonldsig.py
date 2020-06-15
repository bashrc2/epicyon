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
    from Cryptodome.Signature import pkcs1_15 as PKCS1_v1_5
except ImportError:
    from Crypto.PublicKey import RSA
    from Crypto.Hash import SHA256
    from Crypto.Signature import PKCS1_v1_5

from pyld import jsonld

import base64
import json


def b64safeEncode(payload):
    """
    b64 url safe encoding with the padding removed.
    """
    return base64.urlsafe_b64encode(payload).rstrip(b'=')


def b64safeDecode(payload):
    """
    b64 url safe decoding with the padding added.
    """
    return base64.urlsafe_b64decode(payload + b'=' * (4 - len(payload) % 4))


def normalizeJson(payload):
    return json.dumps(payload, separators=(',', ':'),
                      sort_keys=True).encode('utf-8')


def signRs256(payload, private_key):
    """
    Produce a RS256 signature of the payload
    """
    key = RSA.importKey(private_key)
    signer = PKCS1_v1_5.new(key)
    signature = signer.sign(SHA256.new(payload))
    return signature


def verifyRs256(payload, signature, public_key):
    """
    Verifies a RS256 signature
    """
    key = RSA.importKey(public_key)
    verifier = PKCS1_v1_5.new(key)
    return verifier.verify(SHA256.new(payload), signature)


def signJws(payload, private_key):
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

    signature = signRs256(preparedPayload, private_key)
    encodedSignature = b64safeEncode(signature)
    jwsSignature = b'..'.join([encodedHeader, encodedSignature])

    return jwsSignature


def verifyJws(payload, jws_signature, public_key):
    # remove the encoded header from the signature
    encodedHeader, encodedSignature = jws_signature.split(b'..')
    signature = b64safeDecode(encodedSignature)
    payload = b'.'.join([encodedHeader, payload])
    return verifyRs256(payload, signature, public_key)


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


def testSignJsonld(jldDocument: {}, privateKeyPem: str,
                   expectedJldDocumentSigned=None):
    signedJldDocument = jsonldSign(jldDocument, privateKeyPem)
    # pop the created time key since its dynamic
    signedJldDocument['signature'].pop('created')

    if expectedJldDocumentSigned:
        assert signedJldDocument == expectedJldDocumentSigned
    else:
        return signedJldDocument
