__filename__ = "tests.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "0.0.1"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import base64
import time
import os, os.path
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
from posts import deleteAllPosts
from posts import createPublicPost
from posts import sendPost
from posts import archivePosts
from posts import noOfFollowersOnDomain
from follow import clearFollows
from follow import clearFollowers
from utils import followPerson
from follow import followerOfPerson
from follow import unfollowPerson
from follow import unfollowerOfPerson
from follow import getFollowersOfPerson
from follow import sendFollowRequest
from person import createPerson
from person import setPreferredNickname
from person import setBio
from auth import createBasicAuthHeader
from auth import authorizeBasic
from auth import storeBasicCredentials

testServerAliceRunning = False
testServerBobRunning = False
testServerEveRunning = False

def testHttpsigBase(withDigest):
    print('testHttpsig(' + str(withDigest) + ')')
    nickname='socrates'
    domain='argumentative.social'
    httpPrefix='https'
    port=5576
    baseDir=os.getcwd()
    password='SuperSecretPassword'
    privateKeyPem,publicKeyPem,person,wfEndpoint=createPerson(baseDir,nickname,domain,port,httpPrefix,False,password)
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
    signatureHeader = signPostHeaders(privateKeyPem, nickname, domain, port, path, httpPrefix, None)
    headers['signature'] = signatureHeader
    assert verifyPostHeaders(httpPrefix, publicKeyPem, headers, '/inbox' ,False, messageBodyJsonStr)
    assert verifyPostHeaders(httpPrefix, publicKeyPem, headers, '/parambulator/inbox', False , messageBodyJsonStr) == False
    assert verifyPostHeaders(httpPrefix, publicKeyPem, headers, '/inbox', True, messageBodyJsonStr) == False
    if not withDigest:
        # fake domain
        headers = {'host': 'bogon.domain'}
    else:
        # correct domain but fake message
        messageBodyJsonStr = '{"a key": "a value", "another key": "Fake GNUs"}'
        bodyDigest = base64.b64encode(SHA256.new(messageBodyJsonStr.encode()).digest())
        headers = {'host': domain, 'digest': f'SHA-256={bodyDigest}'}        
    headers['signature'] = signatureHeader
    assert verifyPostHeaders(httpPrefix, publicKeyPem, headers, '/inbox', True, messageBodyJsonStr) == False

def testHttpsig():
    testHttpsigBase(False)
    testHttpsigBase(True)

def testCache():
    print('testCache')
    personUrl="cat@cardboard.box"
    personJson={ "id": 123456, "test": "This is a test" }
    personCache={}
    storePersonInCache(personUrl,personJson,personCache)
    result=getPersonFromCache(personUrl,personCache)
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

def createServerAlice(path: str,domain: str,port: int,federationList: [],ocapGranted: {},hasFollows: bool,hasPosts :bool,ocapAlways: bool):
    print('Creating test server: Alice on port '+str(port))
    if os.path.isdir(path):
        shutil.rmtree(path)
    os.mkdir(path)
    os.chdir(path)
    nickname='alice'
    httpPrefix='http'
    useTor=False
    clientToServer=False
    password='alicepass'
    privateKeyPem,publicKeyPem,person,wfEndpoint=createPerson(path,nickname,domain,port,httpPrefix,True,password)
    deleteAllPosts(path,nickname,domain,'inbox')
    deleteAllPosts(path,nickname,domain,'outbox')
    if hasFollows:
        followPerson(path,nickname,domain,'bob','127.0.0.100:61936',federationList,True)
        followerOfPerson(path,nickname,domain,'bob','127.0.0.100:61936',federationList,True)
    if hasPosts:
        createPublicPost(path,nickname, domain, port,httpPrefix, "No wise fish would go anywhere without a porpoise", False, True, clientToServer,ocapGranted)
        createPublicPost(path,nickname, domain, port,httpPrefix, "Curiouser and curiouser!", False, True, clientToServer,ocapGranted)
        createPublicPost(path,nickname, domain, port,httpPrefix, "In the gardens of memory, in the palace of dreams, that is where you and I shall meet", False, True, clientToServer,ocapGranted)
    global testServerAliceRunning
    testServerAliceRunning = True
    print('Server running: Alice')
    runDaemon(path,domain,port,httpPrefix,federationList,ocapAlways,ocapGranted,useTor,True)

