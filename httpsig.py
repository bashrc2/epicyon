__filename__ = "httpsig.py"
__author__ = "Bob Mottram"
__credits__ = ['lamia']
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Security"

# see https://tools.ietf.org/html/draft-cavage-http-signatures-06
#
# This might change in future
# see https://tools.ietf.org/html/draft-ietf-httpbis-message-signatures

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import utils as hazutils
import base64
from time import gmtime, strftime
import datetime
from utils import get_full_domain
from utils import get_sha_256
from utils import get_sha_512
from utils import local_actor_url


def message_content_digest(messageBodyJsonStr: str,
                           digestAlgorithm: str) -> str:
    """Returns the digest for the message body
    """
    msg = messageBodyJsonStr.encode('utf-8')
    if digestAlgorithm == 'rsa-sha512' or \
       digestAlgorithm == 'rsa-pss-sha512':
        hashResult = get_sha_512(msg)
    else:
        hashResult = get_sha_256(msg)
    return base64.b64encode(hashResult).decode('utf-8')


def get_digest_prefix(digestAlgorithm: str) -> str:
    """Returns the prefix for the message body digest
    """
    if digestAlgorithm == 'rsa-sha512' or \
       digestAlgorithm == 'rsa-pss-sha512':
        return 'SHA-512'
    return 'SHA-256'


def get_digest_algorithm_from_headers(httpHeaders: {}) -> str:
    """Returns the digest algorithm from http headers
    """
    digestStr = None
    if httpHeaders.get('digest'):
        digestStr = httpHeaders['digest']
    elif httpHeaders.get('Digest'):
        digestStr = httpHeaders['Digest']
    if digestStr:
        if digestStr.startswith('SHA-512'):
            return 'rsa-sha512'
    return 'rsa-sha256'


def sign_post_headers(dateStr: str, privateKeyPem: str,
                      nickname: str,
                      domain: str, port: int,
                      toDomain: str, toPort: int,
                      path: str,
                      http_prefix: str,
                      messageBodyJsonStr: str,
                      content_type: str,
                      algorithm: str,
                      digestAlgorithm: str) -> str:
    """Returns a raw signature string that can be plugged into a header and
    used to verify the authenticity of an HTTP transmission.
    """
    domain = get_full_domain(domain, port)

    toDomain = get_full_domain(toDomain, toPort)

    if not dateStr:
        dateStr = strftime("%a, %d %b %Y %H:%M:%S %Z", gmtime())
    if nickname != domain and nickname.lower() != 'actor':
        keyID = local_actor_url(http_prefix, nickname, domain)
    else:
        # instance actor
        keyID = http_prefix + '://' + domain + '/actor'
    keyID += '#main-key'
    if not messageBodyJsonStr:
        headers = {
            '(request-target)': f'get {path}',
            'host': toDomain,
            'date': dateStr,
            'accept': content_type
        }
    else:
        bodyDigest = \
            message_content_digest(messageBodyJsonStr, digestAlgorithm)
        digestPrefix = get_digest_prefix(digestAlgorithm)
        contentLength = len(messageBodyJsonStr)
        headers = {
            '(request-target)': f'post {path}',
            'host': toDomain,
            'date': dateStr,
            'digest': f'{digestPrefix}={bodyDigest}',
            'content-type': 'application/activity+json',
            'content-length': str(contentLength)
        }
    key = load_pem_private_key(privateKeyPem.encode('utf-8'),
                               None, backend=default_backend())
    # headers.update({
    #     '(request-target)': f'post {path}',
    # })
    # build a digest for signing
    signedHeaderKeys = headers.keys()
    signedHeaderText = ''
    for headerKey in signedHeaderKeys:
        signedHeaderText += f'{headerKey}: {headers[headerKey]}\n'
    # strip the trailing linefeed
    signedHeaderText = signedHeaderText.rstrip('\n')
    # signedHeaderText.encode('ascii') matches
    headerDigest = get_sha_256(signedHeaderText.encode('ascii'))
    # print('headerDigest2: ' + str(headerDigest))

    # Sign the digest
    rawSignature = key.sign(headerDigest,
                            padding.PKCS1v15(),
                            hazutils.Prehashed(hashes.SHA256()))
    signature = base64.b64encode(rawSignature).decode('ascii')

    # Put it into a valid HTTP signature format
    signatureDict = {
        'keyId': keyID,
        'algorithm': algorithm,
        'headers': ' '.join(signedHeaderKeys),
        'signature': signature
    }
    signatureHeader = ','.join(
        [f'{k}="{v}"' for k, v in signatureDict.items()])
    return signatureHeader


