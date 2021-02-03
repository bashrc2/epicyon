__filename__ = "tests.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import time
import os
import shutil
import json
from time import gmtime, strftime
from pprint import pprint
from httpsig import signPostHeaders
from httpsig import verifyPostHeaders
from httpsig import messageContentDigest
from cache import storePersonInCache
from cache import getPersonFromCache
from threads import threadWithTrace
from daemon import runDaemon
from session import createSession
from posts import getMentionedPeople
from posts import validContentWarning
from posts import deleteAllPosts
from posts import createPublicPost
from posts import sendPost
from posts import noOfFollowersOnDomain
from posts import groupFollowersByDomain
from posts import archivePostsForPerson
from posts import sendPostViaServer
from follow import clearFollows
from follow import clearFollowers
from follow import sendFollowRequestViaServer
from follow import sendUnfollowRequestViaServer
from utils import decodedHost
from utils import getFullDomain
from utils import validNickname
from utils import firstParagraphFromString
from utils import removeIdEnding
from utils import siteIsActive
from utils import updateRecentPostsCache
from utils import followPerson
from utils import getNicknameFromActor
from utils import getDomainFromActor
from utils import copytree
from utils import loadJson
from utils import saveJson
from utils import getStatusNumber
from utils import getFollowersOfPerson
from utils import removeHtml
from utils import dangerousMarkup
from follow import followerOfPerson
from follow import unfollowAccount
from follow import unfollowerOfAccount
from follow import sendFollowRequest
from person import createPerson
from person import setDisplayNickname
from person import setBio
# from person import generateRSAKey
from skills import setSkillLevel
from roles import setRole
from roles import outboxDelegate
from auth import constantTimeStringCheck
from auth import createBasicAuthHeader
from auth import authorizeBasic
from auth import storeBasicCredentials
from like import likePost
from like import sendLikeViaServer
from announce import announcePublic
from announce import sendAnnounceViaServer
from media import getMediaPath
from media import getAttachmentMediaType
from delete import sendDeleteViaServer
from inbox import jsonPostAllowsComments
from inbox import validInbox
from inbox import validInboxFilenames
from categories import guessHashtagCategory
from content import htmlReplaceEmailQuote
from content import htmlReplaceQuoteMarks
from content import dangerousCSS
from content import addWebLinks
from content import replaceEmojiFromTags
from content import addHtmlTags
from content import removeLongWords
from content import replaceContentDuplicates
from content import removeTextFormatting
from content import removeHtmlTag
from theme import setCSSparam
from linked_data_sig import generateJsonSignature
from linked_data_sig import verifyJsonSignature
from newsdaemon import hashtagRuleTree
from newsdaemon import hashtagRuleResolve
from newswire import getNewswireTags
from newswire import parseFeedDate
from mastoapiv1 import getMastoApiV1IdFromNickname
from mastoapiv1 import getNicknameFromMastoApiV1Id
from webapp_post import prepareHtmlPostNickname

testServerAliceRunning = False
testServerBobRunning = False
testServerEveRunning = False
thrAlice = None
thrBob = None
thrEve = None


def _testHttpsigBase(withDigest):
    print('testHttpsig(' + str(withDigest) + ')')

    baseDir = os.getcwd()
    path = baseDir + '/.testHttpsigBase'
    if os.path.isdir(path):
        shutil.rmtree(path)
    os.mkdir(path)
    os.chdir(path)

    contentType = 'application/activity+json'
    nickname = 'socrates'
    domain = 'argumentative.social'
    httpPrefix = 'https'
    port = 5576
    password = 'SuperSecretPassword'
    privateKeyPem, publicKeyPem, person, wfEndpoint = \
        createPerson(path, nickname, domain, port, httpPrefix,
                     False, False, password)
    assert privateKeyPem
    messageBodyJson = {
        "a key": "a value",
        "another key": "A string",
        "yet another key": "Another string"
    }
    messageBodyJsonStr = json.dumps(messageBodyJson)

    headersDomain = getFullDomain(domain, port)

    dateStr = strftime("%a, %d %b %Y %H:%M:%S %Z", gmtime())
    boxpath = '/inbox'
    if not withDigest:
        headers = {
            'host': headersDomain,
            'date': dateStr,
            'content-type': 'application/json'
        }
        signatureHeader = \
            signPostHeaders(dateStr, privateKeyPem, nickname,
                            domain, port,
                            domain, port,
                            boxpath, httpPrefix, None)
    else:
        bodyDigest = messageContentDigest(messageBodyJsonStr)
        contentLength = len(messageBodyJsonStr)
        headers = {
            'host': headersDomain,
            'date': dateStr,
            'digest': f'SHA-256={bodyDigest}',
            'content-type': contentType,
            'content-length': str(contentLength)
        }
        signatureHeader = \
            signPostHeaders(dateStr, privateKeyPem, nickname,
                            domain, port,
                            domain, port,
                            boxpath, httpPrefix, messageBodyJsonStr)

    headers['signature'] = signatureHeader
    assert verifyPostHeaders(httpPrefix, publicKeyPem, headers,
                             boxpath, False, None,
                             messageBodyJsonStr, False)
    if withDigest:
        # everything correct except for content-length
        headers['content-length'] = str(contentLength + 2)
        assert verifyPostHeaders(httpPrefix, publicKeyPem, headers,
                                 boxpath, False, None,
                                 messageBodyJsonStr, False) is False
    assert verifyPostHeaders(httpPrefix, publicKeyPem, headers,
                             '/parambulator' + boxpath, False, None,
                             messageBodyJsonStr, False) is False
    assert verifyPostHeaders(httpPrefix, publicKeyPem, headers,
                             boxpath, True, None,
                             messageBodyJsonStr, False) is False
    if not withDigest:
        # fake domain
        headers = {
            'host': 'bogon.domain',
            'date': dateStr,
            'content-type': 'application/json'
        }
    else:
        # correct domain but fake message
        messageBodyJsonStr = \
            '{"a key": "a value", "another key": "Fake GNUs", ' + \
            '"yet another key": "More Fake GNUs"}'
        contentLength = len(messageBodyJsonStr)
        bodyDigest = messageContentDigest(messageBodyJsonStr)
        headers = {
            'host': domain,
            'date': dateStr,
            'digest': f'SHA-256={bodyDigest}',
            'content-type': contentType,
            'content-length': str(contentLength)
        }
    headers['signature'] = signatureHeader
    assert verifyPostHeaders(httpPrefix, publicKeyPem, headers,
                             boxpath, True, None,
                             messageBodyJsonStr, False) is False

    os.chdir(baseDir)
    shutil.rmtree(path)


def testHttpsig():
    _testHttpsigBase(True)
    _testHttpsigBase(False)


def testCache():
    print('testCache')
    personUrl = "cat@cardboard.box"
    personJson = {
        "id": 123456,
        "test": "This is a test"
    }
    personCache = {}
    storePersonInCache(None, personUrl, personJson, personCache, True)
    result = getPersonFromCache(None, personUrl, personCache, True)
    assert result['id'] == 123456
    assert result['test'] == 'This is a test'


def testThreadsFunction(param: str):
    for i in range(10000):
        time.sleep(2)


def testThreads():
    print('testThreads')
    thr = \
        threadWithTrace(target=testThreadsFunction,
                        args=('test',),
                        daemon=True)
    thr.start()
    assert thr.is_alive() is True
    time.sleep(1)
    thr.kill()
    thr.join()
    assert thr.is_alive() is False


def createServerAlice(path: str, domain: str, port: int,
                      bobAddress: str, federationList: [],
                      hasFollows: bool, hasPosts: bool,
                      sendThreads: []):
    print('Creating test server: Alice on port ' + str(port))
    if os.path.isdir(path):
        shutil.rmtree(path)
    os.mkdir(path)
    os.chdir(path)
    nickname = 'alice'
    httpPrefix = 'http'
    proxyType = None
    password = 'alicepass'
    maxReplies = 64
    domainMaxPostsPerDay = 1000
    accountMaxPostsPerDay = 1000
    allowDeletion = True
    privateKeyPem, publicKeyPem, person, wfEndpoint = \
        createPerson(path, nickname, domain, port, httpPrefix, True,
                     False, password)
    deleteAllPosts(path, nickname, domain, 'inbox')
    deleteAllPosts(path, nickname, domain, 'outbox')
    assert setSkillLevel(path, nickname, domain, 'hacking', 90)
    assert setRole(path, nickname, domain, 'someproject', 'guru')
    if hasFollows:
        followPerson(path, nickname, domain, 'bob', bobAddress,
                     federationList, False)
        followerOfPerson(path, nickname, domain, 'bob', bobAddress,
                         federationList, False)
    if hasPosts:
        testFollowersOnly = False
        testSaveToFile = True
        clientToServer = False
        testCommentsEnabled = True
        testAttachImageFilename = None
        testMediaType = None
        testImageDescription = None
        createPublicPost(path, nickname, domain, port, httpPrefix,
                         "No wise fish would go anywhere without a porpoise",
                         testFollowersOnly,
                         testSaveToFile,
                         clientToServer,
                         testCommentsEnabled,
                         testAttachImageFilename,
                         testMediaType,
                         testImageDescription)
        createPublicPost(path, nickname, domain, port, httpPrefix,
                         "Curiouser and curiouser!",
                         testFollowersOnly,
                         testSaveToFile,
                         clientToServer,
                         testCommentsEnabled,
                         testAttachImageFilename,
                         testMediaType,
                         testImageDescription)
        createPublicPost(path, nickname, domain, port, httpPrefix,
                         "In the gardens of memory, in the palace " +
                         "of dreams, that is where you and I shall meet",
                         testFollowersOnly,
                         testSaveToFile,
                         clientToServer,
                         testCommentsEnabled,
                         testAttachImageFilename,
                         testMediaType,
                         testImageDescription)
    global testServerAliceRunning
    testServerAliceRunning = True
    maxMentions = 10
    maxEmoji = 10
    onionDomain = None
    i2pDomain = None
    allowLocalNetworkAccess = True
    maxNewswirePosts = 20
    dormantMonths = 3
    sendThreadsTimeoutMins = 30
    maxFollowers = 10
    verifyAllSignatures = True
    print('Server running: Alice')
    runDaemon(verifyAllSignatures,
              sendThreadsTimeoutMins,
              dormantMonths, maxNewswirePosts,
              allowLocalNetworkAccess,
              2048, False, True, False, False, True, maxFollowers,
              0, 100, 1024, 5, False,
              0, False, 1, False, False, False,
              5, True, True, 'en', __version__,
              "instanceId", False, path, domain,
              onionDomain, i2pDomain, None, port, port,
              httpPrefix, federationList, maxMentions, maxEmoji, False,
              proxyType, maxReplies,
              domainMaxPostsPerDay, accountMaxPostsPerDay,
              allowDeletion, True, True, False, sendThreads,
              False)


def createServerBob(path: str, domain: str, port: int,
                    aliceAddress: str, federationList: [],
                    hasFollows: bool, hasPosts: bool,
                    sendThreads: []):
    print('Creating test server: Bob on port ' + str(port))
    if os.path.isdir(path):
        shutil.rmtree(path)
    os.mkdir(path)
    os.chdir(path)
    nickname = 'bob'
    httpPrefix = 'http'
    proxyType = None
    clientToServer = False
    password = 'bobpass'
    maxReplies = 64
    domainMaxPostsPerDay = 1000
    accountMaxPostsPerDay = 1000
    allowDeletion = True
    privateKeyPem, publicKeyPem, person, wfEndpoint = \
        createPerson(path, nickname, domain, port, httpPrefix, True,
                     False, password)
    deleteAllPosts(path, nickname, domain, 'inbox')
    deleteAllPosts(path, nickname, domain, 'outbox')
    assert setRole(path, nickname, domain, 'bandname', 'bass player')
    assert setRole(path, nickname, domain, 'bandname', 'publicist')
    if hasFollows:
        followPerson(path, nickname, domain,
                     'alice', aliceAddress, federationList, False)
        followerOfPerson(path, nickname, domain,
                         'alice', aliceAddress, federationList, False)
    if hasPosts:
        testFollowersOnly = False
        testSaveToFile = True
        testCommentsEnabled = True
        testAttachImageFilename = None
        testImageDescription = None
        testMediaType = None
        createPublicPost(path, nickname, domain, port, httpPrefix,
                         "It's your life, live it your way.",
                         testFollowersOnly,
                         testSaveToFile,
                         clientToServer,
                         testCommentsEnabled,
                         testAttachImageFilename,
                         testMediaType,
                         testImageDescription)
        createPublicPost(path, nickname, domain, port, httpPrefix,
                         "One of the things I've realised is that " +
                         "I am very simple",
                         testFollowersOnly,
                         testSaveToFile,
                         clientToServer,
                         testCommentsEnabled,
                         testAttachImageFilename,
                         testMediaType,
                         testImageDescription)
        createPublicPost(path, nickname, domain, port, httpPrefix,
                         "Quantum physics is a bit of a passion of mine",
                         testFollowersOnly,
                         testSaveToFile,
                         clientToServer,
                         testCommentsEnabled,
                         testAttachImageFilename,
                         testMediaType,
                         testImageDescription)
    global testServerBobRunning
    testServerBobRunning = True
    maxMentions = 10
    maxEmoji = 10
    onionDomain = None
    i2pDomain = None
    allowLocalNetworkAccess = True
    maxNewswirePosts = 20
    dormantMonths = 3
    sendThreadsTimeoutMins = 30
    maxFollowers = 10
    verifyAllSignatures = True
    print('Server running: Bob')
    runDaemon(verifyAllSignatures,
              sendThreadsTimeoutMins,
              dormantMonths, maxNewswirePosts,
              allowLocalNetworkAccess,
              2048, False, True, False, False, True, maxFollowers,
              0, 100, 1024, 5, False, 0,
              False, 1, False, False, False,
              5, True, True, 'en', __version__,
              "instanceId", False, path, domain,
              onionDomain, i2pDomain, None, port, port,
              httpPrefix, federationList, maxMentions, maxEmoji, False,
              proxyType, maxReplies,
              domainMaxPostsPerDay, accountMaxPostsPerDay,
              allowDeletion, True, True, False, sendThreads,
              False)


def createServerEve(path: str, domain: str, port: int, federationList: [],
                    hasFollows: bool, hasPosts: bool,
                    sendThreads: []):
    print('Creating test server: Eve on port ' + str(port))
    if os.path.isdir(path):
        shutil.rmtree(path)
    os.mkdir(path)
    os.chdir(path)
    nickname = 'eve'
    httpPrefix = 'http'
    proxyType = None
    password = 'evepass'
    maxReplies = 64
    allowDeletion = True
    privateKeyPem, publicKeyPem, person, wfEndpoint = \
        createPerson(path, nickname, domain, port, httpPrefix, True,
                     False, password)
    deleteAllPosts(path, nickname, domain, 'inbox')
    deleteAllPosts(path, nickname, domain, 'outbox')
    global testServerEveRunning
    testServerEveRunning = True
    maxMentions = 10
    maxEmoji = 10
    onionDomain = None
    i2pDomain = None
    allowLocalNetworkAccess = True
    maxNewswirePosts = 20
    dormantMonths = 3
    sendThreadsTimeoutMins = 30
    maxFollowers = 10
    verifyAllSignatures = True
    print('Server running: Eve')
    runDaemon(verifyAllSignatures,
              sendThreadsTimeoutMins,
              dormantMonths, maxNewswirePosts,
              allowLocalNetworkAccess,
              2048, False, True, False, False, True, maxFollowers,
              0, 100, 1024, 5, False, 0,
              False, 1, False, False, False,
              5, True, True, 'en', __version__,
              "instanceId", False, path, domain,
              onionDomain, i2pDomain, None, port, port,
              httpPrefix, federationList, maxMentions, maxEmoji, False,
              proxyType, maxReplies, allowDeletion, True, True, False,
              sendThreads, False)