def createServerBob(path: str,domain: str,port: int,federationList: [],ocapGranted: {},hasFollows: bool,hasPosts :bool,ocapAlways :bool):
    print('Creating test server: Bob on port '+str(port))
    if os.path.isdir(path):
        shutil.rmtree(path)
    os.mkdir(path)
    os.chdir(path)
    nickname='bob'
    httpPrefix='http'
    useTor=False
    clientToServer=False
    password='bobpass'
    privateKeyPem,publicKeyPem,person,wfEndpoint=createPerson(path,nickname,domain,port,httpPrefix,True,password)
    deleteAllPosts(path,nickname,domain,'inbox')
    deleteAllPosts(path,nickname,domain,'outbox')
    if hasFollows:
        followPerson(path,nickname,domain,'alice','127.0.0.50:61935',federationList,True)
        followerOfPerson(path,nickname,domain,'alice','127.0.0.50:61935',federationList,True)
    if hasPosts:
        createPublicPost(path,nickname, domain, port,httpPrefix, "It's your life, live it your way.", False, True, clientToServer,ocapGranted)
        createPublicPost(path,nickname, domain, port,httpPrefix, "One of the things I've realised is that I am very simple", False, True, clientToServer,ocapGranted)
        createPublicPost(path,nickname, domain, port,httpPrefix, "Quantum physics is a bit of a passion of mine", False, True, clientToServer,ocapGranted)
    global testServerBobRunning
    testServerBobRunning = True
    print('Server running: Bob')
    runDaemon(path,domain,port,httpPrefix,federationList,ocapAlways,ocapGranted,useTor,True)

def createServerEve(path: str,domain: str,port: int,federationList: [],ocapGranted: {},hasFollows: bool,hasPosts :bool,ocapAlways :bool):
    print('Creating test server: Eve on port '+str(port))
    if os.path.isdir(path):
        shutil.rmtree(path)
    os.mkdir(path)
    os.chdir(path)
    nickname='eve'
    httpPrefix='http'
    useTor=False
    clientToServer=False
    password='evepass'
    privateKeyPem,publicKeyPem,person,wfEndpoint=createPerson(path,nickname,domain,port,httpPrefix,True,password)
    deleteAllPosts(path,nickname,domain,'inbox')
    deleteAllPosts(path,nickname,domain,'outbox')
    global testServerEveRunning
    testServerEveRunning = True
    print('Server running: Eve')
    runDaemon(path,domain,port,httpPrefix,federationList,ocapAlways,ocapGranted,useTor,True)

