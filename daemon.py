__filename__ = "daemon.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.0.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
#import socketserver
import commentjson
import json
import time
import base64
import locale
# used for mime decoding of message POST
import email.parser
# for saving images
from binascii import a2b_base64
from hashlib import sha256
from pprint import pprint
from session import createSession
from webfinger import webfingerMeta
from webfinger import webfingerLookup
from webfinger import webfingerHandle
from person import registerAccount
from person import personLookup
from person import personBoxJson
from person import createSharedInbox
from person import isSuspended
from person import suspendAccount
from person import unsuspendAccount
from person import removeAccount
from person import canRemovePost
from posts import outboxMessageCreateWrap
from posts import savePostToBox
from posts import sendToFollowers
from posts import postIsAddressedToPublic
from posts import sendToNamedAddresses
from posts import createPublicPost
from posts import createReportPost
from posts import createUnlistedPost
from posts import createFollowersOnlyPost
from posts import createDirectMessagePost
from posts import populateRepliesJson
from posts import addToField
from posts import expireCache
from inbox import inboxPermittedMessage
from inbox import inboxMessageHasParams
from inbox import runInboxQueue
from inbox import runInboxQueueWatchdog
from inbox import savePostToInboxQueue
from inbox import populateReplies
from inbox import getPersonPubKey
from follow import getFollowingFeed
from follow import outboxUndoFollow
from follow import sendFollowRequest
from auth import authorize
from auth import createPassword
from auth import createBasicAuthHeader
from auth import authorizeBasic
from threads import threadWithTrace
from media import getMediaPath
from media import createMediaDirs
from delete import outboxDelete
from like import outboxLike
from like import outboxUndoLike
from blocking import outboxBlock
from blocking import outboxUndoBlock
from blocking import addBlock
from blocking import removeBlock
from blocking import addGlobalBlock
from blocking import removeGlobalBlock
from blocking import isBlockedHashtag
from blocking import isBlockedDomain
from config import setConfigParam
from config import getConfigParam
from roles import outboxDelegate
from roles import setRole
from roles import clearModeratorStatus
from skills import outboxSkills
from availability import outboxAvailability
from webinterface import htmlDeletePost
from webinterface import htmlAbout
from webinterface import htmlRemoveSharedItem
from webinterface import htmlInboxDMs
from webinterface import htmlInboxReplies
from webinterface import htmlInboxMedia
from webinterface import htmlUnblockConfirm
from webinterface import htmlPersonOptions
from webinterface import htmlIndividualPost
from webinterface import htmlProfile
from webinterface import htmlInbox
from webinterface import htmlOutbox
from webinterface import htmlModeration
from webinterface import htmlPostReplies
from webinterface import htmlLogin
from webinterface import htmlSuspended
from webinterface import htmlGetLoginCredentials
from webinterface import htmlNewPost
from webinterface import htmlFollowConfirm
from webinterface import htmlCalendar
from webinterface import htmlSearch
from webinterface import htmlSearchEmoji
from webinterface import htmlSearchEmojiTextEntry
from webinterface import htmlUnfollowConfirm
from webinterface import htmlProfileAfterSearch
from webinterface import htmlEditProfile
from webinterface import htmlTermsOfService
from webinterface import htmlSkillsSearch
from webinterface import htmlHashtagSearch
from webinterface import htmlModerationInfo
from webinterface import htmlSearchSharedItems
from webinterface import htmlHashtagBlocked
from shares import getSharesFeedForPerson
from shares import outboxShareUpload
from shares import outboxUndoShareUpload
from shares import addShare
from shares import removeShare
from utils import getNicknameFromActor
from utils import getDomainFromActor
from utils import getStatusNumber
from utils import urlPermitted
from manualapprove import manualDenyFollowRequest
from manualapprove import manualApproveFollowRequest
from announce import createAnnounce
from announce import outboxAnnounce
from content import addHtmlTags
from media import removeMetaData
from cache import storePersonInCache
from httpsig import verifyPostHeaders
import os
import sys

# maximum number of posts to list in outbox feed
maxPostsInFeed=12

# reduced posts for media feed because it can take a while
maxPostsInMediaFeed=6

# number of follows/followers per page
followsPerPage=12

# number of item shares per page
sharesPerPage=12

def readFollowList(filename: str):
    """Returns a list of ActivityPub addresses to follow
    """
    followlist=[]
    if not os.path.isfile(filename):
        return followlist
    followUsers = open(filename, "r")    
    for u in followUsers:
        if u not in followlist:
            nickname,domain = parseHandle(u)
            if nickname:
                followlist.append(nickname+'@'+domain)
    followUsers.close()
    return followlist