def testPostMessageBetweenServers():
    print('Testing sending message from one server to the inbox of another')

    global testServerAliceRunning
    global testServerBobRunning
    testServerAliceRunning = False
    testServerBobRunning = False

    httpPrefix = 'http'
    proxyType = None

    baseDir = os.getcwd()
    if os.path.isdir(baseDir + '/.tests'):
        shutil.rmtree(baseDir + '/.tests')
    os.mkdir(baseDir + '/.tests')

    # create the servers
    aliceDir = baseDir + '/.tests/alice'
    aliceDomain = '127.0.0.50'
    alicePort = 61935
    aliceAddress = aliceDomain + ':' + str(alicePort)

    bobDir = baseDir + '/.tests/bob'
    bobDomain = '127.0.0.100'
    bobPort = 61936
    federationList = [bobDomain, aliceDomain]
    aliceSendThreads = []
    bobSendThreads = []
    bobAddress = bobDomain + ':' + str(bobPort)

    global thrAlice
    if thrAlice:
        while thrAlice.is_alive():
            thrAlice.stop()
            time.sleep(1)
        thrAlice.kill()

    thrAlice = \
        threadWithTrace(target=createServerAlice,
                        args=(aliceDir, aliceDomain, alicePort, bobAddress,
                              federationList, False, False,
                              aliceSendThreads),
                        daemon=True)

    global thrBob
    if thrBob:
        while thrBob.is_alive():
            thrBob.stop()
            time.sleep(1)
        thrBob.kill()

    thrBob = \
        threadWithTrace(target=createServerBob,
                        args=(bobDir, bobDomain, bobPort, aliceAddress,
                              federationList, False, False,
                              bobSendThreads),
                        daemon=True)

    thrAlice.start()
    thrBob.start()
    assert thrAlice.is_alive() is True
    assert thrBob.is_alive() is True

    # wait for both servers to be running
    while not (testServerAliceRunning and testServerBobRunning):
        time.sleep(1)

    time.sleep(1)

    print('\n\n*******************************************************')
    print('Alice sends to Bob')
    os.chdir(aliceDir)
    sessionAlice = createSession(proxyType)
    inReplyTo = None
    inReplyToAtomUri = None
    subject = None
    alicePostLog = []
    followersOnly = False
    saveToFile = True
    clientToServer = False
    ccUrl = None
    alicePersonCache = {}
    aliceCachedWebfingers = {}
    attachedImageFilename = baseDir + '/img/logo.png'
    mediaType = getAttachmentMediaType(attachedImageFilename)
    attachedImageDescription = 'Logo'
    isArticle = False
    # nothing in Alice's outbox
    outboxPath = aliceDir + '/accounts/alice@' + aliceDomain + '/outbox'
    assert len([name for name in os.listdir(outboxPath)
                if os.path.isfile(os.path.join(outboxPath, name))]) == 0

    sendResult = \
        sendPost(__version__,
                 sessionAlice, aliceDir, 'alice', aliceDomain, alicePort,
                 'bob', bobDomain, bobPort, ccUrl, httpPrefix,
                 'Why is a mouse when it spins? ' +
                 'यह एक परीक्षण है #sillyquestion',
                 followersOnly,
                 saveToFile, clientToServer, True,
                 attachedImageFilename, mediaType,
                 attachedImageDescription, federationList,
                 aliceSendThreads, alicePostLog, aliceCachedWebfingers,
                 alicePersonCache, isArticle, inReplyTo,
                 inReplyToAtomUri, subject)
    print('sendResult: ' + str(sendResult))

    queuePath = bobDir + '/accounts/bob@' + bobDomain + '/queue'
    inboxPath = bobDir + '/accounts/bob@' + bobDomain + '/inbox'
    mPath = getMediaPath()
    mediaPath = aliceDir + '/' + mPath
    for i in range(30):
        if os.path.isdir(inboxPath):
            if len([name for name in os.listdir(inboxPath)
                    if os.path.isfile(os.path.join(inboxPath, name))]) > 0:
                if len([name for name in os.listdir(outboxPath)
                        if os.path.isfile(os.path.join(outboxPath,
                                                       name))]) == 1:
                    if len([name for name in os.listdir(mediaPath)
                            if os.path.isfile(os.path.join(mediaPath,
                                                           name))]) > 0:
                        if len([name for name in os.listdir(queuePath)
                                if os.path.isfile(os.path.join(queuePath,
                                                               name))]) == 0:
                            break
        time.sleep(1)

    # check that a news account exists
    newsActorDir = aliceDir + '/accounts/news@' + aliceDomain
    print("newsActorDir: " + newsActorDir)
    assert os.path.isdir(newsActorDir)
    newsActorFile = newsActorDir + '.json'
    assert os.path.isfile(newsActorFile)
    newsActorJson = loadJson(newsActorFile)
    assert newsActorJson
    assert newsActorJson.get("id")
    # check the id of the news actor
    print('News actor Id: ' + newsActorJson["id"])
    assert (newsActorJson["id"] ==
            httpPrefix + '://' + aliceAddress + '/users/news')

    # Image attachment created
    assert len([name for name in os.listdir(mediaPath)
                if os.path.isfile(os.path.join(mediaPath, name))]) > 0
    # inbox item created
    assert len([name for name in os.listdir(inboxPath)
                if os.path.isfile(os.path.join(inboxPath, name))]) == 1
    # queue item removed
    testval = len([name for name in os.listdir(queuePath)
                   if os.path.isfile(os.path.join(queuePath, name))])
    print('queuePath: ' + queuePath + ' '+str(testval))
    assert testval == 0
    assert validInbox(bobDir, 'bob', bobDomain)
    assert validInboxFilenames(bobDir, 'bob', bobDomain,
                               aliceDomain, alicePort)
    print('Check that message received from Alice contains the expected text')
    for name in os.listdir(inboxPath):
        filename = os.path.join(inboxPath, name)
        assert os.path.isfile(filename)
        receivedJson = loadJson(filename, 0)
        if receivedJson:
            pprint(receivedJson['object']['content'])
        assert receivedJson
        assert 'Why is a mouse when it spins?' in \
            receivedJson['object']['content']
        assert 'यह एक परीक्षण है' in receivedJson['object']['content']

    print('\n\n*******************************************************')
    print("Bob likes Alice's post")

    aliceDomainStr = aliceDomain + ':' + str(alicePort)
    followerOfPerson(bobDir, 'bob', bobDomain, 'alice',
                     aliceDomainStr, federationList, False)
    bobDomainStr = bobDomain + ':' + str(bobPort)
    followPerson(aliceDir, 'alice', aliceDomain, 'bob',
                 bobDomainStr, federationList, False)

    sessionBob = createSession(proxyType)
    bobPostLog = []
    bobPersonCache = {}
    bobCachedWebfingers = {}
    statusNumber = None
    outboxPostFilename = None
    outboxPath = aliceDir + '/accounts/alice@' + aliceDomain + '/outbox'
    for name in os.listdir(outboxPath):
        if '#statuses#' in name:
            statusNumber = \
                int(name.split('#statuses#')[1].replace('.json', ''))
            outboxPostFilename = outboxPath + '/' + name
    assert statusNumber > 0
    assert outboxPostFilename
    assert likePost({}, sessionBob, bobDir, federationList,
                    'bob', bobDomain, bobPort, httpPrefix,
                    'alice', aliceDomain, alicePort, [],
                    statusNumber, False, bobSendThreads, bobPostLog,
                    bobPersonCache, bobCachedWebfingers,
                    True, __version__)

    for i in range(20):
        if 'likes' in open(outboxPostFilename).read():
            break
        time.sleep(1)

    alicePostJson = loadJson(outboxPostFilename, 0)
    if alicePostJson:
        pprint(alicePostJson)

    assert 'likes' in open(outboxPostFilename).read()

    print('\n\n*******************************************************')
    print("Bob repeats Alice's post")
    objectUrl = \
        httpPrefix + '://' + aliceDomain + ':' + str(alicePort) + \
        '/users/alice/statuses/' + str(statusNumber)
    inboxPath = aliceDir + '/accounts/alice@' + aliceDomain + '/inbox'
    outboxPath = bobDir + '/accounts/bob@' + bobDomain + '/outbox'
    outboxBeforeAnnounceCount = \
        len([name for name in os.listdir(outboxPath)
             if os.path.isfile(os.path.join(outboxPath, name))])
    beforeAnnounceCount = \
        len([name for name in os.listdir(inboxPath)
             if os.path.isfile(os.path.join(inboxPath, name))])
    print('inbox items before announce: ' + str(beforeAnnounceCount))
    print('outbox items before announce: ' + str(outboxBeforeAnnounceCount))
    assert outboxBeforeAnnounceCount == 0
    assert beforeAnnounceCount == 0
    announcePublic(sessionBob, bobDir, federationList,
                   'bob', bobDomain, bobPort, httpPrefix,
                   objectUrl,
                   False, bobSendThreads, bobPostLog,
                   bobPersonCache, bobCachedWebfingers,
                   True, __version__)
    announceMessageArrived = False
    outboxMessageArrived = False
    for i in range(10):
        time.sleep(1)
        if not os.path.isdir(inboxPath):
            continue
        if len([name for name in os.listdir(outboxPath)
                if os.path.isfile(os.path.join(outboxPath, name))]) > 0:
            outboxMessageArrived = True
            print('Announce created by Bob')
        if len([name for name in os.listdir(inboxPath)
                if os.path.isfile(os.path.join(inboxPath, name))]) > 0:
            announceMessageArrived = True
            print('Announce message sent to Alice!')
        if announceMessageArrived and outboxMessageArrived:
            break
    afterAnnounceCount = \
        len([name for name in os.listdir(inboxPath)
             if os.path.isfile(os.path.join(inboxPath, name))])
    outboxAfterAnnounceCount = \
        len([name for name in os.listdir(outboxPath)
             if os.path.isfile(os.path.join(outboxPath, name))])
    print('inbox items after announce: ' + str(afterAnnounceCount))
    print('outbox items after announce: ' + str(outboxAfterAnnounceCount))
    assert afterAnnounceCount == beforeAnnounceCount+1
    assert outboxAfterAnnounceCount == outboxBeforeAnnounceCount + 1
    # stop the servers
    thrAlice.kill()
    thrAlice.join()
    assert thrAlice.is_alive() is False

    thrBob.kill()
    thrBob.join()
    assert thrBob.is_alive() is False

    os.chdir(baseDir)
    shutil.rmtree(aliceDir)
    shutil.rmtree(bobDir)


def testFollowBetweenServers():
    print('Testing sending a follow request from one server to another')

    global testServerAliceRunning
    global testServerBobRunning
    testServerAliceRunning = False
    testServerBobRunning = False

    httpPrefix = 'http'
    proxyType = None
    federationList = []

    baseDir = os.getcwd()
    if os.path.isdir(baseDir + '/.tests'):
        shutil.rmtree(baseDir + '/.tests')
    os.mkdir(baseDir + '/.tests')

    # create the servers
    aliceDir = baseDir + '/.tests/alice'
    aliceDomain = '127.0.0.47'
    alicePort = 61935
    aliceSendThreads = []
    aliceAddress = aliceDomain + ':' + str(alicePort)

    bobDir = baseDir + '/.tests/bob'
    bobDomain = '127.0.0.79'
    bobPort = 61936
    bobSendThreads = []
    bobAddress = bobDomain + ':' + str(bobPort)

    global thrAlice
    if thrAlice:
        while thrAlice.is_alive():
            thrAlice.stop()
            time.sleep(1)
        thrAlice.kill()

    thrAlice = \
        threadWithTrace(target=createServerAlice,
                        args=(aliceDir, aliceDomain, alicePort, bobAddress,
                              federationList, False, False,
                              aliceSendThreads),
                        daemon=True)

    global thrBob
    if thrBob:
        while thrBob.is_alive():
            thrBob.stop()
            time.sleep(1)
        thrBob.kill()

    thrBob = \
        threadWithTrace(target=createServerBob,
                        args=(bobDir, bobDomain, bobPort, aliceAddress,
                              federationList, False, False,
                              bobSendThreads),
                        daemon=True)

    thrAlice.start()
    thrBob.start()
    assert thrAlice.is_alive() is True
    assert thrBob.is_alive() is True

    # wait for all servers to be running
    ctr = 0
    while not (testServerAliceRunning and testServerBobRunning):
        time.sleep(1)
        ctr += 1
        if ctr > 60:
            break
    print('Alice online: ' + str(testServerAliceRunning))
    print('Bob online: ' + str(testServerBobRunning))
    assert ctr <= 60
    time.sleep(1)

    # In the beginning all was calm and there were no follows

    print('*********************************************************')
    print('Alice sends a follow request to Bob')
    os.chdir(aliceDir)
    sessionAlice = createSession(proxyType)
    inReplyTo = None
    inReplyToAtomUri = None
    subject = None
    alicePostLog = []
    followersOnly = False
    saveToFile = True
    clientToServer = False
    ccUrl = None
    alicePersonCache = {}
    aliceCachedWebfingers = {}
    alicePostLog = []
    sendResult = \
        sendFollowRequest(sessionAlice, aliceDir,
                          'alice', aliceDomain, alicePort, httpPrefix,
                          'bob', bobDomain, bobPort, httpPrefix,
                          clientToServer, federationList,
                          aliceSendThreads, alicePostLog,
                          aliceCachedWebfingers, alicePersonCache,
                          True, __version__)
    print('sendResult: ' + str(sendResult))

    for t in range(16):
        if os.path.isfile(bobDir + '/accounts/bob@' +
                          bobDomain + '/followers.txt'):
            if os.path.isfile(aliceDir + '/accounts/alice@' +
                              aliceDomain + '/following.txt'):
                if os.path.isfile(aliceDir + '/accounts/alice@' +
                                  aliceDomain + '/followingCalendar.txt'):
                    break
        time.sleep(1)

    assert validInbox(bobDir, 'bob', bobDomain)
    assert validInboxFilenames(bobDir, 'bob', bobDomain,
                               aliceDomain, alicePort)
    assert 'alice@' + aliceDomain in open(bobDir + '/accounts/bob@' +
                                          bobDomain + '/followers.txt').read()
    assert 'bob@' + bobDomain in open(aliceDir + '/accounts/alice@' +
                                      aliceDomain + '/following.txt').read()
    assert 'bob@' + bobDomain in open(aliceDir + '/accounts/alice@' +
                                      aliceDomain +
                                      '/followingCalendar.txt').read()

    print('\n\n*********************************************************')
    print('Alice sends a message to Bob')
    alicePostLog = []
    alicePersonCache = {}
    aliceCachedWebfingers = {}
    alicePostLog = []
    isArticle = False
    sendResult = \
        sendPost(__version__,
                 sessionAlice, aliceDir, 'alice', aliceDomain, alicePort,
                 'bob', bobDomain, bobPort, ccUrl,
                 httpPrefix, 'Alice message', followersOnly, saveToFile,
                 clientToServer, True,
                 None, None, None, federationList,
                 aliceSendThreads, alicePostLog, aliceCachedWebfingers,
                 alicePersonCache, isArticle, inReplyTo,
                 inReplyToAtomUri, subject)
    print('sendResult: ' + str(sendResult))

    queuePath = bobDir + '/accounts/bob@' + bobDomain + '/queue'
    inboxPath = bobDir + '/accounts/bob@' + bobDomain + '/inbox'
    aliceMessageArrived = False
    for i in range(20):
        time.sleep(1)
        if os.path.isdir(inboxPath):
            if len([name for name in os.listdir(inboxPath)
                    if os.path.isfile(os.path.join(inboxPath, name))]) > 0:
                aliceMessageArrived = True
                print('Alice message sent to Bob!')
                break

    assert aliceMessageArrived is True
    print('Message from Alice to Bob succeeded')

    # stop the servers
    thrAlice.kill()
    thrAlice.join()
    assert thrAlice.is_alive() is False

    thrBob.kill()
    thrBob.join()
    assert thrBob.is_alive() is False

    # queue item removed
    time.sleep(4)
    assert len([name for name in os.listdir(queuePath)
                if os.path.isfile(os.path.join(queuePath, name))]) == 0

    os.chdir(baseDir)
    shutil.rmtree(baseDir + '/.tests')