def testPostMessageBetweenServers():
    print('Testing sending message from one server to the inbox of another')

    global testServerAliceRunning
    global testServerBobRunning
    testServerAliceRunning = False
    testServerBobRunning = False

    httpPrefix='http'
    useTor=False
    federationList=['127.0.0.50','127.0.0.100']
    ocapGranted={}

    baseDir=os.getcwd()
    if os.path.isdir(baseDir+'/.tests'):
        shutil.rmtree(baseDir+'/.tests')
    os.mkdir(baseDir+'/.tests')

    ocapAlways=False
    
    # create the servers
    aliceDir=baseDir+'/.tests/alice'
    aliceDomain='127.0.0.50'
    alicePort=61935
    thrAlice = threadWithTrace(target=createServerAlice,args=(aliceDir,aliceDomain,alicePort,federationList,ocapGranted,True,True,ocapAlways),daemon=True)

    bobDir=baseDir+'/.tests/bob'
    bobDomain='127.0.0.100'
    bobPort=61936
    thrBob = threadWithTrace(target=createServerBob,args=(bobDir,bobDomain,bobPort,federationList,ocapGranted,True,True,ocapAlways),daemon=True)

    thrAlice.start()
    thrBob.start()
    assert thrAlice.isAlive()==True
    assert thrBob.isAlive()==True

    # wait for both servers to be running
    while not (testServerAliceRunning and testServerBobRunning):
        time.sleep(1)
        
    time.sleep(1)

    print('Alice sends to Bob')
    os.chdir(aliceDir)
    sessionAlice = createSession(aliceDomain,alicePort,useTor)
    inReplyTo=None
    inReplyToAtomUri=None
    subject=None
    aliceSendThreads = []
    alicePostLog = []
    followersOnly=False
    saveToFile=True
    clientToServer=False
    ccUrl=None
    alicePersonCache={}
    aliceCachedWebfingers={}
    sendResult = sendPost(sessionAlice,aliceDir,'alice', aliceDomain, alicePort, 'bob', bobDomain, bobPort, ccUrl, httpPrefix, 'Why is a mouse when it spins?', followersOnly, saveToFile, clientToServer, federationList, ocapGranted, aliceSendThreads, alicePostLog, aliceCachedWebfingers,alicePersonCache,inReplyTo, inReplyToAtomUri, subject)
    print('sendResult: '+str(sendResult))

    queuePath=bobDir+'/accounts/bob@'+bobDomain+'/queue'
    inboxPath=bobDir+'/accounts/bob@'+bobDomain+'/inbox'
    for i in range(30):
        if os.path.isdir(inboxPath):
            if len([name for name in os.listdir(inboxPath) if os.path.isfile(os.path.join(inboxPath, name))])>0:
                break
        time.sleep(1)
    
    # stop the servers
    thrAlice.kill()
    thrAlice.join()
    assert thrAlice.isAlive()==False

    thrBob.kill()
    thrBob.join()
    assert thrBob.isAlive()==False

    # inbox item created
    assert len([name for name in os.listdir(inboxPath) if os.path.isfile(os.path.join(inboxPath, name))])==1
    # queue item removed
    assert len([name for name in os.listdir(queuePath) if os.path.isfile(os.path.join(queuePath, name))])==0

    os.chdir(baseDir)
    shutil.rmtree(aliceDir)
    shutil.rmtree(bobDir)