def sign_post_headers_new(dateStr: str, privateKeyPem: str,
                          nickname: str,
                          domain: str, port: int,
                          toDomain: str, toPort: int,
                          path: str,
                          http_prefix: str,
                          messageBodyJsonStr: str,
                          algorithm: str, digestAlgorithm: str,
                          debug: bool) -> (str, str):
    """Returns a raw signature strings that can be plugged into a header
    as "Signature-Input" and "Signature"
    used to verify the authenticity of an HTTP transmission.
    See https://tools.ietf.org/html/draft-ietf-httpbis-message-signatures
    """
    domain = get_full_domain(domain, port)

    toDomain = get_full_domain(toDomain, toPort)

    timeFormat = "%a, %d %b %Y %H:%M:%S %Z"
    if not dateStr:
        curr_time = gmtime()
        dateStr = strftime(timeFormat, curr_time)
    else:
        curr_time = datetime.datetime.strptime(dateStr, timeFormat)
    secondsSinceEpoch = \
        int((curr_time - datetime.datetime(1970, 1, 1)).total_seconds())
    keyID = local_actor_url(http_prefix, nickname, domain) + '#main-key'
    if not messageBodyJsonStr:
        headers = {
            '@request-target': f'get {path}',
            '@created': str(secondsSinceEpoch),
            'host': toDomain,
            'date': dateStr
        }
    else:
        bodyDigest = message_content_digest(messageBodyJsonStr,
                                            digestAlgorithm)
        digestPrefix = get_digest_prefix(digestAlgorithm)
        contentLength = len(messageBodyJsonStr)
        headers = {
            '@request-target': f'post {path}',
            '@created': str(secondsSinceEpoch),
            'host': toDomain,
            'date': dateStr,
            'digest': f'{digestPrefix}={bodyDigest}',
            'content-type': 'application/activity+json',
            'content-length': str(contentLength)
        }
    key = load_pem_private_key(privateKeyPem.encode('utf-8'),
                               None, backend=default_backend())
    # build a digest for signing
    signedHeaderKeys = headers.keys()
    signedHeaderText = ''
    for headerKey in signedHeaderKeys:
        signedHeaderText += f'{headerKey}: {headers[headerKey]}\n'
    signedHeaderText = signedHeaderText.strip()

    if debug:
        print('\nsign_post_headers_new signedHeaderText:\n' +
              signedHeaderText + '\nEND\n')

    # Sign the digest. Potentially other signing algorithms can be added here.
    signature = ''
    if algorithm == 'rsa-sha512':
        headerDigest = get_sha_512(signedHeaderText.encode('ascii'))
        rawSignature = key.sign(headerDigest,
                                padding.PKCS1v15(),
                                hazutils.Prehashed(hashes.SHA512()))
        signature = base64.b64encode(rawSignature).decode('ascii')
    else:
        # default rsa-sha256
        headerDigest = get_sha_256(signedHeaderText.encode('ascii'))
        rawSignature = key.sign(headerDigest,
                                padding.PKCS1v15(),
                                hazutils.Prehashed(hashes.SHA256()))
        signature = base64.b64encode(rawSignature).decode('ascii')

    sigKey = 'sig1'
    # Put it into a valid HTTP signature format
    signatureInputDict = {
        'keyId': keyID,
    }
    signatureIndexHeader = '; '.join(
        [f'{k}="{v}"' for k, v in signatureInputDict.items()])
    signatureIndexHeader += '; alg=hs2019'
    signatureIndexHeader += '; created=' + str(secondsSinceEpoch)
    signatureIndexHeader += \
        '; ' + sigKey + '=(' + ', '.join(signedHeaderKeys) + ')'
    signatureDict = {
        sigKey: signature
    }
    signatureHeader = '; '.join(
        [f'{k}=:{v}:' for k, v in signatureDict.items()])
    return signatureIndexHeader, signatureHeader