def testFollowersOfPerson():
    print('testFollowersOfPerson')
    currDir = os.getcwd()
    nickname = 'mxpop'
    domain = 'diva.domain'
    password = 'birb'
    port = 80
    httpPrefix = 'https'
    federationList = []
    baseDir = currDir + '/.tests_followersofperson'
    if os.path.isdir(baseDir):
        shutil.rmtree(baseDir)
    os.mkdir(baseDir)
    os.chdir(baseDir)
    createPerson(baseDir, nickname, domain, port,
                 httpPrefix, True, False, password)
    createPerson(baseDir, 'maxboardroom', domain, port,
                 httpPrefix, True, False, password)
    createPerson(baseDir, 'ultrapancake', domain, port,
                 httpPrefix, True, False, password)
    createPerson(baseDir, 'drokk', domain, port,
                 httpPrefix, True, False, password)
    createPerson(baseDir, 'sausagedog', domain, port,
                 httpPrefix, True, False, password)

    clearFollows(baseDir, nickname, domain)
    followPerson(baseDir, nickname, domain, 'maxboardroom', domain,
                 federationList, False)
    followPerson(baseDir, 'drokk', domain, 'ultrapancake', domain,
                 federationList, False)
    # deliberate duplication
    followPerson(baseDir, 'drokk', domain, 'ultrapancake', domain,
                 federationList, False)
    followPerson(baseDir, 'sausagedog', domain, 'ultrapancake', domain,
                 federationList, False)
    followPerson(baseDir, nickname, domain, 'ultrapancake', domain,
                 federationList, False)
    followPerson(baseDir, nickname, domain, 'someother', 'randodomain.net',
                 federationList, False)

    followList = getFollowersOfPerson(baseDir, 'ultrapancake', domain)
    assert len(followList) == 3
    assert 'mxpop@' + domain in followList
    assert 'drokk@' + domain in followList
    assert 'sausagedog@' + domain in followList
    os.chdir(currDir)
    shutil.rmtree(baseDir)


def testNoOfFollowersOnDomain():
    print('testNoOfFollowersOnDomain')
    currDir = os.getcwd()
    nickname = 'mxpop'
    domain = 'diva.domain'
    otherdomain = 'soup.dragon'
    password = 'birb'
    port = 80
    httpPrefix = 'https'
    federationList = []
    baseDir = currDir + '/.tests_nooffollowersOndomain'
    if os.path.isdir(baseDir):
        shutil.rmtree(baseDir)
    os.mkdir(baseDir)
    os.chdir(baseDir)
    createPerson(baseDir, nickname, domain, port, httpPrefix, True,
                 False, password)
    createPerson(baseDir, 'maxboardroom', otherdomain, port,
                 httpPrefix, True, False, password)
    createPerson(baseDir, 'ultrapancake', otherdomain, port,
                 httpPrefix, True, False, password)
    createPerson(baseDir, 'drokk', otherdomain, port,
                 httpPrefix, True, False, password)
    createPerson(baseDir, 'sausagedog', otherdomain, port,
                 httpPrefix, True, False, password)

    followPerson(baseDir, 'drokk', otherdomain, nickname, domain,
                 federationList, False)
    followPerson(baseDir, 'sausagedog', otherdomain, nickname, domain,
                 federationList, False)
    followPerson(baseDir, 'maxboardroom', otherdomain, nickname, domain,
                 federationList, False)

    followerOfPerson(baseDir, nickname, domain,
                     'cucumber', 'sandwiches.party',
                     federationList, False)
    followerOfPerson(baseDir, nickname, domain,
                     'captainsensible', 'damned.zone',
                     federationList, False)
    followerOfPerson(baseDir, nickname, domain, 'pilchard', 'zombies.attack',
                     federationList, False)
    followerOfPerson(baseDir, nickname, domain, 'drokk', otherdomain,
                     federationList, False)
    followerOfPerson(baseDir, nickname, domain, 'sausagedog', otherdomain,
                     federationList, False)
    followerOfPerson(baseDir, nickname, domain, 'maxboardroom', otherdomain,
                     federationList, False)

    followersOnOtherDomain = \
        noOfFollowersOnDomain(baseDir, nickname + '@' + domain, otherdomain)
    assert followersOnOtherDomain == 3

    unfollowerOfAccount(baseDir, nickname, domain, 'sausagedog', otherdomain)
    followersOnOtherDomain = \
        noOfFollowersOnDomain(baseDir, nickname + '@' + domain, otherdomain)
    assert followersOnOtherDomain == 2

    os.chdir(currDir)
    shutil.rmtree(baseDir)


def testGroupFollowers():
    print('testGroupFollowers')

    currDir = os.getcwd()
    nickname = 'test735'
    domain = 'mydomain.com'
    password = 'somepass'
    port = 80
    httpPrefix = 'https'
    federationList = []
    baseDir = currDir + '/.tests_testgroupfollowers'
    if os.path.isdir(baseDir):
        shutil.rmtree(baseDir)
    os.mkdir(baseDir)
    os.chdir(baseDir)
    createPerson(baseDir, nickname, domain, port, httpPrefix, True,
                 False, password)

    clearFollowers(baseDir, nickname, domain)
    followerOfPerson(baseDir, nickname, domain, 'badger', 'wild.domain',
                     federationList, False)
    followerOfPerson(baseDir, nickname, domain, 'squirrel', 'wild.domain',
                     federationList, False)
    followerOfPerson(baseDir, nickname, domain, 'rodent', 'wild.domain',
                     federationList, False)
    followerOfPerson(baseDir, nickname, domain, 'utterly', 'clutterly.domain',
                     federationList, False)
    followerOfPerson(baseDir, nickname, domain, 'zonked', 'zzz.domain',
                     federationList, False)
    followerOfPerson(baseDir, nickname, domain, 'nap', 'zzz.domain',
                     federationList, False)

    grouped = groupFollowersByDomain(baseDir, nickname, domain)
    assert len(grouped.items()) == 3
    assert grouped.get('zzz.domain')
    assert grouped.get('clutterly.domain')
    assert grouped.get('wild.domain')
    assert len(grouped['zzz.domain']) == 2
    assert len(grouped['wild.domain']) == 3
    assert len(grouped['clutterly.domain']) == 1

    os.chdir(currDir)
    shutil.rmtree(baseDir)


def testFollows():
    print('testFollows')
    currDir = os.getcwd()
    nickname = 'test529'
    domain = 'testdomain.com'
    password = 'mypass'
    port = 80
    httpPrefix = 'https'
    federationList = ['wild.com', 'mesh.com']
    baseDir = currDir + '/.tests_testfollows'
    if os.path.isdir(baseDir):
        shutil.rmtree(baseDir)
    os.mkdir(baseDir)
    os.chdir(baseDir)
    createPerson(baseDir, nickname, domain, port, httpPrefix, True,
                 False, password)

    clearFollows(baseDir, nickname, domain)
    followPerson(baseDir, nickname, domain, 'badger', 'wild.com',
                 federationList, False)
    followPerson(baseDir, nickname, domain, 'squirrel', 'secret.com',
                 federationList, False)
    followPerson(baseDir, nickname, domain, 'rodent', 'drainpipe.com',
                 federationList, False)
    followPerson(baseDir, nickname, domain, 'batman', 'mesh.com',
                 federationList, False)
    followPerson(baseDir, nickname, domain, 'giraffe', 'trees.com',
                 federationList, False)

    f = open(baseDir + '/accounts/' + nickname + '@' + domain +
             '/following.txt', "r")
    domainFound = False
    for followingDomain in f:
        testDomain = followingDomain.split('@')[1]
        testDomain = testDomain.replace('\n', '').replace('\r', '')
        if testDomain == 'mesh.com':
            domainFound = True
        if testDomain not in federationList:
            print(testDomain)
            assert(False)

    assert(domainFound)
    unfollowAccount(baseDir, nickname, domain, 'batman', 'mesh.com')

    domainFound = False
    for followingDomain in f:
        testDomain = followingDomain.split('@')[1]
        testDomain = testDomain.replace('\n', '').replace('\r', '')
        if testDomain == 'mesh.com':
            domainFound = True
    assert(domainFound is False)

    clearFollowers(baseDir, nickname, domain)
    followerOfPerson(baseDir, nickname, domain, 'badger', 'wild.com',
                     federationList, False)
    followerOfPerson(baseDir, nickname, domain, 'squirrel', 'secret.com',
                     federationList, False)
    followerOfPerson(baseDir, nickname, domain, 'rodent', 'drainpipe.com',
                     federationList, False)
    followerOfPerson(baseDir, nickname, domain, 'batman', 'mesh.com',
                     federationList, False)
    followerOfPerson(baseDir, nickname, domain, 'giraffe', 'trees.com',
                     federationList, False)

    f = open(baseDir + '/accounts/' + nickname + '@' + domain +
             '/followers.txt', "r")
    for followerDomain in f:
        testDomain = followerDomain.split('@')[1]
        testDomain = testDomain.replace('\n', '').replace('\r', '')
        if testDomain not in federationList:
            print(testDomain)
            assert(False)

    os.chdir(currDir)
    shutil.rmtree(baseDir)


def testCreatePerson():
    print('testCreatePerson')
    currDir = os.getcwd()
    nickname = 'test382'
    domain = 'badgerdomain.com'
    password = 'mypass'
    port = 80
    httpPrefix = 'https'
    clientToServer = False
    baseDir = currDir + '/.tests_createperson'
    if os.path.isdir(baseDir):
        shutil.rmtree(baseDir)
    os.mkdir(baseDir)
    os.chdir(baseDir)

    privateKeyPem, publicKeyPem, person, wfEndpoint = \
        createPerson(baseDir, nickname, domain, port,
                     httpPrefix, True, False, password)
    assert os.path.isfile(baseDir + '/accounts/passwords')
    deleteAllPosts(baseDir, nickname, domain, 'inbox')
    deleteAllPosts(baseDir, nickname, domain, 'outbox')
    setDisplayNickname(baseDir, nickname, domain, 'badger')
    setBio(baseDir, nickname, domain, 'Randomly roaming in your backyard')
    archivePostsForPerson(nickname, domain, baseDir, 'inbox', None, {}, 4)
    archivePostsForPerson(nickname, domain, baseDir, 'outbox', None, {}, 4)
    createPublicPost(baseDir, nickname, domain, port, httpPrefix,
                     "G'day world!", False, True, clientToServer,
                     True, None, None, None, None,
                     'Not suitable for Vogons')

    os.chdir(currDir)
    shutil.rmtree(baseDir)


def testDelegateRoles():
    print('testDelegateRoles')
    currDir = os.getcwd()
    nickname = 'test382'
    nicknameDelegated = 'test383'
    domain = 'badgerdomain.com'
    password = 'mypass'
    port = 80
    httpPrefix = 'https'
    baseDir = currDir + '/.tests_delegaterole'
    if os.path.isdir(baseDir):
        shutil.rmtree(baseDir)
    os.mkdir(baseDir)
    os.chdir(baseDir)

    privateKeyPem, publicKeyPem, person, wfEndpoint = \
        createPerson(baseDir, nickname, domain, port,
                     httpPrefix, True, False, password)
    privateKeyPem, publicKeyPem, person, wfEndpoint = \
        createPerson(baseDir, nicknameDelegated, domain, port,
                     httpPrefix, True, False, 'insecure')

    httpPrefix = 'http'
    project = 'artechoke'
    role = 'delegator'
    actorDelegated = \
        httpPrefix + '://' + domain + '/users/' + nicknameDelegated
    newRoleJson = {
        'type': 'Delegate',
        'actor': httpPrefix + '://' + domain + '/users/' + nickname,
        'object': {
            'type': 'Role',
            'actor': actorDelegated,
            'object': project + ';' + role,
            'to': [],
            'cc': []
        },
        'to': [],
        'cc': []
    }

    assert outboxDelegate(baseDir, nickname, newRoleJson, False)
    # second time delegation has already happened so should return false
    assert outboxDelegate(baseDir, nickname, newRoleJson, False) is False

    assert '"delegator"' in open(baseDir + '/accounts/' + nickname +
                                 '@' + domain + '.json').read()
    assert '"delegator"' in open(baseDir + '/accounts/' + nicknameDelegated +
                                 '@' + domain + '.json').read()

    newRoleJson = {
        'type': 'Delegate',
        'actor': httpPrefix + '://' + domain + '/users/' + nicknameDelegated,
        'object': {
            'type': 'Role',
            'actor': httpPrefix + '://' + domain + '/users/' + nickname,
            'object': 'otherproject;otherrole',
            'to': [],
            'cc': []
        },
        'to': [],
        'cc': []
    }

    # non-delegators cannot assign roles
    assert outboxDelegate(baseDir, nicknameDelegated,
                          newRoleJson, False) is False
    assert '"otherrole"' not in open(baseDir + '/accounts/' +
                                     nickname + '@' + domain + '.json').read()

    os.chdir(currDir)
    shutil.rmtree(baseDir)