def testFollowBetweenServers():
    print('Testing sending a follow request from one server to another')

    global testServerAliceRunning
    global testServerBobRunning
    global testServerEveRunning
    testServerAliceRunning = False
    testServerBobRunning = False
    testServerEveRunning = False

    httpPrefix='http'
    useTor=False
    federationList=[]
    ocapGranted={}

    baseDir=os.getcwd()
    if os.path.isdir(baseDir+'/.tests'):
        shutil.rmtree(baseDir+'/.tests')
    os.mkdir(baseDir+'/.tests')

    ocapAlways=True

    # create the servers
    aliceDir=baseDir+'/.tests/alice'
    aliceDomain='127.0.0.42'
    alicePort=61935
    thrAlice = threadWithTrace(target=createServerAlice,args=(aliceDir,aliceDomain,alicePort,federationList,ocapGranted,False,False,ocapAlways),daemon=True)

    bobDir=baseDir+'/.tests/bob'
    bobDomain='127.0.0.64'
    bobPort=61936
    thrBob = threadWithTrace(target=createServerBob,args=(bobDir,bobDomain,bobPort,federationList,ocapGranted,False,False,ocapAlways),daemon=True)

    eveDir=baseDir+'/.tests/eve'
    eveDomain='127.0.0.55'
    evePort=61937
    thrEve = threadWithTrace(target=createServerEve,args=(eveDir,eveDomain,evePort,federationList,ocapGranted,False,False,False),daemon=True)

    thrAlice.start()
    thrBob.start()
    thrEve.start()
    assert thrAlice.isAlive()==True
    assert thrBob.isAlive()==True
    assert thrEve.isAlive()==True

    # wait for both servers to be running
    ctr=0
    while not (testServerAliceRunning and testServerBobRunning and testServerEveRunning):
        time.sleep(1)
        ctr+=1
        if ctr>30:
            break
    print('Alice online: '+str(testServerAliceRunning))
    print('Bob online: '+str(testServerBobRunning))
    print('Eve online: '+str(testServerEveRunning))
    assert ctr<=10
    time.sleep(1)

    # In the beginning all was calm and there were no follows
    
    print('Alice sends a follow request to Bob')
    print('Both are strictly enforcing object capabilities')
    os.chdir(aliceDir)
    sessionAlice = createSession(aliceDomain,alicePort,useTor)
    inReplyTo=None
    inReplyToAtomUri=None
    subject=None
    aliceSendThreads = []
    alicePostLog = []
    followersOnly=False
    saveToFile=True
    clientToServer=False
    ccUrl=None
    alicePersonCache={}
    aliceCachedWebfingers={}
    aliceSendThreads=[]
    alicePostLog=[]
    sendResult = \
        sendFollowRequest(sessionAlice,aliceDir, \
                          'alice',aliceDomain,alicePort,httpPrefix, \
                          'bob',bobDomain,bobPort,httpPrefix, \
                          clientToServer,federationList,ocapGranted,
                          aliceSendThreads,alicePostLog, \
                          aliceCachedWebfingers,alicePersonCache,True)
    print('sendResult: '+str(sendResult))

    for t in range(10):
        if os.path.isfile(bobDir+'/accounts/bob@'+bobDomain+'/followers.txt'):
            if os.path.isfile(aliceDir+'/accounts/alice@'+aliceDomain+'/following.txt'):
                if os.path.isfile(bobDir+'/accounts/bob@'+bobDomain+'/ocap/accept/'+httpPrefix+':##'+aliceDomain+':'+str(alicePort)+'#users#alice.json'):
                    if os.path.isfile(aliceDir+'/accounts/alice@'+aliceDomain+'/ocap/granted/'+httpPrefix+':##'+bobDomain+':'+str(bobPort)+'#users#bob.json'):
                        break
        time.sleep(1)

    print('\n\nEve tries to send to Bob')
    sessionEve = createSession(eveDomain,evePort,useTor)
    eveSendThreads = []
    evePostLog = []
    evePersonCache={}
    eveCachedWebfingers={}
    eveSendThreads=[]
    evePostLog=[]
    sendResult = sendPost(sessionEve,eveDir,'eve', eveDomain, evePort, 'bob', bobDomain, bobPort, ccUrl, httpPrefix, 'Eve message', followersOnly, saveToFile, clientToServer, federationList, ocapGranted, eveSendThreads, evePostLog, eveCachedWebfingers,evePersonCache,inReplyTo, inReplyToAtomUri, subject)
    print('sendResult: '+str(sendResult))

    queuePath=bobDir+'/accounts/bob@'+bobDomain+'/queue'
    inboxPath=bobDir+'/accounts/bob@'+bobDomain+'/inbox'
    eveMessageArrived=False
    for i in range(5):
        time.sleep(1)
        if os.path.isdir(inboxPath):
            if len([name for name in os.listdir(inboxPath) if os.path.isfile(os.path.join(inboxPath, name))])>1:
                eveMessageArrived=True
                print('Eve message sent to Bob!')
                break

    # capabilities should have prevented delivery
    assert eveMessageArrived==False
    print('Message from Eve to Bob was correctly rejected by object capabilities')


    aliceSendThreads = []
    alicePostLog = []
    alicePersonCache={}
    aliceCachedWebfingers={}
    aliceSendThreads=[]
    alicePostLog=[]
    sendResult = sendPost(sessionAlice,aliceDir,'alice', aliceDomain, alicePort, 'bob', bobDomain, bobPort, ccUrl, httpPrefix, 'Alice message', followersOnly, saveToFile, clientToServer, federationList, ocapGranted, aliceSendThreads, alicePostLog, aliceCachedWebfingers,alicePersonCache,inReplyTo, inReplyToAtomUri, subject)
    print('sendResult: '+str(sendResult))

    queuePath=bobDir+'/accounts/bob@'+bobDomain+'/queue'
    inboxPath=bobDir+'/accounts/bob@'+bobDomain+'/inbox'
    aliceMessageArrived=False
    for i in range(5):
        time.sleep(1)
        if os.path.isdir(inboxPath):
            if len([name for name in os.listdir(inboxPath) if os.path.isfile(os.path.join(inboxPath, name))])>1:
                aliceMessageArrived=True
                print('Alice message sent to Bob!')
                break

    assert aliceMessageArrived==True
    print('Message from Alice to Bob succeeded, since it was granted capabilities')

    # stop the servers
    thrAlice.kill()
    thrAlice.join()
    assert thrAlice.isAlive()==False

    thrBob.kill()
    thrBob.join()
    assert thrBob.isAlive()==False
    
    assert os.path.isfile(bobDir+'/accounts/bob@'+bobDomain+'/ocap/accept/'+httpPrefix+':##'+aliceDomain+':'+str(alicePort)+'#users#alice.json')
    assert os.path.isfile(aliceDir+'/accounts/alice@'+aliceDomain+'/ocap/granted/'+httpPrefix+':##'+bobDomain+':'+str(bobPort)+'#users#bob.json')
    
    assert 'alice@'+aliceDomain in open(bobDir+'/accounts/bob@'+bobDomain+'/followers.txt').read()
    assert 'bob@'+bobDomain in open(aliceDir+'/accounts/alice@'+aliceDomain+'/following.txt').read()
    
    os.chdir(baseDir)
    shutil.rmtree(baseDir+'/.tests')

