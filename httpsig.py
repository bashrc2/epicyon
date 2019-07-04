__filename__ = "posts.py"
__author__ = "Bob Mottram"
__credits__ = ['lamia']
__license__ = "AGPL3+"
__version__ = "0.0.1"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

from Crypto.PublicKey import RSA
from Crypto.Hash import SHA256
#from Crypto.Signature import PKCS1_v1_5
from Crypto.Signature import pkcs1_15
from requests.auth import AuthBase
import base64
import json

def signPostHeaders(privateKeyPem: str, nickname: str, domain: str, \
                    port: int,path: str, \
                    httpPrefix: str, messageBodyJson: {}) -> str:
    """Returns a raw signature string that can be plugged into a header and
    used to verify the authenticity of an HTTP transmission.
    """
    if port!=80 and port!=443:
        domain=domain+':'+str(port)

    keyID = httpPrefix+'://'+domain+'/users/'+nickname+'#main-key'
    if not messageBodyJson:
        headers = {'host': domain}
    else:
        bodyDigest = \
            base64.b64encode(SHA256.new(messageBodyJson.encode()).digest())
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

def createSignedHeader(privateKeyPem: str,nickname: str,domain: str,port: int, \
                       path: str,httpPrefix: str,withDigest: bool, \
                       messageBodyJson: {}) -> {}:
    headerDomain=domain

    if port!=80 and port!=443:
        headerDomain=headerDomain+':'+str(port)

    if not withDigest:
        headers = {'host': headerDomain}
    else:
        messageBodyJsonStr=json.dumps(messageBodyJson)
        bodyDigest = \
            base64.b64encode(SHA256.new(messageBodyJsonStr.encode()).digest())
        headers = {'host': headerDomain, 'digest': f'SHA-256={bodyDigest}'}        
    path='/inbox'
    signatureHeader = signPostHeaders(privateKeyPem, nickname, domain, port, \
                                      path, httpPrefix, None)
    headers['signature'] = signatureHeader
    headers['Content-type'] = 'application/json'
    return headers

def verifyPostHeaders(httpPrefix: str, publicKeyPem: str, headers: dict, \
                      path: str, GETmethod: bool, \
                      messageBodyJsonStr: str) -> bool:
    """Returns true or false depending on if the key that we plugged in here
    validates against the headers, method, and path.
    publicKeyPem - the public key from an rsa key pair
    headers - should be a dictionary of request headers
    path - the relative url that was requested from this site
    GETmethod - GET or POST
    messageBodyJsonStr - the received request body (used for digest)
    """
    if GETmethod:
        method='GET'
    else:
        method='POST'
        
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
            bodyDigest = \
                base64.b64encode(SHA256.new(messageBodyJsonStr.encode()).digest())
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