def testAuthentication():
    print('testAuthentication')
    currDir = os.getcwd()
    nickname = 'test8743'
    password = 'SuperSecretPassword12345'

    baseDir = currDir + '/.tests_authentication'
    if os.path.isdir(baseDir):
        shutil.rmtree(baseDir)
    os.mkdir(baseDir)
    os.chdir(baseDir)

    assert storeBasicCredentials(baseDir, 'othernick', 'otherpass')
    assert storeBasicCredentials(baseDir, 'bad:nick', 'otherpass') is False
    assert storeBasicCredentials(baseDir, 'badnick', 'otherpa:ss') is False
    assert storeBasicCredentials(baseDir, nickname, password)

    authHeader = createBasicAuthHeader(nickname, password)
    assert authorizeBasic(baseDir, '/users/' + nickname + '/inbox',
                          authHeader, False)
    assert authorizeBasic(baseDir, '/users/' + nickname,
                          authHeader, False) is False
    assert authorizeBasic(baseDir, '/users/othernick/inbox',
                          authHeader, False) is False

    authHeader = createBasicAuthHeader(nickname, password + '1')
    assert authorizeBasic(baseDir, '/users/' + nickname + '/inbox',
                          authHeader, False) is False

    password = 'someOtherPassword'
    assert storeBasicCredentials(baseDir, nickname, password)

    authHeader = createBasicAuthHeader(nickname, password)
    assert authorizeBasic(baseDir, '/users/' + nickname + '/inbox',
                          authHeader, False)

    os.chdir(currDir)
    shutil.rmtree(baseDir)


def testClientToServer():
    print('Testing sending a post via c2s')

    global testServerAliceRunning
    global testServerBobRunning
    testServerAliceRunning = False
    testServerBobRunning = False

    httpPrefix = 'http'
    proxyType = None
    federationList = []

    baseDir = os.getcwd()
    if os.path.isdir(baseDir + '/.tests'):
        shutil.rmtree(baseDir + '/.tests')
    os.mkdir(baseDir + '/.tests')

    # create the servers
    aliceDir = baseDir + '/.tests/alice'
    aliceDomain = '127.0.0.42'
    alicePort = 61935
    aliceSendThreads = []
    aliceAddress = aliceDomain + ':' + str(alicePort)

    bobDir = baseDir + '/.tests/bob'
    bobDomain = '127.0.0.64'
    bobPort = 61936
    bobSendThreads = []
    bobAddress = bobDomain + ':' + str(bobPort)

    global thrAlice
    if thrAlice:
        while thrAlice.is_alive():
            thrAlice.stop()
            time.sleep(1)
        thrAlice.kill()

    thrAlice = \
        threadWithTrace(target=createServerAlice,
                        args=(aliceDir, aliceDomain, alicePort, bobAddress,
                              federationList, False, False,
                              aliceSendThreads),
                        daemon=True)

    global thrBob
    if thrBob:
        while thrBob.is_alive():
            thrBob.stop()
            time.sleep(1)
        thrBob.kill()

    thrBob = \
        threadWithTrace(target=createServerBob,
                        args=(bobDir, bobDomain, bobPort, aliceAddress,
                              federationList, False, False,
                              bobSendThreads),
                        daemon=True)

    thrAlice.start()
    thrBob.start()
    assert thrAlice.is_alive() is True
    assert thrBob.is_alive() is True

    # wait for both servers to be running
    ctr = 0
    while not (testServerAliceRunning and testServerBobRunning):
        time.sleep(1)
        ctr += 1
        if ctr > 60:
            break
    print('Alice online: ' + str(testServerAliceRunning))
    print('Bob online: ' + str(testServerBobRunning))

    time.sleep(1)

    print('\n\n*******************************************************')
    print('Alice sends to Bob via c2s')

    sessionAlice = createSession(proxyType)
    followersOnly = False
    attachedImageFilename = baseDir+'/img/logo.png'
    mediaType = getAttachmentMediaType(attachedImageFilename)
    attachedImageDescription = 'Logo'
    isArticle = False
    cachedWebfingers = {}
    personCache = {}
    password = 'alicepass'
    outboxPath = aliceDir + '/accounts/alice@' + aliceDomain + '/outbox'
    inboxPath = bobDir + '/accounts/bob@' + bobDomain + '/inbox'
    assert len([name for name in os.listdir(outboxPath)
                if os.path.isfile(os.path.join(outboxPath, name))]) == 0
    assert len([name for name in os.listdir(inboxPath)
                if os.path.isfile(os.path.join(inboxPath, name))]) == 0
    sendResult = \
        sendPostViaServer(__version__,
                          aliceDir, sessionAlice, 'alice', password,
                          aliceDomain, alicePort,
                          'bob', bobDomain, bobPort, None,
                          httpPrefix, 'Sent from my ActivityPub client',
                          followersOnly, True,
                          attachedImageFilename, mediaType,
                          attachedImageDescription,
                          cachedWebfingers, personCache, isArticle,
                          True, None, None, None)
    print('sendResult: ' + str(sendResult))

    for i in range(30):
        if os.path.isdir(outboxPath):
            if len([name for name in os.listdir(outboxPath)
                    if os.path.isfile(os.path.join(outboxPath, name))]) == 1:
                break
        time.sleep(1)

    assert len([name for name in os.listdir(outboxPath)
                if os.path.isfile(os.path.join(outboxPath, name))]) == 1
    print(">>> c2s post arrived in Alice's outbox")

    for i in range(30):
        if os.path.isdir(inboxPath):
            if len([name for name in os.listdir(inboxPath)
                    if os.path.isfile(os.path.join(inboxPath, name))]) == 1:
                break
        time.sleep(1)

    assert len([name for name in os.listdir(inboxPath)
                if os.path.isfile(os.path.join(inboxPath, name))]) == 1
    print(">>> s2s post arrived in Bob's inbox")
    print("c2s send success")

    print('\n\nGetting message id for the post')
    statusNumber = 0
    outboxPostFilename = None
    outboxPostId = None
    for name in os.listdir(outboxPath):
        if '#statuses#' in name:
            statusNumber = name.split('#statuses#')[1].replace('.json', '')
            statusNumber = int(statusNumber.replace('#activity', ''))
            outboxPostFilename = outboxPath + '/' + name
            postJsonObject = loadJson(outboxPostFilename, 0)
            if postJsonObject:
                outboxPostId = removeIdEnding(postJsonObject['id'])
    assert outboxPostId
    print('message id obtained: ' + outboxPostId)
    assert validInbox(bobDir, 'bob', bobDomain)
    assert validInboxFilenames(bobDir, 'bob', bobDomain,
                               aliceDomain, alicePort)

    print('\n\nAlice follows Bob')
    sendFollowRequestViaServer(aliceDir, sessionAlice,
                               'alice', password,
                               aliceDomain, alicePort,
                               'bob', bobDomain, bobPort,
                               httpPrefix,
                               cachedWebfingers, personCache,
                               True, __version__)
    alicePetnamesFilename = aliceDir + '/accounts/' + \
        'alice@' + aliceDomain + '/petnames.txt'
    aliceFollowingFilename = \
        aliceDir + '/accounts/alice@' + aliceDomain + '/following.txt'
    bobFollowersFilename = \
        bobDir + '/accounts/bob@' + bobDomain + '/followers.txt'
    for t in range(10):
        if os.path.isfile(bobFollowersFilename):
            if 'alice@' + aliceDomain + ':' + str(alicePort) in \
               open(bobFollowersFilename).read():
                if os.path.isfile(aliceFollowingFilename) and \
                   os.path.isfile(alicePetnamesFilename):
                    if 'bob@' + bobDomain + ':' + str(bobPort) in \
                       open(aliceFollowingFilename).read():
                        break
        time.sleep(1)

    assert os.path.isfile(bobFollowersFilename)
    assert os.path.isfile(aliceFollowingFilename)
    assert os.path.isfile(alicePetnamesFilename)
    assert 'bob bob@' + bobDomain in \
        open(alicePetnamesFilename).read()
    print('alice@' + aliceDomain + ':' + str(alicePort) + ' in ' +
          bobFollowersFilename)
    assert 'alice@' + aliceDomain + ':' + str(alicePort) in \
        open(bobFollowersFilename).read()
    print('bob@' + bobDomain + ':' + str(bobPort) + ' in ' +
          aliceFollowingFilename)
    assert 'bob@' + bobDomain + ':' + str(bobPort) in \
        open(aliceFollowingFilename).read()
    assert validInbox(bobDir, 'bob', bobDomain)
    assert validInboxFilenames(bobDir, 'bob', bobDomain,
                               aliceDomain, alicePort)

    print('\n\nBob follows Alice')
    sendFollowRequestViaServer(aliceDir, sessionAlice,
                               'bob', 'bobpass',
                               bobDomain, bobPort,
                               'alice', aliceDomain, alicePort,
                               httpPrefix,
                               cachedWebfingers, personCache,
                               True, __version__)
    for t in range(10):
        if os.path.isfile(aliceDir + '/accounts/alice@' + aliceDomain +
                          '/followers.txt'):
            if 'bob@' + bobDomain + ':' + str(bobPort) in \
               open(aliceDir + '/accounts/alice@' + aliceDomain +
                    '/followers.txt').read():
                if os.path.isfile(bobDir + '/accounts/bob@' + bobDomain +
                                  '/following.txt'):
                    aliceHandleStr = \
                        'alice@' + aliceDomain + ':' + str(alicePort)
                    if aliceHandleStr in \
                       open(bobDir + '/accounts/bob@' + bobDomain +
                            '/following.txt').read():
                        if os.path.isfile(bobDir + '/accounts/bob@' +
                                          bobDomain +
                                          '/followingCalendar.txt'):
                            if aliceHandleStr in \
                               open(bobDir + '/accounts/bob@' + bobDomain +
                                    '/followingCalendar.txt').read():
                                break
        time.sleep(1)

    assert os.path.isfile(aliceDir + '/accounts/alice@' + aliceDomain +
                          '/followers.txt')
    assert os.path.isfile(bobDir + '/accounts/bob@' + bobDomain +
                          '/following.txt')
    assert 'bob@' + bobDomain + ':' + str(bobPort) in \
        open(aliceDir + '/accounts/alice@' + aliceDomain +
             '/followers.txt').read()
    assert 'alice@' + aliceDomain + ':' + str(alicePort) in \
        open(bobDir + '/accounts/bob@' + bobDomain + '/following.txt').read()

    print('\n\nBob likes the post')
    sessionBob = createSession(proxyType)
    password = 'bobpass'
    outboxPath = bobDir + '/accounts/bob@' + bobDomain + '/outbox'
    inboxPath = aliceDir + '/accounts/alice@' + aliceDomain + '/inbox'
    print(str(len([name for name in os.listdir(outboxPath)
                   if os.path.isfile(os.path.join(outboxPath, name))])))
    assert len([name for name in os.listdir(outboxPath)
                if os.path.isfile(os.path.join(outboxPath, name))]) == 1
    print(str(len([name for name in os.listdir(inboxPath)
                   if os.path.isfile(os.path.join(inboxPath, name))])))
    assert len([name for name in os.listdir(inboxPath)
                if os.path.isfile(os.path.join(inboxPath, name))]) == 1
    sendLikeViaServer(bobDir, sessionBob,
                      'bob', 'bobpass',
                      bobDomain, bobPort,
                      httpPrefix, outboxPostId,
                      cachedWebfingers, personCache,
                      True, __version__)
    for i in range(20):
        if os.path.isdir(outboxPath) and os.path.isdir(inboxPath):
            if len([name for name in os.listdir(outboxPath)
                    if os.path.isfile(os.path.join(outboxPath, name))]) == 2:
                test = len([name for name in os.listdir(inboxPath)
                            if os.path.isfile(os.path.join(inboxPath, name))])
                if test == 1:
                    break
        time.sleep(1)
    assert len([name for name in os.listdir(outboxPath)
                if os.path.isfile(os.path.join(outboxPath, name))]) == 2
    assert len([name for name in os.listdir(inboxPath)
                if os.path.isfile(os.path.join(inboxPath, name))]) == 1
    print('Post liked')

    print('\n\nBob repeats the post')
    print(str(len([name for name in os.listdir(outboxPath)
                   if os.path.isfile(os.path.join(outboxPath, name))])))
    assert len([name for name in os.listdir(outboxPath)
                if os.path.isfile(os.path.join(outboxPath, name))]) == 2
    print(str(len([name for name in os.listdir(inboxPath)
                   if os.path.isfile(os.path.join(inboxPath, name))])))
    assert len([name for name in os.listdir(inboxPath)
                if os.path.isfile(os.path.join(inboxPath, name))]) == 1
    sendAnnounceViaServer(bobDir, sessionBob, 'bob', password,
                          bobDomain, bobPort,
                          httpPrefix, outboxPostId,
                          cachedWebfingers,
                          personCache, True, __version__)
    for i in range(20):
        if os.path.isdir(outboxPath) and os.path.isdir(inboxPath):
            if len([name for name in os.listdir(outboxPath)
                    if os.path.isfile(os.path.join(outboxPath, name))]) == 3:
                if len([name for name in os.listdir(inboxPath)
                        if os.path.isfile(os.path.join(inboxPath,
                                                       name))]) == 2:
                    break
        time.sleep(1)

    assert len([name for name in os.listdir(outboxPath)
                if os.path.isfile(os.path.join(outboxPath, name))]) == 3
    assert len([name for name in os.listdir(inboxPath)
                if os.path.isfile(os.path.join(inboxPath, name))]) == 2
    print('Post repeated')

    inboxPath = bobDir + '/accounts/bob@' + bobDomain + '/inbox'
    outboxPath = aliceDir + '/accounts/alice@' + aliceDomain + '/outbox'
    postsBefore = \
        len([name for name in os.listdir(inboxPath)
             if os.path.isfile(os.path.join(inboxPath, name))])
    print('\n\nAlice deletes her post: ' + outboxPostId + ' ' +
          str(postsBefore))
    password = 'alicepass'
    sendDeleteViaServer(aliceDir, sessionAlice, 'alice', password,
                        aliceDomain, alicePort,
                        httpPrefix, outboxPostId,
                        cachedWebfingers, personCache,
                        True, __version__)
    for i in range(30):
        if os.path.isdir(inboxPath):
            test = len([name for name in os.listdir(inboxPath)
                        if os.path.isfile(os.path.join(inboxPath, name))])
            if test == postsBefore-1:
                break
        time.sleep(1)

    test = len([name for name in os.listdir(inboxPath)
                if os.path.isfile(os.path.join(inboxPath, name))])
    assert test == postsBefore - 1
    print(">>> post deleted from Alice's outbox and Bob's inbox")
    assert validInbox(bobDir, 'bob', bobDomain)
    assert validInboxFilenames(bobDir, 'bob', bobDomain,
                               aliceDomain, alicePort)

    print('\n\nAlice unfollows Bob')
    password = 'alicepass'
    sendUnfollowRequestViaServer(baseDir, sessionAlice,
                                 'alice', password,
                                 aliceDomain, alicePort,
                                 'bob', bobDomain, bobPort,
                                 httpPrefix,
                                 cachedWebfingers, personCache,
                                 True, __version__)
    for t in range(10):
        if 'alice@' + aliceDomain + ':' + str(alicePort) not in \
           open(bobFollowersFilename).read():
            if 'bob@' + bobDomain + ':' + str(bobPort) not in \
               open(aliceFollowingFilename).read():
                break
        time.sleep(1)

    assert os.path.isfile(bobFollowersFilename)
    assert os.path.isfile(aliceFollowingFilename)
    assert 'alice@' + aliceDomain + ':' + str(alicePort) \
        not in open(bobFollowersFilename).read()
    assert 'bob@' + bobDomain + ':' + str(bobPort) \
        not in open(aliceFollowingFilename).read()
    assert validInbox(bobDir, 'bob', bobDomain)
    assert validInboxFilenames(bobDir, 'bob', bobDomain,
                               aliceDomain, alicePort)
    assert validInbox(aliceDir, 'alice', aliceDomain)
    assert validInboxFilenames(aliceDir, 'alice', aliceDomain,
                               bobDomain, bobPort)

    # stop the servers
    thrAlice.kill()
    thrAlice.join()
    assert thrAlice.is_alive() is False

    thrBob.kill()
    thrBob.join()
    assert thrBob.is_alive() is False

    os.chdir(baseDir)
    # shutil.rmtree(aliceDir)
    # shutil.rmtree(bobDir)


