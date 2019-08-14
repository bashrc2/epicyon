__filename__ = "daemon.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "0.0.1"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
#import socketserver
import commentjson
import json
import time
import base64
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
from inbox import inboxPermittedMessage
from inbox import inboxMessageHasParams
from inbox import runInboxQueue
from inbox import savePostToInboxQueue
from inbox import populateReplies
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
from config import setConfigParam
from config import getConfigParam
from roles import outboxDelegate
from roles import setRole
from roles import clearModeratorStatus
from skills import outboxSkills
from availability import outboxAvailability
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
from webinterface import htmlSearch
from webinterface import htmlUnfollowConfirm
from webinterface import htmlProfileAfterSearch
from webinterface import htmlEditProfile
from webinterface import htmlTermsOfService
from webinterface import htmlHashtagSearch
from webinterface import htmlModerationInfo
from webinterface import htmlSearchSharedItems
from webinterface import htmlHashtagBlocked
from shares import getSharesFeedForPerson
from shares import outboxShareUpload
from shares import outboxUndoShareUpload
from shares import addShare
from utils import getNicknameFromActor
from utils import getDomainFromActor
from manualapprove import manualDenyFollowRequest
from manualapprove import manualApproveFollowRequest
from announce import createAnnounce
from announce import outboxAnnounce
from content import addHtmlTags
from media import removeMetaData
import os
import sys

