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
import commentjson
from pprint import pprint
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
from posts import groupFollowersByDomain
from posts import sendCapabilitiesUpdate
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
from like import likePost

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

def createServerAlice(path: str,domain: str,port: int,federationList: [],hasFollows: bool,hasPosts :bool,ocapAlways: bool):
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
    noreply=False
    nolike=False
    nopics=False
    noannounce=False
    cw=False
    privateKeyPem,publicKeyPem,person,wfEndpoint=createPerson(path,nickname,domain,port,httpPrefix,True,password)
    deleteAllPosts(path,nickname,domain,'inbox')
    deleteAllPosts(path,nickname,domain,'outbox')
    if hasFollows:
        followPerson(path,nickname,domain,'bob','127.0.0.100:61936',federationList,True)
        followerOfPerson(path,nickname,domain,'bob','127.0.0.100:61936',federationList,True)
    if hasPosts:
        createPublicPost(path,nickname, domain, port,httpPrefix, "No wise fish would go anywhere without a porpoise", False, True, clientToServer)
        createPublicPost(path,nickname, domain, port,httpPrefix, "Curiouser and curiouser!", False, True, clientToServer)
        createPublicPost(path,nickname, domain, port,httpPrefix, "In the gardens of memory, in the palace of dreams, that is where you and I shall meet", False, True, clientToServer)
    global testServerAliceRunning
    testServerAliceRunning = True
    print('Server running: Alice')
    runDaemon(path,domain,port,httpPrefix,federationList,noreply,nolike,nopics,noannounce,cw,ocapAlways,useTor,True)

def createServerBob(path: str,domain: str,port: int,federationList: [],hasFollows: bool,hasPosts :bool,ocapAlways :bool):
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
    noreply=False
    nolike=False
    nopics=False
    noannounce=False
    cw=False
    privateKeyPem,publicKeyPem,person,wfEndpoint=createPerson(path,nickname,domain,port,httpPrefix,True,password)
    deleteAllPosts(path,nickname,domain,'inbox')
    deleteAllPosts(path,nickname,domain,'outbox')
    if hasFollows:
        followPerson(path,nickname,domain,'alice','127.0.0.50:61935',federationList,True)
        followerOfPerson(path,nickname,domain,'alice','127.0.0.50:61935',federationList,True)
    if hasPosts:
        createPublicPost(path,nickname, domain, port,httpPrefix, "It's your life, live it your way.", False, True, clientToServer)
        createPublicPost(path,nickname, domain, port,httpPrefix, "One of the things I've realised is that I am very simple", False, True, clientToServer)
        createPublicPost(path,nickname, domain, port,httpPrefix, "Quantum physics is a bit of a passion of mine", False, True, clientToServer)
    global testServerBobRunning
    testServerBobRunning = True
    print('Server running: Bob')
    runDaemon(path,domain,port,httpPrefix,federationList,noreply,nolike,nopics,noannounce,cw,ocapAlways,useTor,True)

def createServerEve(path: str,domain: str,port: int,federationList: [],hasFollows: bool,hasPosts :bool,ocapAlways :bool):
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
    noreply=False
    nolike=False
    nopics=False
    noannounce=False
    cw=False
    privateKeyPem,publicKeyPem,person,wfEndpoint=createPerson(path,nickname,domain,port,httpPrefix,True,password)
    deleteAllPosts(path,nickname,domain,'inbox')
    deleteAllPosts(path,nickname,domain,'outbox')
    global testServerEveRunning
    testServerEveRunning = True
    print('Server running: Eve')
    runDaemon(path,domain,port,httpPrefix,federationList,noreply,nolike,nopics,noannounce,cw,ocapAlways,useTor,True)

