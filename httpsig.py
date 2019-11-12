__filename__ = "posts.py"
__author__ = "Bob Mottram"
__credits__ = ['lamia']
__license__ = "AGPL3+"
__version__ = "1.0.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

# see https://tools.ietf.org/html/draft-cavage-http-signatures-06

from Crypto.PublicKey import RSA
from Crypto.Hash import SHA256
#from Crypto.Signature import PKCS1_v1_5
from Crypto.Signature import pkcs1_15
from requests.auth import AuthBase
import base64
import json
from time import gmtime, strftime
import datetime
from pprint import pprint

def messageContentDigest(messageBodyJsonStr: str) -> str:
    return base64.b64encode(SHA256.new(messageBodyJsonStr.encode('utf-8')).digest()).decode('utf-8')

def signPostHeaders(dateStr: str,privateKeyPem: str, \
                    nickname: str, \
                    domain: str,port: int, \
                    toDomain: str,toPort: int, \
                    path: str, \
                    httpPrefix: str, \
                    messageBodyJsonStr: str) -> str:
    """Returns a raw signature string that can be plugged into a header and
    used to verify the authenticity of an HTTP transmission.
    """
    if port:
        if port!=80 and port!=443:
            if ':' not in domain:
                domain=domain+':'+str(port)

    if toPort:
        if toPort!=80 and toPort!=443:
            if ':' not in toDomain:
                toDomain=toDomain+':'+str(port)

    if not dateStr:
        dateStr=strftime("%a, %d %b %Y %H:%M:%S %Z", gmtime())
    keyID=httpPrefix+'://'+domain+'/users/'+nickname+'#main-key'
    if not messageBodyJsonStr:
        headers={'(request-target)': f'post {path}','host': toDomain,'date': dateStr,'content-type': 'application/json'}
    else:
        bodyDigest=messageContentDigest(messageBodyJsonStr)
        contentLength=len(messageBodyJsonStr)
        headers={'(request-target)': f'post {path}','host': toDomain,'date': dateStr,'digest': f'SHA-256={bodyDigest}','content-type': 'application/activity+json','content-length': str(contentLength)}
    privateKeyPem=RSA.import_key(privateKeyPem)
    #headers.update({
    #    '(request-target)': f'post {path}',
    #})
    # build a digest for signing
    signedHeaderKeys = headers.keys()
    signedHeaderText = ''
    for headerKey in signedHeaderKeys:
        signedHeaderText += f'{headerKey}: {headers[headerKey]}\n'
        #print(f'*********************signing:  headerKey: {headerKey}: {headers[headerKey]}')
    signedHeaderText = signedHeaderText.strip()
    #print('******************************Send: signedHeaderText: '+signedHeaderText)
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

def createSignedHeader(privateKeyPem: str,nickname: str, \
                       domain: str,port: int, \
                       toDomain: str,toPort: int, \
                       path: str,httpPrefix: str,withDigest: bool, \
                       messageBodyJsonStr: str) -> {}:
    """Note that the domain is the destination, not the sender
    """
    contentType='application/activity+json'
    headerDomain=toDomain

    if toPort:
        if toPort!=80 and toPort!=443:
            if ':' not in headerDomain:
                headerDomain=headerDomain+':'+str(toPort)

    dateStr=strftime("%a, %d %b %Y %H:%M:%S %Z", gmtime())
    if not withDigest:
        headers = {'(request-target)': f'post {path}','host': headerDomain,'date': dateStr}
        signatureHeader = \
            signPostHeaders(dateStr,privateKeyPem,nickname, \
                            domain,port,toDomain,toPort, \
                            path,httpPrefix,None)
    else:
        bodyDigest=messageContentDigest(messageBodyJsonStr)
        contentLength=len(messageBodyJsonStr)
        #print('***************************Send (request-target): post '+path)
        #print('***************************Send host: '+headerDomain)
        #print('***************************Send date: '+dateStr)
        #print('***************************Send digest: '+bodyDigest)
        #print('***************************Send Content-type: '+contentType)
        #print('***************************Send Content-Length: '+str(len(messageBodyJsonStr)))
        #print('***************************Send messageBodyJsonStr: '+messageBodyJsonStr)
        headers = {'(request-target)': f'post {path}','host': headerDomain,'date': dateStr,'digest': f'SHA-256={bodyDigest}','content-length': str(contentLength),'content-type': contentType}
        signatureHeader = \
            signPostHeaders(dateStr,privateKeyPem,nickname, \
                            domain,port, \
                            toDomain,toPort, \
                            path,httpPrefix,messageBodyJsonStr)
    headers['signature'] = signatureHeader
    return headers