def testActorParsing():
    print('testActorParsing')
    actor = 'https://mydomain:72/users/mynick'
    domain, port = getDomainFromActor(actor)
    assert domain == 'mydomain'
    assert port == 72
    nickname = getNicknameFromActor(actor)
    assert nickname == 'mynick'

    actor = 'https://element/accounts/badger'
    domain, port = getDomainFromActor(actor)
    assert domain == 'element'
    nickname = getNicknameFromActor(actor)
    assert nickname == 'badger'

    actor = 'egg@chicken.com'
    domain, port = getDomainFromActor(actor)
    assert domain == 'chicken.com'
    nickname = getNicknameFromActor(actor)
    assert nickname == 'egg'

    actor = '@waffle@cardboard'
    domain, port = getDomainFromActor(actor)
    assert domain == 'cardboard'
    nickname = getNicknameFromActor(actor)
    assert nickname == 'waffle'

    actor = 'https://astral/channel/sky'
    domain, port = getDomainFromActor(actor)
    assert domain == 'astral'
    nickname = getNicknameFromActor(actor)
    assert nickname == 'sky'

    actor = 'https://randomain/users/rando'
    domain, port = getDomainFromActor(actor)
    assert domain == 'randomain'
    nickname = getNicknameFromActor(actor)
    assert nickname == 'rando'

    actor = 'https://otherdomain:49/@othernick'
    domain, port = getDomainFromActor(actor)
    assert domain == 'otherdomain'
    assert port == 49
    nickname = getNicknameFromActor(actor)
    assert nickname == 'othernick'


def testWebLinks():
    print('testWebLinks')

    exampleText = \
        '<p><span class=\"h-card\"><a href=\"https://something/@orother' + \
        '\" class=\"u-url mention\">@<span>foo</span></a></span> Some ' + \
        'random text.</p><p>AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA' + \
        'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA' + \
        'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA' + \
        'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA' + \
        'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA' + \
        'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA</p>'
    resultText = removeLongWords(exampleText, 40, [])
    assert resultText == \
        '<p><span class="h-card"><a href="https://something/@orother"' + \
        ' class="u-url mention">@<span>foo</span></a></span> ' + \
        'Some random text.</p>'

    exampleText = \
        'This post has a web links https://somesite.net\n\nAnd some other text'
    linkedText = addWebLinks(exampleText)
    assert \
        '<a href="https://somesite.net" rel="nofollow noopener noreferrer"' + \
        ' target="_blank"><span class="invisible">https://' + \
        '</span><span class="ellipsis">somesite.net</span></a' in linkedText

    exampleText = \
        'This post has a very long web link\n\nhttp://' + \
        'cbwebewuvfuftdiudbqd33dddbbyuef23fyug3bfhcyu2fct2' + \
        'cuyqbcbucuwvckiwyfgewfvqejbchevbhwevuevwbqebqekve' + \
        'qvuvjfkf.onion\n\nAnd some other text'
    linkedText = addWebLinks(exampleText)
    assert 'ellipsis' in linkedText

    exampleText = \
        '<p>1. HAHAHAHAHAHAHAHAHAHAHAHAHAHAHAHAHAHAHAHAHAHAHAHAHAHAHAH' + \
        'AHAHAHHAHAHAHAHAHAHAHAHAHAHAHAHHAHAHAHAHAHAHAHAH</p>'
    resultText = removeLongWords(exampleText, 40, [])
    assert resultText == '<p>1. HAHAHAHAHAHAHAHAHAHAHAHAHAHAHAHAHAHAHAHA</p>'

    exampleText = \
        '<p>Tox address is 88AB9DED6F9FBEF43E105FB72060A2D89F9B93C74' + \
        '4E8C45AB3C5E42C361C837155AFCFD9D448 </p>'
    resultText = removeLongWords(exampleText, 40, [])
    assert resultText == exampleText

    exampleText = \
        'some.incredibly.long.and.annoying.word.which.should.be.removed: ' + \
        'The remaining text'
    resultText = removeLongWords(exampleText, 40, [])
    assert resultText == \
        'some.incredibly.long.and.annoying.word.w\n' + \
        'hich.should.be.removed: The remaining text'

    exampleText = \
        '<p>Tox address is 88AB9DED6F9FBEF43E105FB72060A2D89F9B93C74' + \
        '4E8C45AB3C5E42C361C837155AFCFD9D448</p>'
    resultText = removeLongWords(exampleText, 40, [])
    assert resultText == \
        '<p>Tox address is 88AB9DED6F9FBEF43E105FB72060A2D89F9B93C7\n' + \
        '44E8C45AB3C5E42C361C837155AFCFD9D448</p>'

    exampleText = \
        '<p>ABCABCABCABCABCABCABCABCABCABCABCABCABCABCABCABCABCABCABCA' + \
        'BCABCABCABCABCABCABCABCABCABCABCABCABCABCABCABCABCABCABCABCAB' + \
        'CABCABCABCABCABCABCABCABCABCABCABCABCABCABCABCABCABCABCABCABC' + \
        'ABCABCABCABCABCABCABCABCABCABCABCABCABCABCABCABCABCABCABCABCA' + \
        'BCABCABCABCABCABCABCABCABCABCABCABCABCABCABCABCABCABCABCABCAB' + \
        'CABCABCABCABCABCABCABCABCABCABCABCABCABCABCABCABCABCABCABCABC' + \
        'ABCABCABCABCABCABCABCABCABCABCABCABCABCABCABCABCABCABCABCABCA' + \
        'BCABCABCABCABCABCABCABCABCABCABCABCABCABCABCABCABCABCABCABCAB' + \
        'CABCABCABCABCABCABCABCABC</p>'
    resultText = removeLongWords(exampleText, 40, [])
    assert resultText == r'<p>ABCABCABCABCABCABCABCABCABCABCABCABCABCA<\p>'

    exampleText = \
        '"the nucleus of mutual-support institutions, habits, and customs ' + \
        'remains alive with the millions; it keeps them together; and ' + \
        'they prefer to cling to their customs, beliefs, and traditions ' + \
        'rather than to accept the teachings of a war of each ' + \
        'against all"\n\n--Peter Kropotkin'
    testFnStr = addWebLinks(exampleText)
    resultText = removeLongWords(testFnStr, 40, [])
    assert resultText == exampleText
    assert 'ellipsis' not in resultText

    exampleText = \
        '<p>ｆｉｌｅｐｏｐｏｕｔ＝' + \
        'ＴｅｍｐｌａｔｅＡｔｔａｃｈｍｅｎｔＲｉｃｈＰｏｐｏｕｔ<<\\p>'
    resultText = replaceContentDuplicates(exampleText)
    assert resultText == \
        '<p>ｆｉｌｅｐｏｐｏｕｔ＝' + \
        'ＴｅｍｐｌａｔｅＡｔｔａｃｈｍｅｎｔＲｉｃｈＰｏｐｏｕｔ'

    exampleText = \
        '<p>Test1 test2 #YetAnotherExcessivelyLongwindedAndBoringHashtag</p>'
    testFnStr = addWebLinks(exampleText)
    resultText = removeLongWords(testFnStr, 40, [])
    assert(resultText ==
           '<p>Test1 test2 '
           '#YetAnotherExcessivelyLongwindedAndBorin\ngHashtag</p>')

    exampleText = \
        "<p>Don't remove a p2p link " + \
        "rad:git:hwd1yrerc3mcgn8ga9rho3dqi4w33nep7kxmqezss4topyfgmexihp" + \
        "33xcw</p>"
    testFnStr = addWebLinks(exampleText)
    resultText = removeLongWords(testFnStr, 40, [])
    assert resultText == exampleText


def testAddEmoji():
    print('testAddEmoji')
    content = "Emoji :lemon: :strawberry: :banana:"
    httpPrefix = 'http'
    nickname = 'testuser'
    domain = 'testdomain.net'
    port = 3682
    recipients = []
    hashtags = {}
    baseDir = os.getcwd()
    baseDirOriginal = os.getcwd()
    path = baseDir + '/.tests'
    if not os.path.isdir(path):
        os.mkdir(path)
    path = baseDir + '/.tests/emoji'
    if os.path.isdir(path):
        shutil.rmtree(path)
    os.mkdir(path)
    baseDir = path
    path = baseDir + '/emoji'
    if os.path.isdir(path):
        shutil.rmtree(path)
    os.mkdir(path)
    copytree(baseDirOriginal + '/emoji', baseDir + '/emoji')
    os.chdir(baseDir)
    privateKeyPem, publicKeyPem, person, wfEndpoint = \
        createPerson(baseDir, nickname, domain, port,
                     httpPrefix, True, False, 'password')
    contentModified = \
        addHtmlTags(baseDir, httpPrefix,
                    nickname, domain, content,
                    recipients, hashtags, True)
    assert ':lemon:' in contentModified
    assert contentModified.startswith('<p>')
    assert contentModified.endswith('</p>')
    tags = []
    for tagName, tag in hashtags.items():
        tags.append(tag)
    content = contentModified
    contentModified = replaceEmojiFromTags(content, tags, 'content')
    # print('contentModified: '+contentModified)
    assert contentModified == '<p>Emoji 🍋 🍓 🍌</p>'

    os.chdir(baseDirOriginal)
    shutil.rmtree(baseDirOriginal + '/.tests')


def testGetStatusNumber():
    print('testGetStatusNumber')
    prevStatusNumber = None
    for i in range(1, 20):
        statusNumber, published = getStatusNumber()
        if prevStatusNumber:
            assert len(statusNumber) == 18
            assert int(statusNumber) > prevStatusNumber
        prevStatusNumber = int(statusNumber)


def testJsonString() -> None:
    print('testJsonString')
    filename = '.epicyon_tests_testJsonString.json'
    messageStr = "Crème brûlée यह एक परीक्षण ह"
    testJson = {
        "content": messageStr
    }
    assert saveJson(testJson, filename)
    receivedJson = loadJson(filename, 0)
    assert receivedJson
    assert receivedJson['content'] == messageStr
    encodedStr = json.dumps(testJson, ensure_ascii=False)
    assert messageStr in encodedStr
    os.remove(filename)


def testSaveLoadJson():
    print('testSaveLoadJson')
    testJson = {
        "param1": 3,
        "param2": '"Crème brûlée यह एक परीक्षण ह"'
    }
    testFilename = '.epicyon_tests_testSaveLoadJson.json'
    if os.path.isfile(testFilename):
        os.remove(testFilename)
    assert saveJson(testJson, testFilename)
    assert os.path.isfile(testFilename)
    testLoadJson = loadJson(testFilename)
    assert(testLoadJson)
    assert testLoadJson.get('param1')
    assert testLoadJson.get('param2')
    assert testLoadJson['param1'] == 3
    assert testLoadJson['param2'] == '"Crème brûlée यह एक परीक्षण ह"'
    os.remove(testFilename)


def testTheme():
    print('testTheme')
    css = 'somestring --background-value: 24px; --foreground-value: 24px;'
    result = setCSSparam(css, 'background-value', '32px')
    assert result == \
        'somestring --background-value: 32px; --foreground-value: 24px;'
    css = \
        'somestring --background-value: 24px; --foreground-value: 24px; ' + \
        '--background-value: 24px;'
    result = setCSSparam(css, 'background-value', '32px')
    assert result == \
        'somestring --background-value: 32px; --foreground-value: 24px; ' + \
        '--background-value: 32px;'
    css = '--background-value: 24px; --foreground-value: 24px;'
    result = setCSSparam(css, 'background-value', '32px')
    assert result == '--background-value: 32px; --foreground-value: 24px;'


def testRecentPostsCache():
    print('testRecentPostsCache')
    recentPostsCache = {}
    maxRecentPosts = 3
    htmlStr = '<html></html>'
    for i in range(5):
        postJsonObject = {
            "id": "https://somesite.whatever/users/someuser/statuses/"+str(i)
        }
        updateRecentPostsCache(recentPostsCache, maxRecentPosts,
                               postJsonObject, htmlStr)
    assert len(recentPostsCache['index']) == maxRecentPosts
    assert len(recentPostsCache['json'].items()) == maxRecentPosts
    assert len(recentPostsCache['html'].items()) == maxRecentPosts


def testRemoveTextFormatting():
    print('testRemoveTextFormatting')
    testStr = '<p>Text without formatting</p>'
    resultStr = removeTextFormatting(testStr)
    assert(resultStr == testStr)
    testStr = '<p>Text <i>with</i> <h3>formatting</h3></p>'
    resultStr = removeTextFormatting(testStr)
    assert(resultStr == '<p>Text with formatting</p>')


