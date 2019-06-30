__filename__ = "tests.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "0.0.1"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import base64
import time
from person import createPerson
from Crypto.Hash import SHA256
from httpsig import signPostHeaders
from httpsig import verifyPostHeaders
from cache import storePersonInCache
from cache import getPersonFromCache
from threads import threadWithTrace

def testHttpsigBase(withDigest):
    print('testHttpsig(' + str(withDigest) + ')')
    username='socrates'
    domain='argumentative.social'
    https=True
    port=80
    privateKeyPem,publicKeyPem,person,wfEndpoint=createPerson(username,domain,port,https,False)
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

def testCache():
    print('testCache')
    personUrl="cat@cardboard.box"
    personJson={ "id": 123456, "test": "This is a test" }
    storePersonInCache(personUrl,personJson)
    result=getPersonFromCache(personUrl)
    assert result['id']==123456
    assert result['test']=='This is a test'

def testThreadsFunction(param: str):
    for i in range(10000):
        time.sleep(2)

def testThreads():
    print('testThreads')
    thr = threadWithTrace(target=testThreadsFunction,args=('test',),daemon=True)
    thr.start()
    assert thr.isAlive()==True
    time.sleep(1)
    thr.kill()
    thr.join()
    assert thr.isAlive()==False