def testFollowersOfPerson():
    print('testFollowersOfPerson')
    currDir=os.getcwd()
    nickname='mxpop'
    domain='diva.domain'
    password='birb'
    port=80
    httpPrefix='https'
    federationList=[]
    baseDir=currDir+'/.tests_followersofperson'
    if os.path.isdir(baseDir):
        shutil.rmtree(baseDir)
    os.mkdir(baseDir)
    os.chdir(baseDir)    
    createPerson(baseDir,nickname,domain,port,httpPrefix,True,password)
    createPerson(baseDir,'maxboardroom',domain,port,httpPrefix,True,password)
    createPerson(baseDir,'ultrapancake',domain,port,httpPrefix,True,password)
    createPerson(baseDir,'drokk',domain,port,httpPrefix,True,password)
    createPerson(baseDir,'sausagedog',domain,port,httpPrefix,True,password)

    clearFollows(baseDir,nickname,domain)
    followPerson(baseDir,nickname,domain,'maxboardroom',domain,federationList,True)
    followPerson(baseDir,'drokk',domain,'ultrapancake',domain,federationList,True)
    # deliberate duplication
    followPerson(baseDir,'drokk',domain,'ultrapancake',domain,federationList,True)
    followPerson(baseDir,'sausagedog',domain,'ultrapancake',domain,federationList,True)
    followPerson(baseDir,nickname,domain,'ultrapancake',domain,federationList,True)
    followPerson(baseDir,nickname,domain,'someother','randodomain.net',federationList,True)

    followList=getFollowersOfPerson(baseDir,'ultrapancake',domain)
    assert len(followList)==3
    assert 'mxpop@'+domain in followList
    assert 'drokk@'+domain in followList
    assert 'sausagedog@'+domain in followList
    os.chdir(currDir)
    shutil.rmtree(baseDir)