class PubServer(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def _requestHTTP(self) -> bool:
        """Should a http response be given?
        """
        if not self.headers.get('Accept'):
            return False
        if 'image/' in self.headers['Accept']:
            return False
        if self.headers['Accept'].startswith('*'):
            return False
        if 'json' in self.headers['Accept']:
            return False
        return True

    def _fetchAuthenticated(self) -> bool:
        """http authentication of GET requests for json
        """
        if not self.server.authenticatedFetch:
            return True
        # check that the headers are signed
        if not self.headers.get('signature'):
            if self.server.debug:
                print('WARN: authenticated fetch, GET has no signature in headers')
            return False
        # get the keyId
        keyId=None
        signatureParams=self.headers['signature'].split(',')
        for signatureItem in signatureParams:
            if signatureItem.startswith('keyId='):
                if '"' in signatureItem:
                    keyId=signatureItem.split('"')[1]
                    break
        if not keyId:
            if self.server.debug:
                print('WARN: authenticated fetch, failed to obtain keyId from signature')
            return False
        # is the keyId (actor) valid?
        if not urlPermitted(keyId,self.server.federationList,"inbox:read"):
            if self.server.debug:
                print('Authorized fetch failed: '+keyId+' is not permitted')
            return False
        # make sure we have a session
        if not self.server.session:
            if self.server.debug:
                print('DEBUG: creating new session during authenticated fetch')
            self.server.session= \
                createSession(self.server.domain,self.server.port,self.server.useTor)
        # obtain the public key
        pubKey= \
            getPersonPubKey(self.server.baseDir,self.server.session,keyId, \
                            self.server.personCache,self.server.debug, \
                            __version__,self.server.httpPrefix,self.server.domain)
        if not pubKey:
            if self.server.debug:
                print('DEBUG: Authenticated fetch failed to obtain public key for '+keyId)
            return False
        # it is assumed that there will be no message body on authenticated fetches
        # and also consequently no digest
        GETrequestBody=''
        GETrequestDigest=None
        # verify the GET request without any digest
        if verifyPostHeaders(self.server.httpPrefix, \
                             pubKey,self.headers, \
                             self.path,True, \
                             GETrequestDigest,GETrequestBody):
            return True
        return False

    def _login_headers(self,fileFormat: str,length: int) -> None:
        self.send_response(200)
        self.send_header('Content-type', fileFormat)
        self.send_header('Content-Length', str(length))
        self.send_header('Host', self.server.domainFull)
        self.send_header('WWW-Authenticate', 'title="Login to Epicyon", Basic realm="epicyon"')
        self.send_header('X-Robots-Tag','noindex')
        self.end_headers()

    def _set_headers(self,fileFormat: str,length: int,cookie: str) -> None:
        self.send_response(200)
        self.send_header('Content-type', fileFormat)
        self.send_header('Content-Length', str(length))
        if cookie:
            self.send_header('Cookie', cookie)
        self.send_header('Host', self.server.domainFull)
        self.send_header('InstanceID', self.server.instanceId)
        self.send_header('X-Robots-Tag','noindex')
        self.end_headers()

    def _redirect_headers(self,redirect: str,cookie: str) -> None:
        self.send_response(303)
        #self.send_header('Content-type', 'text/html')
        if cookie:
            self.send_header('Cookie', cookie)
        self.send_header('Location', redirect)
        self.send_header('Host', self.server.domainFull)
        self.send_header('InstanceID', self.server.instanceId)
        self.send_header('Content-Length', '0')
        self.send_header('X-Robots-Tag','noindex')
        self.end_headers()

    def _404(self) -> None:
        msg="<html><head></head><body><h1>404 Not Found</h1></body></html>".encode('utf-8')
        self.send_response(404)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(msg)))
        self.send_header('X-Robots-Tag','noindex')
        self.end_headers()
        try:
            self.wfile.write(msg)
        except Exception as e:
            print('Error when showing 404')
            print(e)

    def _robotsTxt(self) -> bool:
        if not self.path.lower().startswith('/robot'):
            return False
        msg='User-agent: *\nDisallow: /'
        msg=msg.encode('utf-8')
        self._set_headers('text/plain; charset=utf-8',len(msg),None)
        self.wfile.write(msg)
        return True

    def _webfinger(self) -> bool:
        if not self.path.startswith('/.well-known'):
            return False
        if self.server.debug:
            print('DEBUG: WEBFINGER well-known')

        if self.server.debug:
            print('DEBUG: WEBFINGER host-meta')
        if self.path.startswith('/.well-known/host-meta'):
            wfResult=webfingerMeta(self.server.httpPrefix,self.server.domainFull)
            if wfResult:
                msg=wfResult.encode('utf-8')
                self._set_headers('application/xrd+xml',len(msg),None)
                self.wfile.write(msg)
            return

        if self.server.debug:
            print('DEBUG: WEBFINGER lookup '+self.path+' '+str(self.server.baseDir))
        wfResult=webfingerLookup(self.path,self.server.baseDir,self.server.port,self.server.debug)
        if wfResult:
            msg=json.dumps(wfResult).encode('utf-8')
            self._set_headers('application/jrd+json',len(msg),None)
            self.wfile.write(msg)
        else:
            if self.server.debug:
                print('DEBUG: WEBFINGER lookup 404 '+self.path)
            self._404()
        return True

    def _permittedDir(self,path: str) -> bool:
        """These are special paths which should not be accessible
        directly via GET or POST
        """
        if path.startswith('/wfendpoints') or \
           path.startswith('/keys') or \
           path.startswith('/accounts'):
            return False
        return True
        
    def _postToOutbox(self,messageJson: {},version: str) -> bool:
        """post is received by the outbox
        Client to server message post
        https://www.w3.org/TR/activitypub/#client-to-server-outbox-delivery
        """
        if not messageJson.get('type'):
            if self.server.debug:
                print('DEBUG: POST to outbox has no "type" parameter')
            return False
        if not messageJson.get('object') and messageJson.get('content'):
            if messageJson['type']!='Create':
                # https://www.w3.org/TR/activitypub/#object-without-create
                if self.server.debug:
                    print('DEBUG: POST to outbox - adding Create wrapper')
                messageJson= \
                    outboxMessageCreateWrap(self.server.httpPrefix, \
                                            self.postToNickname, \
                                            self.server.domain, \
                                            self.server.port, \
                                            messageJson)
        if messageJson['type']=='Create':
            if not (messageJson.get('id') and \
                    messageJson.get('type') and \
                    messageJson.get('actor') and \
                    messageJson.get('object') and \
                    messageJson.get('to')):
                if self.server.debug:
                    pprint(messageJson)
                    print('DEBUG: POST to outbox - Create does not have the required parameters')
                return False
            testDomain,testPort=getDomainFromActor(messageJson['actor'])
            if testPort:
                if testPort!=80 and testPort!=443:
                    testDomain=testDomain+':'+str(testPort)
            if isBlockedDomain(self.server.baseDir,testDomain):
                if self.server.debug:
                    print('DEBUG: domain is blocked: '+messageJson['actor'])
                return False
            # https://www.w3.org/TR/activitypub/#create-activity-outbox
            messageJson['object']['attributedTo']=messageJson['actor']
            if messageJson['object'].get('attachment'):
                attachmentIndex=0
                if messageJson['object']['attachment'][attachmentIndex].get('mediaType'):
                    fileExtension='png'
                    if messageJson['object']['attachment'][attachmentIndex]['mediaType'].endswith('jpeg'):
                        fileExtension='jpg'
                    if messageJson['object']['attachment'][attachmentIndex]['mediaType'].endswith('gif'):
                        fileExtension='gif'
                    if messageJson['object']['attachment'][attachmentIndex]['mediaType'].endswith('audio/mpeg'):
                        fileExtension='mp3'
                    if messageJson['object']['attachment'][attachmentIndex]['mediaType'].endswith('ogg'):
                        fileExtension='ogg'
                    if messageJson['object']['attachment'][attachmentIndex]['mediaType'].endswith('mp4'):
                        fileExtension='mp4'
                    if messageJson['object']['attachment'][attachmentIndex]['mediaType'].endswith('webm'):
                        fileExtension='webm'
                    if messageJson['object']['attachment'][attachmentIndex]['mediaType'].endswith('ogv'):
                        fileExtension='ogv'
                    mediaDir=self.server.baseDir+'/accounts/'+self.postToNickname+'@'+self.server.domain
                    uploadMediaFilename=mediaDir+'/upload.'+fileExtension
                    if not os.path.isfile(uploadMediaFilename):
                        del messageJson['object']['attachment']
                    else:
                        # generate a path for the uploaded image
                        mPath=getMediaPath()
                        mediaPath=mPath+'/'+createPassword(32)+'.'+fileExtension
                        createMediaDirs(self.server.baseDir,mPath)
                        mediaFilename=self.server.baseDir+'/'+mediaPath
                        # move the uploaded image to its new path
                        os.rename(uploadMediaFilename,mediaFilename)
                        # change the url of the attachment
                        messageJson['object']['attachment'][attachmentIndex]['url']= \
                            self.server.httpPrefix+'://'+self.server.domainFull+'/'+mediaPath
                
        permittedOutboxTypes=[
            'Create','Announce','Like','Follow','Undo', \
            'Update','Add','Remove','Block','Delete', \
            'Delegate','Skill'
        ]
        if messageJson['type'] not in permittedOutboxTypes:
            if self.server.debug:
                print('DEBUG: POST to outbox - '+messageJson['type']+ \
                      ' is not a permitted activity type')
            return False
        if messageJson.get('id'):
            postId=messageJson['id'].replace('/activity','').replace('/undo','')
            if self.server.debug:
                print('DEBUG: id attribute exists within POST to outbox')
        else:
            if self.server.debug:
                print('DEBUG: No id attribute within POST to outbox')
            postId=None
        if self.server.debug:
            pprint(messageJson)
            print('DEBUG: savePostToBox')
        savePostToBox(self.server.baseDir, \
                      self.server.httpPrefix, \
                      postId, \
                      self.postToNickname, \
                      self.server.domainFull,messageJson,'outbox')
        if outboxAnnounce(self.server.baseDir,messageJson,self.server.debug):
            if self.server.debug:
                print('DEBUG: Updated announcements (shares) collection for the post associated with the Announce activity')
        if not self.server.session:
            if self.server.debug:
                print('DEBUG: creating new session for c2s')
            self.server.session= \
                createSession(self.server.domain,self.server.port,self.server.useTor)
        if self.server.debug:
            print('DEBUG: sending c2s post to followers')
        sendToFollowers(self.server.session,self.server.baseDir, \
                        self.postToNickname,self.server.domain, \
                        self.server.port, \
                        self.server.httpPrefix, \
                        self.server.federationList, \
                        self.server.sendThreads, \
                        self.server.postLog, \
                        self.server.cachedWebfingers, \
                        self.server.personCache, \
                        messageJson,self.server.debug, \
                        self.server.projectVersion)
        if self.server.debug:
            print('DEBUG: handle any unfollow requests')
        outboxUndoFollow(self.server.baseDir,messageJson,self.server.debug)
        if self.server.debug:
            print('DEBUG: handle delegation requests')
        outboxDelegate(self.server.baseDir,self.postToNickname,messageJson,self.server.debug)
        if self.server.debug:
            print('DEBUG: handle skills changes requests')
        outboxSkills(self.server.baseDir,self.postToNickname,messageJson,self.server.debug)
        if self.server.debug:
            print('DEBUG: handle availability changes requests')
        outboxAvailability(self.server.baseDir,self.postToNickname,messageJson,self.server.debug)
        if self.server.debug:
            print('DEBUG: handle any like requests')
        outboxLike(self.server.baseDir,self.server.httpPrefix, \
                   self.postToNickname,self.server.domain,self.server.port, \
                   messageJson,self.server.debug)
        if self.server.debug:
            print('DEBUG: handle any undo like requests')
        outboxUndoLike(self.server.baseDir,self.server.httpPrefix, \
                       self.postToNickname,self.server.domain,self.server.port, \
                       messageJson,self.server.debug)
        if self.server.debug:
            print('DEBUG: handle delete requests')        
        outboxDelete(self.server.baseDir,self.server.httpPrefix, \
                     self.postToNickname,self.server.domain, \
                     messageJson,self.server.debug, \
                     self.server.allowDeletion)
        if self.server.debug:
            print('DEBUG: handle block requests')
        outboxBlock(self.server.baseDir,self.server.httpPrefix, \
                    self.postToNickname,self.server.domain, \
                    self.server.port,
                    messageJson,self.server.debug)
        if self.server.debug:
            print('DEBUG: handle undo block requests')
        outboxUndoBlock(self.server.baseDir,self.server.httpPrefix, \
                        self.postToNickname,self.server.domain, \
                        self.server.port,
                        messageJson,self.server.debug)
        if self.server.debug:
            print('DEBUG: handle share uploads')
        outboxShareUpload(self.server.baseDir,self.server.httpPrefix, \
                          self.postToNickname,self.server.domain, \
                          self.server.port,
                          messageJson,self.server.debug)
        if self.server.debug:
            print('DEBUG: handle undo share uploads')
        outboxUndoShareUpload(self.server.baseDir,self.server.httpPrefix, \
                              self.postToNickname,self.server.domain, \
                              self.server.port,
                              messageJson,self.server.debug)
        if self.server.debug:
            print('DEBUG: sending c2s post to named addresses')
            print('c2s sender: '+self.postToNickname+'@'+self.server.domain+':'+str(self.server.port))
        sendToNamedAddresses(self.server.session,self.server.baseDir, \
                             self.postToNickname,self.server.domain, \
                             self.server.port, \
                             self.server.httpPrefix, \
                             self.server.federationList, \
                             self.server.sendThreads, \
                             self.server.postLog, \
                             self.server.cachedWebfingers, \
                             self.server.personCache, \
                             messageJson,self.server.debug, \
                             self.server.projectVersion)
        return True

    def _postToOutboxThread(self,messageJson: {}) -> bool:
        """Creates a thread to send a post
        """
        accountOutboxThreadName=self.postToNickname
        if not accountOutboxThreadName:
            accountOutboxThreadName='*'
        
        if self.server.outboxThread.get(accountOutboxThreadName):
            print('Waiting for previous outbox thread to end')
            waitCtr=0
            while self.server.outboxThread[accountOutboxThreadName].isAlive() and waitCtr<8:
                time.sleep(1)
                waitCtr+=1
            if waitCtr>=8:
                self.server.outboxThread[accountOutboxThreadName].kill()

        print('Creating outbox thread')
        self.server.outboxThread[accountOutboxThreadName]= \
            threadWithTrace(target=self._postToOutbox, \
                            args=(messageJson.copy(),__version__),daemon=True)
        print('Starting outbox thread')
        self.server.outboxThread[accountOutboxThreadName].start()
        return True

    def _inboxQueueCleardown(self):
        """ Check if the queue is full and remove oldest items if it is
        """
        if len(self.server.inboxQueue)>=self.server.maxQueueLength:
            print('Inbox queue is full. Removing oldest items.')
            while len(self.server.inboxQueue) >= self.server.maxQueueLength-4:
                queueFilename=self.server.inboxQueue[0]
                if os.path.isfile(queueFilename):
                    os.remove(queueFilename)
                self.server.inboxQueue.pop(0)
    
    def _updateInboxQueue(self,nickname: str,messageJson: {},messageBytes: str) -> int:
        """Update the inbox queue
        """
        self._inboxQueueCleardown()

        # Convert the headers needed for signature verification to dict
        headersDict={}
        headersDict['host']=self.headers['host']
        headersDict['signature']=self.headers['signature']
        if self.headers.get('Date'):
            headersDict['Date']=self.headers['Date']
        if self.headers.get('digest'):
            headersDict['digest']=self.headers['digest']
        if self.headers.get('Content-type'):
            headersDict['Content-type']=self.headers['Content-type']

        # For follow activities add a 'to' field, which is a copy of the object field
        messageJson,toFieldExists=addToField('Follow',messageJson,self.server.debug)
        
        # For like activities add a 'to' field, which is a copy of the actor within the object field
        messageJson,toFieldExists=addToField('Like',messageJson,self.server.debug)

        pprint(messageJson)

        # save the json for later queue processing
        queueFilename = \
            savePostToInboxQueue(self.server.baseDir,
                                 self.server.httpPrefix,
                                 nickname,
                                 self.server.domainFull,
                                 messageJson,
                                 messageBytes.decode('utf-8'),
                                 headersDict,
                                 self.path,
                                 self.server.debug)
        if queueFilename:
            # add json to the queue
            if queueFilename not in self.server.inboxQueue:
                self.server.inboxQueue.append(queueFilename)
            self.send_response(201)
            self.end_headers()
            self.server.POSTbusy=False
            return 0
        return 2

    def _isAuthorized(self) -> bool:
        # token based authenticated used by the web interface
        if self.headers.get('Cookie'):
            if '=' in self.headers['Cookie']:
                tokenStr=self.headers['Cookie'].split('=',1)[1]
                if self.server.tokensLookup.get(tokenStr):
                    nickname=self.server.tokensLookup[tokenStr]
                    # check that the path contains the same nickname as the cookie
                    # otherwise it would be possible to be authorized to use
                    # an account you don't own
                    if '/'+nickname+'/' in self.path:
                        return True
                    if self.path.endswith('/'+nickname):
                        return True
            return False
        # basic auth
        if self.headers.get('Authorization'):
            if authorize(self.server.baseDir,self.path, \
                         self.headers['Authorization'], \
                         self.server.debug):
                return True
        return False
    
    def do_GET(self):
        # redirect music to #nowplaying list
        if self.path=='/music' or self.path=='/nowplaying':
            self.path='/tags/nowplaying'

        if self.server.debug:
            print('DEBUG: GET from '+self.server.baseDir+ \
                  ' path: '+self.path+' busy: '+ \
                  str(self.server.GETbusy))

        if self.server.debug:
            print(str(self.headers))

        cookie=None
        if self.headers.get('Cookie'):
            cookie=self.headers['Cookie']

        # check authorization
        authorized = self._isAuthorized()
        if authorized:
            if self.server.debug:
                print('GET Authorization granted')
        else:
            if self.server.debug:
                print('GET Not authorized')

        if not self.server.session:
            self.server.session= \
                createSession(self.server.domain,self.server.port,self.server.useTor)

        # is this a html request?
        htmlGET=False
        if self.headers.get('Accept'):
            if self._requestHTTP():
                htmlGET=True

        # replace https://domain/@nick with https://domain/users/nick
        if self.path.startswith('/@'):
            self.path=self.path.replace('/@','/users/')

        # treat shared inbox paths consistently
        if self.path=='/sharedInbox' or \
           self.path=='/users/inbox' or \
           self.path=='/actor/inbox' or \
           self.path=='/users/'+self.server.domain:
            self.path='/inbox'

        # show the person options screen with view/follow/block/report
        if htmlGET and '/users/' in self.path:
           if '?options=' in self.path:
               optionsStr=self.path.split('?options=')[1]
               originPathStr=self.path.split('?options=')[0]
               if ';' in optionsStr:
                   pageNumber=1
                   optionsList=optionsStr.split(';')
                   optionsActor=optionsList[0]
                   optionsPageNumber=optionsList[1]
                   optionsProfileUrl=optionsList[2]
                   if optionsPageNumber.isdigit():
                       pageNumber=int(optionsPageNumber)
                   optionsLink=None
                   if len(optionsList)>3:
                       optionsLink=optionsList[3]
                   msg=htmlPersonOptions(self.server.translate, \
                                         self.server.baseDir, \
                                         self.server.domain, \
                                         originPathStr, \
                                         optionsActor, \
                                         optionsProfileUrl, \
                                         optionsLink, \
                                         pageNumber).encode()
                   self._set_headers('text/html',len(msg),cookie)
                   self.wfile.write(msg)
                   self.server.GETbusy=False
                   return
               self._redirect_headers(originPathStr,cookie)
               self.server.GETbusy=False
               return

        # remove a shared item
        if htmlGET and '?rmshare=' in self.path:
            shareName=self.path.split('?rmshare=')[1]
            actor=self.server.httpPrefix+'://'+self.server.domainFull+self.path.split('?rmshare=')[0]
            msg=htmlRemoveSharedItem(self.server.translate,self.server.baseDir,actor,shareName).encode()
            if not msg:
               self._redirect_headers(actor+'/inbox',cookie)
               self.server.GETbusy=False
               return                
            self._set_headers('text/html',len(msg),cookie)
            self.wfile.write(msg)
            self.server.GETbusy=False
            return

        if self.path.startswith('/terms'):
            msg=htmlTermsOfService(self.server.baseDir, \
                                   self.server.httpPrefix, \
                                   self.server.domainFull).encode()
            self._login_headers('text/html',len(msg))
            self.wfile.write(msg)
            self.server.GETbusy=False
            return

        if self.path.startswith('/about'):
            msg=htmlAbout(self.server.baseDir, \
                          self.server.httpPrefix, \
                          self.server.domainFull).encode()
            self._login_headers('text/html',len(msg))
            self.wfile.write(msg)
            self.server.GETbusy=False
            return

        # send robots.txt if asked
        if self._robotsTxt():
            self.server.GETbusy=False
            return
            
        # if not authorized then show the login screen
        if htmlGET and self.path!='/login' and self.path!='/':
            if '/media/' not in self.path and \
               '/sharefiles/' not in self.path and \
               '/statuses/' not in self.path and \
               '/emoji/' not in self.path and \
               '/tags/' not in self.path and \
               '/avatars/' not in self.path and \
               '/icons/' not in self.path:
                divertToLoginScreen=True
                if self.path.startswith('/users/'):
                    nickStr=self.path.split('/users/')[1]
                    if '/' not in nickStr and '?' not in nickStr:
                        divertToLoginScreen=False
                    else:
                        if self.path.endswith('/following') or \
                           self.path.endswith('/followers') or \
                           self.path.endswith('/skills') or \
                           self.path.endswith('/roles') or \
                           self.path.endswith('/shares'):
                            divertToLoginScreen=False
                if divertToLoginScreen and not authorized:
                    if self.server.debug:
                        print('DEBUG: divertToLoginScreen='+str(divertToLoginScreen))
                        print('DEBUG: authorized='+str(authorized))
                        print('DEBUG: path='+self.path)
                    self.send_response(303)
                    self.send_header('Location', '/login')
                    self.send_header('Content-Length', '0')
                    self.send_header('X-Robots-Tag','noindex')
                    self.end_headers()
                    self.server.GETbusy=False
                    return
            
        # get css
        # Note that this comes before the busy flag to avoid conflicts
        if self.path.endswith('.css'):
            if os.path.isfile('epicyon-profile.css'):
                with open('epicyon-profile.css', 'r') as cssfile:
                    css = cssfile.read()
                msg=css.encode('utf-8')
                self._set_headers('text/css',len(msg),cookie)
                self.wfile.write(msg)
                self.wfile.flush() 
                return
        # image on login screen
        if self.path=='/login.png':
            mediaFilename= \
                self.server.baseDir+'/accounts/login.png'
            if os.path.isfile(mediaFilename):
                with open(mediaFilename, 'rb') as avFile:
                    mediaBinary = avFile.read()
                    self._set_headers('image/png',len(mediaBinary),cookie)
                    self.wfile.write(mediaBinary)
                    self.wfile.flush() 
            self._404()
            return        
        # login screen background image
        if self.path=='/login-background.png':
            mediaFilename= \
                self.server.baseDir+'/accounts/login-background.png'
            if os.path.isfile(mediaFilename):
                with open(mediaFilename, 'rb') as avFile:
                    mediaBinary = avFile.read()
                    self._set_headers('image/png',len(mediaBinary),cookie)
                    self.wfile.write(mediaBinary)
                    self.wfile.flush() 
                    return
            self._404()
            return
        # follow screen background image
        if self.path=='/follow-background.png':
            mediaFilename= \
                self.server.baseDir+'/accounts/follow-background.png'
            if os.path.isfile(mediaFilename):
                with open(mediaFilename, 'rb') as avFile:
                    mediaBinary = avFile.read()
                    self._set_headers('image/png',len(mediaBinary),cookie)
                    self.wfile.write(mediaBinary)
                    self.wfile.flush() 
            self._404()
            return
        # emoji images
        if '/emoji/' in self.path:
            if self.path.endswith('.png') or \
               self.path.endswith('.jpg') or \
               self.path.endswith('.gif'):
                emojiStr=self.path.split('/emoji/')[1]
                emojiFilename= \
                    self.server.baseDir+'/emoji/'+emojiStr
                if os.path.isfile(emojiFilename):
                    mediaImageType='png'
                    if emojiFilename.endswith('.png'):
                        mediaImageType='png'
                    elif emojiFilename.endswith('.jpg'):
                        mediaImageType='jpeg'
                    else:
                        mediaImageType='gif'
                    with open(emojiFilename, 'rb') as avFile:
                        mediaBinary = avFile.read()
                        self._set_headers('image/'+mediaImageType,len(mediaBinary),cookie)
                        self.wfile.write(mediaBinary)
                        self.wfile.flush() 
                    return
            self._404()
            return
        # show media
        # Note that this comes before the busy flag to avoid conflicts
        if '/media/' in self.path:
            if self.path.endswith('.png') or \
               self.path.endswith('.jpg') or \
               self.path.endswith('.gif') or \
               self.path.endswith('.mp4') or \
               self.path.endswith('.ogv') or \
               self.path.endswith('.mp3') or \
               self.path.endswith('.ogg'):
                mediaStr=self.path.split('/media/')[1]
                mediaFilename= \
                    self.server.baseDir+'/media/'+mediaStr
                if os.path.isfile(mediaFilename):
                    mediaFileType='image/png'
                    if mediaFilename.endswith('.png'):
                        mediaFileType='image/png'
                    elif mediaFilename.endswith('.jpg'):
                        mediaFileType='image/jpeg'
                    elif mediaFilename.endswith('.gif'):
                        mediaFileType='image/gif'
                    elif mediaFilename.endswith('.mp4'):
                        mediaFileType='video/mp4'
                    elif mediaFilename.endswith('.ogv'):
                        mediaFileType='video/ogv'
                    elif mediaFilename.endswith('.mp3'):
                        mediaFileType='audio/mpeg'
                    elif mediaFilename.endswith('.ogg'):
                        mediaFileType='audio/ogg'
                    with open(mediaFilename, 'rb') as avFile:
                        mediaBinary = avFile.read()
                        self._set_headers(mediaFileType,len(mediaBinary),cookie)
                        self.wfile.write(mediaBinary)
                        self.wfile.flush() 
                    return        
            self._404()
            return
        # show shared item images
        # Note that this comes before the busy flag to avoid conflicts
        if '/sharefiles/' in self.path:
            if self.path.endswith('.png') or \
               self.path.endswith('.jpg') or \
               self.path.endswith('.gif'):
                mediaStr=self.path.split('/sharefiles/')[1]
                mediaFilename= \
                    self.server.baseDir+'/sharefiles/'+mediaStr
                if os.path.isfile(mediaFilename):
                    mediaFileType='png'
                    if mediaFilename.endswith('.png'):
                        mediaFileType='png'
                    elif mediaFilename.endswith('.jpg'):
                        mediaFileType='jpeg'
                    else:
                        mediaFileType='gif'
                    with open(mediaFilename, 'rb') as avFile:
                        mediaBinary = avFile.read()
                        self._set_headers('image/'+mediaFileType,len(mediaBinary),cookie)
                        self.wfile.write(mediaBinary)
                        self.wfile.flush() 
                    return        
            self._404()
            return
        # icon images
        # Note that this comes before the busy flag to avoid conflicts
        if self.path.startswith('/icons/'):
            if self.path.endswith('.png'):
                mediaStr=self.path.split('/icons/')[1]
                mediaFilename= \
                    self.server.baseDir+'/img/icons/'+mediaStr
                if os.path.isfile(mediaFilename):
                    if mediaFilename.endswith('.png'):
                        with open(mediaFilename, 'rb') as avFile:
                            mediaBinary = avFile.read()
                            self._set_headers('image/png',len(mediaBinary),cookie)
                            self.wfile.write(mediaBinary)
                            self.wfile.flush() 
                        return        
            self._404()
            return
        # cached avatar images
        # Note that this comes before the busy flag to avoid conflicts
        if self.path.startswith('/avatars/'):
            mediaFilename= \
                self.server.baseDir+'/cache/'+self.path
            if os.path.isfile(mediaFilename):
                with open(mediaFilename, 'rb') as avFile:
                    mediaBinary = avFile.read()
                    if mediaFilename.endswith('.png'):
                        self._set_headers('image/png',len(mediaBinary),cookie)
                    elif mediaFilename.endswith('.jpg'):
                        self._set_headers('image/jpeg',len(mediaBinary),cookie)
                    elif mediaFilename.endswith('.gif'):
                        self._set_headers('image/gif',len(mediaBinary),cookie)
                    else:
                        self._404()
                        return
                    self.wfile.write(mediaBinary)
                    self.wfile.flush() 
                    return        
            self._404()
            return
        # show avatar or background image
        # Note that this comes before the busy flag to avoid conflicts
        if '/users/' in self.path:
            if self.path.endswith('.png') or \
               self.path.endswith('.jpg') or \
               self.path.endswith('.gif'):
                avatarStr=self.path.split('/users/')[1]
                if '/' in avatarStr:
                    avatarNickname=avatarStr.split('/')[0]
                    avatarFile=avatarStr.split('/')[1]
                    avatarFilename= \
                        self.server.baseDir+'/accounts/'+ \
                        avatarNickname+'@'+ \
                        self.server.domain+'/'+avatarFile
                    if os.path.isfile(avatarFilename):
                        mediaImageType='png'
                        if avatarFile.endswith('.png'):
                            mediaImageType='png'
                        elif avatarFile.endswith('.jpg'):
                            mediaImageType='jpeg'
                        else:
                            mediaImageType='gif'
                        with open(avatarFilename, 'rb') as avFile:
                            mediaBinary = avFile.read()
                            self._set_headers('image/'+mediaImageType,len(mediaBinary),cookie)
                            self.wfile.write(mediaBinary)
                            self.wfile.flush() 
                        return

        # This busy state helps to avoid flooding
        # Resources which are expected to be called from a web page
        # should be above this
        if self.server.GETbusy:
            currTimeGET=int(time.time())
            if currTimeGET-self.server.lastGET==0:
                if self.server.debug:
                    print('DEBUG: GET Busy')
                self.send_response(429)                    
                self.end_headers()
                return
            self.server.lastGET=currTimeGET
        self.server.GETbusy=True

        if not self._permittedDir(self.path):
            if self.server.debug:
                print('DEBUG: GET Not permitted')
            self._404()
            self.server.GETbusy=False
            return
        # get webfinger endpoint for a person
        if self._webfinger():
            self.server.GETbusy=False
            return

        if self.path.startswith('/login') or self.path=='/':
            # request basic auth
            msg=htmlLogin(self.server.translate,self.server.baseDir).encode('utf-8')
            self._login_headers('text/html',len(msg))
            self.wfile.write(msg)
            self.server.GETbusy=False
            return

        # hashtag search
        if self.path.startswith('/tags/'):
            pageNumber=1
            if '?page=' in self.path:
                pageNumberStr=self.path.split('?page=')[1]
                if pageNumberStr.isdigit():
                    pageNumber=int(pageNumberStr)
            hashtag=self.path.split('/tags/')[1]
            if '?page=' in hashtag:
                hashtag=hashtag.split('?page=')[0]
            if isBlockedHashtag(self.server.baseDir,hashtag):
                msg=htmlHashtagBlocked(self.server.baseDir).encode('utf-8')
                self._login_headers('text/html',len(msg))
                self.wfile.write(msg)
                self.server.GETbusy=False
                return
            hashtagStr= \
                htmlHashtagSearch(self.server.translate, \
                                  self.server.baseDir,hashtag,pageNumber, \
                                  maxPostsInFeed,self.server.session, \
                                  self.server.cachedWebfingers, \
                                  self.server.personCache, \
                                  self.server.httpPrefix, \
                                  self.server.projectVersion)
            if hashtagStr:
                msg=hashtagStr.encode()
                self._set_headers('text/html',len(msg),cookie)
                self.wfile.write(msg)
            else:
                originPathStr=self.path.split('/tags/')[0]
                self._redirect_headers(originPathStr+'/search',cookie)                
            self.server.GETbusy=False
            return

        # search for a fediverse address, shared item or emoji from the web interface by selecting search icon
        if htmlGET and '/users/' in self.path:
           if self.path.endswith('/search'):
               # show the search screen
               msg=htmlSearch(self.server.translate, \
                              self.server.baseDir,self.path).encode()
               self._set_headers('text/html',len(msg),cookie)
               self.wfile.write(msg)
               self.server.GETbusy=False
               return

        # Show the calendar for a user
        if htmlGET and '/users/' in self.path:
           if '/calendar' in self.path:
               # show the calendar screen
               msg=htmlCalendar(self.server.translate, \
                                self.server.baseDir,self.path).encode()
               self._set_headers('text/html',len(msg),cookie)
               self.wfile.write(msg)
               self.server.GETbusy=False
               return

        # search for emoji by name
        if htmlGET and '/users/' in self.path:
           if self.path.endswith('/searchemoji'):
               # show the search screen
               msg=htmlSearchEmojiTextEntry(self.server.translate, \
                                            self.server.baseDir, \
                                            self.path).encode()
               self._set_headers('text/html',len(msg),cookie)
               self.wfile.write(msg)
               self.server.GETbusy=False
               return

        # announce/repeat from the web interface
        if htmlGET and '?repeat=' in self.path:
            pageNumber=1
            repeatUrl=self.path.split('?repeat=')[1]
            if '?' in repeatUrl:
                repeatUrl=repeatUrl.split('?')[0]
            if '?page=' in self.path:
                pageNumberStr=self.path.split('?page=')[1]
                if '?' in pageNumberStr:
                    pageNumberStr=pageNumberStr.split('?')[0]
                if pageNumberStr.isdigit():
                    pageNumber=int(pageNumberStr)                
            timelineStr='inbox'
            if '?tl=' in self.path:
                timelineStr=self.path.split('?tl=')[1]
                if '?' in timelineStr:
                    timelineStr=timelineStr.split('?')[0]
            actor=self.path.split('?repeat=')[0]
            self.postToNickname=getNicknameFromActor(actor)
            if not self.postToNickname:
                print('WARN: unable to find nickname in '+actor)
                self.server.GETbusy=False
                self._redirect_headers(actor+'/'+timelineStr+'?page='+str(pageNumber),cookie)
                return                
            if not self.server.session:
                self.server.session= \
                    createSession(self.server.domain,self.server.port,self.server.useTor)                
            announceJson= \
                createAnnounce(self.server.session, \
                               self.server.baseDir, \
                               self.server.federationList, \
                               self.postToNickname, \
                               self.server.domain,self.server.port, \
                               'https://www.w3.org/ns/activitystreams#Public', \
                               None,self.server.httpPrefix, \
                               repeatUrl,False,False, \
                               self.server.sendThreads, \
                               self.server.postLog, \
                               self.server.personCache, \
                               self.server.cachedWebfingers, \
                               self.server.debug, \
                               self.server.projectVersion)
            if announceJson:
                self._postToOutboxThread(announceJson)
            self.server.GETbusy=False
            self._redirect_headers(actor+'/'+timelineStr+'?page='+str(pageNumber),cookie)
            return

        # undo an announce/repeat from the web interface
        if htmlGET and '?unrepeat=' in self.path:
            pageNumber=1
            repeatUrl=self.path.split('?unrepeat=')[1]
            if '?' in repeatUrl:
                repeatUrl=repeatUrl.split('?')[0]
            if '?page=' in self.path:
                pageNumberStr=self.path.split('?page=')[1]
                if '?' in pageNumberStr:
                    pageNumberStr=pageNumberStr.split('?')[0]
                if pageNumberStr.isdigit():
                    pageNumber=int(pageNumberStr)                
            timelineStr='inbox'
            if '?tl=' in self.path:
                timelineStr=self.path.split('?tl=')[1]
                if '?' in timelineStr:
                    timelineStr=timelineStr.split('?')[0]
            actor=self.path.split('?unrepeat=')[0]
            self.postToNickname=getNicknameFromActor(actor)
            if not self.postToNickname:
                print('WARN: unable to find nickname in '+actor)
                self.server.GETbusy=False
                self._redirect_headers(actor+'/'+timelineStr+'?page='+str(pageNumber),cookie)
                return                
            if not self.server.session:
                self.server.session= \
                    createSession(self.server.domain,self.server.port,self.server.useTor)
            undoAnnounceActor=self.server.httpPrefix+'://'+self.server.domainFull+'/users/'+self.postToNickname
            newUndoAnnounce = {
                "@context": "https://www.w3.org/ns/activitystreams",
                'actor': undoAnnounceActor,
                'type': 'Undo',
                'cc': [undoAnnounceActor+'/followers'],
                'to': ['https://www.w3.org/ns/activitystreams#Public'],
                'object': {
                    'actor': undoAnnounceActor,
                    'cc': [undoAnnounceActor+'/followers'],
                    'object': repeatUrl,
                    'to': ['https://www.w3.org/ns/activitystreams#Public'],
                    'type': 'Announce'
                }
            }                
            self._postToOutboxThread(newUndoAnnounce)
            self.server.GETbusy=False
            self._redirect_headers(actor+'/'+timelineStr+'?page='+str(pageNumber),cookie)
            return

        # send a follow request approval from the web interface
        if authorized and '/followapprove=' in self.path and self.path.startswith('/users/'):
            originPathStr=self.path.split('/followapprove=')[0]
            followerNickname=originPathStr.replace('/users/','')
            followingHandle=self.path.split('/followapprove=')[1]
            if '@' in followingHandle:
                if not self.server.session:
                    self.server.session= \
                        createSession(self.server.domain,self.server.port,self.server.useTor)
                manualApproveFollowRequest(self.server.session, \
                                           self.server.baseDir, \
                                           self.server.httpPrefix, \
                                           followerNickname,self.server.domain,self.server.port, \
                                           followingHandle, \
                                           self.server.federationList, \
                                           self.server.sendThreads, \
                                           self.server.postLog, \
                                           self.server.cachedWebfingers, \
                                           self.server.personCache, \
                                           self.server.acceptedCaps, \
                                           self.server.debug, \
                                           self.server.projectVersion)
            self._redirect_headers(originPathStr,cookie)
            self.server.GETbusy=False
            return

        # deny a follow request from the web interface
        if authorized and '/followdeny=' in self.path and self.path.startswith('/users/'):
            originPathStr=self.path.split('/followdeny=')[0]
            followerNickname=originPathStr.replace('/users/','')
            followingHandle=self.path.split('/followdeny=')[1]
            if '@' in followingHandle:
                manualDenyFollowRequest(self.server.session, \
                                        self.server.baseDir, \
                                        self.server.httpPrefix, \
                                        followerNickname,self.server.domain,self.server.port, \
                                        followingHandle, \
                                        self.server.federationList, \
                                        self.server.sendThreads, \
                                        self.server.postLog, \
                                        self.server.cachedWebfingers, \
                                        self.server.personCache, \
                                        self.server.debug, \
                                        self.server.projectVersion)
            self._redirect_headers(originPathStr,cookie)
            self.server.GETbusy=False
            return

        # like from the web interface icon
        if htmlGET and '?like=' in self.path and '/statuses/' in self.path:
            pageNumber=1
            likeUrl=self.path.split('?like=')[1]
            if '?' in likeUrl:
                likeUrl=likeUrl.split('?')[0]
            actor=self.path.split('?like=')[0]
            if '?page=' in self.path:
                pageNumberStr=self.path.split('?page=')[1]
                if '?' in pageNumberStr:
                    pageNumberStr=pageNumberStr.split('?')[0]
                if pageNumberStr.isdigit():
                    pageNumber=int(pageNumberStr)
            timelineStr='inbox'
            if '?tl=' in self.path:
                timelineStr=self.path.split('?tl=')[1]
                if '?' in timelineStr:
                    timelineStr=timelineStr.split('?')[0]
                
            self.postToNickname=getNicknameFromActor(actor)
            if not self.postToNickname:
                print('WARN: unable to find nickname in '+actor)
                self.server.GETbusy=False
                self._redirect_headers(actor+'/'+timelineStr+'?page='+str(pageNumber),cookie)
                return                
            if not self.server.session:
                self.server.session= \
                    createSession(self.server.domain,self.server.port,self.server.useTor)
            likeActor=self.server.httpPrefix+'://'+self.server.domainFull+'/users/'+self.postToNickname
            actorLiked=likeUrl.split('/statuses/')[0]
            likeJson= {
                "@context": "https://www.w3.org/ns/activitystreams",
                'type': 'Like',
                'actor': likeActor,
                'object': likeUrl
            }    
            self._postToOutboxThread(likeJson)
            self.server.GETbusy=False
            self._redirect_headers(actor+'/'+timelineStr+'?page='+str(pageNumber),cookie)
            return

        # undo a like from the web interface icon
        if htmlGET and '?unlike=' in self.path and '/statuses/' in self.path:
            pageNumber=1
            likeUrl=self.path.split('?unlike=')[1]
            if '?' in likeUrl:
                likeUrl=likeUrl.split('?')[0]
            if '?page=' in self.path:
                pageNumberStr=self.path.split('?page=')[1]
                if '?' in pageNumberStr:
                    pageNumberStr=pageNumberStr.split('?')[0]
                if pageNumberStr.isdigit():
                    pageNumber=int(pageNumberStr)
            timelineStr='inbox'
            if '?tl=' in self.path:
                timelineStr=self.path.split('?tl=')[1]
                if '?' in timelineStr:
                    timelineStr=timelineStr.split('?')[0]
            actor=self.path.split('?unlike=')[0]
            self.postToNickname=getNicknameFromActor(actor)
            if not self.postToNickname:
                print('WARN: unable to find nickname in '+actor)
                self.server.GETbusy=False
                self._redirect_headers(actor+'/'+timelineStr+'?page='+str(pageNumber),cookie)
                return                
            if not self.server.session:
                self.server.session= \
                    createSession(self.server.domain,self.server.port,self.server.useTor)
            undoActor=self.server.httpPrefix+'://'+self.server.domainFull+'/users/'+self.postToNickname
            actorLiked=likeUrl.split('/statuses/')[0]
            undoLikeJson= {
                "@context": "https://www.w3.org/ns/activitystreams",
                'type': 'Undo',
                'actor': undoActor,
                'object': {
                    'type': 'Like',
                    'actor': undoActor,
                    'object': likeUrl
                }
            }
            self._postToOutboxThread(undoLikeJson)
            self.server.GETbusy=False
            self._redirect_headers(actor+'/'+timelineStr+'?page='+str(pageNumber),cookie)
            return

        # delete a post from the web interface icon
        if htmlGET and '?delete=' in self.path:
            pageNumber=1
            if '?page=' in self.path:
                pageNumberStr=self.path.split('?page=')[1]
                if '?' in pageNumberStr:                
                    pageNumberStr=pageNumberStr.split('?')[0]
                if pageNumberStr.isdigit():
                    pageNumber=int(pageNumberStr)
            deleteUrl=self.path.split('?delete=')[1]
            if '?' in deleteUrl:                
                deleteUrl=deleteUrl.split('?')[0]
            actor=self.server.httpPrefix+'://'+self.server.domainFull+self.path.split('?delete=')[0]
            if self.server.allowDeletion or \
               deleteUrl.startswith(actor):
                if self.server.debug:
                    print('DEBUG: deleteUrl='+deleteUrl)
                    print('DEBUG: actor='+actor)
                if actor not in deleteUrl:
                    # You can only delete your own posts
                    self.server.GETbusy=False
                    self._redirect_headers(actor+'/inbox',cookie)
                    return
                self.postToNickname=getNicknameFromActor(actor)
                if not self.postToNickname:
                    print('WARN: unable to find nickname in '+actor)
                    self.server.GETbusy=False
                    self._redirect_headers(actor+'/inbox',cookie)
                    return                    
                if not self.server.session:
                    self.server.session= \
                        createSession(self.server.domain,self.server.port, \
                                      self.server.useTor)

                deleteStr= \
                    htmlDeletePost(self.server.translate,pageNumber, \
                                   self.server.session,self.server.baseDir, \
                                   deleteUrl,self.server.httpPrefix, \
                                   __version__,self.server.cachedWebfingers, \
                                   self.server.personCache)
                if deleteStr:
                    self._set_headers('text/html',len(deleteStr),cookie)
                    self.wfile.write(deleteStr.encode())
                    self.server.GETbusy=False
                    return
            self.server.GETbusy=False
            self._redirect_headers(actor+'/inbox',cookie)
            return

        # reply from the web interface icon
        inReplyToUrl=None
        replyWithDM=False
        replyToList=[]
        replyPageNumber=1
        shareDescription=None
        if htmlGET:
            # public reply
            if '?replyto=' in self.path:
                inReplyToUrl=self.path.split('?replyto=')[1]
                if '?' in inReplyToUrl:
                    mentionsList=inReplyToUrl.split('?')
                    for m in mentionsList:
                        if m.startswith('mention='):
                            replyHandle=m.replace('mention=','')
                            if replyHandle not in replyToList:
                                replyToList.append(replyHandle)
                        if m.startswith('page='):
                            replyPageStr=m.replace('page=','')
                            if replyPageStr.isdigit():
                                replyPageNumber=int(replyPageStr)
                    inReplyToUrl=mentionsList[0]
                self.path=self.path.split('?replyto=')[0]+'/newpost'
                if self.server.debug:
                    print('DEBUG: replyto path '+self.path)

            # reply to followers
            if '?replyfollowers=' in self.path:
                inReplyToUrl=self.path.split('?replyfollowers=')[1]
                if '?' in inReplyToUrl:
                    mentionsList=inReplyToUrl.split('?')
                    for m in mentionsList:
                        if m.startswith('mention='):
                            replyHandle=m.replace('mention=','')
                            if m.replace('mention=','') not in replyToList:
                                replyToList.append(replyHandle)
                        if m.startswith('page='):
                            replyPageStr=m.replace('page=','')
                            if replyPageStr.isdigit():
                                replyPageNumber=int(replyPageStr)
                    inReplyToUrl=mentionsList[0]
                self.path=self.path.split('?replyfollowers=')[0]+'/newfollowers'
                if self.server.debug:
                    print('DEBUG: replyfollowers path '+self.path)

            # replying as a direct message, for moderation posts or the dm timeline
            if '?replydm=' in self.path:
                inReplyToUrl=self.path.split('?replydm=')[1]
                if '?' in inReplyToUrl:
                    mentionsList=inReplyToUrl.split('?')
                    for m in mentionsList:
                        if m.startswith('mention='):
                            replyHandle=m.replace('mention=','')
                            if m.replace('mention=','') not in replyToList:
                                replyToList.append(m.replace('mention=',''))
                        if m.startswith('page='):
                            replyPageStr=m.replace('page=','')
                            if replyPageStr.isdigit():
                                replyPageNumber=int(replyPageStr)
                    inReplyToUrl=mentionsList[0]
                    if inReplyToUrl.startswith('sharedesc:'):
                        shareDescription=inReplyToUrl.replace('sharedesc:','').replace('%20',' ').replace('%40','@').replace('%3A',':').replace('%23','#')
                self.path=self.path.split('?replydm=')[0]+'/newdm'
                if self.server.debug:
                    print('DEBUG: replydm path '+self.path)

            # edit profile in web interface
            if '/users/' in self.path and self.path.endswith('/editprofile'):
                msg=htmlEditProfile(self.server.translate, \
                                    self.server.baseDir, \
                                    self.path,self.server.domain, \
                                    self.server.port).encode()
                self._set_headers('text/html',len(msg),cookie)
                self.wfile.write(msg)
                self.server.GETbusy=False
                return

            # Various types of new post in the web interface
            if '/users/' in self.path and \
               (self.path.endswith('/newpost') or \
                self.path.endswith('/newunlisted') or \
                self.path.endswith('/newfollowers') or \
                self.path.endswith('/newdm') or \
                self.path.endswith('/newreport') or \
                self.path.endswith('/newshare')):
                msg=htmlNewPost(self.server.translate, \
                                self.server.baseDir, \
                                self.path,inReplyToUrl, \
                                replyToList, \
                                shareDescription, \
                                replyPageNumber).encode()
                self._set_headers('text/html',len(msg),cookie)
                self.wfile.write(msg)
                self.server.GETbusy=False
                return

        # get an individual post from the path /@nickname/statusnumber
        if '/@' in self.path:
            namedStatus=self.path.split('/@')[1]
            if '/' not in namedStatus:
                # show actor
                nickname=namedStatus
            else:
                postSections=namedStatus.split('/')
                if len(postSections)==2:
                    nickname=postSections[0]
                    statusNumber=postSections[1]
                    if len(statusNumber)>10 and statusNumber.isdigit():                        
                        postFilename= \
                            self.server.baseDir+'/accounts/'+nickname+'@'+self.server.domain+'/outbox/'+ \
                            self.server.httpPrefix+':##'+self.server.domainFull+'#users#'+nickname+'#statuses#'+statusNumber+'.json'
                        if os.path.isfile(postFilename):
                            postJsonObject={}
                            loadedPost=False
                            try:
                                with open(postFilename, 'r') as fp:
                                    postJsonObject=commentjson.load(fp)
                                    loadedPost=True
                            except Exception as e:
                                print(e)
                            if loadedPost:                            
                                # Only authorized viewers get to see likes on posts
                                # Otherwize marketers could gain more social graph info
                                if not authorized:
                                    if postJsonObject.get('likes'):
                                        postJsonObject['likes']={'items': []}
                                if self._requestHTTP():
                                    msg= \
                                        htmlIndividualPost(self.server.translate, \
                                                           self.server.session, \
                                                           self.server.cachedWebfingers,self.server.personCache, \
                                                           nickname,self.server.domain,self.server.port, \
                                                           authorized,postJsonObject, \
                                                           self.server.httpPrefix, \
                                                           self.server.projectVersion).encode('utf-8')
                                    self._set_headers('text/html',len(msg),cookie)                    
                                    self.wfile.write(msg)
                                else:
                                    if self._fetchAuthenticated():
                                        msg=json.dumps(postJsonObject).encode('utf-8')
                                        self._set_headers('application/json',len(msg),None)
                                        self.wfile.write(msg)
                                    else:
                                        self._404()
                            self.server.GETbusy=False
                            return
                        else:
                            self._404()
                            self.server.GETbusy=False
                            return

        # get replies to a post /users/nickname/statuses/number/replies
        if self.path.endswith('/replies') or '/replies?page=' in self.path:
            if '/statuses/' in self.path and '/users/' in self.path:
                namedStatus=self.path.split('/users/')[1]
                if '/' in namedStatus:
                    postSections=namedStatus.split('/')
                    if len(postSections)>=4:
                        if postSections[3].startswith('replies'):
                            nickname=postSections[0]
                            statusNumber=postSections[2]
                            if len(statusNumber)>10 and statusNumber.isdigit():
                                #get the replies file
                                boxname='outbox'
                                postDir=self.server.baseDir+'/accounts/'+nickname+'@'+self.server.domain+'/'+boxname
                                postRepliesFilename= \
                                    postDir+'/'+ \
                                    self.server.httpPrefix+':##'+self.server.domainFull+'#users#'+nickname+'#statuses#'+statusNumber+'.replies'
                                if not os.path.isfile(postRepliesFilename):
                                    # There are no replies, so show empty collection
                                    repliesJson = {
                                        '@context': 'https://www.w3.org/ns/activitystreams',
                                        'first': self.server.httpPrefix+'://'+self.server.domainFull+'/users/'+nickname+'/statuses/'+statusNumber+'/replies?page=true',
                                        'id': self.server.httpPrefix+'://'+self.server.domainFull+'/users/'+nickname+'/statuses/'+statusNumber+'/replies',
                                        'last': self.server.httpPrefix+'://'+self.server.domainFull+'/users/'+nickname+'/statuses/'+statusNumber+'/replies?page=true',
                                        'totalItems': 0,
                                        'type': 'OrderedCollection'}
                                    if self._requestHTTP():
                                        if not self.server.session:
                                            if self.server.debug:
                                                print('DEBUG: creating new session')
                                            self.server.session= \
                                                createSession(self.server.domain,self.server.port,self.server.useTor)
                                        msg=htmlPostReplies(self.server.translate, \
                                                            self.server.baseDir, \
                                                            self.server.session, \
                                                            self.server.cachedWebfingers, \
                                                            self.server.personCache, \
                                                            nickname, \
                                                            self.server.domain, \
                                                            self.server.port, \
                                                            repliesJson, \
                                                            self.server.httpPrefix, \
                                                            self.server.projectVersion).encode('utf-8')
                                        self._set_headers('text/html',len(msg),cookie)
                                        print('----------------------------------------------------')
                                        pprint(repliesJson)
                                        self.wfile.write(msg)
                                    else:
                                        if self._fetchAuthenticated():
                                            msg=json.dumps(repliesJson).encode('utf-8')
                                            self._set_headers('application/json',len(msg),None)
                                            self.wfile.write(msg)
                                        else:
                                            self._404()
                                    self.server.GETbusy=False
                                    return
                                else:
                                    # replies exist. Itterate through the text file containing message ids
                                    repliesJson = {
                                        '@context': 'https://www.w3.org/ns/activitystreams',
                                        'id': self.server.httpPrefix+'://'+self.server.domainFull+'/users/'+nickname+'/statuses/'+statusNumber+'?page=true',
                                        'orderedItems': [
                                        ],
                                        'partOf': self.server.httpPrefix+'://'+self.server.domainFull+'/users/'+nickname+'/statuses/'+statusNumber,
                                        'type': 'OrderedCollectionPage'}

                                    # populate the items list with replies
                                    populateRepliesJson(self.server.baseDir, \
                                                        nickname, \
                                                        self.server.domain, \
                                                        postRepliesFilename, \
                                                        authorized, \
                                                        repliesJson)

                                    # send the replies json
                                    if self._requestHTTP():
                                        if not self.server.session:
                                            if self.server.debug:
                                                print('DEBUG: creating new session')
                                            self.server.session= \
                                                createSession(self.server.domain,self.server.port,self.server.useTor)
                                        msg=htmlPostReplies(self.server.translate, \
                                                            self.server.baseDir, \
                                                            self.server.session, \
                                                            self.server.cachedWebfingers, \
                                                            self.server.personCache, \
                                                            nickname, \
                                                            self.server.domain, \
                                                            self.server.port, \
                                                            repliesJson, \
                                                            self.server.httpPrefix, \
                                                            self.server.projectVersion).encode('utf-8')
                                        self._set_headers('text/html',len(msg),cookie)
                                        self.wfile.write(msg)
                                    else:
                                        if self._fetchAuthenticated():
                                            msg=json.dumps(repliesJson).encode('utf-8')
                                            self._set_headers('application/json',len(msg),None)
                                            self.wfile.write(msg)
                                        else:
                                            self._404()
                                    self.server.GETbusy=False
                                    return

        if self.path.endswith('/roles') and '/users/' in self.path:
            namedStatus=self.path.split('/users/')[1]
            if '/' in namedStatus:
                postSections=namedStatus.split('/')
                nickname=postSections[0]
                actorFilename=self.server.baseDir+'/accounts/'+nickname+'@'+self.server.domain+'.json'
                if os.path.isfile(actorFilename):
                    loadedActor=False
                    try:
                        with open(actorFilename, 'r') as fp:
                            actorJson=commentjson.load(fp)
                            loadedActor=True
                    except Exception as e:
                        print(e)
                    if loadedActor:                    
                        if actorJson.get('roles'):
                            if self._requestHTTP():
                                getPerson = \
                                    personLookup(self.server.domain,self.path.replace('/roles',''), \
                                                 self.server.baseDir)
                                if getPerson:
                                    msg=htmlProfile(self.server.translate, \
                                                    self.server.projectVersion, \
                                                    self.server.baseDir, \
                                                    self.server.httpPrefix, \
                                                    True, \
                                                    self.server.ocapAlways, \
                                                    getPerson,'roles', \
                                                    self.server.session, \
                                                    self.server.cachedWebfingers, \
                                                    self.server.personCache, \
                                                    actorJson['roles'], \
                                                    None,None).encode('utf-8')
                                    self._set_headers('text/html',len(msg),cookie)
                                    self.wfile.write(msg)     
                            else:
                                if self._fetchAuthenticated():
                                    msg=json.dumps(actorJson['roles']).encode('utf-8')
                                    self._set_headers('application/json',len(msg),None)
                                    self.wfile.write(msg)
                                else:
                                    self._404()
                            self.server.GETbusy=False
                            return

        # show skills on the profile page
        if self.path.endswith('/skills') and '/users/' in self.path:
            namedStatus=self.path.split('/users/')[1]
            if '/' in namedStatus:
                postSections=namedStatus.split('/')
                nickname=postSections[0]
                actorFilename=self.server.baseDir+'/accounts/'+nickname+'@'+self.server.domain+'.json'
                if os.path.isfile(actorFilename):
                    loadedActor=False
                    try:
                        with open(actorFilename, 'r') as fp:
                            actorJson=commentjson.load(fp)
                            loadedActor=True
                    except Exception as e:
                        print(e)
                    if loadedActor:                    
                        if actorJson.get('skills'):
                            if self._requestHTTP():
                                getPerson = \
                                    personLookup(self.server.domain,self.path.replace('/skills',''), \
                                                 self.server.baseDir)
                                if getPerson:
                                    msg=htmlProfile(self.server.translate, \
                                                    self.server.projectVersion, \
                                                    self.server.baseDir, \
                                                    self.server.httpPrefix, \
                                                    True, \
                                                    self.server.ocapAlways, \
                                                    getPerson,'skills', \
                                                    self.server.session, \
                                                    self.server.cachedWebfingers, \
                                                    self.server.personCache, \
                                                    actorJson['skills'], \
                                                    None,None).encode('utf-8')
                                    self._set_headers('text/html',len(msg),cookie)
                                    self.wfile.write(msg)     
                            else:
                                if self._fetchAuthenticated():
                                    msg=json.dumps(actorJson['skills']).encode('utf-8')
                                    self._set_headers('application/json',len(msg),None)
                                    self.wfile.write(msg)
                                else:
                                    self._404()
                            self.server.GETbusy=False
                            return
            actor=self.path.replace('/skills','')
            self._redirect_headers(actor,cookie)
            self.server.GETbusy=False
            return

        # get an individual post from the path /users/nickname/statuses/number
        if '/statuses/' in self.path and '/users/' in self.path:
            namedStatus=self.path.split('/users/')[1]
            if '/' in namedStatus:
                postSections=namedStatus.split('/')
                if len(postSections)>=3:
                    nickname=postSections[0]
                    statusNumber=postSections[2]
                    if len(statusNumber)>10 and statusNumber.isdigit():
                        postFilename= \
                            self.server.baseDir+'/accounts/'+nickname+'@'+self.server.domain+'/outbox/'+ \
                            self.server.httpPrefix+':##'+self.server.domainFull+'#users#'+nickname+'#statuses#'+statusNumber+'.json'
                        if os.path.isfile(postFilename):
                            postJsonObject={}
                            readPost=False
                            try:
                                with open(postFilename, 'r') as fp:
                                    postJsonObject=commentjson.load(fp)
                                    readPost=True
                            except Exception as e:
                                print(e)
                            if not readPost:
                                self.send_response(429)
                                self.end_headers()
                                self.server.GETbusy=False
                                return
                            else:
                                # Only authorized viewers get to see likes on posts
                                # Otherwize marketers could gain more social graph info
                                if not authorized:
                                    if postJsonObject.get('likes'):
                                        postJsonObject['likes']={'items': []}                                    
                                if self._requestHTTP():
                                    msg=htmlIndividualPost(self.server.translate, \
                                                           self.server.baseDir, \
                                                           self.server.session, \
                                                           self.server.cachedWebfingers,self.server.personCache, \
                                                           nickname,self.server.domain,self.server.port, \
                                                           authorized,postJsonObject, \
                                                           self.server.httpPrefix, \
                                                           self.server.projectVersion).encode('utf-8')
                                    self._set_headers('text/html',len(msg),cookie)
                                    self.wfile.write(msg)
                                else:
                                    if self._fetchAuthenticated():
                                        msg=json.dumps(postJsonObject).encode('utf-8')
                                        self._set_headers('application/json',len(msg),None)
                                        self.wfile.write(msg)
                                    else:
                                        self._404()
                            self.server.GETbusy=False
                            return
                        else:
                            self._404()
                            self.server.GETbusy=False
                            return

        # get the inbox for a given person
        if self.path.endswith('/inbox') or '/inbox?page=' in self.path:
            if '/users/' in self.path:
                if authorized:
                    inboxFeed=personBoxJson(self.server.session, \
                                            self.server.baseDir, \
                                            self.server.domain, \
                                            self.server.port, \
                                            self.path, \
                                            self.server.httpPrefix, \
                                            maxPostsInFeed, 'inbox', \
                                            True,self.server.ocapAlways)
                    if inboxFeed:
                        if self._requestHTTP():
                            nickname=self.path.replace('/users/','').replace('/inbox','')
                            pageNumber=1
                            if '?page=' in nickname:
                                pageNumber=nickname.split('?page=')[1]
                                nickname=nickname.split('?page=')[0]
                                if pageNumber.isdigit():
                                    pageNumber=int(pageNumber)
                                else:
                                    pageNumber=1                                
                            if 'page=' not in self.path:
                                # if no page was specified then show the first
                                inboxFeed=personBoxJson(self.server.session, \
                                                        self.server.baseDir, \
                                                        self.server.domain, \
                                                        self.server.port, \
                                                        self.path+'?page=1', \
                                                        self.server.httpPrefix, \
                                                        maxPostsInFeed, 'inbox', \
                                                        True,self.server.ocapAlways)
                            msg=htmlInbox(self.server.translate, \
                                          pageNumber,maxPostsInFeed, \
                                          self.server.session, \
                                          self.server.baseDir, \
                                          self.server.cachedWebfingers, \
                                          self.server.personCache, \
                                          nickname, \
                                          self.server.domain, \
                                          self.server.port, \
                                          inboxFeed, \
                                          self.server.allowDeletion, \
                                          self.server.httpPrefix, \
                                          self.server.projectVersion).encode('utf-8')
                            self._set_headers('text/html',len(msg),cookie)
                            self.wfile.write(msg)
                        else:
                            # don't need authenticated fetch here because there is
                            # already the authorization check
                            msg=json.dumps(inboxFeed).encode('utf-8')
                            self._set_headers('application/json',len(msg),None)
                            self.wfile.write(msg)
                        self.server.GETbusy=False
                        return
                else:
                    if self.server.debug:
                        nickname=self.path.replace('/users/','').replace('/inbox','')
                        print('DEBUG: '+nickname+ \
                              ' was not authorized to access '+self.path)
            if self.path!='/inbox':
                # not the shared inbox
                if self.server.debug:
                    print('DEBUG: GET access to inbox is unauthorized')
                self.send_response(405)
                self.end_headers()
                self.server.GETbusy=False
                return

        # get the direct messages for a given person
        if self.path.endswith('/dm') or '/dm?page=' in self.path:
            if '/users/' in self.path:
                if authorized:
                    inboxDMFeed=personBoxJson(self.server.session, \
                                              self.server.baseDir, \
                                              self.server.domain, \
                                              self.server.port, \
                                              self.path, \
                                              self.server.httpPrefix, \
                                              maxPostsInFeed, 'dm', \
                                              True,self.server.ocapAlways)
                    if inboxDMFeed:
                        if self._requestHTTP():
                            nickname=self.path.replace('/users/','').replace('/dm','')
                            pageNumber=1
                            if '?page=' in nickname:
                                pageNumber=nickname.split('?page=')[1]
                                nickname=nickname.split('?page=')[0]
                                if pageNumber.isdigit():
                                    pageNumber=int(pageNumber)
                                else:
                                    pageNumber=1                                
                            if 'page=' not in self.path:
                                # if no page was specified then show the first
                                inboxDMFeed=personBoxJson(self.server.session, \
                                                          self.server.baseDir, \
                                                          self.server.domain, \
                                                          self.server.port, \
                                                          self.path+'?page=1', \
                                                          self.server.httpPrefix, \
                                                          maxPostsInFeed, 'dm', \
                                                          True,self.server.ocapAlways)
                            msg=htmlInboxDMs(self.server.translate, \
                                             pageNumber,maxPostsInFeed, \
                                             self.server.session, \
                                             self.server.baseDir, \
                                             self.server.cachedWebfingers, \
                                             self.server.personCache, \
                                             nickname, \
                                             self.server.domain, \
                                             self.server.port, \
                                             inboxDMFeed, \
                                             self.server.allowDeletion, \
                                             self.server.httpPrefix, \
                                             self.server.projectVersion).encode('utf-8')
                            self._set_headers('text/html',len(msg),cookie)
                            self.wfile.write(msg)
                        else:
                            # don't need authenticated fetch here because there is
                            # already the authorization check
                            msg=json.dumps(inboxDMFeed).encode('utf-8')
                            self._set_headers('application/json',len(msg),None)
                            self.wfile.write(msg)
                        self.server.GETbusy=False
                        return
                else:
                    if self.server.debug:
                        nickname=self.path.replace('/users/','').replace('/dm','')
                        print('DEBUG: '+nickname+ \
                              ' was not authorized to access '+self.path)
            if self.path!='/dm':
                # not the DM inbox
                if self.server.debug:
                    print('DEBUG: GET access to inbox is unauthorized')
                self.send_response(405)
                self.end_headers()
                self.server.GETbusy=False
                return

        # get the replies for a given person
        if self.path.endswith('/tlreplies') or '/tlreplies?page=' in self.path:
            if '/users/' in self.path:
                if authorized:
                    inboxRepliesFeed= \
                        personBoxJson(self.server.session, \
                                      self.server.baseDir, \
                                      self.server.domain, \
                                      self.server.port, \
                                      self.path, \
                                      self.server.httpPrefix, \
                                      maxPostsInFeed, 'tlreplies', \
                                      True,self.server.ocapAlways)
                    if not inboxRepliesFeed:
                        inboxRepliesFeed=[]
                    if self._requestHTTP():
                        nickname=self.path.replace('/users/','').replace('/tlreplies','')
                        pageNumber=1
                        if '?page=' in nickname:
                            pageNumber=nickname.split('?page=')[1]
                            nickname=nickname.split('?page=')[0]
                            if pageNumber.isdigit():
                                pageNumber=int(pageNumber)
                            else:
                                pageNumber=1
                        if 'page=' not in self.path:
                            # if no page was specified then show the first
                            inboxRepliesFeed= \
                                personBoxJson(self.server.session, \
                                              self.server.baseDir, \
                                              self.server.domain, \
                                              self.server.port, \
                                              self.path+'?page=1', \
                                              self.server.httpPrefix, \
                                              maxPostsInFeed, 'tlreplies', \
                                              True,self.server.ocapAlways)
                        msg=htmlInboxReplies(self.server.translate, \
                                             pageNumber,maxPostsInFeed, \
                                             self.server.session, \
                                             self.server.baseDir, \
                                             self.server.cachedWebfingers, \
                                             self.server.personCache, \
                                             nickname, \
                                             self.server.domain, \
                                             self.server.port, \
                                             inboxRepliesFeed, \
                                             self.server.allowDeletion, \
                                             self.server.httpPrefix, \
                                             self.server.projectVersion).encode('utf-8')
                        self._set_headers('text/html',len(msg),cookie)
                        self.wfile.write(msg)
                    else:
                        # don't need authenticated fetch here because there is
                        # already the authorization check
                        msg=json.dumps(inboxRepliesFeed).encode('utf-8')
                        self._set_headers('application/json',len(msg),None)
                        self.wfile.write(msg)
                    self.server.GETbusy=False
                    return
                else:
                    if self.server.debug:
                        nickname=self.path.replace('/users/','').replace('/tlreplies','')
                        print('DEBUG: '+nickname+ \
                              ' was not authorized to access '+self.path)
            if self.path!='/tlreplies':
                # not the replies inbox
                if self.server.debug:
                    print('DEBUG: GET access to inbox is unauthorized')
                self.send_response(405)
                self.end_headers()
                self.server.GETbusy=False
                return

        # get the media for a given person
        if self.path.endswith('/tlmedia') or '/tlmedia?page=' in self.path:
            if '/users/' in self.path:
                if authorized:
                    inboxMediaFeed= \
                        personBoxJson(self.server.session, \
                                      self.server.baseDir, \
                                      self.server.domain, \
                                      self.server.port, \
                                      self.path, \
                                      self.server.httpPrefix, \
                                      maxPostsInMediaFeed, 'tlmedia', \
                                      True,self.server.ocapAlways)
                    if not inboxMediaFeed:
                        inboxMediaFeed=[]
                    if self._requestHTTP():
                        nickname=self.path.replace('/users/','').replace('/tlmedia','')
                        pageNumber=1
                        if '?page=' in nickname:
                            pageNumber=nickname.split('?page=')[1]
                            nickname=nickname.split('?page=')[0]
                            if pageNumber.isdigit():
                                pageNumber=int(pageNumber)
                            else:
                                pageNumber=1
                        if 'page=' not in self.path:
                            # if no page was specified then show the first
                            inboxMediaFeed= \
                                personBoxJson(self.server.session, \
                                              self.server.baseDir, \
                                              self.server.domain, \
                                              self.server.port, \
                                              self.path+'?page=1', \
                                              self.server.httpPrefix, \
                                              maxPostsInMediaFeed, 'tlmedia', \
                                              True,self.server.ocapAlways)
                        msg=htmlInboxMedia(self.server.translate, \
                                           pageNumber,maxPostsInMediaFeed, \
                                           self.server.session, \
                                           self.server.baseDir, \
                                           self.server.cachedWebfingers, \
                                           self.server.personCache, \
                                           nickname, \
                                           self.server.domain, \
                                           self.server.port, \
                                           inboxMediaFeed, \
                                           self.server.allowDeletion, \
                                           self.server.httpPrefix, \
                                           self.server.projectVersion).encode('utf-8')
                        self._set_headers('text/html',len(msg),cookie)
                        self.wfile.write(msg)
                    else:
                        # don't need authenticated fetch here because there is
                        # already the authorization check
                        msg=json.dumps(inboxMediaFeed).encode('utf-8')
                        self._set_headers('application/json',len(msg),None)
                        self.wfile.write(msg)
                    self.server.GETbusy=False
                    return
                else:
                    if self.server.debug:
                        nickname=self.path.replace('/users/','').replace('/tlmedia','')
                        print('DEBUG: '+nickname+ \
                              ' was not authorized to access '+self.path)
            if self.path!='/tlmedia':
                # not the media inbox
                if self.server.debug:
                    print('DEBUG: GET access to inbox is unauthorized')
                self.send_response(405)
                self.end_headers()
                self.server.GETbusy=False
                return

        # get outbox feed for a person
        outboxFeed=personBoxJson(self.server.session, \
                                 self.server.baseDir,self.server.domain, \
                                 self.server.port,self.path, \
                                 self.server.httpPrefix, \
                                 maxPostsInFeed, 'outbox', \
                                 authorized, \
                                 self.server.ocapAlways)
        if outboxFeed:
            if self._requestHTTP():
                nickname=self.path.replace('/users/','').replace('/outbox','')
                pageNumber=1
                if '?page=' in nickname:
                    pageNumber=nickname.split('?page=')[1]
                    nickname=nickname.split('?page=')[0]
                    if pageNumber.isdigit():
                        pageNumber=int(pageNumber)
                    else:
                        pageNumber=1
                if 'page=' not in self.path:
                    # if a page wasn't specified then show the first one
                    outboxFeed=personBoxJson(self.server.session, \
                                             self.server.baseDir,self.server.domain, \
                                             self.server.port,self.path+'?page=1', \
                                             self.server.httpPrefix, \
                                             maxPostsInFeed, 'outbox', \
                                             authorized, \
                                             self.server.ocapAlways)
                msg=htmlOutbox(self.server.translate, \
                               pageNumber,maxPostsInFeed, \
                               self.server.session, \
                               self.server.baseDir, \
                               self.server.cachedWebfingers, \
                               self.server.personCache, \
                               nickname, \
                               self.server.domain, \
                               self.server.port, \
                               outboxFeed, \
                               self.server.allowDeletion, \
                               self.server.httpPrefix, \
                               self.server.projectVersion).encode('utf-8')
                self._set_headers('text/html',len(msg),cookie)
                self.wfile.write(msg)
            else:
                if self._fetchAuthenticated():
                    msg=json.dumps(outboxFeed).encode('utf-8')
                    self._set_headers('application/json',len(msg),None)
                    self.wfile.write(msg)
                else:
                    self._404()
            self.server.GETbusy=False
            return

        # get the moderation feed for a moderator
        if self.path.endswith('/moderation') or '/moderation?page=' in self.path:
            if '/users/' in self.path:
                if authorized:
                    moderationFeed= \
                        personBoxJson(self.server.session, \
                                      self.server.baseDir, \
                                      self.server.domain, \
                                      self.server.port, \
                                      self.path, \
                                      self.server.httpPrefix, \
                                      maxPostsInFeed, 'moderation', \
                                      True,self.server.ocapAlways)
                    if moderationFeed:
                        if self._requestHTTP():
                            nickname=self.path.replace('/users/','').replace('/moderation','')
                            pageNumber=1
                            if '?page=' in nickname:
                                pageNumber=nickname.split('?page=')[1]
                                nickname=nickname.split('?page=')[0]
                                if pageNumber.isdigit():
                                    pageNumber=int(pageNumber)
                                else:
                                    pageNumber=1                                
                            if 'page=' not in self.path:
                                # if no page was specified then show the first
                                moderationFeed= \
                                    personBoxJson(self.server.session, \
                                                  self.server.baseDir, \
                                                  self.server.domain, \
                                                  self.server.port, \
                                                  self.path+'?page=1', \
                                                  self.server.httpPrefix, \
                                                  maxPostsInFeed, 'moderation', \
                                                  True,self.server.ocapAlways)
                            msg=htmlModeration(self.server.translate, \
                                               pageNumber,maxPostsInFeed, \
                                               self.server.session, \
                                               self.server.baseDir, \
                                               self.server.cachedWebfingers, \
                                               self.server.personCache, \
                                               nickname, \
                                               self.server.domain, \
                                               self.server.port, \
                                               moderationFeed, \
                                               True, \
                                               self.server.httpPrefix, \
                                               self.server.projectVersion).encode('utf-8')
                            self._set_headers('text/html',len(msg),cookie)
                            self.wfile.write(msg)
                        else:
                            # don't need authenticated fetch here because there is
                            # already the authorization check
                            msg=json.dumps(moderationFeed).encode('utf-8')
                            self._set_headers('application/json',len(msg),None)
                            self.wfile.write(msg)
                        self.server.GETbusy=False
                        return
                else:
                    if self.server.debug:
                        nickname=self.path.replace('/users/','').replace('/moderation','')
                        print('DEBUG: '+nickname+ \
                              ' was not authorized to access '+self.path)
            if self.server.debug:
                print('DEBUG: GET access to moderation feed is unauthorized')
            self.send_response(405)
            self.end_headers()
            self.server.GETbusy=False
            return
        
        shares=getSharesFeedForPerson(self.server.baseDir, \
                                      self.server.domain, \
                                      self.server.port,self.path, \
                                      self.server.httpPrefix, \
                                      sharesPerPage)
        if shares:
            if self._requestHTTP():
                pageNumber=1
                if '?page=' not in self.path:
                    searchPath=self.path
                    # get a page of shares, not the summary
                    shares=getSharesFeedForPerson(self.server.baseDir,self.server.domain, \
                                                  self.server.port,self.path+'?page=true', \
                                                  self.server.httpPrefix, \
                                                  sharesPerPage)
                else:
                    pageNumberStr=self.path.split('?page=')[1]
                    if pageNumberStr.isdigit():
                        pageNumber=int(pageNumberStr)
                    searchPath=self.path.split('?page=')[0]
                getPerson = personLookup(self.server.domain,searchPath.replace('/shares',''), \
                                         self.server.baseDir)
                if getPerson:
                    if not self.server.session:
                        if self.server.debug:
                            print('DEBUG: creating new session')
                        self.server.session= \
                            createSession(self.server.domain,self.server.port,self.server.useTor)
                    msg=htmlProfile(self.server.translate, \
                                    self.server.projectVersion, \
                                    self.server.baseDir, \
                                    self.server.httpPrefix, \
                                    authorized, \
                                    self.server.ocapAlways, \
                                    getPerson,'shares', \
                                    self.server.session, \
                                    self.server.cachedWebfingers, \
                                    self.server.personCache, \
                                    shares, \
                                    pageNumber,sharesPerPage).encode('utf-8')
                    self._set_headers('text/html',len(msg),cookie)
                    self.wfile.write(msg)                
                    self.server.GETbusy=False
                    return
            else:
                if self._fetchAuthenticated():
                    msg=json.dumps(shares).encode('utf-8')
                    self._set_headers('application/json',len(msg),None)
                    self.wfile.write(msg)
                else:
                    self._404()
                self.server.GETbusy=False
                return

        following=getFollowingFeed(self.server.baseDir,self.server.domain, \
                                   self.server.port,self.path, \
                                   self.server.httpPrefix, \
                                   authorized,followsPerPage)
        if following:
            if self._requestHTTP():
                pageNumber=1
                if '?page=' not in self.path:
                    searchPath=self.path
                    # get a page of following, not the summary
                    following=getFollowingFeed(self.server.baseDir,self.server.domain, \
                                               self.server.port,self.path+'?page=true', \
                                               self.server.httpPrefix, \
                                               authorized,followsPerPage)
                else:
                    pageNumberStr=self.path.split('?page=')[1]
                    if pageNumberStr.isdigit():
                        pageNumber=int(pageNumberStr)
                    searchPath=self.path.split('?page=')[0]
                getPerson = personLookup(self.server.domain,searchPath.replace('/following',''), \
                                         self.server.baseDir)
                if getPerson:
                    if not self.server.session:
                        if self.server.debug:
                            print('DEBUG: creating new session')
                        self.server.session= \
                            createSession(self.server.domain,self.server.port,self.server.useTor)

                    msg=htmlProfile(self.server.translate, \
                                    self.server.projectVersion, \
                                    self.server.baseDir, \
                                    self.server.httpPrefix, \
                                    authorized, \
                                    self.server.ocapAlways, \
                                    getPerson,'following', \
                                    self.server.session, \
                                    self.server.cachedWebfingers, \
                                    self.server.personCache, \
                                    following, \
                                    pageNumber,followsPerPage).encode('utf-8')
                    self._set_headers('text/html',len(msg),cookie)
                    self.wfile.write(msg)                
                    self.server.GETbusy=False
                    return
            else:
                if self._fetchAuthenticated():
                    msg=json.dumps(following).encode('utf-8')
                    self._set_headers('application/json',len(msg),None)
                    self.wfile.write(msg)
                else:
                    self._404()
                self.server.GETbusy=False
                return
        followers=getFollowingFeed(self.server.baseDir,self.server.domain, \
                                   self.server.port,self.path, \
                                   self.server.httpPrefix, \
                                   authorized,followsPerPage,'followers')
        if followers:
            if self._requestHTTP():
                pageNumber=1
                if '?page=' not in self.path:
                    searchPath=self.path
                    # get a page of followers, not the summary
                    followers=getFollowingFeed(self.server.baseDir,self.server.domain, \
                                               self.server.port,self.path+'?page=1', \
                                               self.server.httpPrefix, \
                                               authorized,followsPerPage,'followers')
                else:
                    pageNumberStr=self.path.split('?page=')[1]
                    if pageNumberStr.isdigit():
                        pageNumber=int(pageNumberStr)
                    searchPath=self.path.split('?page=')[0]
                getPerson = personLookup(self.server.domain,searchPath.replace('/followers',''), \
                                         self.server.baseDir)
                if getPerson:
                    if not self.server.session:
                        if self.server.debug:
                            print('DEBUG: creating new session')
                        self.server.session= \
                            createSession(self.server.domain,self.server.port,self.server.useTor)
                    msg=htmlProfile(self.server.translate, \
                                    self.server.projectVersion, \
                                    self.server.baseDir, \
                                    self.server.httpPrefix, \
                                    authorized, \
                                    self.server.ocapAlways, \
                                    getPerson,'followers', \
                                    self.server.session, \
                                    self.server.cachedWebfingers, \
                                    self.server.personCache, \
                                    followers, \
                                    pageNumber,followsPerPage).encode('utf-8')
                    self._set_headers('text/html',len(msg),cookie)
                    self.wfile.write(msg)                
                    self.server.GETbusy=False
                    return
            else:
                if self._fetchAuthenticated():
                    msg=json.dumps(followers).encode('utf-8')
                    self._set_headers('application/json',len(msg),None)
                    self.wfile.write(msg)
                else:
                    self._404()
            self.server.GETbusy=False
            return
        # look up a person
        getPerson = personLookup(self.server.domain,self.path, \
                                 self.server.baseDir)
        if getPerson:
            if self._requestHTTP():
                if not self.server.session:
                    if self.server.debug:
                        print('DEBUG: creating new session')
                    self.server.session= \
                        createSession(self.server.domain,self.server.port,self.server.useTor)
                msg=htmlProfile(self.server.translate, \
                                self.server.projectVersion, \
                                self.server.baseDir, \
                                self.server.httpPrefix, \
                                authorized, \
                                self.server.ocapAlways, \
                                getPerson,'posts',
                                self.server.session, \
                                self.server.cachedWebfingers, \
                                self.server.personCache, \
                                None,None).encode('utf-8')
                self._set_headers('text/html',len(msg),cookie)
                self.wfile.write(msg)
            else:
                if self._fetchAuthenticated():
                    msg=json.dumps(getPerson).encode('utf-8')
                    self._set_headers('application/json',len(msg),None)
                    self.wfile.write(msg)
                else:
                    self._404()
            self.server.GETbusy=False
            return
        # check that a json file was requested
        if not self.path.endswith('.json'):
            if self.server.debug:
                print('DEBUG: GET Not json: '+self.path+' '+self.server.baseDir)
            self._404()
            self.server.GETbusy=False
            return

        if not self._fetchAuthenticated():
            if self.server.debug:
                print('WARN: Unauthenticated GET')
            self._404()
        
        # check that the file exists
        filename=self.server.baseDir+self.path
        if os.path.isfile(filename):
            with open(filename, 'r', encoding='utf-8') as File:
                content = File.read()
                contentJson=json.loads(content)
                msg=json.dumps(contentJson).encode('utf-8')
                self._set_headers('application/json',len(msg),None)
                self.wfile.write(msg)
        else:
            if self.server.debug:
                print('DEBUG: GET Unknown file')
            self._404()
        self.server.GETbusy=False

    def do_HEAD(self):
        self._set_headers('application/json',0,None)

    def _receiveNewPostThread(self,authorized: bool,postType: str,path: str,headers: {}) -> int:
        # 0 = this is not a new post
        # 1 = new post success
        # -1 = new post failed
        # 2 = new post canceled
        if ' boundary=' in headers['Content-Type']:
            nickname=None
            nicknameStr=path.split('/users/')[1]
            if '/' in nicknameStr:
                nickname=nicknameStr.split('/')[0]
            else:
                return -1
            length = int(headers['Content-Length'])
            if length>self.server.maxPostLength:
                print('POST size too large')
                return -1

            boundary=headers['Content-Type'].split('boundary=')[1]
            if ';' in boundary:
                boundary=boundary.split(';')[0]

            # Note: we don't use cgi here because it's due to be deprecated
            # in Python 3.8/3.10
            # Instead we use the multipart mime parser from the email module
            postBytes=self.rfile.read(length)
            msg = email.parser.BytesParser().parsebytes(postBytes)
            # why don't we just use msg.is_multipart(), rather than splitting?
            # TL;DR it doesn't work for this use case because we're not using
            # email style encoding message/rfc822
            messageFields=msg.get_payload(decode=False).split(boundary)
            fields={}
            filename=None
            attachmentMediaType=None
            for f in messageFields:
                if f=='--':
                    continue
                if ' name="' in f:
                    postStr=f.split(' name="',1)[1]
                    if '"' in postStr:
                        postKey=postStr.split('"',1)[0]
                        postValueStr=postStr.split('"',1)[1]
                        if ';' not in postValueStr:
                            if '\r\n' in postValueStr:
                                postLines=postValueStr.split('\r\n')                                    
                                postValue=''
                                if len(postLines)>2:
                                    for line in range(2,len(postLines)-1):
                                        if line>2:
                                            postValue+='\n'
                                        postValue+=postLines[line]
                                fields[postKey]=postValue
                        else:
                            # directly search the binary array for the beginning
                            # of an image
                            extensionList=['png','jpeg','gif','mp4','webm','ogv','mp3','ogg']
                            for extension in extensionList:
                                searchStr=b'Content-Type: image/png'
                                if extension=='jpeg':
                                    searchStr=b'Content-Type: image/jpeg'
                                elif extension=='gif':
                                    searchStr=b'Content-Type: image/gif'
                                elif extension=='mp4':
                                    searchStr=b'Content-Type: video/mp4'
                                elif extension=='ogv':
                                    searchStr=b'Content-Type: video/ogv'
                                elif extension=='mp3':
                                    searchStr=b'Content-Type: audio/mpeg'
                                elif extension=='ogg':
                                    searchStr=b'Content-Type: audio/ogg'
                                imageLocation=postBytes.find(searchStr)
                                filenameBase=self.server.baseDir+'/accounts/'+nickname+'@'+self.server.domain+'/upload'
                                if imageLocation>-1:
                                    if extension=='jpeg':
                                        extension='jpg'
                                    if extension=='mpeg':
                                        extension='mp3'
                                    filename=filenameBase+'.'+extension
                                    attachmentMediaType=searchStr.decode().split('/')[0].replace('Content-Type: ','')
                                    break
                            if filename and imageLocation>-1:
                                # locate the beginning of the image, after any
                                # carriage returns
                                startPos=imageLocation+len(searchStr)
                                for offset in range(1,8):
                                    if postBytes[startPos+offset]!=10:
                                        if postBytes[startPos+offset]!=13:
                                            startPos+=offset
                                            break

                                fd = open(filename, 'wb')
                                fd.write(postBytes[startPos:])
                                fd.close()
                            else:
                                filename=None

            # send the post
            if not fields.get('message') and not fields.get('imageDescription'):
                return -1
            if fields.get('submitPost'):
                if fields['submitPost']!='Submit':
                    return -1
            else:
                return 2

            if not fields.get('imageDescription'):
                fields['imageDescription']=None
            if not fields.get('subject'):
                fields['subject']=None
            if not fields.get('replyTo'):
                fields['replyTo']=None
            if not fields.get('eventDate'):
                fields['eventDate']=None
            if not fields.get('eventTime'):
                fields['eventTime']=None
            if not fields.get('location'):
                fields['location']=None

            if postType=='newpost':
                messageJson= \
                    createPublicPost(self.server.baseDir, \
                                     nickname, \
                                     self.server.domain,self.server.port, \
                                     self.server.httpPrefix, \
                                     fields['message'],False,False,False, \
                                     filename,attachmentMediaType,fields['imageDescription'],True, \
                                     fields['replyTo'],fields['replyTo'],fields['subject'], \
                                     fields['eventDate'],fields['eventTime'],fields['location'])
                if messageJson:
                    self.postToNickname=nickname
                    if self._postToOutbox(messageJson,__version__):
                        populateReplies(self.server.baseDir, \
                                        self.server.httpPrefix, \
                                        self.server.domainFull, \
                                        messageJson, \
                                        self.server.maxReplies, \
                                        self.server.debug)
                        return 1
                    else:
                        return -1

            if postType=='newunlisted':
                messageJson= \
                    createUnlistedPost(self.server.baseDir, \
                                       nickname, \
                                       self.server.domain,self.server.port, \
                                       self.server.httpPrefix, \
                                       fields['message'],False,False,False, \
                                       filename,attachmentMediaType,fields['imageDescription'],True, \
                                       fields['replyTo'], fields['replyTo'],fields['subject'], \
                                       fields['eventDate'],fields['eventTime'],fields['location'])
                if messageJson:
                    self.postToNickname=nickname
                    if self._postToOutbox(messageJson,__version__):
                        populateReplies(self.server.baseDir, \
                                        self.server.httpPrefix, \
                                        self.server.domain, \
                                        messageJson, \
                                        self.server.maxReplies, \
                                        self.server.debug)
                        return 1
                    else:
                        return -1

            if postType=='newfollowers':
                messageJson= \
                    createFollowersOnlyPost(self.server.baseDir, \
                                            nickname, \
                                            self.server.domain,self.server.port, \
                                            self.server.httpPrefix, \
                                            fields['message'],True,False,False, \
                                            filename,attachmentMediaType,fields['imageDescription'],True, \
                                            fields['replyTo'], fields['replyTo'],fields['subject'],
                                            fields['eventDate'],fields['eventTime'],fields['location'])
                if messageJson:
                    self.postToNickname=nickname
                    if self._postToOutbox(messageJson,__version__):
                        populateReplies(self.server.baseDir, \
                                        self.server.httpPrefix, \
                                        self.server.domain, \
                                        messageJson, \
                                        self.server.maxReplies, \
                                        self.server.debug)
                        return 1
                    else:
                        return -1

            if postType=='newdm':
                messageJson=None
                if '@' in fields['message']:
                    messageJson= \
                        createDirectMessagePost(self.server.baseDir, \
                                                nickname, \
                                                self.server.domain,self.server.port, \
                                                self.server.httpPrefix, \
                                                fields['message'],True,False,False, \
                                                filename,attachmentMediaType, \
                                                fields['imageDescription'],True, \
                                                fields['replyTo'],fields['replyTo'], \
                                                fields['subject'], \
                                                self.server.debug, \
                                                fields['eventDate'],fields['eventTime'],fields['location'])
                if messageJson:
                    self.postToNickname=nickname
                    if self.server.debug:
                        print('DEBUG: new DM to '+str(messageJson['object']['to']))
                    if self._postToOutbox(messageJson,__version__):
                        populateReplies(self.server.baseDir, \
                                        self.server.httpPrefix, \
                                        self.server.domain, \
                                        messageJson, \
                                        self.server.maxReplies, \
                                        self.server.debug)
                        return 1
                    else:
                        return -1

            if postType=='newreport':
                if attachmentMediaType:
                    if attachmentMediaType!='image':
                        return -1
                # So as to be sure that this only goes to moderators
                # and not accounts being reported we disable any
                # included fediverse addresses by replacing '@' with '-at-'
                fields['message']=fields['message'].replace('@','-at-')
                messageJson= \
                    createReportPost(self.server.baseDir, \
                                     nickname, \
                                     self.server.domain,self.server.port, \
                                     self.server.httpPrefix, \
                                     fields['message'],True,False,False, \
                                     filename,attachmentMediaType, \
                                     fields['imageDescription'],True, \
                                     self.server.debug,fields['subject'])
                if messageJson:
                    self.postToNickname=nickname
                    if self._postToOutbox(messageJson,__version__):
                        return 1
                    else:
                        return -1

            if postType=='newshare':
                if not fields.get('itemType'):
                    return -1
                if not fields.get('category'):
                    return -1
                if not fields.get('location'):
                    return -1
                if not fields.get('duration'):
                    return -1
                if attachmentMediaType:
                    if attachmentMediaType!='image':
                        return -1
                addShare(self.server.baseDir, \
                         self.server.httpPrefix, \
                         nickname, \
                         self.server.domain,self.server.port, \
                         fields['subject'], \
                         fields['message'], \
                         filename, \
                         fields['itemType'], \
                         fields['category'], \
                         fields['location'], \
                         fields['duration'],
                         self.server.debug)
                if filename:
                    if os.path.isfile(filename):
                        os.remove(filename)
                self.postToNickname=nickname
                return 1
        return -1

    def _receiveNewPost(self,authorized: bool,postType: str,path: str) -> int:
        """A new post has been created
        This creates a thread to send the new post
        """
        pageNumber=1
        if not (authorized and '/users/' in path and '?'+postType+'?' in path):
            print('Not receiving new post for '+path)
            return None

        print('New post begins: '+postType+' '+path)

        if '?page=' in path:
            pageNumberStr=path.split('?page=')[1]
            if '?' in pageNumberStr:
                pageNumberStr=pageNumberStr.split('?')[0]
            if pageNumberStr.isdigit():
                pageNumber=int(pageNumberStr)
                path=path.split('?page=')[0]

        newPostThreadName=self.postToNickname
        if not newPostThreadName:
            newPostThreadName='*'
        
        if self.server.newPostThread.get(newPostThreadName):
            print('Waiting for previous new post thread to end')
            waitCtr=0
            while self.server.newPostThread[newPostThreadName].isAlive() and waitCtr<8:
                time.sleep(1)
                waitCtr+=1
            if waitCtr>=8:
                self.server.newPostThread[newPostThreadName].kill()

        # make a copy of self.headers
        headers={}
        for dictEntryName,headerLine in self.headers.items():
            headers[dictEntryName]=headerLine
        print('New post headers: '+str(headers))

        print('Creating new post thread: '+newPostThreadName)
        self.server.newPostThread[newPostThreadName]= \
            threadWithTrace(target=self._receiveNewPostThread, \
                            args=(authorized,postType,path,headers),daemon=True)

        print('Starting new post thread')
        self.server.newPostThread[newPostThreadName].start()
        return pageNumber
        
    def do_POST(self):
        if not self.server.session:
            self.server.session= \
                createSession(self.server.domain,self.server.port,self.server.useTor)

        if self.server.debug:
            print('DEBUG: POST to from '+self.server.baseDir+ \
                  ' path: '+self.path+' busy: '+ \
                  str(self.server.POSTbusy))
        if self.server.POSTbusy:
            currTimePOST=int(time.time())
            if currTimePOST-self.server.lastPOST==0:
                self.send_response(429)
                self.end_headers()
                return              
            self.server.lastPOST=currTimePOST
            
        self.server.POSTbusy=True
        if not self.headers.get('Content-type'):
            print('Content-type header missing')
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy=False
            return

        # remove any trailing slashes from the path
        if not self.path.endswith('confirm'):
            self.path=self.path.replace('/outbox/','/outbox').replace('/inbox/','/inbox').replace('/shares/','/shares').replace('/sharedInbox/','/sharedInbox')

        cookie=None
        if self.headers.get('Cookie'):
            cookie=self.headers['Cookie']

        # check authorization
        authorized = self._isAuthorized()
        if authorized:
            if self.server.debug:
                print('POST Authorization granted')
        else:
            if self.server.debug:
                print('POST Not authorized')
                print(str(self.headers))

        # if this is a POST to teh outbox then check authentication
        self.outboxAuthenticated=False
        self.postToNickname=None

        if self.path.startswith('/login'):
            # get the contents of POST containing login credentials
            length = int(self.headers['Content-length'])
            if length>512:
                print('Login failed - credentials too long')
                self.send_response(401)
                self.end_headers()
                self.server.POSTbusy=False
                return                
            loginParams=self.rfile.read(length).decode('utf-8')
            loginNickname,loginPassword,register=htmlGetLoginCredentials(loginParams,self.server.lastLoginTime)
            if loginNickname:
                self.server.lastLoginTime=int(time.time())
                if register:
                    if not registerAccount(self.server.baseDir,self.server.httpPrefix, \
                                           self.server.domain,self.server.port, \
                                           loginNickname,loginPassword):
                        self.server.POSTbusy=False
                        self._redirect_headers('/login',cookie)
                        return
                authHeader=createBasicAuthHeader(loginNickname,loginPassword)
                if not authorizeBasic(self.server.baseDir,'/users/'+loginNickname+'/outbox',authHeader,False):
                    print('Login failed: '+loginNickname)
                    # remove any token
                    if self.server.tokens.get(loginNickname):
                        del self.server.tokensLookup[self.server.tokens[loginNickname]]
                        del self.server.tokens[loginNickname]
                        del self.server.salts[loginNickname]
                    self.send_response(303)
                    self.send_header('Content-Length', '0')
                    self.send_header('Set-Cookie', 'epicyon=; SameSite=Strict')
                    self.send_header('Location', '/login')
                    self.send_header('X-Robots-Tag','noindex')
                    self.end_headers()                    
                    self.server.POSTbusy=False
                    return
                else:
                    if isSuspended(self.server.baseDir,loginNickname):
                        msg=htmlSuspended(self.server.baseDir).encode('utf-8')
                        self._login_headers('text/html',len(msg))
                        self.wfile.write(msg)
                        self.server.POSTbusy=False
                        return                        
                    # login success - redirect with authorization
                    print('Login success: '+loginNickname)
                    self.send_response(303)
                    # This produces a deterministic token based on nick+password+salt
                    # But notice that the salt is ephemeral, so a server reboot changes them.
                    # This allows you to be logged in on two or more devices with the
                    # same token, but also ensures that if an adversary obtains the token
                    # then rebooting the server is sufficient to thwart them, without
                    # any password changes.
                    if not self.server.salts.get(loginNickname):
                        self.server.salts[loginNickname]=createPassword(32)
                    self.server.tokens[loginNickname]=sha256((loginNickname+loginPassword+self.server.salts[loginNickname]).encode('utf-8')).hexdigest()
                    self.server.tokensLookup[self.server.tokens[loginNickname]]=loginNickname
                    self.send_header('Set-Cookie', 'epicyon='+self.server.tokens[loginNickname]+'; SameSite=Strict')
                    self.send_header('Location', '/users/'+loginNickname+'/inbox')
                    self.send_header('Content-Length', '0')
                    self.send_header('X-Robots-Tag','noindex')
                    self.end_headers()
                    self.server.POSTbusy=False
                    return
            self.send_response(200)
            self.end_headers()
            self.server.POSTbusy=False
            return            

        # update of profile/avatar from web interface
        if authorized and self.path.endswith('/profiledata'):
            if ' boundary=' in self.headers['Content-type']:
                boundary=self.headers['Content-type'].split('boundary=')[1]
                if ';' in boundary:
                    boundary=boundary.split(';')[0]

                actorStr=self.path.replace('/profiledata','').replace('/editprofile','')
                nickname=getNicknameFromActor(actorStr)
                if not nickname:
                    print('WARN: nickname not found in '+actorStr)
                    self._redirect_headers(actorStr,cookie)
                    self.server.POSTbusy=False
                    return
                length = int(self.headers['Content-length'])
                if length>self.server.maxPostLength:
                    print('Maximum profile data length exceeded '+str(length))
                    self._redirect_headers(actorStr,cookie)
                    self.server.POSTbusy=False
                    return

                postBytes=self.rfile.read(length)

                msg = email.parser.BytesParser().parsebytes(postBytes)                
                messageFields=msg.get_payload(decode=False).split(boundary)
                fields={}
                filename=None
                lastImageLocation=0
                for f in messageFields:
                    if f=='--':
                        continue
                    if ' name="' in f:
                        postStr=f.split(' name="',1)[1]
                        if '"' in postStr:
                            postKey=postStr.split('"',1)[0]
                            postValueStr=postStr.split('"',1)[1]
                            if ';' not in postValueStr:
                                if '\r\n' in postValueStr:
                                    postLines=postValueStr.split('\r\n')                                    
                                    postValue=''
                                    if len(postLines)>2:
                                        for line in range(2,len(postLines)-1):
                                            if line>2:
                                                postValue+='\n'
                                            postValue+=postLines[line]
                                    fields[postKey]=postValue
                            else:
                                if 'filename="' not in postStr:
                                    continue
                                filenameStr=postStr.split('filename="')[1]
                                if '"' not in filenameStr:
                                    continue
                                postImageFilename=filenameStr.split('"')[0]
                                if '.' not in postImageFilename:
                                    continue
                                # directly search the binary array for the beginning
                                # of an image
                                searchStr=b'Content-Type: image/png'                                
                                imageLocation=postBytes.find(searchStr,lastImageLocation)
                                filenameBase=self.server.baseDir+'/accounts/'+nickname+'@'+self.server.domain+'/'+postKey
                                # Note: a .temp extension is used here so that at no time is
                                # an image with metadata publicly exposed, even for a few mS
                                if imageLocation>-1:
                                    filename=filenameBase+'.png.temp'
                                else:        
                                    searchStr=b'Content-Type: image/jpeg'
                                    imageLocation=postBytes.find(searchStr,lastImageLocation)
                                    if imageLocation>-1:                                    
                                        filename=filenameBase+'.jpg.temp'
                                    else:     
                                        searchStr=b'Content-Type: image/gif'
                                        imageLocation=postBytes.find(searchStr,lastImageLocation)
                                        if imageLocation>-1:                                    
                                            filename=filenameBase+'.gif.temp'
                                if filename and imageLocation>-1:
                                    # locate the beginning of the image, after any
                                    # carriage returns
                                    startPos=imageLocation+len(searchStr)
                                    for offset in range(1,8):
                                        if postBytes[startPos+offset]!=10:
                                            if postBytes[startPos+offset]!=13:
                                                startPos+=offset
                                                break

                                    # look for the end of the image
                                    imageLocationEnd=postBytes.find(b'-------',imageLocation+1)

                                    fd = open(filename, 'wb')
                                    if imageLocationEnd>-1:
                                        fd.write(postBytes[startPos:][:imageLocationEnd-startPos])
                                    else:
                                        fd.write(postBytes[startPos:])
                                    fd.close()

                                    # remove exif/metadata
                                    removeMetaData(filename,filename.replace('.temp',''))
                                    os.remove(filename)
                                    lastImageLocation=imageLocation+1
                                    
                actorFilename=self.server.baseDir+'/accounts/'+nickname+'@'+self.server.domain+'.json'
                if os.path.isfile(actorFilename):
                    loadedActor=False
                    try:
                        with open(actorFilename, 'r') as fp:
                            actorJson=commentjson.load(fp)
                            loadedActor=True
                    except Exception as e:
                        print(e)
                    if loadedActor:                    
                        actorChanged=False
                        skillCtr=1
                        newSkills={}
                        while skillCtr<10:
                            skillName=fields.get('skillName'+str(skillCtr))
                            if not skillName:
                                skillCtr+=1
                                continue
                            skillValue=fields.get('skillValue'+str(skillCtr))
                            if not skillValue:
                                skillCtr+=1
                                continue
                            if not actorJson['skills'].get(skillName):
                                actorChanged=True
                            else:
                                if actorJson['skills'][skillName]!=int(skillValue):
                                    actorChanged=True
                            newSkills[skillName]=int(skillValue)
                            skillCtr+=1
                        if len(actorJson['skills'].items())!=len(newSkills.items()):
                            actorChanged=True
                        actorJson['skills']=newSkills
                        if fields.get('displayNickname'):
                            if fields['displayNickname']!=actorJson['name']:
                                actorJson['name']=fields['displayNickname']
                                actorChanged=True
                        if fields.get('bio'):
                            if fields['bio']!=actorJson['summary']:
                                actorTags={}
                                actorJson['summary']= \
                                    addHtmlTags(self.server.baseDir, \
                                                self.server.httpPrefix, \
                                                nickname, \
                                                self.server.domainFull, \
                                                fields['bio'],[],actorTags)
                                if actorTags:
                                    actorJson['tag']=[]
                                    for tagName,tag in actorTags.items():
                                        actorJson['tag'].append(tag)
                                actorChanged=True
                        if fields.get('moderators'):
                            adminNickname=getConfigParam(self.server.baseDir,'admin')
                            if self.path.startswith('/users/'+adminNickname+'/'):
                                moderatorsFile=self.server.baseDir+'/accounts/moderators.txt'
                                clearModeratorStatus(self.server.baseDir)
                                if ',' in fields['moderators']:
                                    # if the list was given as comma separated
                                    modFile=open(moderatorsFile,"w+")
                                    for modNick in fields['moderators'].split(','):
                                        modNick=modNick.strip()
                                        if os.path.isdir(self.server.baseDir+'/accounts/'+modNick+'@'+self.server.domain):
                                            modFile.write(modNick+'\n')
                                    modFile.close()
                                    for modNick in fields['moderators'].split(','):
                                        modNick=modNick.strip()
                                        if os.path.isdir(self.server.baseDir+'/accounts/'+modNick+'@'+self.server.domain):
                                            setRole(self.server.baseDir,modNick,self.server.domain,'instance','moderator')
                                else:
                                    # nicknames on separate lines
                                    modFile=open(moderatorsFile,"w+")
                                    for modNick in fields['moderators'].split('\n'):
                                        modNick=modNick.strip()
                                        if os.path.isdir(self.server.baseDir+'/accounts/'+modNick+'@'+self.server.domain):
                                            modFile.write(modNick+'\n')
                                    modFile.close()
                                    for modNick in fields['moderators'].split('\n'):
                                        modNick=modNick.strip()
                                        if os.path.isdir(self.server.baseDir+'/accounts/'+modNick+'@'+self.server.domain):
                                            setRole(self.server.baseDir,modNick,self.server.domain,'instance','moderator')
                                        
                        approveFollowers=False
                        if fields.get('approveFollowers'):
                            if fields['approveFollowers']=='on':
                                approveFollowers=True
                        if approveFollowers!=actorJson['manuallyApprovesFollowers']:
                            actorJson['manuallyApprovesFollowers']=approveFollowers
                            actorChanged=True
                        if fields.get('isBot'):
                            if fields['isBot']=='on':
                                if actorJson['type']!='Service':
                                    actorJson['type']='Service'
                                    actorChanged=True
                        else:
                            if fields.get('isGroup'):
                                if fields['isGroup']=='on':
                                    if actorJson['type']!='Group':
                                        actorJson['type']='Group'
                                        actorChanged=True
                            else:
                                if actorJson['type']!='Person':
                                    actorJson['type']='Person'
                                    actorChanged=True
                        # save filtered words list
                        filterFilename=self.server.baseDir+'/accounts/'+nickname+'@'+self.server.domain+'/filters.txt'
                        if fields.get('filteredWords'):
                            with open(filterFilename, "w") as filterfile:
                                filterfile.write(fields['filteredWords'])
                        else:
                            if os.path.isfile(filterFilename):
                                os.remove(filterFilename)
                        # save blocked accounts list
                        blockedFilename=self.server.baseDir+'/accounts/'+nickname+'@'+self.server.domain+'/blocking.txt'
                        if fields.get('blocked'):
                            with open(blockedFilename, "w") as blockedfile:
                                blockedfile.write(fields['blocked'])
                        else:
                            if os.path.isfile(blockedFilename):
                                os.remove(blockedFilename)
                        # save allowed instances list
                        allowedInstancesFilename=self.server.baseDir+'/accounts/'+nickname+'@'+self.server.domain+'/allowedinstances.txt'
                        if fields.get('allowedInstances'):
                            with open(allowedInstancesFilename, "w") as allowedInstancesFile:
                                allowedInstancesFile.write(fields['allowedInstances'])
                        else:
                            if os.path.isfile(allowedInstancesFilename):
                                os.remove(allowedInstancesFilename)
                        # save actor json file within accounts
                        if actorChanged:
                            try:
                                with open(actorFilename, 'w') as fp:
                                    commentjson.dump(actorJson, fp, indent=4, sort_keys=False)
                            except Exception as e:
                                print(e)
                            # also copy to the actors cache and personCache in memory
                            storePersonInCache(self.server.baseDir,actorJson['id'],actorJson,self.server.personCache)
                            actorCacheFilename=self.server.baseDir+'/cache/actors/'+actorJson['id'].replace('/','#')+'.json'
                            try:
                                with open(actorCacheFilename, 'w') as fp:
                                    commentjson.dump(actorJson, fp, indent=4, sort_keys=False)                            
                            except Exception as e:
                                print(e)
                            # send actor update to followers
                            updateActorJson={
                                'type': 'Update',
                                'actor': actorJson['id'],
                                'to': ['https://www.w3.org/ns/activitystreams#Public'],
                                'cc': [actorJson['id']+'/followers'],
                                'object': actorJson
                            }
                            self.postToNickname=nickname
                            self._postToOutboxThread(updateActorJson)
            self._redirect_headers(actorStr,cookie)
            self.server.POSTbusy=False
            return

        # moderator action buttons
        if authorized and '/users/' in self.path and \
           self.path.endswith('/moderationaction'):
            actorStr=self.path.replace('/moderationaction','')
            length = int(self.headers['Content-length'])
            moderationParams=self.rfile.read(length).decode('utf-8')
            print('moderationParams: '+moderationParams)
            if '&' in moderationParams:
                moderationText=None
                moderationButton=None
                for moderationStr in moderationParams.split('&'):
                    print('moderationStr: '+moderationStr)
                    if moderationStr.startswith('moderationAction'):
                        if '=' in moderationStr:
                            moderationText=moderationStr.split('=')[1].strip()
                            moderationText=moderationText.replace('+',' ').replace('%40','@').replace('%3A',':').replace('%23','#').strip()
                    elif moderationStr.startswith('submitInfo'):
                        msg=htmlModerationInfo(self.server.translate, \
                                               self.server.baseDir).encode('utf-8')
                        self._login_headers('text/html',len(msg))
                        self.wfile.write(msg)
                        self.server.POSTbusy=False
                        return                        
                    elif moderationStr.startswith('submitBlock'):
                        moderationButton='block'
                    elif moderationStr.startswith('submitUnblock'):
                        moderationButton='unblock'
                    elif moderationStr.startswith('submitSuspend'):
                        moderationButton='suspend'
                    elif moderationStr.startswith('submitUnsuspend'):
                        moderationButton='unsuspend'
                    elif moderationStr.startswith('submitRemove'):
                        moderationButton='remove'
                if moderationButton and moderationText:
                    if self.server.debug:
                        print('moderationButton: '+moderationButton)
                        print('moderationText: '+moderationText)
                    nickname=moderationText
                    if nickname.startswith('http') or \
                       nickname.startswith('dat'):
                        nickname=getNicknameFromActor(nickname)
                    if '@' in nickname:
                        nickname=nickname.split('@')[0]
                    if moderationButton=='suspend':
                        suspendAccount(self.server.baseDir,nickname,self.server.salts)
                    if moderationButton=='unsuspend':
                        unsuspendAccount(self.server.baseDir,nickname)
                    if moderationButton=='block':
                        fullBlockDomain=None
                        if moderationText.startswith('http') or \
                           moderationText.startswith('dat'):
                            blockDomain,blockPort=getDomainFromActor(moderationText)
                            fullBlockDomain=blockDomain
                            if blockPort:
                                if blockPort!=80 and blockPort!=443:
                                    if ':' not in blockDomain:
                                        fullBlockDomain=blockDomain+':'+str(blockPort)
                        if '@' in moderationText:
                            fullBlockDomain=moderationText.split('@')[1]
                        if fullBlockDomain or nickname.startswith('#'):
                            addGlobalBlock(self.server.baseDir, \
                                           nickname,fullBlockDomain)
                    if moderationButton=='unblock':
                        fullBlockDomain=None
                        if moderationText.startswith('http') or \
                           moderationText.startswith('dat'):
                            blockDomain,blockPort=getDomainFromActor(moderationText)
                            fullBlockDomain=blockDomain
                            if blockPort:
                                if blockPort!=80 and blockPort!=443:
                                    if ':' not in blockDomain:
                                        fullBlockDomain=blockDomain+':'+str(blockPort)
                        if '@' in moderationText:
                            fullBlockDomain=moderationText.split('@')[1]
                        if fullBlockDomain or nickname.startswith('#'):
                            removeGlobalBlock(self.server.baseDir, \
                                              nickname,fullBlockDomain)
                    if moderationButton=='remove':
                        if '/statuses/' not in moderationText:
                            removeAccount(self.server.baseDir, \
                                          nickname, \
                                          self.server.domain, \
                                          self.server.port)
                        else:
                            # remove a post or thread                            
                            postFilename= \
                                locatePost(self.server.baseDir, \
                                           nickname,self.server.domain, \
                                           moderationText)
                            if postFilename:
                                if canRemovePost(self.server.baseDir, \
                                                 nickname, \
                                                 self.server.domain, \
                                                 self.server.port, \
                                                 moderationText):                                
                                    deletePost(self.server.baseDir, \
                                               self.server.httpPrefix, \
                                               nickname,self.server.omain, \
                                               postFilename, \
                                               self.server.debug)
            self._redirect_headers(actorStr+'/moderation',cookie)
            self.server.POSTbusy=False
            return

        searchForEmoji=False
        if self.path.endswith('/searchhandleemoji'):
            searchForEmoji=True
            self.path=self.path.replace('/searchhandleemoji','/searchhandle')
            if self.server.debug:
                print('DEBUG: searching for emoji')
                print('authorized: '+str(authorized))

        # a vote/question/poll is posted
        if authorized and \
           (self.path.endswith('/question') or '/question?page=' in self.path):
            pageNumber=1
            if '?page=' in self.path:
                pageNumberStr=self.path.split('?page=')[1]
                if pageNumberStr.isdigit():
                    pageNumber=int(pageNumberStr)
                self.path=self.path.split('?page=')[0]
            # the actor who votes
            actor=self.server.httpPrefix+'://'+self.server.domainFull+self.path.replace('/question','')
            nickname=getNicknameFromActor(actor)
            if not nickname:
                self._redirect_headers(actor+'/inbox?page='+str(pageNumber),cookie)
                self.server.POSTbusy=False
                return
            # get the parameters
            length = int(self.headers['Content-length'])
            questionParams=self.rfile.read(length).decode('utf-8')
            questionParams=questionParams.replace('+',' ').replace('%40','@').replace('%3A',':').replace('%23','#').strip()
            # post being voted on
            messageId=None
            if 'messageId=' in questionParams:
                messageId=searchParams.split('messageId=')[1]
                if '&' in messageId:
                    messageId=messageId.split('&')[0]
            answer=None
            if 'answer=' in questionParams:
                answer=searchParams.split('answer=')[1]
                if '&' in answer:
                    answer=answer.split('&')[0]
            print('Voting on message '+messageId)
            print('Vote for: '+answer)
            messageJson= \
                createPublicPost(self.server.baseDir, \
                                 nickname, \
                                 self.server.domain,self.server.port, \
                                 self.server.httpPrefix, \
                                 answer,False,False,False, \
                                 filename,attachmentMediaType,None,True, \
                                 messageId,messageId,None, \
                                 None,None,None)
            if messageJson:
                self.postToNickname=nickname
                if self._postToOutbox(messageJson,__version__):
                    populateReplies(self.server.baseDir, \
                                    self.server.httpPrefix, \
                                    self.server.domainFull, \
                                    messageJson, \
                                    self.server.maxReplies, \
                                    self.server.debug)
            self._redirect_headers(actor+'/inbox?page='+str(pageNumber),cookie)
            self.server.POSTbusy=False
            return                

        # a search was made
        if (authorized or searchForEmoji) and \
           (self.path.endswith('/searchhandle') or '/searchhandle?page=' in self.path):
            # get the page number
            pageNumber=1
            if '/searchhandle?page=' in self.path:
                pageNumberStr=self.path.split('/searchhandle?page=')[1]
                if pageNumberStr.isdigit():
                    pageNumber=int(pageNumberStr)
                self.path=self.path.split('?page=')[0]

            actorStr=self.server.httpPrefix+'://'+self.server.domainFull+self.path.replace('/searchhandle','')
            length = int(self.headers['Content-length'])
            searchParams=self.rfile.read(length).decode('utf-8')
            if 'searchtext=' in searchParams:
                searchStr=searchParams.split('searchtext=')[1]
                if '&' in searchStr:
                    searchStr=searchStr.split('&')[0]
                searchStr=searchStr.replace('+',' ').replace('%40','@').replace('%3A',':').replace('%23','#').replace('%2F','/').strip()
                if self.server.debug:
                    print('searchStr: '+searchStr)
                if searchForEmoji:
                    searchStr=':'+searchStr+':'
                if searchStr.startswith('#'):      
                    # hashtag search
                    hashtagStr= \
                        htmlHashtagSearch(self.server.translate, \
                                          self.server.baseDir,searchStr[1:],1, \
                                          maxPostsInFeed,self.server.session, \
                                          self.server.cachedWebfingers, \
                                          self.server.personCache, \
                                          self.server.httpPrefix, \
                                          self.server.projectVersion)
                    if hashtagStr:
                        msg=hashtagStr.encode('utf-8')
                        self._login_headers('text/html',len(msg))
                        self.wfile.write(msg)
                        self.server.POSTbusy=False
                        return
                elif searchStr.startswith('*'):      
                    # skill search
                    searchStr=searchStr.replace('*','').strip()
                    skillStr= \
                        htmlSkillsSearch(self.server.translate, \
                                         self.server.baseDir,searchStr, \
                                         self.server.instanceOnlySkillsSearch, \
                                         64)
                    if skillStr:
                        msg=skillStr.encode('utf-8')
                        self._login_headers('text/html',len(msg))
                        self.wfile.write(msg)
                        self.server.POSTbusy=False
                        return
                elif '@' in searchStr:
                    # profile search
                    nickname=getNicknameFromActor(self.path)
                    if not self.server.session:
                        self.server.session= \
                            createSession(self.server.domain, \
                                          self.server.port, \
                                          self.server.useTor)
                    profileStr= \
                        htmlProfileAfterSearch(self.server.translate, \
                                               self.server.baseDir, \
                                               self.path.replace('/searchhandle',''), \
                                               self.server.httpPrefix, \
                                               nickname, \
                                               self.server.domain,self.server.port, \
                                               searchStr, \
                                               self.server.session, \
                                               self.server.cachedWebfingers, \
                                               self.server.personCache, \
                                               self.server.debug, \
                                               self.server.projectVersion)
                    if profileStr:
                        msg=profileStr.encode('utf-8')
                        self._login_headers('text/html',len(msg))
                        self.wfile.write(msg)
                        self.server.POSTbusy=False
                        return
                    else:
                        self._redirect_headers(actorStr+'/search',cookie)
                        self.server.POSTbusy=False
                        return                        
                elif searchStr.startswith(':') or \
                     searchStr.lower().strip('\n').endswith(' emoji'):
                    # eg. "cat emoji"
                    if searchStr.lower().strip('\n').endswith(' emoji'):
                        searchStr=searchStr.lower().strip('\n').replace(' emoji','')
                    # emoji search
                    emojiStr= \
                        htmlSearchEmoji(self.server.translate,self.server.baseDir,searchStr)
                    if emojiStr:
                        msg=emojiStr.encode('utf-8')
                        self._login_headers('text/html',len(msg))
                        self.wfile.write(msg)
                        self.server.POSTbusy=False
                        return
                else:
                    # shared items search
                    sharedItemsStr= \
                        htmlSearchSharedItems(self.server.translate, \
                                              self.server.baseDir, \
                                              searchStr,pageNumber, \
                                              maxPostsInFeed, \
                                              self.server.httpPrefix, \
                                              self.server.domainFull, \
                                              actorStr)
                    if sharedItemsStr:
                        msg=sharedItemsStr.encode('utf-8')
                        self._login_headers('text/html',len(msg))
                        self.wfile.write(msg)
                        self.server.POSTbusy=False
                        return
            self._redirect_headers(actorStr+'/inbox',cookie)
            self.server.POSTbusy=False
            return

        # removes a shared item
        if authorized and self.path.endswith('/rmshare'):
            originPathStr=self.path.split('/rmshare')[0]
            length = int(self.headers['Content-length'])
            removeShareConfirmParams=self.rfile.read(length).decode('utf-8')
            if '&submitYes=' in removeShareConfirmParams:
                removeShareConfirmParams=removeShareConfirmParams.replace('%3A',':').replace('%2F','/')
                shareActor=removeShareConfirmParams.split('actor=')[1]
                if '&' in shareActor:
                    shareActor=shareActor.split('&')[0]
                shareName=removeShareConfirmParams.split('shareName=')[1]
                if '&' in shareName:
                    shareName=shareName.split('&')[0]
                shareNickname=getNicknameFromActor(shareActor)
                if shareNickname:
                    shareDomain,sharePort=getDomainFromActor(shareActor)
                    removeShare(self.server.baseDir,shareNickname,shareDomain,shareName)
            self._redirect_headers(originPathStr+'/inbox',cookie)
            self.server.POSTbusy=False
            return

        # removes a post
        if authorized and self.path.endswith('/rmpost'):
            pageNumber=1
            originPathStr=self.path.split('/rmpost')[0]
            length = int(self.headers['Content-length'])
            removePostConfirmParams=self.rfile.read(length).decode('utf-8')
            if '&submitYes=' in removePostConfirmParams:
                removePostConfirmParams=removePostConfirmParams.replace('%3A',':').replace('%2F','/')
                removeMessageId=removePostConfirmParams.split('messageId=')[1]
                if '&' in removeMessageId:
                    removeMessageId=removeMessageId.split('&')[0]
                if 'pageNumber=' in removePostConfirmParams:
                    pageNumberStr=removePostConfirmParams.split('pageNumber=')[1]
                    if '&' in pageNumberStr:
                        pageNumberStr=pageNumberStr.split('&')[0]
                    if pageNumberStr.isdigit():
                        pageNumber=int(pageNumberStr)
                if '/statuses/' in removeMessageId:
                    removePostActor=removeMessageId.split('/statuses/')[0]
                if originPathStr in removePostActor:
                    deleteJson= {
                        "@context": "https://www.w3.org/ns/activitystreams",
                        'actor': removePostActor,
                        'object': removeMessageId,
                        'to': ['https://www.w3.org/ns/activitystreams#Public',removePostActor],
                        'cc': [removePostActor+'/followers'],
                        'type': 'Delete'
                    }
                    if self.server.debug:
                        pprint(deleteJson)
                    self.postToNickname=getNicknameFromActor(removePostActor)
                    if self.postToNickname:
                        self._postToOutboxThread(deleteJson)
            if pageNumber==1:
                self._redirect_headers(originPathStr+'/outbox',cookie)
            else:
                self._redirect_headers(originPathStr+'/outbox?page='+str(pageNumber),cookie)
            self.server.POSTbusy=False
            return

        # decision to follow in the web interface is confirmed
        if authorized and self.path.endswith('/followconfirm'):
            originPathStr=self.path.split('/followconfirm')[0]
            followerNickname=getNicknameFromActor(originPathStr)
            length = int(self.headers['Content-length'])
            followConfirmParams=self.rfile.read(length).decode('utf-8')
            if '&submitYes=' in followConfirmParams:
                followingActor=followConfirmParams.replace('%3A',':').replace('%2F','/').split('actor=')[1]
                if '&' in followingActor:
                    followingActor=followingActor.split('&')[0]
                followingNickname=getNicknameFromActor(followingActor)
                followingDomain,followingPort=getDomainFromActor(followingActor)
                if followerNickname==followingNickname and \
                   followingDomain==self.server.domain and \
                   followingPort==self.server.port:
                    if self.server.debug:
                        print('You cannot follow yourself!')
                else:
                    if self.server.debug:
                        print('Sending follow request from '+followerNickname+' to '+followingActor)
                    sendFollowRequest(self.server.session, \
                                      self.server.baseDir, \
                                      followerNickname, \
                                      self.server.domain,self.server.port, \
                                      self.server.httpPrefix, \
                                      followingNickname, \
                                      followingDomain, \
                                      followingPort,self.server.httpPrefix, \
                                      False,self.server.federationList, \
                                      self.server.sendThreads, \
                                      self.server.postLog, \
                                      self.server.cachedWebfingers, \
                                      self.server.personCache, \
                                      self.server.debug, \
                                      self.server.projectVersion)
            self._redirect_headers(originPathStr,cookie)
            self.server.POSTbusy=False
            return

        # decision to unfollow in the web interface is confirmed
        if authorized and self.path.endswith('/unfollowconfirm'):
            originPathStr=self.path.split('/unfollowconfirm')[0]
            followerNickname=getNicknameFromActor(originPathStr)
            length = int(self.headers['Content-length'])
            followConfirmParams=self.rfile.read(length).decode('utf-8')
            if '&submitYes=' in followConfirmParams:
                followingActor=followConfirmParams.replace('%3A',':').replace('%2F','/').split('actor=')[1]
                if '&' in followingActor:
                    followingActor=followingActor.split('&')[0]
                followingNickname=getNicknameFromActor(followingActor)
                followingDomain,followingPort=getDomainFromActor(followingActor)
                if followerNickname==followingNickname and \
                   followingDomain==self.server.domain and \
                   followingPort==self.server.port:
                    if self.server.debug:
                        print('You cannot unfollow yourself!')
                else:
                    if self.server.debug:
                        print(followerNickname+' stops following '+followingActor)
                    followActor=self.server.httpPrefix+'://'+self.server.domainFull+'/users/'+followerNickname
                    statusNumber,published = getStatusNumber()
                    followId=followActor+'/statuses/'+str(statusNumber)
                    unfollowJson = {
                        '@context': 'https://www.w3.org/ns/activitystreams',
                        'id': followId+'/undo',
                        'type': 'Undo',
                        'actor': followActor,
                        'object': {
                            'id': followId,
                            'type': 'Follow',
                            'actor': followActor,
                            'object': followingActor
                        }
                    }
                    pathUsersSection=self.path.split('/users/')[1]
                    self.postToNickname=pathUsersSection.split('/')[0]
                    self._postToOutboxThread(unfollowJson)
            self._redirect_headers(originPathStr,cookie)
            self.server.POSTbusy=False
            return

        # decision to unblock in the web interface is confirmed
        if authorized and self.path.endswith('/unblockconfirm'):
            originPathStr=self.path.split('/unblockconfirm')[0]
            blockerNickname=getNicknameFromActor(originPathStr)
            if not blockerNickname:
                print('WARN: unable to find nickname in '+originPathStr)
                self._redirect_headers(originPathStr,cookie)
                self.server.POSTbusy=False
                return                
            length = int(self.headers['Content-length'])
            blockConfirmParams=self.rfile.read(length).decode('utf-8')
            if '&submitYes=' in blockConfirmParams:
                blockingActor=blockConfirmParams.replace('%3A',':').replace('%2F','/').split('actor=')[1]
                if '&' in blockingActor:
                    blockingActor=blockingActor.split('&')[0]
                blockingNickname=getNicknameFromActor(blockingActor)
                if not blockingNickname:
                    print('WARN: unable to find nickname in '+blockingActor)
                    self._redirect_headers(originPathStr,cookie)
                    self.server.POSTbusy=False
                    return                    
                blockingDomain,blockingPort=getDomainFromActor(blockingActor)
                blockingDomainFull=blockingDomain
                if blockingPort:
                    if blockingPort!=80 and blockingPort!=443:
                        if ':' not in blockingDomain:
                            blockingDomainFull=blockingDomain+':'+str(blockingPort)
                if blockerNickname==blockingNickname and \
                   blockingDomain==self.server.domain and \
                   blockingPort==self.server.port:
                    if self.server.debug:
                        print('You cannot unblock yourself!')
                else:
                    if self.server.debug:
                        print(blockerNickname+' stops blocking '+blockingActor)
                    removeBlock(self.server.baseDir,blockerNickname,self.server.domain, \
                                blockingNickname,blockingDomainFull)
            self._redirect_headers(originPathStr,cookie)
            self.server.POSTbusy=False
            return

        # decision to block in the web interface is confirmed
        if authorized and self.path.endswith('/blockconfirm'):
            originPathStr=self.path.split('/blockconfirm')[0]
            blockerNickname=getNicknameFromActor(originPathStr)
            if not blockerNickname:
                print('WARN: unable to find nickname in '+originPathStr)
                self._redirect_headers(originPathStr,cookie)
                self.server.POSTbusy=False
                return                
            length = int(self.headers['Content-length'])
            blockConfirmParams=self.rfile.read(length).decode('utf-8')
            if '&submitYes=' in blockConfirmParams:
                blockingActor=blockConfirmParams.replace('%3A',':').replace('%2F','/').split('actor=')[1]
                if '&' in blockingActor:
                    blockingActor=blockingActor.split('&')[0]
                blockingNickname=getNicknameFromActor(blockingActor)
                if not blockingNickname:
                    print('WARN: unable to find nickname in '+blockingActor)
                    self._redirect_headers(originPathStr,cookie)
                    self.server.POSTbusy=False
                    return                    
                blockingDomain,blockingPort=getDomainFromActor(blockingActor)
                blockingDomainFull=blockingDomain
                if blockingPort:
                    if blockingPort!=80 and blockingPort!=443:
                        if ':' not in blockingDomain:
                            blockingDomainFull=blockingDomain+':'+str(blockingPort)
                if blockerNickname==blockingNickname and \
                   blockingDomain==self.server.domain and \
                   blockingPort==self.server.port:
                    if self.server.debug:
                        print('You cannot block yourself!')
                else:
                    if self.server.debug:
                        print('Adding block by '+blockerNickname+' of '+blockingActor)
                    addBlock(self.server.baseDir,blockerNickname,self.server.domain, \
                             blockingNickname,blockingDomainFull)
            self._redirect_headers(originPathStr,cookie)
            self.server.POSTbusy=False
            return

        # an option was chosen from person options screen
        # view/follow/block/report
        if authorized and self.path.endswith('/personoptions'):
            pageNumber=1
            originPathStr=self.path.split('/personoptions')[0]
            chooserNickname=getNicknameFromActor(originPathStr)
            if not chooserNickname:
                print('WARN: unable to find nickname in '+originPathStr)
                self._redirect_headers(originPathStr,cookie)
                self.server.POSTbusy=False
                return                
            length = int(self.headers['Content-length'])
            optionsConfirmParams=self.rfile.read(length).decode('utf-8').replace('%3A',':').replace('%2F','/')
            # page number to return to
            if 'pageNumber=' in optionsConfirmParams:
                pageNumberStr=optionsConfirmParams.split('pageNumber=')[1]
                if '&' in pageNumberStr:
                    pageNumberStr=pageNumberStr.split('&')[0]
                if pageNumberStr.isdigit():
                    pageNumber=int(pageNumberStr)
            # actor for the person
            optionsActor=optionsConfirmParams.split('actor=')[1]
            if '&' in optionsActor:
                optionsActor=optionsActor.split('&')[0]
            # url of the avatar
            optionsAvatarUrl=optionsConfirmParams.split('avatarUrl=')[1]
            if '&' in optionsAvatarUrl:
                optionsAvatarUrl=optionsAvatarUrl.split('&')[0]
            # link to a post, which can then be included in reports
            postUrl=None
            if 'postUrl' in optionsConfirmParams:
                postUrl=optionsConfirmParams.split('postUrl=')[1]
                if '&' in postUrl:
                    postUrl=postUrl.split('&')[0]
                
            optionsNickname=getNicknameFromActor(optionsActor)
            if not optionsNickname:
                print('WARN: unable to find nickname in '+optionsActor)
                self._redirect_headers(originPathStr,cookie)
                self.server.POSTbusy=False
                return                
            optionsDomain,optionsPort=getDomainFromActor(optionsActor)
            optionsDomainFull=optionsDomain
            if optionsPort:
                if optionsPort!=80 and optionsPort!=443:
                    if ':' not in optionsDomain:
                        optionsDomainFull=optionsDomain+':'+str(optionsPort)
            if chooserNickname==optionsNickname and \
               optionsDomain==self.server.domain and \
               optionsPort==self.server.port:
                if self.server.debug:
                    print('You cannot perform an option action on yourself')

            if '&submitView=' in optionsConfirmParams:
                if self.server.debug:
                    print('Viewing '+optionsActor)
                self._redirect_headers(optionsActor,cookie)
                self.server.POSTbusy=False
                return
            if '&submitBlock=' in optionsConfirmParams:
                if self.server.debug:
                    print('Adding block by '+chooserNickname+' of '+optionsActor)
                addBlock(self.server.baseDir,chooserNickname,self.server.domain, \
                         optionsNickname,optionsDomainFull)
            if '&submitUnblock=' in optionsConfirmParams:
                if self.server.debug:
                    print('Unblocking '+optionsActor)
                msg=htmlUnblockConfirm(self.server.translate, \
                                       self.server.baseDir, \
                                       originPathStr, \
                                       optionsActor, \
                                       optionsAvatarUrl).encode()
                self._set_headers('text/html',len(msg),cookie)
                self.wfile.write(msg)
                self.server.POSTbusy=False
                return
            if '&submitFollow=' in optionsConfirmParams:
                if self.server.debug:
                    print('Following '+optionsActor)
                msg=htmlFollowConfirm(self.server.translate, \
                                      self.server.baseDir, \
                                      originPathStr, \
                                      optionsActor, \
                                      optionsAvatarUrl).encode()
                self._set_headers('text/html',len(msg),cookie)
                self.wfile.write(msg)
                self.server.POSTbusy=False
                return
            if '&submitUnfollow=' in optionsConfirmParams:
                if self.server.debug:
                    print('Unfollowing '+optionsActor)
                msg=htmlUnfollowConfirm(self.server.translate, \
                                        self.server.baseDir, \
                                        originPathStr, \
                                        optionsActor, \
                                        optionsAvatarUrl).encode()
                self._set_headers('text/html',len(msg),cookie)
                self.wfile.write(msg)
                self.server.POSTbusy=False
                return
            if '&submitDM=' in optionsConfirmParams:
                if self.server.debug:
                    print('Sending DM to '+optionsActor)
                reportPath=self.path.replace('/personoptions','')+'/newdm'
                msg=htmlNewPost(self.server.translate, \
                                self.server.baseDir, \
                                reportPath,None, \
                                [optionsActor],None, \
                                pageNumber).encode()
                self._set_headers('text/html',len(msg),cookie)
                self.wfile.write(msg)
                self.server.POSTbusy=False
                return            
            if '&submitReport=' in optionsConfirmParams:
                if self.server.debug:
                    print('Reporting '+optionsActor)
                reportPath=self.path.replace('/personoptions','')+'/newreport'
                msg=htmlNewPost(self.server.translate, \
                                self.server.baseDir, \
                                reportPath,None,[], \
                                postUrl,pageNumber).encode()
                self._set_headers('text/html',len(msg),cookie)
                self.wfile.write(msg)
                self.server.POSTbusy=False
                return            

            self._redirect_headers(originPathStr,cookie)
            self.server.POSTbusy=False
            return

        pageNumber=self._receiveNewPost(authorized,'newpost',self.path)
        if pageNumber:
            nickname=self.path.split('/users/')[1]
            if '/' in nickname:
                nickname=nickname.split('/')[0]
            self._redirect_headers('/users/'+nickname+'/inbox?page='+str(pageNumber),cookie)
            self.server.POSTbusy=False
            return
        pageNumber=self._receiveNewPost(authorized,'newunlisted',self.path)
        if pageNumber:
            nickname=self.path.split('/users/')[1]
            if '/' in nickname:
                nickname=nickname.split('/')[0]
            self._redirect_headers('/users/'+nickname+'/inbox?page='+str(pageNumber),cookie)
            self.server.POSTbusy=False
            return
        pageNumber=self._receiveNewPost(authorized,'newfollowers',self.path)
        if pageNumber:
            nickname=self.path.split('/users/')[1]
            if '/' in nickname:
                nickname=nickname.split('/')[0]
            self._redirect_headers('/users/'+nickname+'/inbox?page='+str(pageNumber),cookie)
            self.server.POSTbusy=False
            return
        pageNumber=self._receiveNewPost(authorized,'newdm',self.path)
        if pageNumber:
            nickname=self.path.split('/users/')[1]
            if '/' in nickname:
                nickname=nickname.split('/')[0]
            self._redirect_headers('/users/'+nickname+'/inbox?page='+str(pageNumber),cookie)
            self.server.POSTbusy=False
            return
        pageNumber=self._receiveNewPost(authorized,'newreport',self.path)
        if pageNumber:
            nickname=self.path.split('/users/')[1]
            if '/' in nickname:
                nickname=nickname.split('/')[0]
            self._redirect_headers('/users/'+nickname+'/inbox?page='+str(pageNumber),cookie)
            self.server.POSTbusy=False
            return
        pageNumber=self._receiveNewPost(authorized,'newshare',self.path)
        if pageNumber:
            nickname=self.path.split('/users/')[1]
            if '/' in nickname:
                nickname=nickname.split('/')[0]
            self._redirect_headers('/users/'+nickname+'/shares?page='+str(pageNumber),cookie)
            self.server.POSTbusy=False
            return

        if self.path.endswith('/outbox') or self.path.endswith('/shares'):
            if '/users/' in self.path:
                if authorized:
                    self.outboxAuthenticated=True
                    pathUsersSection=self.path.split('/users/')[1]
                    self.postToNickname=pathUsersSection.split('/')[0]
            if not self.outboxAuthenticated:
                self.send_response(405)
                self.end_headers()
                self.server.POSTbusy=False
                return

        # check that the post is to an expected path
        if not (self.path.endswith('/outbox') or \
                self.path.endswith('/inbox') or \
                self.path.endswith('/shares') or \
                self.path.endswith('/moderationaction') or \
                self.path.endswith('/caps/new') or \
                self.path=='/sharedInbox'):
            print('Attempt to POST to invalid path '+self.path)
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy=False
            return

        # read the message and convert it into a python dictionary
        length = int(self.headers['Content-length'])
        if self.server.debug:
            print('DEBUG: content-length: '+str(length))
        if not self.headers['Content-type'].startswith('image/') and \
           not self.headers['Content-type'].startswith('video/') and \
           not self.headers['Content-type'].startswith('audio/'):
            if length>self.server.maxMessageLength:
                print('Maximum message length exceeded '+str(length))
                self.send_response(400)
                self.end_headers()
                self.server.POSTbusy=False
                return
        else:
            if length>self.server.maxMediaSize:
                print('Maximum media size exceeded '+str(length))
                self.send_response(400)
                self.end_headers()
                self.server.POSTbusy=False
                return

        # receive images to the outbox
        if self.headers['Content-type'].startswith('image/') and \
           '/users/' in self.path:
            if not self.outboxAuthenticated:
                if self.server.debug:
                    print('DEBUG: unauthenticated attempt to post image to outbox')
                self.send_response(403)
                self.end_headers()
                self.server.POSTbusy=False
                return            
            pathUsersSection=self.path.split('/users/')[1]
            if '/' not in pathUsersSection:
                self.send_response(404)
                self.end_headers()
                self.server.POSTbusy=False
                return                
            self.postFromNickname=pathUsersSection.split('/')[0]
            accountsDir=self.server.baseDir+'/accounts/'+self.postFromNickname+'@'+self.server.domain
            if not os.path.isdir(accountsDir):
                self.send_response(404)
                self.end_headers()
                self.server.POSTbusy=False
                return                
            mediaBytes=self.rfile.read(length)
            mediaFilenameBase=accountsDir+'/upload'
            mediaFilename=mediaFilenameBase+'.png'
            if self.headers['Content-type'].endswith('jpeg'):
                mediaFilename=mediaFilenameBase+'.jpg'
            if self.headers['Content-type'].endswith('gif'):
                mediaFilename=mediaFilenameBase+'.gif'
            with open(mediaFilename, 'wb') as avFile:
                avFile.write(mediaBytes)
            if self.server.debug:
                print('DEBUG: image saved to '+mediaFilename)
            self.send_response(201)
            self.end_headers()
            self.server.POSTbusy=False
            return            

        # refuse to receive non-json content
        if self.headers['Content-type'] != 'application/json' and \
           self.headers['Content-type'] != 'application/activity+json':
            print("POST is not json: "+self.headers['Content-type'])
            if self.server.debug:
                print(str(self.headers))
                length = int(self.headers['Content-length'])
                if length<self.server.maxPostLength:
                    unknownPost=self.rfile.read(length).decode('utf-8')
                    print(str(unknownPost))
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy=False
            return

        if self.server.debug:
            print('DEBUG: Reading message')

        messageBytes=self.rfile.read(length)
        messageJson=json.loads(messageBytes)
            
        # https://www.w3.org/TR/activitypub/#object-without-create
        if self.outboxAuthenticated:
            if self._postToOutbox(messageJson,__version__):                
                if messageJson.get('id'):
                    self.headers['Location']= \
                        messageJson['id'].replace('/activity','').replace('/undo','')
                self.send_response(201)
                self.end_headers()
                self.server.POSTbusy=False
                return
            else:
                if self.server.debug:
                    print('Failed to post to outbox')
                self.send_response(403)
                self.end_headers()
                self.server.POSTbusy=False
                return

        # check the necessary properties are available
        if self.server.debug:
            print('DEBUG: Check message has params')

        if self.path.endswith('/inbox') or \
           self.path=='/sharedInbox':
            if not inboxMessageHasParams(messageJson):
                if self.server.debug:
                    pprint(messageJson)
                    print("DEBUG: inbox message doesn't have the required parameters")
                self.send_response(403)
                self.end_headers()
                self.server.POSTbusy=False
                return

        if not inboxPermittedMessage(self.server.domain, \
                                     messageJson, \
                                     self.server.federationList):
            if self.server.debug:
                # https://www.youtube.com/watch?v=K3PrSj9XEu4
                print('DEBUG: Ah Ah Ah')
            self.send_response(403)
            self.end_headers()
            self.server.POSTbusy=False
            return

        if self.server.debug:
            pprint(messageJson)

        if not self.headers.get('signature'):
            if 'keyId=' not in self.headers['signature']:
                if self.server.debug:
                    print('DEBUG: POST to inbox has no keyId in header signature parameter')
                self.send_response(403)
                self.end_headers()
                self.server.POSTbusy=False
                return
        
        if self.server.debug:
            print('DEBUG: POST saving to inbox queue')
        if '/users/' in self.path:
            pathUsersSection=self.path.split('/users/')[1]
            if '/' not in pathUsersSection:
                if self.server.debug:
                    print('DEBUG: This is not a users endpoint')
            else:
                self.postToNickname=pathUsersSection.split('/')[0]
                if self.postToNickname:
                    queueStatus=self._updateInboxQueue(self.postToNickname,messageJson,messageBytes)
                    if queueStatus==0:
                        self.send_response(200)
                        self.end_headers()
                        self.server.POSTbusy=False
                        return
                    if queueStatus==1:
                        self.send_response(503)
                        self.end_headers()
                        self.server.POSTbusy=False
                        return
                    if self.server.debug:
                        print('_updateInboxQueue exited without doing anything')
                else:
                    if self.server.debug:
                        print('self.postToNickname is None')
            self.send_response(403)
            self.end_headers()
            self.server.POSTbusy=False
            return
        else:
            if self.path == '/sharedInbox' or self.path == '/inbox':
                print('DEBUG: POST to shared inbox')
                queueStatus=self._updateInboxQueue('inbox',messageJson,messageBytes)
                if queueStatus==0:
                    self.send_response(200)
                    self.end_headers()
                    self.server.POSTbusy=False
                    return
                if queueStatus==1:
                    self.send_response(503)
                    self.end_headers()
                    self.server.POSTbusy=False
                    return                    
        self.send_response(200)
        self.end_headers()
        self.server.POSTbusy=False