def testJsonld():
    print("testJsonld")

    jldDocument = {
        "@context": "https://www.w3.org/ns/activitystreams",
        "actor": "https://somesite.net/users/gerbil",
        "description": "My json document",
        "numberField": 83582,
        "object": {
            "content": "valid content"
        }
    }
    # privateKeyPem, publicKeyPem = generateRSAKey()
    privateKeyPem = '-----BEGIN RSA PRIVATE KEY-----\n' \
        'MIIEowIBAAKCAQEAod9iHfIn4ugY/2byFrFjUprrFLkkH5bCrjiBq2/MdHFg99IQ\n' \
        '7li2x2mg5fkBMhU5SJIxlN8kiZMFq7JUXSA97Yo4puhVubqTSHihIh6Xn2mTjTgs\n' \
        'zNo9SBbmN3YiyBPTcr0rF4jGWZAduJ8u6i7Eky2QH+UBKyUNRZrcfoVq+7grHUIA\n' \
        '45pE7vAfEEWtgRiw32Nwlx55N3hayHax0y8gMdKEF/vfYKRLcM7rZgEASMtlCpgy\n' \
        'fsyHwFCDzl/BP8AhP9u3dM+SEundeAvF58AiXx1pKvBpxqttDNAsKWCRQ06/WI/W\n' \
        '2Rwihl9yCjobqRoFsZ/cTEi6FG9AbDAds5YjTwIDAQABAoIBAERL3rbpy8Bl0t43\n' \
        'jh7a+yAIMvVMZBxb3InrV3KAug/LInGNFQ2rKnsaawN8uu9pmwCuhfLc7yqIeJUH\n' \
        'qaadCuPlNJ/fWQQC309tbfbaV3iv78xejjBkSATZfIqb8nLeQpGflMXaNG3na1LQ\n' \
        '/tdZoiDC0ZNTaNnOSTo765oKKqhHUTQkwkGChrwG3Js5jekV4zpPMLhUafXk6ksd\n' \
        '8XLlZdCF3RUnuguXAg2xP/duxMYmTCx3eeGPkXBPQl0pahu8/6OtBoYvBrqNdQcx\n' \
        'jnEtYX9PCqDY3hAXW9GWsxNfu02DKhWigFHFNRUQtMI++438+QIfzXPslE2bTQIt\n' \
        '0OXUlwECgYEAxTKUZ7lwIBb5XKPJq53RQmX66M3ArxI1RzFSKm1+/CmxvYiN0c+5\n' \
        '2Aq62WEIauX6hoZ7yQb4zhdeNRzinLR7rsmBvIcP12FidXG37q9v3Vu70KmHniJE\n' \
        'TPbt5lHQ0bNACFxkar4Ab/JZN4CkMRgJdlcZ5boYNmcGOYCvw9izuM8CgYEA0iQ1\n' \
        'khIFZ6fCiXwVRGvEHmqSnkBmBHz8MY8fczv2Z4Gzfq3Tlh9VxpigK2F2pFt7keWc\n' \
        '53HerYFHFpf5otDhEyRwA1LyIcwbj5HopumxsB2WG+/M2as45lLfWa6KO73OtPpU\n' \
        'wGZYW+i/otdk9eFphceYtw19mxI+3lYoeI8EjYECgYBxOtTKJkmCs45lqkp/d3QT\n' \
        '2zjSempcXGkpQuG6KPtUUaCUgxdj1RISQj792OCbeQh8PDZRvOYaeIKInthkQKIQ\n' \
        'P/Z1yVvIQUvmwfBqZmQmR6k1bFLJ80UiqFr7+BiegH2RD3Q9cnIP1aly3DPrWLD+\n' \
        'OY9OQKfsfQWu+PxzyTeRMwKBgD8Zjlh5PtQ8RKcB8mTkMzSq7bHFRpzsZtH+1wPE\n' \
        'Kp40DRDp41H9wMTsiZPdJUH/EmDh4LaCs8nHuu/m3JfuPtd/pn7pBjntzwzSVFji\n' \
        'bW+jwrJK1Gk8B87pbZXBWlLMEOi5Dn/je37Fqd2c7f0DHauFHq9AxsmsteIPXwGs\n' \
        'eEKBAoGBAIzJX/5yFp3ObkPracIfOJ/U/HF1UdP6Y8qmOJBZOg5s9Y+JAdY76raK\n' \
        '0SbZPsOpuFUdTiRkSI3w/p1IuM5dPxgCGH9MHqjqogU5QwXr3vLF+a/PFhINkn1x\n' \
        'lozRZjDcF1y6xHfExotPC973UZnKEviq9/FqOsovZpvSQkzAYSZF\n' \
        '-----END RSA PRIVATE KEY-----'
    publicKeyPem = '-----BEGIN PUBLIC KEY-----\n' \
        'MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAod9iHfIn4ugY/2byFrFj\n' \
        'UprrFLkkH5bCrjiBq2/MdHFg99IQ7li2x2mg5fkBMhU5SJIxlN8kiZMFq7JUXSA9\n' \
        '7Yo4puhVubqTSHihIh6Xn2mTjTgszNo9SBbmN3YiyBPTcr0rF4jGWZAduJ8u6i7E\n' \
        'ky2QH+UBKyUNRZrcfoVq+7grHUIA45pE7vAfEEWtgRiw32Nwlx55N3hayHax0y8g\n' \
        'MdKEF/vfYKRLcM7rZgEASMtlCpgyfsyHwFCDzl/BP8AhP9u3dM+SEundeAvF58Ai\n' \
        'Xx1pKvBpxqttDNAsKWCRQ06/WI/W2Rwihl9yCjobqRoFsZ/cTEi6FG9AbDAds5Yj\n' \
        'TwIDAQAB\n' \
        '-----END PUBLIC KEY-----'

    signedDocument = jldDocument.copy()
    generateJsonSignature(signedDocument, privateKeyPem)
    assert(signedDocument)
    assert(signedDocument.get('signature'))
    assert(signedDocument['signature'].get('signatureValue'))
    assert(signedDocument['signature'].get('type'))
    assert(len(signedDocument['signature']['signatureValue']) > 50)
    # print(str(signedDocument['signature']))
    assert(signedDocument['signature']['type'] == 'RsaSignature2017')
    assert(verifyJsonSignature(signedDocument, publicKeyPem))

    # alter the signed document
    signedDocument['object']['content'] = 'forged content'
    assert(not verifyJsonSignature(signedDocument, publicKeyPem))

    jldDocument2 = {
        "@context": "https://www.w3.org/ns/activitystreams",
        "actor": "https://somesite.net/users/gerbil",
        "description": "Another json document",
        "numberField": 13353,
        "object": {
            "content": "More content"
        }
    }
    signedDocument2 = jldDocument2.copy()
    generateJsonSignature(signedDocument2, privateKeyPem)
    assert(signedDocument2)
    assert(signedDocument2.get('signature'))
    assert(signedDocument2['signature'].get('signatureValue'))
    # changed signature on different document
    if signedDocument['signature']['signatureValue'] == \
       signedDocument2['signature']['signatureValue']:
        print('json signature has not changed for different documents')
    assert '.' not in str(signedDocument['signature']['signatureValue'])
    assert len(str(signedDocument['signature']['signatureValue'])) > 340
    assert(signedDocument['signature']['signatureValue'] !=
           signedDocument2['signature']['signatureValue'])


def testSiteIsActive():
    print('testSiteIsActive')
    assert(siteIsActive('https://mastodon.social'))
    assert(not siteIsActive('https://notarealwebsite.a.b.c'))


def testRemoveHtml():
    print('testRemoveHtml')
    testStr = 'This string has no html.'
    assert(removeHtml(testStr) == testStr)
    testStr = 'This string <a href="1234.567">has html</a>.'
    assert(removeHtml(testStr) == 'This string has html.')


def testDangerousCSS():
    print('testDangerousCSS')
    baseDir = os.getcwd()
    for subdir, dirs, files in os.walk(baseDir):
        for f in files:
            if not f.endswith('.css'):
                continue
            assert not dangerousCSS(baseDir + '/' + f, False)
        break


def testDangerousMarkup():
    print('testDangerousMarkup')
    allowLocalNetworkAccess = False
    content = '<p>This is a valid message</p>'
    assert(not dangerousMarkup(content, allowLocalNetworkAccess))

    content = 'This is a valid message without markup'
    assert(not dangerousMarkup(content, allowLocalNetworkAccess))

    content = '<p>This is a valid-looking message. But wait... ' + \
        '<script>document.getElementById("concentrated")' + \
        '.innerHTML = "evil";</script></p>'
    assert(dangerousMarkup(content, allowLocalNetworkAccess))

    content = '<p>This html contains more than you expected... ' + \
        '<script language="javascript">document.getElementById("abc")' + \
        '.innerHTML = "def";</script></p>'
    assert(dangerousMarkup(content, allowLocalNetworkAccess))

    content = '<p>This is a valid-looking message. But wait... ' + \
        '<script src="https://evilsite/payload.js" /></p>'
    assert(dangerousMarkup(content, allowLocalNetworkAccess))

    content = '<p>This message embeds an evil frame.' + \
        '<iframe src="somesite"></iframe></p>'
    assert(dangerousMarkup(content, allowLocalNetworkAccess))

    content = '<p>This message tries to obfuscate an evil frame.' + \
        '<  iframe     src = "somesite"></    iframe  ></p>'
    assert(dangerousMarkup(content, allowLocalNetworkAccess))

    content = '<p>This message is not necessarily evil, but annoying.' + \
        '<hr><br><br><br><br><br><br><br><hr><hr></p>'
    assert(dangerousMarkup(content, allowLocalNetworkAccess))

    content = '<p>This message contans a ' + \
        '<a href="https://validsite/index.html">valid link.</a></p>'
    assert(not dangerousMarkup(content, allowLocalNetworkAccess))

    content = '<p>This message contans a ' + \
        '<a href="https://validsite/iframe.html">' + \
        'valid link having invalid but harmless name.</a></p>'
    assert(not dangerousMarkup(content, allowLocalNetworkAccess))

    content = '<p>This message which <a href="127.0.0.1:8736">' + \
        'tries to access the local network</a></p>'
    assert(dangerousMarkup(content, allowLocalNetworkAccess))

    content = '<p>This message which <a href="http://192.168.5.10:7235">' + \
        'tries to access the local network</a></p>'
    assert(dangerousMarkup(content, allowLocalNetworkAccess))

    content = '<p>127.0.0.1 This message which does not access ' + \
        'the local network</a></p>'
    assert(not dangerousMarkup(content, allowLocalNetworkAccess))


def runHtmlReplaceQuoteMarks():
    print('htmlReplaceQuoteMarks')
    testStr = 'The "cat" "sat" on the mat'
    result = htmlReplaceQuoteMarks(testStr)
    assert result == 'The “cat” “sat” on the mat'

    testStr = 'The cat sat on the mat'
    result = htmlReplaceQuoteMarks(testStr)
    assert result == 'The cat sat on the mat'

    testStr = '"hello"'
    result = htmlReplaceQuoteMarks(testStr)
    assert result == '“hello”'

    testStr = '"hello" <a href="somesite.html">&quot;test&quot; html</a>'
    result = htmlReplaceQuoteMarks(testStr)
    assert result == '“hello” <a href="somesite.html">“test” html</a>'


def testJsonPostAllowsComments():
    print('testJsonPostAllowsComments')
    postJsonObject = {
        "id": "123"
    }
    assert jsonPostAllowsComments(postJsonObject)
    postJsonObject = {
        "id": "123",
        "commentsEnabled": False
    }
    assert not jsonPostAllowsComments(postJsonObject)
    postJsonObject = {
        "id": "123",
        "commentsEnabled": True
    }
    assert jsonPostAllowsComments(postJsonObject)
    postJsonObject = {
        "id": "123",
        "object": {
            "commentsEnabled": True
        }
    }
    assert jsonPostAllowsComments(postJsonObject)
    postJsonObject = {
        "id": "123",
        "object": {
            "commentsEnabled": False
        }
    }
    assert not jsonPostAllowsComments(postJsonObject)


def testRemoveIdEnding():
    print('testRemoveIdEnding')
    testStr = 'https://activitypub.somedomain.net'
    resultStr = removeIdEnding(testStr)
    assert resultStr == 'https://activitypub.somedomain.net'

    testStr = \
        'https://activitypub.somedomain.net/users/foo/' + \
        'statuses/34544814814/activity'
    resultStr = removeIdEnding(testStr)
    assert resultStr == \
        'https://activitypub.somedomain.net/users/foo/statuses/34544814814'

    testStr = \
        'https://undo.somedomain.net/users/foo/statuses/34544814814/undo'
    resultStr = removeIdEnding(testStr)
    assert resultStr == \
        'https://undo.somedomain.net/users/foo/statuses/34544814814'

    testStr = \
        'https://event.somedomain.net/users/foo/statuses/34544814814/event'
    resultStr = removeIdEnding(testStr)
    assert resultStr == \
        'https://event.somedomain.net/users/foo/statuses/34544814814'


def testValidContentWarning():
    print('testValidContentWarning')
    resultStr = validContentWarning('Valid content warning')
    assert resultStr == 'Valid content warning'

    resultStr = validContentWarning('Invalid #content warning')
    assert resultStr == 'Invalid content warning'

    resultStr = \
        validContentWarning('Invalid <a href="somesite">content warning</a>')
    assert resultStr == 'Invalid content warning'


def testTranslations():
    print('testTranslations')
    languagesStr = ('ar', 'ca', 'cy', 'de', 'es', 'fr', 'ga',
                    'hi', 'it', 'ja', 'oc', 'pt', 'ru', 'zh')

    # load all translations into a dict
    langDict = {}
    for lang in languagesStr:
        langJson = loadJson('translations/' + lang + '.json')
        if not langJson:
            print('Missing language file ' +
                  'translations/' + lang + '.json')
        assert langJson
        langDict[lang] = langJson

    # load english translations
    translationsJson = loadJson('translations/en.json')
    # test each english string exists in the other language files
    for englishStr, translatedStr in translationsJson.items():
        for lang in languagesStr:
            langJson = langDict[lang]
            if not langJson.get(englishStr):
                print(englishStr + ' is missing from ' + lang + '.json')
            assert langJson.get(englishStr)


def testConstantTimeStringCheck():
    print('testConstantTimeStringCheck')
    assert constantTimeStringCheck('testing', 'testing')
    assert not constantTimeStringCheck('testing', '1234')
    assert not constantTimeStringCheck('testing', '1234567')

    itterations = 256

    start = time.time()
    for timingTest in range(itterations):
        constantTimeStringCheck('nnjfbefefbsnjsdnvbcueftqfeuqfbqefnjeniwufgy',
                                'nnjfbefefbsnjsdnvbcueftqfeuqfbqefnjeniwufgy')
    end = time.time()
    avTime1 = ((end - start) * 1000000 / itterations)

    # change a single character and observe timing difference
    start = time.time()
    for timingTest in range(itterations):
        constantTimeStringCheck('nnjfbefefbsnjsdnvbcueftqfeuqfbqefnjeniwufgy',
                                'nnjfbefefbsnjsdnvbcueftqfeuqfbqeznjeniwufgy')
    end = time.time()
    avTime2 = ((end - start) * 1000000 / itterations)
    timeDiffMicroseconds = abs(avTime2 - avTime1)
    # time difference should be less than 10uS
    assert int(timeDiffMicroseconds) < 10

    # change multiple characters and observe timing difference
    start = time.time()
    for timingTest in range(itterations):
        constantTimeStringCheck('nnjfbefefbsnjsdnvbcueftqfeuqfbqefnjeniwufgy',
                                'ano1befffbsn7sd3vbluef6qseuqfpqeznjgni9bfgi')
    end = time.time()
    avTime2 = ((end - start) * 1000000 / itterations)
    timeDiffMicroseconds = abs(avTime2 - avTime1)
    # time difference should be less than 10uS
    assert int(timeDiffMicroseconds) < 10