def testNoOfFollowersOnDomain():
    print('testNoOfFollowersOnDomain')
    currDir=os.getcwd()
    nickname='mxpop'
    domain='diva.domain'
    otherdomain='soup.dragon'
    password='birb'
    port=80
    httpPrefix='https'
    federationList=[]
    baseDir=currDir+'/.tests_nooffollowersOndomain'
    if os.path.isdir(baseDir):
        shutil.rmtree(baseDir)
    os.mkdir(baseDir)
    os.chdir(baseDir)    
    createPerson(baseDir,nickname,domain,port,httpPrefix,True,password)
    createPerson(baseDir,'maxboardroom',otherdomain,port,httpPrefix,True,password)
    createPerson(baseDir,'ultrapancake',otherdomain,port,httpPrefix,True,password)
    createPerson(baseDir,'drokk',otherdomain,port,httpPrefix,True,password)
    createPerson(baseDir,'sausagedog',otherdomain,port,httpPrefix,True,password)

    followPerson(baseDir,'drokk',otherdomain,nickname,domain,federationList,True)
    followPerson(baseDir,'sausagedog',otherdomain,nickname,domain,federationList,True)
    followPerson(baseDir,'maxboardroom',otherdomain,nickname,domain,federationList,True)
    
    followerOfPerson(baseDir,nickname,domain,'cucumber','sandwiches.party',federationList,True)
    followerOfPerson(baseDir,nickname,domain,'captainsensible','damned.zone',federationList,True)
    followerOfPerson(baseDir,nickname,domain,'pilchard','zombies.attack',federationList,True)
    followerOfPerson(baseDir,nickname,domain,'drokk',otherdomain,federationList,True)
    followerOfPerson(baseDir,nickname,domain,'sausagedog',otherdomain,federationList,True)
    followerOfPerson(baseDir,nickname,domain,'maxboardroom',otherdomain,federationList,True)

    followersOnOtherDomain=noOfFollowersOnDomain(baseDir,nickname+'@'+domain, otherdomain)
    assert followersOnOtherDomain==3

    unfollowerOfPerson(baseDir,nickname,domain,'sausagedog',otherdomain)
    followersOnOtherDomain=noOfFollowersOnDomain(baseDir,nickname+'@'+domain, otherdomain)
    assert followersOnOtherDomain==2
    
    os.chdir(currDir)
    shutil.rmtree(baseDir)

def testFollows():
    print('testFollows')
    currDir=os.getcwd()
    nickname='test529'
    domain='testdomain.com'
    password='mypass'
    port=80
    httpPrefix='https'
    federationList=['wild.com','mesh.com']
    baseDir=currDir+'/.tests_testfollows'
    if os.path.isdir(baseDir):
        shutil.rmtree(baseDir)
    os.mkdir(baseDir)
    os.chdir(baseDir)    
    createPerson(baseDir,nickname,domain,port,httpPrefix,True,password)

    clearFollows(baseDir,nickname,domain)
    followPerson(baseDir,nickname,domain,'badger','wild.com',federationList,False)
    followPerson(baseDir,nickname,domain,'squirrel','secret.com',federationList,False)
    followPerson(baseDir,nickname,domain,'rodent','drainpipe.com',federationList,False)
    followPerson(baseDir,nickname,domain,'batman','mesh.com',federationList,False)
    followPerson(baseDir,nickname,domain,'giraffe','trees.com',federationList,False)

    f = open(baseDir+'/accounts/'+nickname+'@'+domain+'/following.txt', "r")
    domainFound=False
    for followingDomain in f:
        testDomain=followingDomain.split('@')[1].replace('\n','')
        if testDomain=='mesh.com':
            domainFound=True
        if testDomain not in federationList:
            print(testDomain)
            assert(False)

    assert(domainFound)
    unfollowPerson(baseDir,nickname,domain,'batman','mesh.com')

    domainFound=False
    for followingDomain in f:
        testDomain=followingDomain.split('@')[1].replace('\n','')
        if testDomain=='mesh.com':
            domainFound=True
    assert(domainFound==False)

    clearFollowers(baseDir,nickname,domain)
    followerOfPerson(baseDir,nickname,domain,'badger','wild.com',federationList,False)
    followerOfPerson(baseDir,nickname,domain,'squirrel','secret.com',federationList,False)
    followerOfPerson(baseDir,nickname,domain,'rodent','drainpipe.com',federationList,False)
    followerOfPerson(baseDir,nickname,domain,'batman','mesh.com',federationList,False)
    followerOfPerson(baseDir,nickname,domain,'giraffe','trees.com',federationList,False)

    f = open(baseDir+'/accounts/'+nickname+'@'+domain+'/followers.txt', "r")
    for followerDomain in f:
        testDomain=followerDomain.split('@')[1].replace('\n','')
        if testDomain not in federationList:
            print(testDomain)
            assert(False)

    os.chdir(currDir)
    shutil.rmtree(baseDir)