class PubServerUnitTest(PubServer):
    protocol_version = 'HTTP/1.0'
        
def runDaemon(projectVersion, \
              instanceId,clientToServer: bool, \
              baseDir: str,domain: str, \
              port=80,proxyPort=80,httpPrefix='https', \
              fedList=[],maxMentions=10, \
              authenticatedFetch=False, \
              noreply=False,nolike=False,nopics=False, \
              noannounce=False,cw=False,ocapAlways=False, \
              useTor=False,maxReplies=64, \
              domainMaxPostsPerDay=8640,accountMaxPostsPerDay=8640, \
              allowDeletion=False,debug=False,unitTest=False, \
              instanceOnlySkillsSearch=False) -> None:
    if len(domain)==0:
        domain='localhost'
    if '.' not in domain:
        if domain != 'localhost':
            print('Invalid domain: ' + domain)
            return

    serverAddress = ('', proxyPort)
    if unitTest: 
        httpd = ThreadingHTTPServer(serverAddress, PubServerUnitTest)
    else:
        httpd = ThreadingHTTPServer(serverAddress, PubServer)

    # load translations dictionary
    httpd.translate={}
    if not unitTest:
        if not os.path.isdir(baseDir+'/translations'):
            print('ERROR: translations directory not found')
            return
        systemLanguage=locale.getdefaultlocale()[0]
        if '_' in systemLanguage:
            systemLanguage=systemLanguage.split('_')[0]
        if '.' in systemLanguage:
            systemLanguage=systemLanguage.split('.')[0]
        translationsFile=baseDir+'/translations/'+systemLanguage+'.json'
        if not os.path.isfile(translationsFile):
            systemLanguage='en'
            translationsFile=baseDir+'/translations/'+systemLanguage+'.json'
        print('System language: '+systemLanguage)

        try:
            with open(translationsFile, 'r') as fp:
                httpd.translate=commentjson.load(fp)
        except Exception as e:
            print('ERROR while loading translations '+translationsFile)
            print(e)

    httpd.outboxThread={}
    httpd.newPostThread={}
    httpd.projectVersion=projectVersion
    httpd.authenticatedFetch=authenticatedFetch
    # max POST size of 30M
    httpd.maxPostLength=1024*1024*30
    httpd.maxMediaSize=httpd.maxPostLength
    httpd.maxMessageLength=5000
    httpd.maxPostsInBox=100000
    httpd.domain=domain
    httpd.port=port
    httpd.domainFull=domain
    if port:
        if port!=80 and port!=443:
            if ':' not in domain:
                httpd.domainFull=domain+':'+str(port)
    httpd.httpPrefix=httpPrefix
    httpd.debug=debug
    httpd.federationList=fedList.copy()
    httpd.baseDir=baseDir
    httpd.instanceId=instanceId
    httpd.personCache={}
    httpd.cachedWebfingers={}
    httpd.useTor=useTor
    httpd.session = None
    httpd.sessionLastUpdate=0
    httpd.lastGET=0
    httpd.lastPOST=0
    httpd.GETbusy=False
    httpd.POSTbusy=False
    httpd.receivedMessage=False
    httpd.inboxQueue=[]
    httpd.sendThreads=[]
    httpd.postLog=[]
    httpd.maxQueueLength=16
    httpd.ocapAlways=ocapAlways
    httpd.allowDeletion=allowDeletion
    httpd.lastLoginTime=0
    httpd.maxReplies=maxReplies
    httpd.salts={}
    httpd.tokens={}
    httpd.tokensLookup={}
    httpd.instanceOnlySkillsSearch=instanceOnlySkillsSearch
    httpd.acceptedCaps=["inbox:write","objects:read"]
    if noreply:
        httpd.acceptedCaps.append('inbox:noreply')
    if nolike:
        httpd.acceptedCaps.append('inbox:nolike')
    if nopics:
        httpd.acceptedCaps.append('inbox:nopics')
    if noannounce:
        httpd.acceptedCaps.append('inbox:noannounce')
    if cw:
        httpd.acceptedCaps.append('inbox:cw')

    if not os.path.isdir(baseDir+'/accounts/inbox@'+domain):
        print('Creating shared inbox: inbox@'+domain)
        createSharedInbox(baseDir,'inbox',domain,port,httpPrefix)

    if not os.path.isdir(baseDir+'/cache'):
        os.mkdir(baseDir+'/cache')
    if not os.path.isdir(baseDir+'/cache/actors'):
        print('Creating actors cache')
        os.mkdir(baseDir+'/cache/actors')
    if not os.path.isdir(baseDir+'/cache/announce'):
        print('Creating announce cache')
        os.mkdir(baseDir+'/cache/announce')
    if not os.path.isdir(baseDir+'/cache/avatars'):
        print('Creating avatars cache')
        os.mkdir(baseDir+'/cache/avatars')

    archiveDir=baseDir+'/archive'
    if not os.path.isdir(archiveDir):
        print('Creating archive')
        os.mkdir(archiveDir)
        
    print('Creating cache expiry thread')
    httpd.thrCache= \
        threadWithTrace(target=expireCache, \
                        args=(baseDir,httpd.personCache, \
                              httpd.httpPrefix, \
                              archiveDir, \
                              httpd.maxPostsInBox),daemon=True)
    httpd.thrCache.start()

    print('Creating inbox queue')
    httpd.thrInboxQueue= \
        threadWithTrace(target=runInboxQueue, \
                        args=(projectVersion, \
                              baseDir,httpPrefix,httpd.sendThreads, \
                              httpd.postLog,httpd.cachedWebfingers, \
                              httpd.personCache,httpd.inboxQueue, \
                              domain,port,useTor,httpd.federationList, \
                              httpd.ocapAlways,maxReplies, \
                              domainMaxPostsPerDay,accountMaxPostsPerDay, \
                              allowDeletion,debug,maxMentions, \
                              httpd.acceptedCaps),daemon=True)
    if not unitTest: 
        httpd.thrWatchdog= \
            threadWithTrace(target=runInboxQueueWatchdog, \
                            args=(projectVersion,httpd),daemon=True)        
        httpd.thrWatchdog.start()
    else:
        httpd.thrInboxQueue.start()

    if clientToServer:
        print('Running ActivityPub client on ' + domain + ' port ' + str(proxyPort))
    else:
        print('Running ActivityPub server on ' + domain + ' port ' + str(proxyPort))
    httpd.serve_forever()