def testReplaceEmailQuote():
    print('testReplaceEmailQuote')
    testStr = '<p>This content has no quote.</p>'
    assert htmlReplaceEmailQuote(testStr) == testStr

    testStr = '<p>This content has no quote.</p>' + \
        '<p>With multiple</p><p>lines</p>'
    assert htmlReplaceEmailQuote(testStr) == testStr

    testStr = '<p>&quot;This is a quoted paragraph.&quot;</p>'
    assert htmlReplaceEmailQuote(testStr) == \
        '<p><blockquote>This is a quoted paragraph.</blockquote></p>'

    testStr = "<p><span class=\"h-card\">" + \
        "<a href=\"https://somewebsite/@nickname\" " + \
        "class=\"u-url mention\">@<span>nickname</span></a></span> " + \
        "<br />&gt; This is a quote</p><p>Some other text.</p>"
    expectedStr = "<p><span class=\"h-card\">" + \
        "<a href=\"https://somewebsite/@nickname\" " + \
        "class=\"u-url mention\">@<span>nickname</span></a></span> " + \
        "<br /><blockquote>This is a quote</blockquote></p>" + \
        "<p>Some other text.</p>"
    resultStr = htmlReplaceEmailQuote(testStr)
    if resultStr != expectedStr:
        print('Result: ' + str(resultStr))
        print('Expect: ' + expectedStr)
    assert resultStr == expectedStr

    testStr = "<p>Some text:</p><p>&gt; first line-&gt;second line</p>" + \
        "<p>Some question?</p>"
    expectedStr = "<p>Some text:</p><p><blockquote>first line-<br>" + \
        "second line</blockquote></p><p>Some question?</p>"
    resultStr = htmlReplaceEmailQuote(testStr)
    if resultStr != expectedStr:
        print('Result: ' + str(resultStr))
        print('Expect: ' + expectedStr)
    assert resultStr == expectedStr

    testStr = "<p><span class=\"h-card\">" + \
        "<a href=\"https://somedomain/@somenick\" " + \
        "class=\"u-url mention\">@<span>somenick</span>" + \
        "</a></span> </p><p>&gt; Text1.<br />&gt; <br />" + \
        "&gt; Text2<br />&gt; <br />&gt; Text3<br />" + \
        "&gt;<br />&gt; Text4<br />&gt; <br />&gt; " + \
        "Text5<br />&gt; <br />&gt; Text6</p><p>Text7</p>"
    expectedStr = "<p><span class=\"h-card\">" + \
        "<a href=\"https://somedomain/@somenick\" " + \
        "class=\"u-url mention\">@<span>somenick</span></a>" + \
        "</span> </p><p><blockquote> Text1.<br /><br />" + \
        "Text2<br /><br />Text3<br />&gt;<br />Text4<br />" + \
        "<br />Text5<br /><br />Text6</blockquote></p><p>Text7</p>"
    resultStr = htmlReplaceEmailQuote(testStr)
    if resultStr != expectedStr:
        print('Result: ' + str(resultStr))
        print('Expect: ' + expectedStr)
    assert resultStr == expectedStr


def testRemoveHtmlTag():
    print('testRemoveHtmlTag')
    testStr = "<p><img width=\"864\" height=\"486\" " + \
        "src=\"https://somesiteorother.com/image.jpg\"></p>"
    resultStr = removeHtmlTag(testStr, 'width')
    assert resultStr == "<p><img height=\"486\" " + \
        "src=\"https://somesiteorother.com/image.jpg\"></p>"


def testHashtagRuleTree():
    print('testHashtagRuleTree')
    operators = ('not', 'and', 'or', 'xor', 'from', 'contains')

    url = 'testsite.com'
    moderated = True
    conditionsStr = \
        'contains "Cat" or contains "Corvid" or ' + \
        'contains "Dormouse" or contains "Buzzard"'
    tagsInConditions = []
    tree = hashtagRuleTree(operators, conditionsStr,
                           tagsInConditions, moderated)
    assert str(tree) == str(['or', ['contains', ['"Cat"']],
                             ['contains', ['"Corvid"']],
                             ['contains', ['"Dormouse"']],
                             ['contains', ['"Buzzard"']]])

    content = 'This is a test'
    moderated = True
    conditionsStr = '#foo or #bar'
    tagsInConditions = []
    tree = hashtagRuleTree(operators, conditionsStr,
                           tagsInConditions, moderated)
    assert str(tree) == str(['or', ['#foo'], ['#bar']])
    assert str(tagsInConditions) == str(['#foo', '#bar'])
    hashtags = ['#foo']
    assert hashtagRuleResolve(tree, hashtags, moderated, content, url)
    hashtags = ['#carrot', '#stick']
    assert not hashtagRuleResolve(tree, hashtags, moderated, content, url)

    content = 'This is a test'
    url = 'https://testsite.com/something'
    moderated = True
    conditionsStr = '#foo and from "testsite.com"'
    tagsInConditions = []
    tree = hashtagRuleTree(operators, conditionsStr,
                           tagsInConditions, moderated)
    assert str(tree) == str(['and', ['#foo'], ['from', ['"testsite.com"']]])
    assert str(tagsInConditions) == str(['#foo'])
    hashtags = ['#foo']
    assert hashtagRuleResolve(tree, hashtags, moderated, content, url)
    assert not hashtagRuleResolve(tree, hashtags, moderated, content,
                                  'othersite.net')

    content = 'This is a test'
    moderated = True
    conditionsStr = 'contains "is a" and #foo or #bar'
    tagsInConditions = []
    tree = hashtagRuleTree(operators, conditionsStr,
                           tagsInConditions, moderated)
    assert str(tree) == \
        str(['and', ['contains', ['"is a"']],
             ['or', ['#foo'], ['#bar']]])
    assert str(tagsInConditions) == str(['#foo', '#bar'])
    hashtags = ['#foo']
    assert hashtagRuleResolve(tree, hashtags, moderated, content, url)
    hashtags = ['#carrot', '#stick']
    assert not hashtagRuleResolve(tree, hashtags, moderated, content, url)

    moderated = False
    conditionsStr = 'not moderated and #foo or #bar'
    tagsInConditions = []
    tree = hashtagRuleTree(operators, conditionsStr,
                           tagsInConditions, moderated)
    assert str(tree) == \
        str(['not', ['and', ['moderated'], ['or', ['#foo'], ['#bar']]]])
    assert str(tagsInConditions) == str(['#foo', '#bar'])
    hashtags = ['#foo']
    assert hashtagRuleResolve(tree, hashtags, moderated, content, url)
    hashtags = ['#carrot', '#stick']
    assert hashtagRuleResolve(tree, hashtags, moderated, content, url)

    moderated = True
    conditionsStr = 'moderated and #foo or #bar'
    tagsInConditions = []
    tree = hashtagRuleTree(operators, conditionsStr,
                           tagsInConditions, moderated)
    assert str(tree) == \
        str(['and', ['moderated'], ['or', ['#foo'], ['#bar']]])
    assert str(tagsInConditions) == str(['#foo', '#bar'])
    hashtags = ['#foo']
    assert hashtagRuleResolve(tree, hashtags, moderated, content, url)
    hashtags = ['#carrot', '#stick']
    assert not hashtagRuleResolve(tree, hashtags, moderated, content, url)

    conditionsStr = 'x'
    tagsInConditions = []
    tree = hashtagRuleTree(operators, conditionsStr,
                           tagsInConditions, moderated)
    assert tree is None
    assert tagsInConditions == []
    hashtags = ['#foo']
    assert not hashtagRuleResolve(tree, hashtags, moderated, content, url)

    conditionsStr = '#x'
    tagsInConditions = []
    tree = hashtagRuleTree(operators, conditionsStr,
                           tagsInConditions, moderated)
    assert str(tree) == str(['#x'])
    assert str(tagsInConditions) == str(['#x'])
    hashtags = ['#x']
    assert hashtagRuleResolve(tree, hashtags, moderated, content, url)
    hashtags = ['#y', '#z']
    assert not hashtagRuleResolve(tree, hashtags, moderated, content, url)

    conditionsStr = 'not #b'
    tagsInConditions = []
    tree = hashtagRuleTree(operators, conditionsStr,
                           tagsInConditions, moderated)
    assert str(tree) == str(['not', ['#b']])
    assert str(tagsInConditions) == str(['#b'])
    hashtags = ['#y', '#z']
    assert hashtagRuleResolve(tree, hashtags, moderated, content, url)
    hashtags = ['#a', '#b', '#c']
    assert not hashtagRuleResolve(tree, hashtags, moderated, content, url)

    conditionsStr = '#foo or #bar and #a'
    tagsInConditions = []
    tree = hashtagRuleTree(operators, conditionsStr,
                           tagsInConditions, moderated)
    assert str(tree) == str(['and', ['or', ['#foo'], ['#bar']], ['#a']])
    assert str(tagsInConditions) == str(['#foo', '#bar', '#a'])
    hashtags = ['#foo', '#bar', '#a']
    assert hashtagRuleResolve(tree, hashtags, moderated, content, url)
    hashtags = ['#bar', '#a']
    assert hashtagRuleResolve(tree, hashtags, moderated, content, url)
    hashtags = ['#foo', '#a']
    assert hashtagRuleResolve(tree, hashtags, moderated, content, url)
    hashtags = ['#x', '#a']
    assert not hashtagRuleResolve(tree, hashtags, moderated, content, url)


def testGetNewswireTags():
    print('testGetNewswireTags')
    rssDescription = '<img src="https://somesite/someimage.jpg" ' + \
        'class="misc-stuff" alt="#ExcitingHashtag" ' + \
        'srcset="https://somesite/someimage.jpg" ' + \
        'sizes="(max-width: 864px) 100vw, 864px" />' + \
        'Compelling description with #ExcitingHashtag, which is ' + \
        'being posted in #BoringForum'
    tags = getNewswireTags(rssDescription, 10)
    assert len(tags) == 2
    assert '#BoringForum' in tags
    assert '#ExcitingHashtag' in tags


def testFirstParagraphFromString():
    print('testFirstParagraphFromString')
    testStr = \
        '<p><a href="https://somesite.com/somepath">This is a test</a></p>' + \
        '<p>This is another paragraph</p>'
    resultStr = firstParagraphFromString(testStr)
    assert resultStr == 'This is a test'

    testStr = 'Testing without html'
    resultStr = firstParagraphFromString(testStr)
    assert resultStr == testStr


def testParseFeedDate():
    print('testParseFeedDate')

    pubDate = "2020-12-14T00:08:06+00:00"
    publishedDate = parseFeedDate(pubDate)
    assert publishedDate == "2020-12-14 00:08:06+00:00"

    pubDate = "Tue, 08 Dec 2020 06:24:38 -0600"
    publishedDate = parseFeedDate(pubDate)
    assert publishedDate == "2020-12-08 12:24:38+00:00"

    pubDate = "2020-08-27T16:12:34+00:00"
    publishedDate = parseFeedDate(pubDate)
    assert publishedDate == "2020-08-27 16:12:34+00:00"

    pubDate = "Sun, 22 Nov 2020 19:51:33 +0100"
    publishedDate = parseFeedDate(pubDate)
    assert publishedDate == "2020-11-22 18:51:33+00:00"


def testValidNickname():
    print('testValidNickname')
    domain = 'somedomain.net'

    nickname = 'myvalidnick'
    assert validNickname(domain, nickname)

    nickname = 'my.invalid.nick'
    assert not validNickname(domain, nickname)

    nickname = 'myinvalidnick?'
    assert not validNickname(domain, nickname)

    nickname = 'my invalid nick?'
    assert not validNickname(domain, nickname)


def testGuessHashtagCategory() -> None:
    print('testGuessHashtagCategory')
    hashtagCategories = {
        "foo": ["swan", "goose"],
        "bar": ["cat", "mouse"]
    }
    guess = guessHashtagCategory("unspecifiedgoose", hashtagCategories)
    assert guess == "foo"

    guess = guessHashtagCategory("catpic", hashtagCategories)
    assert guess == "bar"


def testGetMentionedPeople() -> None:
    print('testGetMentionedPeople')
    baseDir = os.getcwd()

    content = "@dragon@cave.site @bat@cave.site This is a test."
    actors = getMentionedPeople(baseDir, 'https',
                                content,
                                'mydomain', False)
    assert actors
    assert len(actors) == 2
    assert actors[0] == "https://cave.site/users/dragon"
    assert actors[1] == "https://cave.site/users/bat"


def testReplyToPublicPost() -> None:
    baseDir = os.getcwd()
    nickname = 'test7492362'
    domain = 'other.site'
    port = 443
    httpPrefix = 'https'
    postId = httpPrefix + '://rat.site/users/ninjarodent/statuses/63746173435'
    reply = \
        createPublicPost(baseDir, nickname, domain, port, httpPrefix,
                         "@ninjarodent@rat.site This is a test.",
                         False, False, False, True,
                         None, None, False, postId)
    # print(str(reply))
    assert reply['object']['content'] == \
        '<p><span class=\"h-card\">' + \
        '<a href=\"https://rat.site/@ninjarodent\" ' + \
        'class=\"u-url mention\">@<span>ninjarodent</span>' + \
        '</a></span> This is a test.</p>'
    assert reply['object']['tag'][0]['type'] == 'Mention'
    assert reply['object']['tag'][0]['name'] == '@ninjarodent@rat.site'
    assert reply['object']['tag'][0]['href'] == \
        'https://rat.site/users/ninjarodent'
    assert len(reply['object']['to']) == 1
    assert reply['object']['to'][0].endswith('#Public')
    assert len(reply['object']['cc']) >= 1
    assert reply['object']['cc'][0].endswith(nickname + '/followers')
    assert len(reply['object']['tag']) == 1
    assert len(reply['object']['cc']) == 2
    assert reply['object']['cc'][1] == \
        httpPrefix + '://rat.site/users/ninjarodent'


def getFunctionCallArgs(name: str, lines: [], startLineCtr: int) -> []:
    """Returns the arguments of a function call given lines
    of source code and a starting line number
    """
    argsStr = lines[startLineCtr].split(name + '(')[1]
    if ')' in argsStr:
        argsStr = argsStr.split(')')[0].replace(' ', '').split(',')
        return argsStr
    for lineCtr in range(startLineCtr + 1, len(lines)):
        if ')' not in lines[lineCtr]:
            argsStr += lines[lineCtr]
            continue
        else:
            argsStr += lines[lineCtr].split(')')[0]
            break
    return argsStr.replace('\n', '').replace(' ', '').split(',')


def getFunctionCalls(name: str, lines: [], startLineCtr: int,
                     functionProperties: {}) -> []:
    """Returns the functions called by the given one,
    Starting with the given source code at the given line
    """
    callsFunctions = []
    functionContentStr = ''
    for lineCtr in range(startLineCtr + 1, len(lines)):
        lineStr = lines[lineCtr].strip()
        if lineStr.startswith('def '):
            break
        if lineStr.startswith('class '):
            break
        functionContentStr += lines[lineCtr]
    for funcName, properties in functionProperties.items():
        if funcName + '(' in functionContentStr:
            callsFunctions.append(funcName)
    return callsFunctions


def functionArgsMatch(callArgs: [], funcArgs: []):
    """Do the function artuments match the function call arguments
    """
    if len(callArgs) == len(funcArgs):
        return True

    # count non-optional arguments
    callArgsCtr = 0
    for a in callArgs:
        if a == 'self':
            continue
        if '=' not in a or a.startswith("'"):
            callArgsCtr += 1

    funcArgsCtr = 0
    for a in funcArgs:
        if a == 'self':
            continue
        if '=' not in a or a.startswith("'"):
            funcArgsCtr += 1

    return callArgsCtr >= funcArgsCtr