# maximum number of posts to list in outbox feed
maxPostsInFeed=12

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
    def _login_headers(self,fileFormat: str) -> None:            
        self.send_response(200)
        self.send_header('Content-type', fileFormat)
        self.send_header('Host', self.server.domainFull)
        self.send_header('WWW-Authenticate', 'title="Login to Epicyon", Basic realm="epicyon"')
        self.end_headers()

    def _set_headers(self,fileFormat: str,cookie: str) -> None:
        self.send_response(200)
        self.send_header('Content-type', fileFormat)
        if cookie:
            self.send_header('Cookie', cookie)
        self.send_header('Host', self.server.domainFull)
        self.send_header('InstanceID', self.server.instanceId)
        self.end_headers()

    def _redirect_headers(self,redirect: str,cookie: str) -> None:
        self.send_response(303)
        self.send_header('Content-type', 'text/html')
        if cookie:
            self.send_header('Cookie', cookie)
        self.send_header('Location', redirect)
        self.send_header('Host', self.server.domainFull)
        self.send_header('InstanceID', self.server.instanceId)
        self.end_headers()

    def _404(self) -> None:
        self.send_response(404)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write("<html><head></head><body><h1>404 Not Found</h1></body></html>".encode('utf-8'))

    def _webfinger(self) -> bool:
        if not self.path.startswith('/.well-known'):
            return False
        if self.server.debug:
            print('DEBUG: WEBFINGER well-known')

        if self.server.debug:
            print('DEBUG: WEBFINGER host-meta')
        if self.path.startswith('/.well-known/host-meta'):
            wfResult=webfingerMeta()
            if wfResult:
                self._set_headers('application/xrd+xml')
                self.wfile.write(wfResult.encode('utf-8'))
            return

        if self.server.debug:
            print('DEBUG: WEBFINGER lookup '+self.path+' '+str(self.server.baseDir))
        wfResult=webfingerLookup(self.path,self.server.baseDir,self.server.port,self.server.debug)
        if wfResult:
            self._set_headers('application/jrd+json',None)
            self.wfile.write(json.dumps(wfResult).encode('utf-8'))
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

    def _postToOutbox(self,messageJson: {}) -> bool:
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
            postId=messageJson['id'].replace('/activity','')
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

    def _updateInboxQueue(self,nickname: str,messageJson: {}) -> int:
        """Update the inbox queue
        """
        # Check if the queue is full
        if len(self.server.inboxQueue)>=self.server.maxQueueLength:
            print('Inbox queue is full')
            return 1
        
        # save the json for later queue processing            
        queueFilename = \
            savePostToInboxQueue(self.server.baseDir, \
                                 self.server.httpPrefix, \
                                 nickname, \
                                 self.server.domainFull, \
                                 messageJson,
                                 self.headers['host'],
                                 self.headers['signature'],
                                 '/'+self.path.split('/')[-1],
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

        # treat shared inbox paths consistently
        if self.path=='/sharedInbox' or self.path=='/users/inbox':
            self.path='/inbox'

        # if not authorized then show the login screen
        if self.headers.get('Accept'):
            if 'text/html' in self.headers['Accept'] and self.path!='/login' and self.path!='/terms':                
                if '/media/' not in self.path and \
                   '/sharefiles/' not in self.path and \
                   '/statuses/' not in self.path and \
                   '/emoji/' not in self.path and \
                   '/tags/' not in self.path and \
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
                        self.send_response(303)
                        self.send_header('Location', '/login')
                        self.end_headers()
                        self.server.POSTbusy=False
                        return
            
        # get css
        # Note that this comes before the busy flag to avoid conflicts
        if self.path.endswith('.css'):
            if os.path.isfile('epicyon-profile.css'):
                with open('epicyon-profile.css', 'r') as cssfile:
                    css = cssfile.read()
                self._set_headers('text/css',cookie)
                self.wfile.write(css.encode('utf-8'))
                return
        # image on login screen
        if self.path=='/login.png':
            mediaFilename= \
                self.server.baseDir+'/accounts/login.png'
            if os.path.isfile(mediaFilename):
                self._set_headers('image/png',cookie)
                with open(mediaFilename, 'rb') as avFile:
                    mediaBinary = avFile.read()
                    self.wfile.write(mediaBinary)
            return        
        # login screen background image
        if self.path=='/login-background.png':
            mediaFilename= \
                self.server.baseDir+'/accounts/login-background.png'
            if os.path.isfile(mediaFilename):
                self._set_headers('image/png',cookie)
                with open(mediaFilename, 'rb') as avFile:
                    mediaBinary = avFile.read()
                    self.wfile.write(mediaBinary)
            return        
        # follow screen background image
        if self.path=='/follow-background.png':
            mediaFilename= \
                self.server.baseDir+'/accounts/follow-background.png'
            if os.path.isfile(mediaFilename):
                self._set_headers('image/png',cookie)
                with open(mediaFilename, 'rb') as avFile:
                    mediaBinary = avFile.read()
                    self.wfile.write(mediaBinary)
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
                    if emojiFilename.endswith('.png'):
                        self._set_headers('image/png',cookie)
                    elif emojiFilename.endswith('.jpg'):
                        self._set_headers('image/jpeg',cookie)
                    else:
                        self._set_headers('image/gif',cookie)
                    with open(emojiFilename, 'rb') as avFile:
                        emojiBinary = avFile.read()
                        self.wfile.write(emojiBinary)
                    return
            self._404()
            return
        # show media
        # Note that this comes before the busy flag to avoid conflicts
        if '/media/' in self.path:
            if self.path.endswith('.png') or \
               self.path.endswith('.jpg') or \
               self.path.endswith('.gif'):
                mediaStr=self.path.split('/media/')[1]
                mediaFilename= \
                    self.server.baseDir+'/media/'+mediaStr
                if os.path.isfile(mediaFilename):
                    if mediaFilename.endswith('.png'):
                        self._set_headers('image/png',cookie)
                    elif mediaFilename.endswith('.jpg'):
                        self._set_headers('image/jpeg',cookie)
                    else:
                        self._set_headers('image/gif',cookie)
                    with open(mediaFilename, 'rb') as avFile:
                        mediaBinary = avFile.read()
                        self.wfile.write(mediaBinary)
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
                    if mediaFilename.endswith('.png'):
                        self._set_headers('image/png',cookie)
                    elif mediaFilename.endswith('.jpg'):
                        self._set_headers('image/jpeg',cookie)
                    else:
                        self._set_headers('image/gif',cookie)
                    with open(mediaFilename, 'rb') as avFile:
                        mediaBinary = avFile.read()
                        self.wfile.write(mediaBinary)
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
                        self._set_headers('image/png',cookie)
                        with open(mediaFilename, 'rb') as avFile:
                            mediaBinary = avFile.read()
                            self.wfile.write(mediaBinary)
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
                        if avatarFile.endswith('.png'):
                            self._set_headers('image/png',cookie)
                        elif avatarFile.endswith('.jpg'):
                            self._set_headers('image/jpeg',cookie)
                        else:
                            self._set_headers('image/gif',cookie)
                        with open(avatarFilename, 'rb') as avFile:
                            avBinary = avFile.read()
                            self.wfile.write(avBinary)
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

        if self.path.startswith('/terms'):
            self._login_headers('text/html')
            self.wfile.write(htmlTermsOfService(self.server.baseDir, \
                                                self.server.httpPrefix, \
                                                self.server.domainFull).encode())
            self.server.GETbusy=False
            return

        if self.path.startswith('/login'):
            # request basic auth
            self._login_headers('text/html')
            self.wfile.write(htmlLogin(self.server.baseDir).encode('utf-8'))
            self.server.GETbusy=False
            return

        # follow a person from the web interface by selecting Follow on the dropdown
        if '/users/' in self.path:
           if '?follow=' in self.path:
               followStr=self.path.split('?follow=')[1]
               originPathStr=self.path.split('?follow=')[0]
               if ';' in followStr:
                   followActor=followStr.split(';')[0]
                   followProfileUrl=followStr.split(';')[1]
                   # show the confirm follow screen
                   self._set_headers('text/html',cookie)
                   self.wfile.write(htmlFollowConfirm(self.server.baseDir,originPathStr,followActor,followProfileUrl).encode())
                   self.server.GETbusy=False
                   return
               self._redirect_headers(originPathStr,cookie)
               self.server.GETbusy=False
               return

        # block a person from the web interface by selecting Block on the dropdown
        if '/users/' in self.path:
           if '?block=' in self.path:
               blockStr=self.path.split('?block=')[1]
               originPathStr=self.path.split('?block=')[0]
               if ';' in blockStr:
                   blockActor=blockStr.split(';')[0]
                   blockProfileUrl=blockStr.split(';')[1]
                   # show the confirm block screen
                   self._set_headers('text/html',cookie)
                   self.wfile.write(htmlBlockConfirm(self.server.baseDir,originPathStr,blockActor,blockProfileUrl).encode())
                   self.server.GETbusy=False
                   return
               self._redirect_headers(originPathStr,cookie)
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
                self._login_headers('text/html')
                self.wfile.write(htmlHashtagBlocked(self.server.baseDir).encode('utf-8'))
                self.server.GETbusy=False
                return
            hashtagStr= \
                htmlHashtagSearch(self.server.baseDir,hashtag,pageNumber, \
                                  maxPostsInFeed,self.server.session, \
                                  self.server.cachedWebfingers, \
                                  self.server.personCache, \
                                  self.server.httpPrefix, \
                                  self.server.projectVersion)
            self._set_headers('text/html',cookie)
            if hashtagStr:
               self.wfile.write(hashtagStr.encode())
            else:
               originPathStr=self.path.split('/tags/')[0]
               self._redirect_headers(originPathStr+'/search',cookie)                
            self.server.GETbusy=False
            return

        # search for a fediverse address from the web interface by selecting search icon
        if '/users/' in self.path:
           if self.path.endswith('/search'):
               # show the search screen
               self._set_headers('text/html',cookie)
               self.wfile.write(htmlSearch(self.server.baseDir,self.path).encode())
               self.server.GETbusy=False
               return

        # Unfollow a person from the web interface by selecting Unfollow on the dropdown
        if '/users/' in self.path:
           if '?unfollow=' in self.path:
               followStr=self.path.split('?unfollow=')[1]
               originPathStr=self.path.split('?unfollow=')[0]
               if ';' in followStr:
                   followActor=followStr.split(';')[0]
                   followProfileUrl=followStr.split(';')[1]
                   # show the confirm follow screen
                   self._set_headers('text/html',cookie)
                   self.wfile.write(htmlUnfollowConfirm(self.server.baseDir,originPathStr,followActor,followProfileUrl).encode())
                   self.server.GETbusy=False
                   return
               self._redirect_headers(originPathStr,cookie)
               self.server.GETbusy=False
               return

        # Unblock a person from the web interface by selecting Unblock on the dropdown
        if '/users/' in self.path:
           if '?unblock=' in self.path:
               blockStr=self.path.split('?unblock=')[1]
               originPathStr=self.path.split('?unblock=')[0]
               if ';' in blockStr:
                   blockActor=blockStr.split(';')[0]
                   blockProfileUrl=blockStr.split(';')[1]
                   # show the confirm unblock screen
                   self._set_headers('text/html',cookie)
                   self.wfile.write(htmlUnblockConfirm(self.server.baseDir,originPathStr,blockActor,blockProfileUrl).encode())
                   self.server.GETbusy=False
                   return
               self._redirect_headers(originPathStr,cookie)
               self.server.GETbusy=False
               return

        # announce/repeat from the web interface
        if authorized and '?repeat=' in self.path:
            repeatUrl=self.path.split('?repeat=')[1]
            actor=self.path.split('?repeat=')[0]
            self.postToNickname=getNicknameFromActor(actor)
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
                self._postToOutbox(announceJson)
            self.server.GETbusy=False
            self._redirect_headers(actor+'/inbox',cookie)
            return

        # undo an announce/repeat from the web interface
        if authorized and '?unrepeat=' in self.path:
            repeatUrl=self.path.split('?unrepeat=')[1]
            actor=self.path.split('?unrepeat=')[0]
            self.postToNickname=getNicknameFromActor(actor)
            if not self.server.session:
                self.server.session= \
                    createSession(self.server.domain,self.server.port,self.server.useTor)
            undoAnnounceActor=self.server.httpPrefix+'://'+self.server.domainFull+'/users/'+self.postToNickname
            newUndoAnnounce = {
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
            self._postToOutbox(newUndoAnnounce)
            self.server.GETbusy=False
            self._redirect_headers(actor+'/inbox',cookie)
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
                manualDenyFollowRequest(self.server.baseDir, \
                                        followerNickname,self.server.domain, \
                                        followingHandle)
            self._redirect_headers(originPathStr,cookie)
            self.server.GETbusy=False
            return

        # like from the web interface icon
        if authorized and '?like=' in self.path and '/statuses/' in self.path:
            likeUrl=self.path.split('?like=')[1]
            actor=self.path.split('?like=')[0]
            self.postToNickname=getNicknameFromActor(actor)
            if not self.server.session:
                self.server.session= \
                    createSession(self.server.domain,self.server.port,self.server.useTor)
            likeActor=self.server.httpPrefix+'://'+self.server.domainFull+'/users/'+self.postToNickname
            actorLiked=likeUrl.split('/statuses/')[0]
            likeJson= {
                'type': 'Like',
                'actor': likeActor,
                'object': likeUrl,
                'to': [actorLiked],
                'cc': [likeActor+'/followers']
            }    
            self._postToOutbox(likeJson)
            self.server.GETbusy=False
            self._redirect_headers(actor+'/inbox',cookie)
            return

        # undo a like from the web interface icon
        if authorized and '?unlike=' in self.path and '/statuses/' in self.path:
            likeUrl=self.path.split('?unlike=')[1]
            actor=self.path.split('?unlike=')[0]
            self.postToNickname=getNicknameFromActor(actor)
            if not self.server.session:
                self.server.session= \
                    createSession(self.server.domain,self.server.port,self.server.useTor)
            undoActor=self.server.httpPrefix+'://'+self.server.domainFull+'/users/'+self.postToNickname
            actorLiked=likeUrl.split('/statuses/')[0]
            undoLikeJson= {
                'type': 'Undo',
                'actor': undoActor,
                'object': {
                    'type': 'Like',
                    'actor': undoActor,
                    'object': likeUrl,
                    'cc': [undoActor+'/followers'],
                    'to': [actorLiked]
                },
                'cc': [undoActor+'/followers'],
                'to': [actorLiked]
            }
            self._postToOutbox(undoLikeJson)
            self.server.GETbusy=False
            self._redirect_headers(actor+'/inbox',cookie)
            return

        # delete a post from the web interface icon
        if authorized and '?delete=' in self.path:
            deleteUrl=self.path.split('?delete=')[1]
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
                if not self.server.session:
                    self.server.session= \
                        createSession(self.server.domain,self.server.port,self.server.useTor)
                deleteActor=self.server.httpPrefix+'://'+self.server.domainFull+'/users/'+self.postToNickname
                deleteJson= {
                    'actor': actor,
                    'object': deleteUrl,
                    'to': ['https://www.w3.org/ns/activitystreams#Public',actor],
                    'cc': [actor+'/followers'],
                    'type': 'Delete'
                }
                if self.server.debug:
                    pprint(deleteJson)
                self._postToOutbox(deleteJson)
            self.server.GETbusy=False
            self._redirect_headers(actor+'/inbox',cookie)
            return

        # reply from the web interface icon
        inReplyToUrl=None
        replyWithDM=False
        replyToList=[]
        if authorized and '?replyto=' in self.path:
            inReplyToUrl=self.path.split('?replyto=')[1]
            if '?' in inReplyToUrl:
                mentionsList=inReplyToUrl.split('?')
                for m in mentionsList:
                    if m.startswith('mention='):
                        replyToList.append(m.replace('mention=',''))
                inReplyToUrl=mentionsList[0]
            self.path=self.path.split('?replyto=')[0]+'/newpost'

        # replying as a direct message, for moderation posts
        if authorized and '?replydm=' in self.path:
            inReplyToUrl=self.path.split('?replydm=')[1]
            if '?' in inReplyToUrl:
                mentionsList=inReplyToUrl.split('?')
                for m in mentionsList:
                    if m.startswith('mention='):
                        replyToList.append(m.replace('mention=',''))
                inReplyToUrl=mentionsList[0]
            self.path=self.path.split('?replydm=')[0]+'/newdm'

        # edit profile in web interface
        if '/users/' in self.path and self.path.endswith('/editprofile'):
            self._set_headers('text/html',cookie)
            self.wfile.write(htmlEditProfile(self.server.baseDir,self.path,self.server.domain,self.server.port).encode())
            self.server.GETbusy=False
            return        

        # Various types of new post in the web interface
        if '/users/' in self.path and \
           (self.path.endswith('/newpost') or \
            self.path.endswith('/newunlisted') or \
            self.path.endswith('/newfollowers') or \
            self.path.endswith('/newdm') or \
            self.path.endswith('/newreport') or \
            '/newreport?=' in self.path or \
            self.path.endswith('/newshare')):
            self._set_headers('text/html',cookie)
            self.wfile.write(htmlNewPost(self.server.baseDir,self.path,inReplyToUrl,replyToList).encode())
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
                            with open(postFilename, 'r') as fp:
                                postJsonObject=commentjson.load(fp)
                                # Only authorized viewers get to see likes on posts
                                # Otherwize marketers could gain more social graph info
                                if not authorized:
                                    if postJsonObject.get('likes'):
                                        postJsonObject['likes']={}
                                if 'text/html' in self.headers['Accept']:
                                    self._set_headers('text/html',cookie)                    
                                    self.wfile.write(htmlIndividualPost( \
                                        self.server.session, \
                                        self.server.cachedWebfingers,self.server.personCache, \
                                        nickname,self.server.domain,self.server.port, \
                                        authorized,postJsonObject, \
                                        self.server.httpPrefix, \
                                        self.server.projectVersion).encode('utf-8'))
                                else:
                                    self._set_headers('application/json',None)
                                    self.wfile.write(json.dumps(postJsonObject).encode('utf-8'))
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
                                    if 'text/html' in self.headers['Accept']:
                                        if not self.server.session:
                                            if self.server.debug:
                                                print('DEBUG: creating new session')
                                            self.server.session= \
                                                createSession(self.server.domain,self.server.port,self.server.useTor)
                                        self._set_headers('text/html',cookie)
                                        print('----------------------------------------------------')
                                        pprint(repliesJson)
                                        self.wfile.write(htmlPostReplies(self.server.baseDir, \
                                                                         self.server.session, \
                                                                         self.server.cachedWebfingers, \
                                                                         self.server.personCache, \
                                                                         nickname, \
                                                                         self.server.domain, \
                                                                         self.server.port, \
                                                                         repliesJson, \
                                                                         self.server.httpPrefix, \
                                                                         self.server.projectVersion).encode('utf-8'))
                                    else:
                                        self._set_headers('application/json',None)
                                        self.wfile.write(json.dumps(repliesJson).encode('utf-8'))
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
                                    if 'text/html' in self.headers['Accept']:
                                        if not self.server.session:
                                            if self.server.debug:
                                                print('DEBUG: creating new session')
                                            self.server.session= \
                                                createSession(self.server.domain,self.server.port,self.server.useTor)
                                        self._set_headers('text/html',cookie)
                                        self.wfile.write(htmlPostReplies(self.server.baseDir, \
                                                                         self.server.session, \
                                                                         self.server.cachedWebfingers, \
                                                                         self.server.personCache, \
                                                                         nickname, \
                                                                         self.server.domain, \
                                                                         self.server.port, \
                                                                         repliesJson, \
                                                                         self.server.httpPrefix, \
                                                                         self.server.projectVersion).encode('utf-8'))
                                    else:
                                        self._set_headers('application/json',None)
                                        self.wfile.write(json.dumps(repliesJson).encode('utf-8'))
                                    self.server.GETbusy=False
                                    return

        if self.path.endswith('/roles') and '/users/' in self.path:
            namedStatus=self.path.split('/users/')[1]
            if '/' in namedStatus:
                postSections=namedStatus.split('/')
                nickname=postSections[0]
                actorFilename=self.server.baseDir+'/accounts/'+nickname+'@'+self.server.domain+'.json'
                if os.path.isfile(actorFilename):
                    with open(actorFilename, 'r') as fp:
                        actorJson=commentjson.load(fp)
                        if actorJson.get('roles'):
                            if 'text/html' in self.headers['Accept']:
                                getPerson = \
                                    personLookup(self.server.domain,self.path.replace('/roles',''), \
                                                 self.server.baseDir)
                                if getPerson:
                                    self._set_headers('text/html',cookie)
                                    self.wfile.write(htmlProfile(self.server.projectVersion, \
                                                                 self.server.baseDir, \
                                                                 self.server.httpPrefix, \
                                                                 True, \
                                                                 self.server.ocapAlways, \
                                                                 getPerson,'roles', \
                                                                 self.server.session, \
                                                                 self.server.cachedWebfingers, \
                                                                 self.server.personCache, \
                                                                 actorJson['roles']).encode('utf-8'))     
                            else:
                                self._set_headers('application/json',None)
                                self.wfile.write(json.dumps(actorJson['roles']).encode('utf-8'))
                            self.server.GETbusy=False
                            return

        if self.path.endswith('/skills') and '/users/' in self.path:
            namedStatus=self.path.split('/users/')[1]
            if '/' in namedStatus:
                postSections=namedStatus.split('/')
                nickname=postSections[0]
                actorFilename=self.server.baseDir+'/accounts/'+nickname+'@'+self.server.domain+'.json'
                if os.path.isfile(actorFilename):
                    with open(actorFilename, 'r') as fp:
                        actorJson=commentjson.load(fp)
                        if actorJson.get('skills'):
                            if 'text/html' in self.headers['Accept']:
                                getPerson = \
                                    personLookup(self.server.domain,self.path.replace('/skills',''), \
                                                 self.server.baseDir)
                                if getPerson:
                                    self._set_headers('text/html',cookie)
                                    self.wfile.write(htmlProfile(self.server.projectVersion, \
                                                                 self.server.baseDir, \
                                                                 self.server.httpPrefix, \
                                                                 True, \
                                                                 self.server.ocapAlways, \
                                                                 getPerson,'skills', \
                                                                 self.server.session, \
                                                                 self.server.cachedWebfingers, \
                                                                 self.server.personCache, \
                                                                 actorJson['skills']).encode('utf-8'))     
                            else:
                                self._set_headers('application/json',None)
                                self.wfile.write(json.dumps(actorJson['skills']).encode('utf-8'))
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
                            with open(postFilename, 'r') as fp:
                                postJsonObject=commentjson.load(fp)
                                # Only authorized viewers get to see likes on posts
                                # Otherwize marketers could gain more social graph info
                                if not authorized:
                                    if postJsonObject.get('likes'):
                                        postJsonObject['likes']={}                                    
                                if 'text/html' in self.headers['Accept']:
                                    self._set_headers('text/html',cookie)
                                    self.wfile.write(htmlIndividualPost( \
                                        self.server.baseDir, \
                                        self.server.session, \
                                        self.server.cachedWebfingers,self.server.personCache, \
                                        nickname,self.server.domain,self.server.port, \
                                        authorized,postJsonObject, \
                                        self.server.httpPrefix, \
                                        self.server.projectVersion).encode('utf-8'))
                                else:
                                    self._set_headers('application/json',None)
                                    self.wfile.write(json.dumps(postJsonObject).encode('utf-8'))
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
                    inboxFeed=personBoxJson(self.server.baseDir, \
                                            self.server.domain, \
                                            self.server.port, \
                                            self.path, \
                                            self.server.httpPrefix, \
                                            maxPostsInFeed, 'inbox', \
                                            True,self.server.ocapAlways)
                    if inboxFeed:
                        if 'text/html' in self.headers['Accept']:
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
                                inboxFeed=personBoxJson(self.server.baseDir, \
                                                        self.server.domain, \
                                                        self.server.port, \
                                                        self.path+'?page=1', \
                                                        self.server.httpPrefix, \
                                                        maxPostsInFeed, 'inbox', \
                                                        True,self.server.ocapAlways)
                            self._set_headers('text/html',cookie)
                            self.wfile.write(htmlInbox(pageNumber,maxPostsInFeed, \
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
                                                       self.server.projectVersion).encode('utf-8'))
                        else:
                            self._set_headers('application/json',None)
                            self.wfile.write(json.dumps(inboxFeed).encode('utf-8'))
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
        
        # get outbox feed for a person
        outboxFeed=personBoxJson(self.server.baseDir,self.server.domain, \
                                 self.server.port,self.path, \
                                 self.server.httpPrefix, \
                                 maxPostsInFeed, 'outbox', \
                                 authorized, \
                                 self.server.ocapAlways)
        if outboxFeed:
            if 'text/html' in self.headers['Accept']:
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
                    outboxFeed=personBoxJson(self.server.baseDir,self.server.domain, \
                                             self.server.port,self.path+'?page=1', \
                                             self.server.httpPrefix, \
                                             maxPostsInFeed, 'outbox', \
                                             authorized, \
                                             self.server.ocapAlways)
                    
                self._set_headers('text/html',cookie)
                self.wfile.write(htmlOutbox(pageNumber,maxPostsInFeed, \
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
                                            self.server.projectVersion).encode('utf-8'))
            else:
                self._set_headers('application/json',None)
                self.wfile.write(json.dumps(outboxFeed).encode('utf-8'))
            self.server.GETbusy=False
            return

        # get the moderation feed for a moderator
        if self.path.endswith('/moderation') or '/moderation?page=' in self.path:
            if '/users/' in self.path:
                if authorized:
                    moderationFeed= \
                        personBoxJson(self.server.baseDir, \
                                      self.server.domain, \
                                      self.server.port, \
                                      self.path, \
                                      self.server.httpPrefix, \
                                      maxPostsInFeed, 'moderation', \
                                      True,self.server.ocapAlways)
                    if moderationFeed:
                        if 'text/html' in self.headers['Accept']:
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
                                    personBoxJson(self.server.baseDir, \
                                                  self.server.domain, \
                                                  self.server.port, \
                                                  self.path+'?page=1', \
                                                  self.server.httpPrefix, \
                                                  maxPostsInFeed, 'moderation', \
                                                  True,self.server.ocapAlways)
                            self._set_headers('text/html',cookie)
                            self.wfile.write(htmlModeration(pageNumber,maxPostsInFeed, \
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
                                                            self.server.projectVersion).encode('utf-8'))
                        else:
                            self._set_headers('application/json',None)
                            self.wfile.write(json.dumps(moderationFeed).encode('utf-8'))
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
            if 'text/html' in self.headers['Accept']:
                if 'page=' not in self.path:
                    # get a page of shares, not the summary
                    shares=getSharesFeedForPerson(self.server.baseDir,self.server.domain, \
                                                  self.server.port,self.path+'?page=true', \
                                                  self.server.httpPrefix, \
                                                  sharesPerPage)
                getPerson = personLookup(self.server.domain,self.path.replace('/shares',''), \
                                         self.server.baseDir)
                if getPerson:
                    if not self.server.session:
                        if self.server.debug:
                            print('DEBUG: creating new session')
                        self.server.session= \
                            createSession(self.server.domain,self.server.port,self.server.useTor)
                    
                    self._set_headers('text/html',cookie)
                    self.wfile.write(htmlProfile(self.server.projectVersion, \
                                                 self.server.baseDir, \
                                                 self.server.httpPrefix, \
                                                 authorized, \
                                                 self.server.ocapAlways, \
                                                 getPerson,'shares', \
                                                 self.server.session, \
                                                 self.server.cachedWebfingers, \
                                                 self.server.personCache, \
                                                 shares).encode('utf-8'))                
                    self.server.GETbusy=False
                    return
            else:
                self._set_headers('application/json',None)
                self.wfile.write(json.dumps(shares).encode('utf-8'))
                self.server.GETbusy=False
                return

        following=getFollowingFeed(self.server.baseDir,self.server.domain, \
                                   self.server.port,self.path, \
                                   self.server.httpPrefix, \
                                   authorized,followsPerPage)
        if following:
            if 'text/html' in self.headers['Accept']:
                if 'page=' not in self.path:
                    # get a page of following, not the summary
                    following=getFollowingFeed(self.server.baseDir,self.server.domain, \
                                               self.server.port,self.path+'?page=true', \
                                               self.server.httpPrefix, \
                                               authorized,followsPerPage)
                getPerson = personLookup(self.server.domain,self.path.replace('/following',''), \
                                         self.server.baseDir)
                if getPerson:
                    if not self.server.session:
                        if self.server.debug:
                            print('DEBUG: creating new session')
                        self.server.session= \
                            createSession(self.server.domain,self.server.port,self.server.useTor)
                    
                    self._set_headers('text/html',cookie)
                    self.wfile.write(htmlProfile(self.server.projectVersion, \
                                                 self.server.baseDir, \
                                                 self.server.httpPrefix, \
                                                 authorized, \
                                                 self.server.ocapAlways, \
                                                 getPerson,'following', \
                                                 self.server.session, \
                                                 self.server.cachedWebfingers, \
                                                 self.server.personCache, \
                                                 following).encode('utf-8'))                
                    self.server.GETbusy=False
                    return
            else:
                self._set_headers('application/json',None)
                self.wfile.write(json.dumps(following).encode('utf-8'))
                self.server.GETbusy=False
                return
        followers=getFollowingFeed(self.server.baseDir,self.server.domain, \
                                   self.server.port,self.path, \
                                   self.server.httpPrefix, \
                                   authorized,followsPerPage,'followers')
        if followers:
            if 'text/html' in self.headers['Accept']:
                if 'page=' not in self.path:
                    # get a page of followers, not the summary
                    followers=getFollowingFeed(self.server.baseDir,self.server.domain, \
                                               self.server.port,self.path+'?page=1', \
                                               self.server.httpPrefix, \
                                               authorized,followsPerPage,'followers')
                getPerson = personLookup(self.server.domain,self.path.replace('/followers',''), \
                                         self.server.baseDir)
                if getPerson:
                    if not self.server.session:
                        if self.server.debug:
                            print('DEBUG: creating new session')
                        self.server.session= \
                            createSession(self.server.domain,self.server.port,self.server.useTor)
                    self._set_headers('text/html',cookie)
                    self.wfile.write(htmlProfile(self.server.projectVersion, \
                                                 self.server.baseDir, \
                                                 self.server.httpPrefix, \
                                                 authorized, \
                                                 self.server.ocapAlways, \
                                                 getPerson,'followers', \
                                                 self.server.session, \
                                                 self.server.cachedWebfingers, \
                                                 self.server.personCache, \
                                                 followers).encode('utf-8'))                
                    self.server.GETbusy=False
                    return
            else:
                self._set_headers('application/json',None)
                self.wfile.write(json.dumps(followers).encode('utf-8'))
            self.server.GETbusy=False
            return
        # look up a person
        getPerson = personLookup(self.server.domain,self.path, \
                                 self.server.baseDir)
        if getPerson:
            if 'text/html' in self.headers['Accept']:
                if not self.server.session:
                    if self.server.debug:
                        print('DEBUG: creating new session')
                    self.server.session= \
                        createSession(self.server.domain,self.server.port,self.server.useTor)
                self._set_headers('text/html',cookie)
                self.wfile.write(htmlProfile(self.server.projectVersion, \
                                             self.server.baseDir, \
                                             self.server.httpPrefix, \
                                             authorized, \
                                             self.server.ocapAlways, \
                                             getPerson,'posts',
                                             self.server.session, \
                                             self.server.cachedWebfingers, \
                                             self.server.personCache).encode('utf-8'))
            else:
                self._set_headers('application/json',None)
                self.wfile.write(json.dumps(getPerson).encode('utf-8'))
            self.server.GETbusy=False
            return
        # check that a json file was requested
        if not self.path.endswith('.json'):
            if self.server.debug:
                print('DEBUG: GET Not json: '+self.path+' '+self.server.baseDir)
            self._404()
            self.server.GETbusy=False
            return
        # check that the file exists
        filename=self.server.baseDir+self.path
        if os.path.isfile(filename):
            self._set_headers('application/json',None)
            with open(filename, 'r', encoding='utf-8') as File:
                content = File.read()
                contentJson=json.loads(content)
                self.wfile.write(json.dumps(contentJson).encode('utf-8'))
        else:
            if self.server.debug:
                print('DEBUG: GET Unknown file')
            self._404()
        self.server.GETbusy=False

    def do_HEAD(self):
        self._set_headers('application/json',None)

    def _receiveNewPost(self,authorized: bool,postType: str) -> bool:
        # 0 = this is not a new post
        # 1 = new post success
        # -1 = new post failed
        # 2 = new post canceled
        if authorized and '/users/' in self.path and self.path.endswith('?'+postType):            
            if ' boundary=' in self.headers['Content-type']:
                nickname=None
                nicknameStr=self.path.split('/users/')[1]
                if '/' in nicknameStr:
                    nickname=nicknameStr.split('/')[0]
                else:
                    return -1
                length = int(self.headers['Content-length'])
                if length>self.server.maxPostLength:
                    print('POST size too large')
                    return -1

                boundary=self.headers['Content-type'].split('boundary=')[1]
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
                                searchStr=b'Content-Type: image/png'
                                imageLocation=postBytes.find(searchStr)
                                filenameBase=self.server.baseDir+'/accounts/'+nickname+'@'+self.server.domain+'/upload'
                                if imageLocation>-1:
                                    filename=filenameBase+'.png'
                                else:        
                                    searchStr=b'Content-Type: image/jpeg'
                                    imageLocation=postBytes.find(searchStr)
                                    if imageLocation>-1:                                    
                                        filename=filenameBase+'.jpg'
                                    else:     
                                        searchStr=b'Content-Type: image/gif'
                                        imageLocation=postBytes.find(searchStr)
                                        if imageLocation>-1:                                    
                                            filename=filenameBase+'.gif'
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

                # send the post
                if not fields.get('message'):
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

                if postType=='newpost':
                    messageJson= \
                        createPublicPost(self.server.baseDir, \
                                         nickname, \
                                         self.server.domain,self.server.port, \
                                         self.server.httpPrefix, \
                                         fields['message'],False,False,False, \
                                         filename,fields['imageDescription'],True, \
                                         fields['replyTo'], fields['replyTo'],fields['subject'])
                    if messageJson:
                        self.postToNickname=nickname
                        if self._postToOutbox(messageJson):
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
                                           filename,fields['imageDescription'],True, \
                                           fields['replyTo'], fields['replyTo'],fields['subject'])
                    if messageJson:
                        self.postToNickname=nickname
                        if self._postToOutbox(messageJson):
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
                                                filename,fields['imageDescription'],True, \
                                                fields['replyTo'], fields['replyTo'],fields['subject'])
                    if messageJson:
                        self.postToNickname=nickname
                        if self._postToOutbox(messageJson):
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
                                                    filename,fields['imageDescription'],True, \
                                                    fields['replyTo'],fields['replyTo'],fields['subject'])
                    if messageJson:
                        self.postToNickname=nickname
                        if self._postToOutbox(messageJson):
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
                                         filename,fields['imageDescription'],True, \
                                         self.server.debug,fields['subject'])
                    if messageJson:
                        self.postToNickname=nickname
                        if self._postToOutbox(messageJson):
                            return 1
                        else:
                            return -1

                if postType=='newshare':
                    if not fields.get('itemType'):
                        return False
                    if not fields.get('category'):
                        return False
                    if not fields.get('location'):
                        return False
                    if not fields.get('duration'):
                        return False
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
                    if os.path.isfile(filename):
                        os.remove(filename)
                    self.postToNickname=nickname
                    if self._postToOutbox(messageJson):
                        return 1
                    else:
                        return -1
            return -1
        else:
            return 0
        
    def do_POST(self):
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
                    self.send_header('Content-type', 'text/html; charset=utf-8')
                    self.send_header('Set-Cookie', 'epicyon=; SameSite=Strict')
                    self.send_header('Location', '/login')
                    self.end_headers()                    
                    self.server.POSTbusy=False
                    return
                else:
                    if isSuspended(self.server.baseDir,loginNickname):
                        self._login_headers('text/html')
                        self.wfile.write(htmlSuspended(self.server.baseDir).encode('utf-8'))
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
                    self._redirect_headers(actorStr,cookie)
                    self.server.POSTbusy=False
                    return
                length = int(self.headers['Content-length'])
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
                    with open(actorFilename, 'r') as fp:
                        actorJson=commentjson.load(fp)
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
                        if fields.get('preferredNickname'):
                            if fields['preferredNickname']!=actorJson['preferredUsername']:
                                actorJson['preferredUsername']=fields['preferredNickname']
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
                            with open(actorFilename, 'w') as fp:
                                commentjson.dump(actorJson, fp, indent=4, sort_keys=False)
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
                        self._login_headers('text/html')
                        self.wfile.write(htmlModerationInfo(self.server.baseDir).encode('utf-8'))
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

        # a search was made
        if authorized and \
           (self.path.endswith('/searchhandle') or '/searchhandle?page=' in self.path):
            # get the page number
            pageNumber=1
            if '/searchhandle?page=' in self.path:
                pageNumberStr=self.path.split('/searchhandle?page=')[1]
                if pageNumberStr.isdigit():
                    pageNumber=int(pageNumberStr)
                self.path=self.path.split('?page=')[0]

            actorStr=self.path.replace('/searchhandle','')
            length = int(self.headers['Content-length'])
            searchParams=self.rfile.read(length).decode('utf-8')
            if 'searchtext=' in searchParams:
                searchStr=searchParams.split('searchtext=')[1]
                if '&' in searchStr:
                    searchStr=searchStr.split('&')[0]
                searchStr=searchStr.replace('+',' ').replace('%40','@').replace('%3A',':').replace('%23','#').strip()
                if searchStr.startswith('#'):      
                    # hashtag search
                    hashtagStr= \
                        htmlHashtagSearch(self.server.baseDir,searchStr[1:],1, \
                                          maxPostsInFeed,self.server.session, \
                                          self.server.cachedWebfingers, \
                                          self.server.personCache, \
                                          self.server.httpPrefix, \
                                          self.server.projectVersion)
                    if hashtagStr:
                        self._login_headers('text/html')
                        self.wfile.write(hashtagStr.encode('utf-8'))
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
                        htmlProfileAfterSearch(self.server.baseDir, \
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
                        self._login_headers('text/html')
                        self.wfile.write(profileStr.encode('utf-8'))
                        self.server.POSTbusy=False
                        return
                else:
                    # shared items search
                    sharedItemsStr= \
                        htmlSearchSharedItems(self.server.baseDir, \
                                              searchStr,pageNumber, \
                                              maxPostsInFeed,actorStr)
                    if sharedItemsStr:
                        self._login_headers('text/html')
                        self.wfile.write(sharedItemsStr.encode('utf-8'))
                        self.server.POSTbusy=False
                        return
            self._redirect_headers(actorStr,cookie)
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
                    unfollowJson = {
                        'type': 'Undo',
                        'actor': followActor,
                        'object': {
                            'type': 'Follow',
                            'actor': followActor,
                            'object': followingActor,
                            'to': [followingActor],
                            'cc': ['https://www.w3.org/ns/activitystreams#Public']
                        }
                    }
                    pathUsersSection=self.path.split('/users/')[1]
                    self.postToNickname=pathUsersSection.split('/')[0]
                    self._postToOutbox(unfollowJson)
            self._redirect_headers(originPathStr,cookie)
            self.server.POSTbusy=False
            return

        # decision to unblock in the web interface is confirmed
        if authorized and self.path.endswith('/unblockconfirm'):
            originPathStr=self.path.split('/unblockconfirm')[0]
            blockerNickname=getNicknameFromActor(originPathStr)
            length = int(self.headers['Content-length'])
            blockConfirmParams=self.rfile.read(length).decode('utf-8')
            if '&submitYes=' in blockConfirmParams:
                blockingActor=blockConfirmParams.replace('%3A',':').replace('%2F','/').split('actor=')[1]
                if '&' in blockingActor:
                    blockingActor=blockingActor.split('&')[0]
                blockingNickname=getNicknameFromActor(blockingActor)
                blockingDomain,blockingPort=getDomainFromActor(blockingActor)
                blockingDomainFull=blockingDomain
                if blockingPort:
                    if blockingPort!=80 and blockingPort!=443:
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
            length = int(self.headers['Content-length'])
            blockConfirmParams=self.rfile.read(length).decode('utf-8')
            if '&submitYes=' in blockConfirmParams:
                blockingActor=blockConfirmParams.replace('%3A',':').replace('%2F','/').split('actor=')[1]
                if '&' in blockingActor:
                    blockingActor=blockingActor.split('&')[0]
                blockingNickname=getNicknameFromActor(blockingActor)
                blockingDomain,blockingPort=getDomainFromActor(blockingActor)
                blockingDomainFull=blockingDomain
                if blockingPort:
                    if blockingPort!=80 and blockingPort!=443:
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

        postState=self._receiveNewPost(authorized,'newpost')
        if postState!=0:
            nickname=self.path.split('/users/')[1]
            if '/' in nickname:
                nickname=nickname.split('/')[0]
            self._redirect_headers('/users/'+nickname+'/outbox',cookie)
            self.server.POSTbusy=False
            return
        postState=self._receiveNewPost(authorized,'newunlisted')
        if postState!=0:
            nickname=self.path.split('/users/')[1]
            if '/' in nickname:
                nickname=nickname.split('/')[0]
            self._redirect_headers('/users/'+self.postToNickname+'/outbox',cookie)
            self.server.POSTbusy=False
            return
        postState=self._receiveNewPost(authorized,'newfollowers')
        if postState!=0:
            nickname=self.path.split('/users/')[1]
            if '/' in nickname:
                nickname=nickname.split('/')[0]
            self._redirect_headers('/users/'+self.postToNickname+'/outbox',cookie)
            self.server.POSTbusy=False
            return
        postState=self._receiveNewPost(authorized,'newdm')
        if postState!=0:
            nickname=self.path.split('/users/')[1]
            if '/' in nickname:
                nickname=nickname.split('/')[0]
            self._redirect_headers('/users/'+self.postToNickname+'/outbox',cookie)
            self.server.POSTbusy=False
            return
        postState=self._receiveNewPost(authorized,'newreport')
        if postState!=0:
            nickname=self.path.split('/users/')[1]
            if '/' in nickname:
                nickname=nickname.split('/')[0]
            self._redirect_headers('/users/'+self.postToNickname+'/outbox',cookie)
            self.server.POSTbusy=False
            return
        postState=self._receiveNewPost(authorized,'newshare')
        if postState!=0:
            nickname=self.path.split('/users/')[1]
            if '/' in nickname:
                nickname=nickname.split('/')[0]
            self._redirect_headers('/users/'+self.postToNickname+'/shares',cookie)
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
        if not self.headers['Content-type'].startswith('image/'):
            if length>self.server.maxMessageLength:
                print('Maximum message length exceeded '+str(length))
                self.send_response(400)
                self.end_headers()
                self.server.POSTbusy=False
                return
        else:
            if length>self.server.maxImageSize:
                print('Maximum image size exceeded '+str(length))
                self.send_response(400)
                self.end_headers()
                self.server.POSTbusy=False
                return

        # receive images to the outbox
        if self.headers['Content-type'].startswith('image/') and \
           '/users/' in self.path:
            if not self.outboxAuthenticated:
                if self.server.debug:
                    print('DEBUG: unathenticated attempt to post image to outbox')
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
            if self._postToOutbox(messageJson):                
                if messageJson.get('id'):
                    self.headers['Location']= \
                        messageJson['id'].replace('/activity','')
                self.send_response(201)
                self.end_headers()
                self.server.POSTbusy=False
                return
            else:
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
                    queueStatus=self._updateInboxQueue(self.postToNickname,messageJson)
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
                queueStatus=self._updateInboxQueue('inbox',messageJson)
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

def runDaemon(projectVersion, \
              instanceId,clientToServer: bool, \
              baseDir: str,domain: str, \
              port=80,proxyPort=80,httpPrefix='https', \
              fedList=[],noreply=False,nolike=False,nopics=False, \
              noannounce=False,cw=False,ocapAlways=False, \
              useTor=False,maxReplies=64, \
              domainMaxPostsPerDay=8640,accountMaxPostsPerDay=8640, \
              allowDeletion=False,debug=False) -> None:
    if len(domain)==0:
        domain='localhost'
    if '.' not in domain:
        if domain != 'localhost':
            print('Invalid domain: ' + domain)
            return

    serverAddress = ('', proxyPort)
    httpd = ThreadingHTTPServer(serverAddress, PubServer)
    # max POST size of 10M
    httpd.projectVersion=projectVersion
    httpd.maxPostLength=1024*1024*10
    httpd.domain=domain
    httpd.port=port
    httpd.domainFull=domain
    if port!=80 and port!=443:
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
    httpd.maxMessageLength=5000
    httpd.maxImageSize=10*1024*1024
    httpd.allowDeletion=allowDeletion
    httpd.lastLoginTime=0
    httpd.maxReplies=maxReplies
    httpd.salts={}
    httpd.tokens={}
    httpd.tokensLookup={}
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
                              allowDeletion,debug,httpd.acceptedCaps),daemon=True)
    httpd.thrInboxQueue.start()
    if clientToServer:
        print('Running ActivityPub client on ' + domain + ' port ' + str(proxyPort))
    else:
        print('Running ActivityPub server on ' + domain + ' port ' + str(proxyPort))
    httpd.serve_forever()