def testPostMessageBetweenServers():
    print('Testing sending message from one server to the inbox of another')

    global testServerAliceRunning
    global testServerBobRunning
    testServerAliceRunning = False
    testServerBobRunning = False

    httpPrefix='http'
    useTor=False

    baseDir=os.getcwd()
    if os.path.isdir(baseDir+'/.tests'):
        shutil.rmtree(baseDir+'/.tests')
    os.mkdir(baseDir+'/.tests')

    ocapAlways=False
    
    # create the servers
    aliceDir=baseDir+'/.tests/alice'
    aliceDomain='127.0.0.50'
    alicePort=61935
    bobDir=baseDir+'/.tests/bob'
    bobDomain='127.0.0.100'
    bobPort=61936
    federationList=[bobDomain,aliceDomain]

    thrAlice = threadWithTrace(target=createServerAlice,args=(aliceDir,aliceDomain,alicePort,federationList,False,False,ocapAlways),daemon=True)
    thrBob = threadWithTrace(target=createServerBob,args=(bobDir,bobDomain,bobPort,federationList,False,False,ocapAlways),daemon=True)

    thrAlice.start()
    thrBob.start()
    assert thrAlice.isAlive()==True
    assert thrBob.isAlive()==True

    # wait for both servers to be running
    while not (testServerAliceRunning and testServerBobRunning):
        time.sleep(1)
        
    time.sleep(1)

    print('\n\n*******************************************************')
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

    # nothing in Alice's outbox
    outboxPath=aliceDir+'/accounts/alice@'+aliceDomain+'/outbox'
    assert len([name for name in os.listdir(outboxPath) if os.path.isfile(os.path.join(outboxPath, name))])==0

    sendResult = sendPost(sessionAlice,aliceDir,'alice', aliceDomain, alicePort, 'bob', bobDomain, bobPort, ccUrl, httpPrefix, 'Why is a mouse when it spins?', followersOnly, saveToFile, clientToServer, federationList, aliceSendThreads, alicePostLog, aliceCachedWebfingers,alicePersonCache,inReplyTo, inReplyToAtomUri, subject)
    print('sendResult: '+str(sendResult))

    queuePath=bobDir+'/accounts/bob@'+bobDomain+'/queue'
    inboxPath=bobDir+'/accounts/bob@'+bobDomain+'/inbox'
    for i in range(30):
        if os.path.isdir(inboxPath):
            if len([name for name in os.listdir(inboxPath) if os.path.isfile(os.path.join(inboxPath, name))])>0:
                if len([name for name in os.listdir(outboxPath) if os.path.isfile(os.path.join(outboxPath, name))])==1:
                    break
        time.sleep(1)

    # inbox item created
    assert len([name for name in os.listdir(inboxPath) if os.path.isfile(os.path.join(inboxPath, name))])==1
    # queue item removed
    assert len([name for name in os.listdir(queuePath) if os.path.isfile(os.path.join(queuePath, name))])==0

    #print('\n\n*******************************************************')
    #print("Bob likes Alice's post")

    #followerOfPerson(bobDir,'bob',bobDomain,'alice',aliceDomain+':'+str(alicePort),federationList,True)
    #followPerson(aliceDir,'alice',aliceDomain,'bob',bobDomain+':'+str(bobPort),federationList,True)
    #followList=getFollowersOfPerson(bobDir,'bob',bobDomain,'followers.txt')
    #assert len(followList)==1

    #sessionBob = createSession(bobDomain,bobPort,useTor)
    #bobSendThreads = []
    #bobPostLog = []
    #bobPersonCache={}
    #bobCachedWebfingers={}
    #statusNumber=None
    #outboxPostFilename=None
    #outboxPath=aliceDir+'/accounts/alice@'+aliceDomain+'/outbox'
    #for name in os.listdir(outboxPath):
    #    if '#statuses#' in name:
    #        statusNumber=int(name.split('#statuses#')[1].replace('.json',''))
    #        outboxPostFilename=outboxPath+'/'+name
    #assert statusNumber
    #assert outboxPostFilename
    #assert likePost(sessionBob,bobDir,federationList, \
    #                'bob',bobDomain,bobPort,httpPrefix, \
    #                'alice',aliceDomain,alicePort,[], \
    #                statusNumber,False,bobSendThreads,bobPostLog, \
    #                bobPersonCache,bobCachedWebfingers,True)

    #for i in range(20):
    #    if 'likes' in open(outboxPostFilename).read():
    #        break
    #    time.sleep(1)

    #with open(outboxPostFilename, 'r') as fp:
    #    alicePostJson=commentjson.load(fp)
    #    pprint(alicePostJson)
    #assert 'likes' in open(outboxPostFilename).read()
    
    # stop the servers
    thrAlice.kill()
    thrAlice.join()
    assert thrAlice.isAlive()==False

    thrBob.kill()
    thrBob.join()
    assert thrBob.isAlive()==False

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

    baseDir=os.getcwd()
    if os.path.isdir(baseDir+'/.tests'):
        shutil.rmtree(baseDir+'/.tests')
    os.mkdir(baseDir+'/.tests')

    ocapAlways=True

    # create the servers
    aliceDir=baseDir+'/.tests/alice'
    aliceDomain='127.0.0.42'
    alicePort=61935
    thrAlice = threadWithTrace(target=createServerAlice,args=(aliceDir,aliceDomain,alicePort,federationList,False,False,ocapAlways),daemon=True)

    bobDir=baseDir+'/.tests/bob'
    bobDomain='127.0.0.64'
    bobPort=61936
    thrBob = threadWithTrace(target=createServerBob,args=(bobDir,bobDomain,bobPort,federationList,False,False,ocapAlways),daemon=True)

    eveDir=baseDir+'/.tests/eve'
    eveDomain='127.0.0.55'
    evePort=61937
    thrEve = threadWithTrace(target=createServerEve,args=(eveDir,eveDomain,evePort,federationList,False,False,False),daemon=True)

    thrAlice.start()
    thrBob.start()
    thrEve.start()
    assert thrAlice.isAlive()==True
    assert thrBob.isAlive()==True
    assert thrEve.isAlive()==True

    # wait for all servers to be running
    ctr=0
    while not (testServerAliceRunning and testServerBobRunning and testServerEveRunning):
        time.sleep(1)
        ctr+=1
        if ctr>60:
            break
    print('Alice online: '+str(testServerAliceRunning))
    print('Bob online: '+str(testServerBobRunning))
    print('Eve online: '+str(testServerEveRunning))
    assert ctr<=60
    time.sleep(1)

    # In the beginning all was calm and there were no follows

    print('*********************************************************')
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
                          clientToServer,federationList, \
                          aliceSendThreads,alicePostLog, \
                          aliceCachedWebfingers,alicePersonCache,True)
    print('sendResult: '+str(sendResult))

    bobCapsFilename=bobDir+'/accounts/bob@'+bobDomain+'/ocap/accept/'+httpPrefix+':##'+aliceDomain+':'+str(alicePort)+'#users#alice.json'
    aliceCapsFilename=aliceDir+'/accounts/alice@'+aliceDomain+'/ocap/granted/'+httpPrefix+':##'+bobDomain+':'+str(bobPort)+'#users#bob.json'

    for t in range(10):
        if os.path.isfile(bobDir+'/accounts/bob@'+bobDomain+'/followers.txt'):
            if os.path.isfile(aliceDir+'/accounts/alice@'+aliceDomain+'/following.txt'):
                if os.path.isfile(bobCapsFilename):
                    if os.path.isfile(aliceCapsFilename):
                        break
        time.sleep(1)

    with open(bobCapsFilename, 'r') as fp:
        bobCapsJson=commentjson.load(fp)
        if not bobCapsJson.get('capability'):
            print("Unexpected format for Bob's capabilities")
            pprint(bobCapsJson)
            assert False
        
    print('\n\n*********************************************************')
    print('Eve tries to send to Bob')
    sessionEve = createSession(eveDomain,evePort,useTor)
    eveSendThreads = []
    evePostLog = []
    evePersonCache={}
    eveCachedWebfingers={}
    eveSendThreads=[]
    evePostLog=[]
    sendResult = sendPost(sessionEve,eveDir,'eve', eveDomain, evePort, 'bob', bobDomain, bobPort, ccUrl, httpPrefix, 'Eve message', followersOnly, saveToFile, clientToServer, federationList, eveSendThreads, evePostLog, eveCachedWebfingers,evePersonCache,inReplyTo, inReplyToAtomUri, subject)
    print('sendResult: '+str(sendResult))

    queuePath=bobDir+'/accounts/bob@'+bobDomain+'/queue'
    inboxPath=bobDir+'/accounts/bob@'+bobDomain+'/inbox'
    eveMessageArrived=False
    for i in range(10):
        time.sleep(1)
        if os.path.isdir(inboxPath):
            if len([name for name in os.listdir(inboxPath) if os.path.isfile(os.path.join(inboxPath, name))])>1:
                eveMessageArrived=True
                print('Eve message sent to Bob!')
                break

    # capabilities should have prevented delivery
    assert eveMessageArrived==False
    print('Message from Eve to Bob was correctly rejected by object capabilities')

    print('\n\n*********************************************************')
    print('Alice sends a message to Bob')
    aliceSendThreads = []
    alicePostLog = []
    alicePersonCache={}
    aliceCachedWebfingers={}
    aliceSendThreads=[]
    alicePostLog=[]
    sendResult = sendPost(sessionAlice,aliceDir,'alice', aliceDomain, alicePort, 'bob', bobDomain, bobPort, ccUrl, httpPrefix, 'Alice message', followersOnly, saveToFile, clientToServer, federationList, aliceSendThreads, alicePostLog, aliceCachedWebfingers,alicePersonCache,inReplyTo, inReplyToAtomUri, subject)
    print('sendResult: '+str(sendResult))

    queuePath=bobDir+'/accounts/bob@'+bobDomain+'/queue'
    inboxPath=bobDir+'/accounts/bob@'+bobDomain+'/inbox'
    aliceMessageArrived=False    
    for i in range(20):
        time.sleep(1)
        if os.path.isdir(inboxPath):
            if len([name for name in os.listdir(inboxPath) if os.path.isfile(os.path.join(inboxPath, name))])>0:
                aliceMessageArrived=True
                print('Alice message sent to Bob!')
                break

    assert aliceMessageArrived==True
    print('Message from Alice to Bob succeeded, since it was granted capabilities')
    
    print('\n\n*********************************************************')
    print("\nBob changes Alice's capabilities so that she can't reply on his posts")
    bobCapsFilename=bobDir+'/accounts/bob@'+bobDomain+'/ocap/accept/'+httpPrefix+':##'+aliceDomain+':'+str(alicePort)+'#users#alice.json'
    aliceCapsFilename=aliceDir+'/accounts/alice@'+aliceDomain+'/ocap/granted/'+httpPrefix+':##'+bobDomain+':'+str(bobPort)+'#users#bob.json'
    sessionBob = createSession(bobDomain,bobPort,useTor)
    bobSendThreads = []
    bobPostLog = []
    bobPersonCache={}
    bobCachedWebfingers={}
    print("Bob's capabilities for Alice:")
    with open(bobCapsFilename, 'r') as fp:
        bobCapsJson=commentjson.load(fp)
        pprint(bobCapsJson)
        assert "inbox:noreply" not in bobCapsJson['capability']
    print("Alice's capabilities granted by Bob")
    with open(aliceCapsFilename, 'r') as fp:
        aliceCapsJson=commentjson.load(fp)
        pprint(aliceCapsJson)
        assert "inbox:noreply" not in aliceCapsJson['capability']
    newCapabilities=["inbox:write","objects:read","inbox:noreply"]
    sendCapabilitiesUpdate(sessionBob,bobDir,httpPrefix, \
                           'bob',bobDomain,bobPort, \
                           httpPrefix+'://'+aliceDomain+':'+str(alicePort)+'/users/alice',
                           newCapabilities, \
                           bobSendThreads, bobPostLog, \
                           bobCachedWebfingers,bobPersonCache, \
                           federationList,True)

    bobChanged=False
    bobNewCapsJson=None
    for i in range(20):
        time.sleep(1)
        with open(bobCapsFilename, 'r') as fp:
            bobNewCapsJson=commentjson.load(fp)
            if "inbox:noreply" in bobNewCapsJson['capability']:
                print("Bob's capabilities were changed")
                pprint(bobNewCapsJson)
                bobChanged=True
                break

    assert bobChanged

    aliceChanged=False
    aliceNewCapsJson=None
    for i in range(20):
        time.sleep(1)
        with open(aliceCapsFilename, 'r') as fp:
            aliceNewCapsJson=commentjson.load(fp)
            if "inbox:noreply" in aliceNewCapsJson['capability']:
                print("Alice's granted capabilities were changed")
                pprint(aliceNewCapsJson)
                aliceChanged=True
                break

    assert aliceChanged

    # check that the capabilities id has changed
    assert bobNewCapsJson['id']!=bobCapsJson['id']
    assert aliceNewCapsJson['id']!=aliceCapsJson['id']

    # stop the servers
    thrAlice.kill()
    thrAlice.join()
    assert thrAlice.isAlive()==False

    thrBob.kill()
    thrBob.join()
    assert thrBob.isAlive()==False

    thrEve.kill()
    thrEve.join()
    assert thrEve.isAlive()==False
    
    assert os.path.isfile(bobDir+'/accounts/bob@'+bobDomain+'/ocap/accept/'+httpPrefix+':##'+aliceDomain+':'+str(alicePort)+'#users#alice.json')
    assert os.path.isfile(aliceDir+'/accounts/alice@'+aliceDomain+'/ocap/granted/'+httpPrefix+':##'+bobDomain+':'+str(bobPort)+'#users#bob.json')
    
    assert 'alice@'+aliceDomain in open(bobDir+'/accounts/bob@'+bobDomain+'/followers.txt').read()
    assert 'bob@'+bobDomain in open(aliceDir+'/accounts/alice@'+aliceDomain+'/following.txt').read()

    # queue item removed
    assert len([name for name in os.listdir(queuePath) if os.path.isfile(os.path.join(queuePath, name))])==0
    
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

