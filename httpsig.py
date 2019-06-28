__filename__ = "posts.py"
__author__ = "Bob Mottram"
__credits__ = ['lamia']
__license__ = "AGPL3+"
__version__ = "0.0.1"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

from person import createPerson
from Crypto.PublicKey import RSA
from Crypto.Hash import SHA256
#from Crypto.Signature import PKCS1_v1_5
from Crypto.Signature import pkcs1_15
from requests.auth import AuthBase
import base64
import json

def signPostHeaders(privateKeyPem: str, username: str, domain: str, path: str, https: bool, messageBodyJson) -> str:
    """Returns a raw signature string that can be plugged into a header and
    used to verify the authenticity of an HTTP transmission.
    """
    prefix='https'
    if not https:
        prefix='http'    
    keyID = prefix+'://'+domain+'/'+username+'#main-key'
    if not messageBodyJson:
        headers = {'host': domain}
    else:
        bodyDigest = base64.b64encode(SHA256.new(messageBodyJson.encode()).digest())
        headers = {'host': domain, 'digest': f'SHA-256={bodyDigest}'}        
    privateKeyPem = RSA.import_key(privateKeyPem)
    headers.update({
        '(request-target)': f'post {path}',
    })
    # build a digest for signing
    signedHeaderKeys = headers.keys()
    signedHeaderText = ''
    for headerKey in signedHeaderKeys:
        signedHeaderText += f'{headerKey}: {headers[headerKey]}\n'
    signedHeaderText = signedHeaderText.strip()
    headerDigest = SHA256.new(signedHeaderText.encode('ascii'))

    # Sign the digest
    rawSignature = pkcs1_15.new(privateKeyPem).sign(headerDigest)
    signature = base64.b64encode(rawSignature).decode('ascii')

    # Put it into a valid HTTP signature format
    signatureDict = {
        'keyId': keyID,
        'algorithm': 'rsa-sha256',
        'headers': ' '.join(signedHeaderKeys),
        'signature': signature
    }
    signatureHeader = ','.join(
        [f'{k}="{v}"' for k, v in signatureDict.items()])
    return signatureHeader

def verifyPostHeaders(https: bool, publicKeyPem: str, headers: dict, path: str, GETmethod: bool, messageBodyJson: str) -> bool:
    """Returns true or false depending on if the key that we plugged in here
    validates against the headers, method, and path.
    publicKeyPem - the public key from an rsa key pair
    headers - should be a dictionary of request headers
    path - the relative url that was requested from this site
    GETmethod - GET or POST
    messageBodyJson - the received request body (used for digest)
    """
    if GETmethod:
        method='GET'
    else:
        method='POST'
        
    prefix='https'
    if not https:
        prefix='http'

    publicKeyPem = RSA.import_key(publicKeyPem)
    # Build a dictionary of the signature values
    signatureHeader = headers['signature']
    signatureDict = {
        k: v[1:-1]
        for k, v in [i.split('=', 1) for i in signatureHeader.split(',')]
    }

    # Unpack the signed headers and set values based on current headers and
    # body (if a digest was included)
    signedHeaderList = []
    for signedHeader in signatureDict['headers'].split(' '):
        if signedHeader == '(request-target)':
            signedHeaderList.append(
                f'(request-target): {method.lower()} {path}')
        elif signedHeader == 'digest':
            bodyDigest = base64.b64encode(SHA256.new(messageBodyJson.encode()).digest())
            signedHeaderList.append(f'digest: SHA-256={bodyDigest}')
        else:
            signedHeaderList.append(
                f'{signedHeader}: {headers[signedHeader]}')

    # Now we have our header data digest
    signedHeaderText = '\n'.join(signedHeaderList)
    headerDigest = SHA256.new(signedHeaderText.encode('ascii'))

    # Get the signature, verify with public key, return result
    signature = base64.b64decode(signatureDict['signature'])

    try:
        pkcs1_15.new(publicKeyPem).verify(headerDigest, signature)
        return True
    except (ValueError, TypeError):
        return False

def testHttpsigBase(withDigest):
    print('testHttpsig(' + str(withDigest) + ')')
    username='socrates'
    domain='argumentative.social'
    https=True
    privateKeyPem,publicKeyPem,person,wfEndpoint=createPerson(username,domain,https,False)
    messageBodyJson = '{"a key": "a value", "another key": "A string"}'
    if not withDigest:
        headers = {'host': domain}
    else:
        bodyDigest = base64.b64encode(SHA256.new(messageBodyJson.encode()).digest())
        headers = {'host': domain, 'digest': f'SHA-256={bodyDigest}'}        
    path='/inbox'
    signatureHeader = signPostHeaders(privateKeyPem, username, domain, path, https, None)
    headers['signature'] = signatureHeader
    assert verifyPostHeaders(https, publicKeyPem, headers, '/inbox' ,False, messageBodyJson)
    assert verifyPostHeaders(https, publicKeyPem, headers, '/parambulator/inbox', False , messageBodyJson) == False
    assert verifyPostHeaders(https, publicKeyPem, headers, '/inbox', True, messageBodyJson) == False
    if not withDigest:
        # fake domain
        headers = {'host': 'bogon.domain'}
    else:
        # correct domain but fake message
        messageBodyJson = '{"a key": "a value", "another key": "Fake GNUs"}'
        bodyDigest = base64.b64encode(SHA256.new(messageBodyJson.encode()).digest())
        headers = {'host': domain, 'digest': f'SHA-256={bodyDigest}'}        
    headers['signature'] = signatureHeader
    assert verifyPostHeaders(https, publicKeyPem, headers, '/inbox', True, messageBodyJson) == False

def testHttpsig():
    testHttpsigBase(False)
    testHttpsigBase(True)
