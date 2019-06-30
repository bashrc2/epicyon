__filename__ = "tests.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "0.0.1"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import base64
import time
import os
import shutil
from person import createPerson
from Crypto.Hash import SHA256
from httpsig import signPostHeaders
from httpsig import verifyPostHeaders
from cache import storePersonInCache
from cache import getPersonFromCache
from threads import threadWithTrace
from daemon import runDaemon
from session import createSession
from person import createPerson
from posts import deleteAllPosts
from posts import createPublicPost
from follow import followPerson
from follow import followerOfPerson

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

def createServerAlice(path: str,port: int):
    print('Creating test server: Alice on port '+str(port))
    if os.path.isdir(path):
        shutil.rmtree(path)
    os.mkdir(path)
    os.chdir(path)
    federationList=['127.0.0.1']
    username='alice'
    domain='127.0.0.1'
    https=False
    useTor=False
    session = createSession(useTor)
    privateKeyPem,publicKeyPem,person,wfEndpoint=createPerson(username,domain,port,https,True)
    deleteAllPosts(username,domain)
    followPerson(username,domain,'bob','127.0.0.1:61936',federationList)
    followerOfPerson(username,domain,'bob','127.0.0.1:61936',federationList)
    createPublicPost(username, domain, https, "No wise fish would go anywhere without a porpoise", False, True)
    createPublicPost(username, domain, https, "Curiouser and curiouser!", False, True)
    createPublicPost(username, domain, https, "In the gardens of memory, in the palace of dreams, that is where you and I shall meet", False, True)
    print('Server running: Alice')
    runDaemon(domain,port,https,federationList,useTor)

def createServerBob(path: str,port: int):
    print('Creating test server: Bob on port '+str(port))
    if os.path.isdir(path):
        shutil.rmtree(path)
    os.mkdir(path)
    os.chdir(path)
    federationList=['127.0.0.1']
    username='alice'
    domain='127.0.0.1'
    https=False
    useTor=False
    session = createSession(useTor)
    privateKeyPem,publicKeyPem,person,wfEndpoint=createPerson(username,domain,port,https,True)
    deleteAllPosts(username,domain)
    followPerson(username,domain,'alice','127.0.0.1:61935',federationList)
    followerOfPerson(username,domain,'alice','127.0.0.1:61935',federationList)
    createPublicPost(username, domain, https, "It's your life, live it your way.", False, True)
    createPublicPost(username, domain, https, "One of the things I've realised is that I am very simple", False, True)
    createPublicPost(username, domain, https, "Quantum physics is a bit of a passion of mine", False, True)
    print('Server running: Bob')
    runDaemon(domain,port,https,federationList,useTor)

def testPostMessageBetweenServers():
    print('Testing sending message from one server to the inbox of another')
    baseDir=os.getcwd()
    if not os.path.isdir(baseDir+'/.tests'):
        os.mkdir(baseDir+'/.tests')

    # create the servers
    thrAlice = threadWithTrace(target=createServerAlice,args=(baseDir+'/.tests/alice',61935),daemon=True)
    thrAlice.start()
    assert thrAlice.isAlive()==True

    thrBob = threadWithTrace(target=createServerBob,args=(baseDir+'/.tests/bob',61936),daemon=True)
    thrBob.start()
    assert thrBob.isAlive()==True

    time.sleep(10)

    # stop the servers
    thrAlice.kill()
    thrAlice.join()
    assert thrAlice.isAlive()==False

    thrBob.kill()
    thrBob.join()
    assert thrBob.isAlive()==False

def runAllTests():
    print('Running tests...')
    testHttpsig()
    testCache()
    testThreads()
    print('Tests succeeded\n')

        