def testFunctions():
    print('testFunctions')
    function = {}
    functionProperties = {}
    modules = {}

    for subdir, dirs, files in os.walk('.'):
        for sourceFile in files:
            if not sourceFile.endswith('.py'):
                continue
            modName = sourceFile.replace('.py', '')
            modules[modName] = {
                'functions': []
            }
            sourceStr = ''
            with open(sourceFile, "r") as f:
                sourceStr = f.read()
                modules[modName]['source'] = sourceStr
            with open(sourceFile, "r") as f:
                lines = f.readlines()
                modules[modName]['lines'] = lines
                for line in lines:
                    if not line.strip().startswith('def '):
                        continue
                    methodName = line.split('def ', 1)[1].split('(')[0]
                    methodArgs = \
                        sourceStr.split('def ' + methodName + '(')[1]
                    methodArgs = methodArgs.split(')')[0]
                    methodArgs = methodArgs.replace(' ', '').split(',')
                    if function.get(modName):
                        function[modName].append(methodName)
                    else:
                        function[modName] = [methodName]
                    if methodName not in modules[modName]['functions']:
                        modules[modName]['functions'].append(methodName)
                    functionProperties[methodName] = {
                        "args": methodArgs,
                        "module": modName,
                        "calledInModule": []
                    }
        break

    excludeFuncArgs = [
        'pyjsonld'
    ]
    excludeFuncs = [
        'link',
        'set',
        'get'
    ]
    # which modules is each function used within?
    for modName, modProperties in modules.items():
        print('Module: ' + modName + ' ✓')
        for name, properties in functionProperties.items():
            lineCtr = 0
            for line in modules[modName]['lines']:
                lineStr = line.strip()
                if lineStr.startswith('def '):
                    lineCtr += 1
                    continue
                if lineStr.startswith('class '):
                    lineCtr += 1
                    continue
                if name + '(' in line:
                    modList = \
                        functionProperties[name]['calledInModule']
                    if modName not in modList:
                        modList.append(modName)
                    if modName in excludeFuncArgs:
                        lineCtr += 1
                        continue
                    if name in excludeFuncs:
                        lineCtr += 1
                        continue
                    callArgs = \
                        getFunctionCallArgs(name,
                                            modules[modName]['lines'],
                                            lineCtr)
                    if not functionArgsMatch(callArgs,
                                             functionProperties[name]['args']):
                        print('Call to function ' + name +
                              ' does not match its arguments')
                        print('def args: ' +
                              str(len(functionProperties[name]['args'])) +
                              '\n' + str(functionProperties[name]['args']))
                        print('Call args: ' + str(len(callArgs)) + '\n' +
                              str(callArgs))
                        print('module ' + modName + ' line ' + str(lineCtr))
                        assert False
                lineCtr += 1

    # don't check these functions, because they are procedurally called
    exclusions = [
        'do_GET',
        'do_POST',
        'do_HEAD',
        '__run',
        'globaltrace',
        'localtrace',
        'kill',
        'clone',
        'unregister_rdf_parser',
        'set_document_loader',
        'has_property',
        'has_value',
        'add_value',
        'get_values',
        'remove_property',
        'remove_value',
        'normalize',
        'get_document_loader',
        'runInboxQueueWatchdog',
        'runInboxQueue',
        'runPostSchedule',
        'runPostScheduleWatchdog',
        'str2bool',
        'runNewswireDaemon',
        'runNewswireWatchdog',
        'threadSendPost',
        'sendToFollowers',
        'expireCache',
        'getMutualsOfPerson',
        'runPostsQueue',
        'runSharesExpire',
        'runPostsWatchdog',
        'runSharesExpireWatchdog',
        'getThisWeeksEvents',
        'getAvailability',
        'testThreadsFunction',
        'createServerAlice',
        'createServerBob',
        'createServerEve',
        'E2EEremoveDevice',
        'setOrganizationScheme'
    ]
    excludeImports = [
        'link',
        'start'
    ]
    excludeLocal = [
        'pyjsonld',
        'daemon',
        'tests'
    ]
    excludeMods = [
        'pyjsonld'
    ]
    # check that functions are called somewhere
    for name, properties in functionProperties.items():
        if name.startswith('__'):
            if name.endswith('__'):
                continue
        if name in exclusions:
            continue
        if properties['module'] in excludeMods:
            continue
        isLocalFunction = False
        if not properties['calledInModule']:
            print('function ' + name +
                  ' in module ' + properties['module'] +
                  ' is not called anywhere')
        assert properties['calledInModule']

        if len(properties['calledInModule']) == 1:
            modName = properties['calledInModule'][0]
            if modName not in excludeLocal and \
               modName == properties['module']:
                isLocalFunction = True
                if not name.startswith('_'):
                    print('Local function ' + name +
                          ' in ' + modName + '.py does not begin with _')
                    assert False

        if name not in excludeImports:
            for modName in properties['calledInModule']:
                if modName == properties['module']:
                    continue
                importStr = 'from ' + properties['module'] + ' import ' + name
                if importStr not in modules[modName]['source']:
                    print(importStr + ' not found in ' + modName + '.py')
                    assert False

        if not isLocalFunction:
            if name.startswith('_'):
                excludePublic = [
                    'pyjsonld',
                    'daemon',
                    'tests'
                ]
                modName = properties['module']
                if modName not in excludePublic:
                    print('Public function ' + name + ' in ' +
                          modName + '.py begins with _')
                    assert False
        print('Function: ' + name + ' ✓')

    print('Constructing function call graph')
    moduleColors = ('red', 'green', 'yellow', 'orange', 'purple', 'cyan',
                    'darkgoldenrod3', 'darkolivegreen1', 'darkorange1',
                    'darkorchid1', 'darkseagreen', 'darkslategray4',
                    'deeppink1', 'deepskyblue1', 'dimgrey', 'gold1',
                    'goldenrod', 'burlywood2', 'bisque1', 'brown1',
                    'chartreuse2', 'cornsilk', 'darksalmon')
    maxModuleCalls = 1
    maxFunctionCalls = 1
    colorCtr = 0
    for modName, modProperties in modules.items():
        lineCtr = 0
        modules[modName]['color'] = moduleColors[colorCtr]
        colorCtr += 1
        if colorCtr >= len(moduleColors):
            colorCtr = 0
        for line in modules[modName]['lines']:
            if line.strip().startswith('def '):
                name = line.split('def ')[1].split('(')[0]
                callsList = \
                    getFunctionCalls(name, modules[modName]['lines'],
                                     lineCtr, functionProperties)
                functionProperties[name]['calls'] = callsList.copy()
                if len(callsList) > maxFunctionCalls:
                    maxFunctionCalls = len(callsList)
                # keep track of which module calls which other module
                for fn in callsList:
                    modCall = functionProperties[fn]['module']
                    if modCall != modName:
                        if modules[modName].get('calls'):
                            if modCall not in modules[modName]['calls']:
                                modules[modName]['calls'].append(modCall)
                                if len(modules[modName]['calls']) > \
                                   maxModuleCalls:
                                    maxModuleCalls = \
                                        len(modules[modName]['calls'])
                        else:
                            modules[modName]['calls'] = [modCall]
            lineCtr += 1
    callGraphStr = 'digraph EpicyonModules {\n\n'
    callGraphStr += '  graph [fontsize=10 fontname="Verdana" compound=true];\n'
    callGraphStr += '  node [shape=record fontsize=10 fontname="Verdana"];\n\n'
    # colors of modules nodes
    for modName, modProperties in modules.items():
        if not modProperties.get('calls'):
            callGraphStr += '  "' + modName + \
                '" [fillcolor=yellow style=filled];\n'
            continue
        if len(modProperties['calls']) <= int(maxModuleCalls / 8):
            callGraphStr += '  "' + modName + \
                '" [fillcolor=green style=filled];\n'
        elif len(modProperties['calls']) < int(maxModuleCalls / 4):
            callGraphStr += '  "' + modName + \
                '" [fillcolor=orange style=filled];\n'
        else:
            callGraphStr += '  "' + modName + \
                '" [fillcolor=red style=filled];\n'
    callGraphStr += '\n'
    # connections between modules
    for modName, modProperties in modules.items():
        if not modProperties.get('calls'):
            continue
        for modCall in modProperties['calls']:
            callGraphStr += '  "' + modName + '" -> "' + modCall + '";\n'
    callGraphStr += '\n}\n'
    with open('epicyon_modules.dot', 'w+') as fp:
        fp.write(callGraphStr)
        print('Modules call graph saved to epicyon_modules.dot')
        print('Plot using: ' +
              'sfdp -x -Goverlap=false -Goverlap_scaling=2 ' +
              '-Gsep=+100 -Tx11 epicyon_modules.dot')

    callGraphStr = 'digraph Epicyon {\n\n'
    callGraphStr += '  size="8,6"; ratio=fill;\n'
    callGraphStr += '  graph [fontsize=10 fontname="Verdana" compound=true];\n'
    callGraphStr += '  node [shape=record fontsize=10 fontname="Verdana"];\n\n'

    for modName, modProperties in modules.items():
        callGraphStr += '  subgraph cluster_' + modName + ' {\n'
        callGraphStr += '    label = "' + modName + '";\n'
        callGraphStr += '    node [style=filled];\n'
        moduleFunctionsStr = ''
        for name in modProperties['functions']:
            if name.startswith('test'):
                continue
            if name not in excludeFuncs:
                if not functionProperties[name]['calls']:
                    moduleFunctionsStr += \
                        '  "' + name + '" [fillcolor=yellow style=filled];\n'
                    continue
                noOfCalls = len(functionProperties[name]['calls'])
                if noOfCalls < int(maxFunctionCalls / 4):
                    moduleFunctionsStr += '  "' + name + \
                        '" [fillcolor=orange style=filled];\n'
                else:
                    moduleFunctionsStr += '  "' + name + \
                        '" [fillcolor=red style=filled];\n'

        if moduleFunctionsStr:
            callGraphStr += moduleFunctionsStr + '\n'
        callGraphStr += '    color=blue;\n'
        callGraphStr += '  }\n\n'

    for name, properties in functionProperties.items():
        if not properties['calls']:
            continue
        noOfCalls = len(properties['calls'])
        if noOfCalls <= int(maxFunctionCalls / 8):
            modColor = 'blue'
        elif noOfCalls < int(maxFunctionCalls / 4):
            modColor = 'green'
        else:
            modColor = 'red'
        for calledFunc in properties['calls']:
            if calledFunc.startswith('test'):
                continue
            if calledFunc not in excludeFuncs:
                callGraphStr += '  "' + name + '" -> "' + calledFunc + \
                    '" [color=' + modColor + '];\n'

    callGraphStr += '\n}\n'
    with open('epicyon.dot', 'w+') as fp:
        fp.write(callGraphStr)
        print('Call graph saved to epicyon.dot')
        print('Plot using: ' +
              'sfdp -x -Goverlap=prism -Goverlap_scaling=8 ' +
              '-Gsep=+120 -Tx11 epicyon.dot')


def testLinksWithinPost() -> None:
    baseDir = os.getcwd()
    nickname = 'test27636'
    domain = 'rando.site'
    port = 443
    httpPrefix = 'https'
    content = 'This is a test post with links.\n\n' + \
        'ftp://ftp.ncdc.noaa.gov/pub/data/ghcn/v4/\n\nhttps://freedombone.net'
    postJsonObject = \
        createPublicPost(baseDir, nickname, domain, port, httpPrefix,
                         content,
                         False, False, False, True,
                         None, None, False, None)
    assert postJsonObject['object']['content'] == \
        '<p>This is a test post with links.<br><br>' + \
        '<a href="ftp://ftp.ncdc.noaa.gov/pub/data/ghcn/v4/" ' + \
        'rel="nofollow noopener noreferrer" target="_blank">' + \
        '<span class="invisible">ftp://</span>' + \
        '<span class="ellipsis">' + \
        'ftp.ncdc.noaa.gov/pub/data/ghcn/v4/</span>' + \
        '</a><br><br><a href="https://freedombone.net" ' + \
        'rel="nofollow noopener noreferrer" target="_blank">' + \
        '<span class="invisible">https://</span>' + \
        '<span class="ellipsis">freedombone.net</span></a></p>'

    content = "<p>Some text</p><p>Other text</p><p>More text</p>" + \
        "<pre><code>Errno::EOHNOES (No such file or rodent @ " + \
        "ik_right - /tmp/blah.png)<br></code></pre><p>" + \
        "(<a href=\"https://welllookeyhere.maam/error.txt\" " + \
        "rel=\"nofollow noopener noreferrer\" target=\"_blank\">" + \
        "wuh</a>)</p><p>Oh yeah like for sure</p>" + \
        "<p>Ground sloth tin opener</p>" + \
        "<p><a href=\"https://whocodedthis.huh/tags/" + \
        "taggedthing\" class=\"mention hashtag\" rel=\"tag\" " + \
        "target=\"_blank\">#<span>taggedthing</span></a></p>"
    postJsonObject = \
        createPublicPost(baseDir, nickname, domain, port, httpPrefix,
                         content,
                         False, False, False, True,
                         None, None, False, None)
    assert postJsonObject['object']['content'] == content


def testMastoApi():
    print('testMastoApi')
    nickname = 'ThisIsATestNickname'
    mastoId = getMastoApiV1IdFromNickname(nickname)
    assert(mastoId)
    nickname2 = getNicknameFromMastoApiV1Id(mastoId)
    if nickname2 != nickname:
        print(nickname + ' != ' + nickname2)
    assert nickname2 == nickname


def testDomainHandling():
    print('testDomainHandling')
    testDomain = 'localhost'
    assert decodedHost(testDomain) == testDomain
    testDomain = '127.0.0.1:60'
    assert decodedHost(testDomain) == testDomain
    testDomain = '192.168.5.153'
    assert decodedHost(testDomain) == testDomain
    testDomain = 'xn--espaa-rta.icom.museum'
    assert decodedHost(testDomain) == "españa.icom.museum"


def testPrepareHtmlPostNickname():
    print('testPrepareHtmlPostNickname')
    postHtml = '<a class="imageAnchor" href="/users/bob?replyfollowers='
    postHtml += '<a class="imageAnchor" href="/users/bob?repeatprivate='
    result = prepareHtmlPostNickname('alice', postHtml)
    assert result == postHtml.replace('/bob?', '/alice?')

    postHtml = '<a class="imageAnchor" href="/users/bob?replyfollowers='
    postHtml += '<a class="imageAnchor" href="/users/bob;repeatprivate='
    expectedHtml = '<a class="imageAnchor" href="/users/alice?replyfollowers='
    expectedHtml += '<a class="imageAnchor" href="/users/bob;repeatprivate='
    result = prepareHtmlPostNickname('alice', postHtml)
    assert result == expectedHtml


def runAllTests():
    print('Running tests...')
    testFunctions()
    testPrepareHtmlPostNickname()
    testDomainHandling()
    testMastoApi()
    testLinksWithinPost()
    testReplyToPublicPost()
    testGetMentionedPeople()
    testGuessHashtagCategory()
    testValidNickname()
    testParseFeedDate()
    testFirstParagraphFromString()
    testGetNewswireTags()
    testHashtagRuleTree()
    testRemoveHtmlTag()
    testReplaceEmailQuote()
    testConstantTimeStringCheck()
    testTranslations()
    testValidContentWarning()
    testRemoveIdEnding()
    testJsonPostAllowsComments()
    runHtmlReplaceQuoteMarks()
    testDangerousCSS()
    testDangerousMarkup()
    testRemoveHtml()
    testSiteIsActive()
    testJsonld()
    testRemoveTextFormatting()
    testWebLinks()
    testRecentPostsCache()
    testTheme()
    testSaveLoadJson()
    testJsonString()
    testGetStatusNumber()
    testAddEmoji()
    testActorParsing()
    testHttpsig()
    testCache()
    testThreads()
    testCreatePerson()
    testAuthentication()
    testFollowersOfPerson()
    testNoOfFollowersOnDomain()
    testFollows()
    testGroupFollowers()
    testDelegateRoles()
    print('Tests succeeded\n')