def testGroupFollowers():
    print('testGroupFollowers')

    currDir=os.getcwd()
    nickname='test735'
    domain='mydomain.com'
    password='somepass'
    port=80
    httpPrefix='https'
    federationList=[]
    baseDir=currDir+'/.tests_testgroupfollowers'
    if os.path.isdir(baseDir):
        shutil.rmtree(baseDir)
    os.mkdir(baseDir)
    os.chdir(baseDir)    
    createPerson(baseDir,nickname,domain,port,httpPrefix,True,password)

    clearFollowers(baseDir,nickname,domain)
    followerOfPerson(baseDir,nickname,domain,'badger','wild.domain',federationList,False)
    followerOfPerson(baseDir,nickname,domain,'squirrel','wild.domain',federationList,False)
    followerOfPerson(baseDir,nickname,domain,'rodent','wild.domain',federationList,False)
    followerOfPerson(baseDir,nickname,domain,'utterly','clutterly.domain',federationList,False)
    followerOfPerson(baseDir,nickname,domain,'zonked','zzz.domain',federationList,False)
    followerOfPerson(baseDir,nickname,domain,'nap','zzz.domain',federationList,False)

    grouped=groupFollowersByDomain(baseDir,nickname,domain)
    assert len(grouped.items())==3
    assert grouped.get('zzz.domain')
    assert grouped.get('clutterly.domain')
    assert grouped.get('wild.domain')
    assert len(grouped['zzz.domain'])==2
    assert len(grouped['wild.domain'])==3
    assert len(grouped['clutterly.domain'])==1
    
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
    testGroupFollowers()
    print('Tests succeeded\n')        
