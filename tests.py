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
from posts import sendPost
from follow import followPerson
from follow import followerOfPerson

testServerAliceRunning = False
testServerBobRunning = False

def testHttpsigBase(withDigest):
    print('testHttpsig(' + str(withDigest) + ')')
    username='socrates'
    domain='argumentative.social'
    https=True
    port=5576
    baseDir=os.getcwd()
    privateKeyPem,publicKeyPem,person,wfEndpoint=createPerson(baseDir,username,domain,port,https,False)
    messageBodyJsonStr = '{"a key": "a value", "another key": "A string"}'

    headersDomain=domain
    if port!=80 and port !=443:
        headersDomain=domain+':'+str(port)

    if not withDigest:
        headers = {'host': headersDomain}
    else:
        bodyDigest = base64.b64encode(SHA256.new(messageBodyJsonStr.encode()).digest())
        headers = {'host': headersDomain, 'digest': f'SHA-256={bodyDigest}'}

    path='/inbox'
    signatureHeader = signPostHeaders(privateKeyPem, username, domain, port, path, https, None)
    headers['signature'] = signatureHeader
    assert verifyPostHeaders(https, publicKeyPem, headers, '/inbox' ,False, messageBodyJsonStr)
    assert verifyPostHeaders(https, publicKeyPem, headers, '/parambulator/inbox', False , messageBodyJsonStr) == False
    assert verifyPostHeaders(https, publicKeyPem, headers, '/inbox', True, messageBodyJsonStr) == False
    if not withDigest:
        # fake domain
        headers = {'host': 'bogon.domain'}
    else:
        # correct domain but fake message
        messageBodyJsonStr = '{"a key": "a value", "another key": "Fake GNUs"}'
        bodyDigest = base64.b64encode(SHA256.new(messageBodyJsonStr.encode()).digest())
        headers = {'host': domain, 'digest': f'SHA-256={bodyDigest}'}        
    headers['signature'] = signatureHeader
    assert verifyPostHeaders(https, publicKeyPem, headers, '/inbox', True, messageBodyJsonStr) == False

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
    privateKeyPem,publicKeyPem,person,wfEndpoint=createPerson(path,username,domain,port,https,True)
    deleteAllPosts(username,domain,path)
    followPerson(path,username,domain,'bob','127.0.0.1:61936',federationList)
    followerOfPerson(path,username,domain,'bob','127.0.0.1:61936',federationList)
    createPublicPost(username, domain, https, "No wise fish would go anywhere without a porpoise", False, True)
    createPublicPost(username, domain, https, "Curiouser and curiouser!", False, True)
    createPublicPost(username, domain, https, "In the gardens of memory, in the palace of dreams, that is where you and I shall meet", False, True)
    global testServerAliceRunning
    testServerAliceRunning = True
    print('Server running: Alice')
    runDaemon(domain,port,https,federationList,useTor)

def createServerBob(path: str,port: int):
    print('Creating test server: Bob on port '+str(port))
    if os.path.isdir(path):
        shutil.rmtree(path)
    os.mkdir(path)
    os.chdir(path)
    federationList=['127.0.0.1']
    username='bob'
    domain='127.0.0.1'
    https=False
    useTor=False
    privateKeyPem,publicKeyPem,person,wfEndpoint=createPerson(path,username,domain,port,https,True)
    deleteAllPosts(username,domain,path)
    followPerson(path,username,domain,'alice','127.0.0.1:61935',federationList)
    followerOfPerson(path,username,domain,'alice','127.0.0.1:61935',federationList)
    createPublicPost(username, domain, https, "It's your life, live it your way.", False, True)
    createPublicPost(username, domain, https, "One of the things I've realised is that I am very simple", False, True)
    createPublicPost(username, domain, https, "Quantum physics is a bit of a passion of mine", False, True)
    global testServerBobRunning
    testServerBobRunning = True
    print('Server running: Bob')
    runDaemon(domain,port,https,federationList,useTor)

def testPostMessageBetweenServers():
    print('Testing sending message from one server to the inbox of another')

    global testServerAliceRunning
    global testServerBobRunning
    testServerAliceRunning = False
    testServerBobRunning = False

    https=False
    useTor=False
    federationList=['127.0.0.1']

    baseDir=os.getcwd()
    if not os.path.isdir(baseDir+'/.tests'):
        os.mkdir(baseDir+'/.tests')

    # create the servers
    aliceDir=baseDir+'/.tests/alice'
    alicePort=61935
    thrAlice = threadWithTrace(target=createServerAlice,args=(aliceDir,alicePort),daemon=True)
    thrAlice.start()
    assert thrAlice.isAlive()==True

    bobDir=baseDir+'/.tests/bob'
    bobPort=61936
    thrBob = threadWithTrace(target=createServerBob,args=(bobDir,bobPort),daemon=True)
    thrBob.start()
    assert thrBob.isAlive()==True

    # wait for both servers to be running
    while not (testServerAliceRunning and testServerBobRunning):
        time.sleep(1)
        
    time.sleep(3)

    print('Alice sends to Bob')
    os.chdir(aliceDir)
    sessionAlice = createSession(useTor)
    inReplyTo=None
    inReplyToAtomUri=None
    subject=None
    aliceSendThreads = []
    alicePostLog = []
    sendResult = sendPost(sessionAlice,aliceDir,'alice', '127.0.0.1', alicePort, 'bob', '127.0.0.1', bobPort, '', https, 'Why is a mouse when it spins?', False, True, federationList, aliceSendThreads, alicePostLog, inReplyTo, inReplyToAtomUri, subject)
    print('sendResult: '+str(sendResult))

    time.sleep(5)
    
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

        