def create_signed_header(dateStr: str, privateKeyPem: str, nickname: str,
                         domain: str, port: int,
                         toDomain: str, toPort: int,
                         path: str, http_prefix: str, withDigest: bool,
                         messageBodyJsonStr: str,
                         content_type: str) -> {}:
    """Note that the domain is the destination, not the sender
    """
    algorithm = 'rsa-sha256'
    digestAlgorithm = 'rsa-sha256'
    headerDomain = get_full_domain(toDomain, toPort)

    # if no date is given then create one
    if not dateStr:
        dateStr = strftime("%a, %d %b %Y %H:%M:%S %Z", gmtime())

    # Content-Type or Accept header
    if not content_type:
        content_type = 'application/activity+json'

    if not withDigest:
        headers = {
            '(request-target)': f'get {path}',
            'host': headerDomain,
            'date': dateStr,
            'accept': content_type
        }
        signatureHeader = \
            sign_post_headers(dateStr, privateKeyPem, nickname,
                              domain, port, toDomain, toPort,
                              path, http_prefix, None, content_type,
                              algorithm, None)
    else:
        bodyDigest = message_content_digest(messageBodyJsonStr,
                                            digestAlgorithm)
        digestPrefix = get_digest_prefix(digestAlgorithm)
        contentLength = len(messageBodyJsonStr)
        headers = {
            '(request-target)': f'post {path}',
            'host': headerDomain,
            'date': dateStr,
            'digest': f'{digestPrefix}={bodyDigest}',
            'content-length': str(contentLength),
            'content-type': content_type
        }
        signatureHeader = \
            sign_post_headers(dateStr, privateKeyPem, nickname,
                              domain, port,
                              toDomain, toPort,
                              path, http_prefix, messageBodyJsonStr,
                              content_type, algorithm, digestAlgorithm)
    headers['signature'] = signatureHeader
    return headers


def _verify_recent_signature(signedDateStr: str) -> bool:
    """Checks whether the given time taken from the header is within
    12 hours of the current time
    """
    currDate = datetime.datetime.utcnow()
    dateFormat = "%a, %d %b %Y %H:%M:%S %Z"
    signedDate = datetime.datetime.strptime(signedDateStr, dateFormat)
    time_diffSec = (currDate - signedDate).seconds
    # 12 hours tollerance
    if time_diffSec > 43200:
        print('WARN: Header signed too long ago: ' + signedDateStr)
        print(str(time_diffSec / (60 * 60)) + ' hours')
        return False
    if time_diffSec < 0:
        print('WARN: Header signed in the future! ' + signedDateStr)
        print(str(time_diffSec / (60 * 60)) + ' hours')
        return False
    return True