def testCreatePerson():
    print('testCreatePerson')
    currDir=os.getcwd()
    nickname='test382'
    domain='badgerdomain.com'
    password='mypass'
    port=80
    httpPrefix='https'
    clientToServer=False
    baseDir=currDir+'/.tests_createperson'
    if os.path.isdir(baseDir):
        shutil.rmtree(baseDir)
    os.mkdir(baseDir)
    os.chdir(baseDir)
    
    privateKeyPem,publicKeyPem,person,wfEndpoint=createPerson(baseDir,nickname,domain,port,httpPrefix,True,password)
    assert os.path.isfile(baseDir+'/accounts/passwords')
    deleteAllPosts(baseDir,nickname,domain,'inbox')
    deleteAllPosts(baseDir,nickname,domain,'outbox')
    setPreferredNickname(baseDir,nickname,domain,'badger')
    setBio(baseDir,nickname,domain,'Randomly roaming in your backyard')
    archivePosts(nickname,domain,baseDir,'inbox',4)
    archivePosts(nickname,domain,baseDir,'outbox',4)
    createPublicPost(baseDir,nickname, domain, port,httpPrefix, "G'day world!", False, True, clientToServer, None, None, 'Not suitable for Vogons')

    os.chdir(currDir)
    shutil.rmtree(baseDir)

def testAuthentication():
    print('testAuthentication')
    currDir=os.getcwd()
    nickname='test8743'
    password='SuperSecretPassword12345'

    baseDir=currDir+'/.tests_authentication'
    if os.path.isdir(baseDir):
        shutil.rmtree(baseDir)
    os.mkdir(baseDir)
    os.chdir(baseDir)

    assert storeBasicCredentials(baseDir,'othernick','otherpass')
    assert storeBasicCredentials(baseDir,'bad:nick','otherpass')==False
    assert storeBasicCredentials(baseDir,'badnick','otherpa:ss')==False
    assert storeBasicCredentials(baseDir,nickname,password)

    authHeader=createBasicAuthHeader(nickname,password)
    assert authorizeBasic(baseDir,'/users/'+nickname+'/inbox',authHeader,False)
    assert authorizeBasic(baseDir,'/users/'+nickname,authHeader,False)==False
    assert authorizeBasic(baseDir,'/users/othernick/inbox',authHeader,False)==False

    authHeader=createBasicAuthHeader(nickname,password+'1')
    assert authorizeBasic(baseDir,'/users/'+nickname+'/inbox',authHeader,False)==False

    password='someOtherPassword'
    assert storeBasicCredentials(baseDir,nickname,password)

    authHeader=createBasicAuthHeader(nickname,password)
    assert authorizeBasic(baseDir,'/users/'+nickname+'/inbox',authHeader,False)

    os.chdir(currDir)
    shutil.rmtree(baseDir)
    
def runAllTests():
    print('Running tests...')
    testHttpsig()
    testCache()
    testThreads()
    testCreatePerson()
    testAuthentication()
    testFollowersOfPerson()
    testNoOfFollowersOnDomain()
    testFollows()    
    print('Tests succeeded\n')        