def verifyRecentSignature(signedDateStr: str) -> bool:
    """Checks whether the given time taken from the header is within
    12 hours of the current time
    """
    currDate=datetime.datetime.utcnow()
    signedDate=datetime.datetime.strptime(signedDateStr,"%a, %d %b %Y %H:%M:%S %Z")
    timeDiffSec=(currDate-signedDate).seconds
    # 12 hours tollerance
    if timeDiffSec > 43200:
        print('WARN: Header signed too long ago: '+signedDateStr)
        print(str(timeDiffSec/(60*60))+' hours')
        return False
    if timeDiffSec < 0:
        print('WARN: Header signed in the future! '+signedDateStr)
        print(str(timeDiffSec/(60*60))+' hours')
        return False
    return True

def verifyPostHeaders(httpPrefix: str,publicKeyPem: str,headers: dict, \
                      path: str,GETmethod: bool, \
                      messageBodyDigest: str, \
                      messageBodyJsonStr: str,debug: bool) -> bool:
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

    if debug:
        print('DEBUG: verifyPostHeaders '+method)
        
    publicKeyPem = RSA.import_key(publicKeyPem)
    # Build a dictionary of the signature values
    signatureHeader = headers['signature']
    signatureDict = {
        k: v[1:-1]
        for k, v in [i.split('=', 1) for i in signatureHeader.split(',')]
    }
    #print('********************signatureHeader: '+str(signatureHeader))
    #print('********************signatureDict: '+str(signatureDict))

    # Unpack the signed headers and set values based on current headers and
    # body (if a digest was included)
    signedHeaderList = []
    for signedHeader in signatureDict['headers'].split(' '):
        if debug:
            print('DEBUG: verifyPostHeaders signedHeader='+signedHeader)
        if signedHeader == '(request-target)':
            signedHeaderList.append(
                f'(request-target): {method.lower()} {path}')
            #print('***************************Verify (request-target): '+method.lower()+' '+path)
        elif signedHeader == 'digest':
            if messageBodyDigest:
                bodyDigest=messageBodyDigest
            else:
                bodyDigest=messageContentDigest(messageBodyJsonStr)
            signedHeaderList.append(f'digest: SHA-256={bodyDigest}')
            #print('***************************Verify digest: SHA-256='+bodyDigest)
            #print('***************************Verify messageBodyJsonStr: '+messageBodyJsonStr)
        elif signedHeader == 'content-length':
            if headers.get(signedHeader):
                signedHeaderList.append(f'content-length: {headers[signedHeader]}')
            else:
                if debug:
                    print('DEBUG: verifyPostHeaders '+signedHeader+' not found in '+str(headers))
        elif signedHeader == 'Content-Length':
            if headers.get(signedHeader):
                signedHeaderList.append(f'Content-Length: {headers[signedHeader]}')
            else:
                if debug:
                    print('DEBUG: verifyPostHeaders '+signedHeader+' not found in '+str(headers))
        else:
            if headers.get(signedHeader):
                if signedHeader=='date':
                    if not verifyRecentSignature(headers[signedHeader]):
                        if debug:
                            print('DEBUG: verifyPostHeaders date is not recent '+headers[signedHeader])
                        return False
                #print('***************************Verify '+signedHeader+': '+headers[signedHeader])
                signedHeaderList.append(
                    f'{signedHeader}: {headers[signedHeader]}')
            else:
                signedHeaderCap=signedHeader.capitalize()
                if signedHeaderCap=='Date':
                    if not verifyRecentSignature(headers[signedHeaderCap]):
                        if debug:
                            print('DEBUG: verifyPostHeaders date is not recent '+headers[signedHeader])
                        return False
                #print('***************************Verify '+signedHeaderCap+': '+headers[signedHeaderCap])
                if headers.get(signedHeaderCap):
                    signedHeaderList.append(
                        f'{signedHeader}: {headers[signedHeaderCap]}')

    #print('***********************signedHeaderList: ')
    #pprint(signedHeaderList)
    if debug:
        print('DEBUG: signedHeaderList: '+str(signedHeaderList))
    # Now we have our header data digest
    signedHeaderText = '\n'.join(signedHeaderList)
    #print('***********************Verify: signedHeaderText: '+signedHeaderText)
    headerDigest = SHA256.new(signedHeaderText.encode('ascii'))

    # Get the signature, verify with public key, return result
    signature = base64.b64decode(signatureDict['signature'])

    try:
        pkcs1_15.new(publicKeyPem).verify(headerDigest, signature)
        return True
    except (ValueError, TypeError):
        if debug:
            print('DEBUG: verifyPostHeaders pkcs1_15 verify failure')
        return False