def verify_post_headers(http_prefix: str,
                        publicKeyPem: str, headers: dict,
                        path: str, GETmethod: bool,
                        messageBodyDigest: str,
                        messageBodyJsonStr: str, debug: bool,
                        noRecencyCheck: bool = False) -> bool:
    """Returns true or false depending on if the key that we plugged in here
    validates against the headers, method, and path.
    publicKeyPem - the public key from an rsa key pair
    headers - should be a dictionary of request headers
    path - the relative url that was requested from this site
    GETmethod - GET or POST
    messageBodyJsonStr - the received request body (used for digest)
    """

    if GETmethod:
        method = 'GET'
    else:
        method = 'POST'

    if debug:
        print('DEBUG: verify_post_headers ' + method)
        print('verify_post_headers publicKeyPem: ' + str(publicKeyPem))
        print('verify_post_headers headers: ' + str(headers))
        print('verify_post_headers messageBodyJsonStr: ' +
              str(messageBodyJsonStr))

    pubkey = load_pem_public_key(publicKeyPem.encode('utf-8'),
                                 backend=default_backend())
    # Build a dictionary of the signature values
    if headers.get('Signature-Input') or headers.get('signature-input'):
        if headers.get('Signature-Input'):
            signatureHeader = headers['Signature-Input']
        else:
            signatureHeader = headers['signature-input']
        fieldSep2 = ','
        # split the signature input into separate fields
        signatureDict = {
            k.strip(): v.strip()
            for k, v in [i.split('=', 1) for i in signatureHeader.split(';')]
        }
        requestTargetKey = None
        requestTargetStr = None
        for k, v in signatureDict.items():
            if v.startswith('('):
                requestTargetKey = k
                requestTargetStr = v[1:-1]
            elif v.startswith('"'):
                signatureDict[k] = v[1:-1]
        if not requestTargetKey:
            return False
        signatureDict[requestTargetKey] = requestTargetStr
    else:
        requestTargetKey = 'headers'
        signatureHeader = headers['signature']
        fieldSep2 = ' '
        # split the signature input into separate fields
        signatureDict = {
            k: v[1:-1]
            for k, v in [i.split('=', 1) for i in signatureHeader.split(',')]
        }

    if debug:
        print('signatureDict: ' + str(signatureDict))

    # Unpack the signed headers and set values based on current headers and
    # body (if a digest was included)
    signedHeaderList = []
    algorithm = 'rsa-sha256'
    digestAlgorithm = 'rsa-sha256'
    for signedHeader in signatureDict[requestTargetKey].split(fieldSep2):
        signedHeader = signedHeader.strip()
        if debug:
            print('DEBUG: verify_post_headers signedHeader=' + signedHeader)
        if signedHeader == '(request-target)':
            # original Mastodon http signature
            appendStr = f'(request-target): {method.lower()} {path}'
            signedHeaderList.append(appendStr)
        elif '@request-target' in signedHeader:
            # https://tools.ietf.org/html/
            # draft-ietf-httpbis-message-signatures
            appendStr = f'@request-target: {method.lower()} {path}'
            signedHeaderList.append(appendStr)
        elif '@created' in signedHeader:
            if signatureDict.get('created'):
                createdStr = str(signatureDict['created'])
                appendStr = f'@created: {createdStr}'
                signedHeaderList.append(appendStr)
        elif '@expires' in signedHeader:
            if signatureDict.get('expires'):
                expiresStr = str(signatureDict['expires'])
                appendStr = f'@expires: {expiresStr}'
                signedHeaderList.append(appendStr)
        elif '@method' in signedHeader:
            appendStr = f'@expires: {method}'
            signedHeaderList.append(appendStr)
        elif '@scheme' in signedHeader:
            signedHeaderList.append('@scheme: http')
        elif '@authority' in signedHeader:
            authorityStr = None
            if signatureDict.get('authority'):
                authorityStr = str(signatureDict['authority'])
            elif signatureDict.get('Authority'):
                authorityStr = str(signatureDict['Authority'])
            if authorityStr:
                appendStr = f'@authority: {authorityStr}'
                signedHeaderList.append(appendStr)
        elif signedHeader == 'algorithm':
            if headers.get(signedHeader):
                algorithm = headers[signedHeader]
                if debug:
                    print('http signature algorithm: ' + algorithm)
        elif signedHeader == 'digest':
            if messageBodyDigest:
                bodyDigest = messageBodyDigest
            else:
                bodyDigest = \
                    message_content_digest(messageBodyJsonStr, digestAlgorithm)
            signedHeaderList.append(f'digest: SHA-256={bodyDigest}')
        elif signedHeader == 'content-length':
            if headers.get(signedHeader):
                appendStr = f'content-length: {headers[signedHeader]}'
                signedHeaderList.append(appendStr)
            elif headers.get('Content-Length'):
                contentLength = headers['Content-Length']
                signedHeaderList.append(f'content-length: {contentLength}')
            elif headers.get('Content-length'):
                contentLength = headers['Content-length']
                appendStr = f'content-length: {contentLength}'
                signedHeaderList.append(appendStr)
            else:
                if debug:
                    print('DEBUG: verify_post_headers ' + signedHeader +
                          ' not found in ' + str(headers))
        else:
            if headers.get(signedHeader):
                if signedHeader == 'date' and not noRecencyCheck:
                    if not _verify_recent_signature(headers[signedHeader]):
                        if debug:
                            print('DEBUG: ' +
                                  'verify_post_headers date is not recent ' +
                                  headers[signedHeader])
                        return False
                signedHeaderList.append(
                    f'{signedHeader}: {headers[signedHeader]}')
            else:
                if '-' in signedHeader:
                    # capitalise with dashes
                    # my-header becomes My-Header
                    headerParts = signedHeader.split('-')
                    signedHeaderCap = None
                    for part in headerParts:
                        if signedHeaderCap:
                            signedHeaderCap += '-' + part.capitalize()
                        else:
                            signedHeaderCap = part.capitalize()
                else:
                    # header becomes Header
                    signedHeaderCap = signedHeader.capitalize()

                if debug:
                    print('signedHeaderCap: ' + signedHeaderCap)

                # if this is the date header then check it is recent
                if signedHeaderCap == 'Date':
                    if not _verify_recent_signature(headers[signedHeaderCap]):
                        if debug:
                            print('DEBUG: ' +
                                  'verify_post_headers date is not recent ' +
                                  headers[signedHeader])
                        return False

                # add the capitalised header
                if headers.get(signedHeaderCap):
                    signedHeaderList.append(
                        f'{signedHeader}: {headers[signedHeaderCap]}')
                elif '-' in signedHeader:
                    # my-header becomes My-header
                    signedHeaderCap = signedHeader.capitalize()
                    if headers.get(signedHeaderCap):
                        signedHeaderList.append(
                            f'{signedHeader}: {headers[signedHeaderCap]}')

    # Now we have our header data digest
    signedHeaderText = '\n'.join(signedHeaderList)
    if debug:
        print('\nverify_post_headers signedHeaderText:\n' +
              signedHeaderText + '\nEND\n')

    # Get the signature, verify with public key, return result
    if (headers.get('Signature-Input') and headers.get('Signature')) or \
       (headers.get('signature-input') and headers.get('signature')):
        # https://tools.ietf.org/html/
        # draft-ietf-httpbis-message-signatures
        if headers.get('Signature'):
            headersSig = headers['Signature']
        else:
            headersSig = headers['signature']
        # remove sig1=:
        if requestTargetKey + '=:' in headersSig:
            headersSig = headersSig.split(requestTargetKey + '=:')[1]
            headersSig = headersSig[:len(headersSig)-1]
        signature = base64.b64decode(headersSig)
    else:
        # Original Mastodon signature
        headersSig = signatureDict['signature']
        signature = base64.b64decode(headersSig)
    if debug:
        print('signature: ' + algorithm + ' ' + headersSig)

    # log unusual signing algorithms
    if signatureDict.get('alg'):
        print('http signature algorithm: ' + signatureDict['alg'])

    # If extra signing algorithms need to be added then do it here
    if not signatureDict.get('alg'):
        alg = hazutils.Prehashed(hashes.SHA256())
    elif (signatureDict['alg'] == 'rsa-sha256' or
          signatureDict['alg'] == 'rsa-v1_5-sha256' or
          signatureDict['alg'] == 'hs2019'):
        alg = hazutils.Prehashed(hashes.SHA256())
    elif (signatureDict['alg'] == 'rsa-sha512' or
          signatureDict['alg'] == 'rsa-pss-sha512'):
        alg = hazutils.Prehashed(hashes.SHA512())
    else:
        alg = hazutils.Prehashed(hashes.SHA256())

    if digestAlgorithm == 'rsa-sha256':
        headerDigest = get_sha_256(signedHeaderText.encode('ascii'))
    elif digestAlgorithm == 'rsa-sha512':
        headerDigest = get_sha_512(signedHeaderText.encode('ascii'))
    else:
        print('Unknown http digest algorithm: ' + digestAlgorithm)
        headerDigest = ''
    paddingStr = padding.PKCS1v15()

    try:
        pubkey.verify(signature, headerDigest, paddingStr, alg)
        return True
    except BaseException:
        if debug:
            print('EX: verify_post_headers pkcs1_15 verify failure')
    return False
