__filename__ = "daemon.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.0.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
#import socketserver
import json
import time
import base64
import locale
# used for mime decoding of message POST
import email.parser
# for saving images
from binascii import a2b_base64
from hashlib import sha256
from session import createSession
from webfinger import webfingerMeta
from webfinger import webfingerNodeInfo
from webfinger import webfingerLookup
from webfinger import webfingerHandle
from metadata import metaDataNodeInfo
from metadata import metaDataInstance
from donate import getDonationUrl
from donate import setDonationUrl
from person import activateAccount
from person import deactivateAccount
from person import registerAccount
from person import personLookup
from person import personBoxJson
from person import createSharedInbox
from person import isSuspended
from person import suspendAccount
from person import unsuspendAccount
from person import removeAccount
from person import canRemovePost
from person import personSnooze
from person import personUnsnooze
from posts import createQuestionPost
from posts import outboxMessageCreateWrap
from posts import savePostToBox
from posts import sendToFollowersThread
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
from inbox import inboxUpdateIndex
from follow import getFollowingFeed
from follow import outboxUndoFollow
from follow import sendFollowRequest
from auth import authorize
from auth import createPassword
from auth import createBasicAuthHeader
from auth import authorizeBasic
from auth import storeBasicCredentials
from threads import threadWithTrace
from threads import removeDormantThreads
from media import getMediaPath
from media import createMediaDirs
from delete import outboxDelete
from like import outboxLike
from like import outboxUndoLike
from bookmarks import outboxBookmark
from bookmarks import outboxUndoBookmark
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
from webinterface import htmlBookmarks
from webinterface import htmlShares
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
from shares import expireShares
from utils import getCachedPostFilename
from utils import removePostFromCache
from utils import getNicknameFromActor
from utils import getDomainFromActor
from utils import getStatusNumber
from utils import urlPermitted
from utils import loadJson
from utils import saveJson
from manualapprove import manualDenyFollowRequest
from manualapprove import manualApproveFollowRequest
from announce import createAnnounce
from announce import outboxAnnounce
from content import addHtmlTags
from content import extractMediaInFormPOST
from content import saveMediaInFormPOST
from content import extractTextFieldsInPOST
from media import removeMetaData
from cache import storePersonInCache
from cache import getPersonFromCache
from httpsig import verifyPostHeaders
from theme import setTheme
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

def readFollowList(filename: str) -> None:
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

    def _sendReplyToQuestion(self,nickname: str,messageId: str,answer: str) -> None:
        """Sends a reply to a question
        """
        votesFilename= \
            self.server.baseDir+'/accounts/'+ \
            nickname+'@'+self.server.domain+'/questions.txt'

        # have we already voted on this?
        if messageId in open(votesFilename).read():
            print('Already voted on message '+messageId)
            return

        print('Voting on message '+messageId)
        print('Vote for: '+answer)
        messageJson= \
            createPublicPost(self.server.baseDir, \
                             nickname, \
                             self.server.domain,self.server.port, \
                             self.server.httpPrefix, \
                             answer,False,False,False, \
                             None,None,None,True, \
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
                # record the vote
                votesFile=open(votesFilename,'a+')
                if votesFile:
                    votesFile.write(messageId+'\n')
                    votesFile.close()

                # ensure that the cached post is removed if it exists, so
                # that it then will be recreated
                cachedPostFilename= \
                    getCachedPostFilename(self.server.baseDir, \
                                          nickname, \
                                          self.server.domain,messageJson)
                if cachedPostFilename:
                    if os.path.isfile(cachedPostFilename):
                        os.remove(cachedPostFilename)
                # remove from memory cache
                removePostFromCache(messageJson,self.server.recentPostsCache)                    
            else:
                print('ERROR: unable to post vote to outbox')
        else:
            print('ERROR: unable to create vote')
    
    def _removePostInteractions(self,postJsonObject: {}) -> None:
        """Removes potentially sensitive interactions from a post
        This is the type of thing which would be of interest to marketers
        or of saleable value to them. eg. Knowing who likes who or what.
        """
        if postJsonObject.get('likes'):
            postJsonObject['likes']={'items': []}
        if postJsonObject.get('shares'):
            postJsonObject['shares']={}
        if postJsonObject.get('replies'):
            postJsonObject['replies']={}
        if postJsonObject.get('bookmarks'):
            postJsonObject['bookmarks']={}
        if not postJsonObject.get('object'):
            return
        if not isinstance(postJsonObject['object'], dict):
            return
        if postJsonObject['object'].get('likes'):
            postJsonObject['object']['likes']={'items': []}
        if postJsonObject['object'].get('shares'):
            postJsonObject['object']['shares']={}
        if postJsonObject['object'].get('replies'):
            postJsonObject['object']['replies']={}
        if postJsonObject['object'].get('bookmarks'):
            postJsonObject['object']['bookmarks']={}

    def _requestHTTP(self) -> bool:
        """Should a http response be given?
        """
        if not self.headers.get('Accept'):
            return False
        if self.server.debug:
            print('ACCEPT: '+self.headers['Accept'])
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
                createSession(self.server.useTor)
        # obtain the public key
        pubKey= \
            getPersonPubKey(self.server.baseDir,self.server.session,keyId, \
                            self.server.personCache,self.server.debug, \
                            __version__,self.server.httpPrefix, \
                            self.server.domain)
        if not pubKey:
            if self.server.debug:
                print('DEBUG: Authenticated fetch failed to obtain public key for '+ \
                      keyId)
            return False
        # it is assumed that there will be no message body on authenticated fetches
        # and also consequently no digest
        GETrequestBody=''
        GETrequestDigest=None
        # verify the GET request without any digest
        if verifyPostHeaders(self.server.httpPrefix, \
                             pubKey,self.headers, \
                             self.path,True, \
                             GETrequestDigest, \
                             GETrequestBody,debug):
            return True
        return False

    def _login_headers(self,fileFormat: str,length: int) -> None:
        self.send_response(200)
        self.send_header('Content-type', fileFormat)
        self.send_header('Content-Length', str(length))
        self.send_header('Host', self.server.domainFull)
        self.send_header('WWW-Authenticate', \
                         'title="Login to Epicyon", Basic realm="epicyon"')
        self.send_header('X-Robots-Tag','noindex')
        self.end_headers()

    def _logout_headers(self,fileFormat: str,length: int) -> None:
        self.send_response(200)
        self.send_header('Content-type', fileFormat)
        self.send_header('Content-Length', str(length))
        self.send_header('Set-Cookie', 'epicyon=; SameSite=Strict')
        self.send_header('Host', self.server.domainFull)
        self.send_header('WWW-Authenticate', \
                         'title="Login to Epicyon", Basic realm="epicyon"')
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
        if '://' not in redirect:
            print('REDIRECT ERROR: redirect is not an absolute url '+redirect)
        self.send_header('Location', redirect)
        self.send_header('Host', self.server.domainFull)
        self.send_header('InstanceID', self.server.instanceId)
        self.send_header('Content-Length', '0')
        self.send_header('X-Robots-Tag','noindex')
        self.end_headers()

    def _httpReturnCode(self,httpCode: int,httpDescription: str) -> None:
        msg="<html><head></head><body><h1>"+str(httpCode)+" "+httpDescription+"</h1></body></html>"
        msg=msg.encode('utf-8')
        self.send_response(httpCode)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(msg)))
        self.send_header('X-Robots-Tag','noindex')
        self.end_headers()
        try:
            self.wfile.write(msg)
        except Exception as e:
            print('Error when showing '+str(httpCode))
            print(e)

    def _404(self) -> None:
        self._httpReturnCode(404,'Not Found')

    def _400(self) -> None:
        self._httpReturnCode(400,'Bad Request')

    def _503(self) -> None:
        self._httpReturnCode(503,'Service Unavailable')
            
    def _write(self,msg) -> None:
        tries=0
        while tries<5:
            try:
                self.wfile.write(msg)
                break
            except Exception as e:
                print(e)
                time.sleep(1)
                tries+=1

    def _robotsTxt(self) -> bool:
        if not self.path.lower().startswith('/robot'):
            return False
        msg='User-agent: *\nDisallow: /'
        msg=msg.encode('utf-8')
        self._set_headers('text/plain; charset=utf-8',len(msg),None)
        self._write(msg)
        return True

    def _mastoApi(self) -> bool:
        """This is a vestigil mastodon API for the purpose
        of returning an empty result to sites like
        https://mastopeek.app-dist.eu
        """
        if not self.path.startswith('/api/v1/'):
            return False
        if self.server.debug:
            print('DEBUG: mastodon api '+self.path)
        if self.path=='/api/v1/instance':
            adminNickname=getConfigParam(self.server.baseDir,'admin')
            instanceDescriptionShort=getConfigParam(self.server.baseDir,'instanceDescriptionShort')
            instanceDescription=getConfigParam(self.server.baseDir,'instanceDescription')
            instanceTitle=getConfigParam(self.server.baseDir,'instanceTitle')
            instanceJson= \
                metaDataInstance(instanceTitle, \
                                 instanceDescriptionShort, \
                                 instanceDescription, \
                                 self.server.httpPrefix, \
                                 self.server.baseDir, \
                                 adminNickname, \
                                 self.server.domain,self.server.domainFull, \
                                 self.server.registration, \
                                 self.server.systemLanguage, \
                                 self.server.projectVersion)
            msg=json.dumps(instanceJson).encode('utf-8')
            if self.headers.get('Accept'):
                if 'application/ld+json' in self.headers['Accept']:
                    self._set_headers('application/ld+json',len(msg),None)
                else:
                    self._set_headers('application/json',len(msg),None)
            else:
                self._set_headers('application/ld+json',len(msg),None)
            self._write(msg)
            print('instance metadata sent')
            return True            
        if self.path.startswith('/api/v1/instance/peers'):
            # This is just a dummy result.
            # Showing the full list of peers would have privacy implications.
            # On a large instance you are somewhat lost in the crowd, but on small
            # instances a full list of peers would convey a lot of information about
            # the interests of a small number of accounts
            msg=json.dumps(['mastodon.social',self.server.domainFull]).encode('utf-8')
            if self.headers.get('Accept'):
                if 'application/ld+json' in self.headers['Accept']:
                    self._set_headers('application/ld+json',len(msg),None)
                else:
                    self._set_headers('application/json',len(msg),None)
            else:
                self._set_headers('application/ld+json',len(msg),None)
            self._write(msg)
            print('instance peers metadata sent')
            return True
        if self.path.startswith('/api/v1/instance/activity'):
            # This is just a dummy result.
            msg=json.dumps([]).encode('utf-8')
            if self.headers.get('Accept'):
                if 'application/ld+json' in self.headers['Accept']:
                    self._set_headers('application/ld+json',len(msg),None)
                else:
                    self._set_headers('application/json',len(msg),None)
            else:
                self._set_headers('application/ld+json',len(msg),None)
            self._write(msg)
            print('instance activity metadata sent')
            return True
        self._404()            
        return True
        
    def _nodeinfo(self) -> bool:
        if not self.path.startswith('/nodeinfo/2.0'):
            return False
        if self.server.debug:
            print('DEBUG: nodeinfo '+self.path)        
        info=metaDataNodeInfo(self.server.baseDir,self.server.registration,self.server.projectVersion)
        if info:
            msg=json.dumps(info).encode('utf-8')
            if self.headers.get('Accept'):
                if 'application/ld+json' in self.headers['Accept']:
                    self._set_headers('application/ld+json',len(msg),None)
                else:
                    self._set_headers('application/json',len(msg),None)
            else:
                self._set_headers('application/ld+json',len(msg),None)
            self._write(msg)
            print('nodeinfo sent')
            return True
        self._404()
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
                self._write(msg)
                return True
            self._404()            
            return True
        if self.path.startswith('/.well-known/nodeinfo'):
            wfResult=webfingerNodeInfo(self.server.httpPrefix,self.server.domainFull)
            if wfResult:
                msg=json.dumps(wfResult).encode('utf-8')
                if self.headers.get('Accept'):
                    if 'application/ld+json' in self.headers['Accept']:
                        self._set_headers('application/ld+json',len(msg),None)
                    else:
                        self._set_headers('application/json',len(msg),None)
                else:
                    self._set_headers('application/ld+json',len(msg),None)
                self._write(msg)
                return True
            self._404()            
            return True

        if self.server.debug:
            print('DEBUG: WEBFINGER lookup '+self.path+' '+str(self.server.baseDir))
        wfResult=webfingerLookup(self.path,self.server.baseDir,self.server.port,self.server.debug)
        if wfResult:
            msg=json.dumps(wfResult).encode('utf-8')
            self._set_headers('application/jrd+json',len(msg),None)
            self._write(msg)
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
                    mediaTypeStr= \
                        messageJson['object']['attachment'][attachmentIndex]['mediaType']
                    if mediaTypeStr.endswith('jpeg'):
                        fileExtension='jpg'
                    elif mediaTypeStr.endswith('gif'):
                        fileExtension='gif'
                    elif mediaTypeStr.endswith('webp'):
                        fileExtension='webp'
                    elif mediaTypeStr.endswith('audio/mpeg'):
                        fileExtension='mp3'
                    elif mediaTypeStr.endswith('ogg'):
                        fileExtension='ogg'
                    elif mediaTypeStr.endswith('mp4'):
                        fileExtension='mp4'
                    elif mediaTypeStr.endswith('webm'):
                        fileExtension='webm'
                    elif mediaTypeStr.endswith('ogv'):
                        fileExtension='ogv'
                    mediaDir= \
                        self.server.baseDir+'/accounts/'+ \
                        self.postToNickname+'@'+self.server.domain
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
                            self.server.httpPrefix+'://'+self.server.domainFull+ \
                            '/'+mediaPath

        permittedOutboxTypes=[
            'Create','Announce','Like','Follow','Undo', \
            'Update','Add','Remove','Block','Delete', \
            'Delegate','Skill','Bookmark'
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
            print('DEBUG: savePostToBox')
        if messageJson['type']!='Upgrade':
            savedFilename= \
                savePostToBox(self.server.baseDir, \
                              self.server.httpPrefix, \
                              postId, \
                              self.postToNickname, \
                              self.server.domainFull,messageJson,'outbox')
            if messageJson['type']=='Create' or \
               messageJson['type']=='Question' or \
               messageJson['type']=='Note' or \
               messageJson['type']=='Announce':
                inboxUpdateIndex('outbox',self.server.baseDir, \
                                 self.postToNickname+'@'+self.server.domain, \
                                 savedFilename,self.server.debug)            
        if outboxAnnounce(self.server.recentPostsCache, \
                          self.server.baseDir,messageJson,self.server.debug):
            if self.server.debug:
                print('DEBUG: Updated announcements (shares) collection for the post associated with the Announce activity')
        if not self.server.session:
            if self.server.debug:
                print('DEBUG: creating new session for c2s')
            self.server.session= \
                createSession(self.server.useTor)
        if self.server.debug:
            print('DEBUG: sending c2s post to followers')
        # remove inactive threads
        inactiveFollowerThreads=[]
        for th in self.server.followersThreads:
            if not th.is_alive():
                inactiveFollowerThreads.append(th)
        for th in inactiveFollowerThreads:
            self.server.followersThreads.remove(th)
        if self.server.debug:
            print('DEBUG: '+str(len(self.server.followersThreads))+' followers threads active')
        # retain up to 20 threads
        if len(self.server.followersThreads)>20:
            # kill the thread if it is still alive
            if self.server.followersThreads[0].is_alive():
                self.server.followersThreads[0].kill()
            # remove it from the list
            self.server.followersThreads.pop(0)
        # create a thread to send the post to followers
        followersThread= \
            sendToFollowersThread(self.server.session, \
                                  self.server.baseDir, \
                                  self.postToNickname, \
                                  self.server.domain, \
                                  self.server.port, \
                                  self.server.httpPrefix, \
                                  self.server.federationList, \
                                  self.server.sendThreads, \
                                  self.server.postLog, \
                                  self.server.cachedWebfingers, \
                                  self.server.personCache, \
                                  messageJson,self.server.debug, \
                                  self.server.projectVersion)
        self.server.followersThreads.append(followersThread)
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
        outboxLike(self.server.recentPostsCache, \
                   self.server.baseDir,self.server.httpPrefix, \
                   self.postToNickname,self.server.domain,self.server.port, \
                   messageJson,self.server.debug)
        if self.server.debug:
            print('DEBUG: handle any undo like requests')
        outboxUndoLike(self.server.baseDir,self.server.httpPrefix, \
                       self.postToNickname,self.server.domain,self.server.port, \
                       messageJson,self.server.debug)

        if self.server.debug:
            print('DEBUG: handle any bookmark requests')
        outboxBookmark(self.server.recentPostsCache, \
                       self.server.baseDir,self.server.httpPrefix, \
                       self.postToNickname,self.server.domain,self.server.port, \
                       messageJson,self.server.debug)
        if self.server.debug:
            print('DEBUG: handle any undo bookmark requests')
        outboxUndoBookmark(self.server.recentPostsCache, \
                           self.server.baseDir,self.server.httpPrefix, \
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
            print('c2s sender: '+self.postToNickname+'@'+ \
                  self.server.domain+':'+str(self.server.port))
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

    def _inboxQueueCleardown(self) -> None:
        """ Check if the queue is full and remove oldest items if it is
        """
        if len(self.server.inboxQueue)>=self.server.maxQueueLength:
            print('Inbox queue is full. Removing oldest items.')
            cleardownStartTime=time.time()
            while len(self.server.inboxQueue) >= self.server.maxQueueLength-4:
                queueFilename=self.server.inboxQueue[0]
                if os.path.isfile(queueFilename):
                    try:
                        os.remove(queueFilename)
                    except:
                        pass
                self.server.inboxQueue.pop(0)
            timeDiff=str(int((time.time()-cleardownStartTime)*1000))
            print('Inbox cleardown took '+timeDiff+' mS')
    
    def _updateInboxQueue(self,nickname: str,messageJson: {}, \
                          messageBytes: str) -> int:
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
        if self.headers.get('Content-Length'):
            headersDict['Content-Length']=self.headers['Content-Length']            
        elif self.headers.get('content-length'):
            headersDict['content-length']=self.headers['content-length']

        # For follow activities add a 'to' field, which is a copy
        # of the object field
        messageJson,toFieldExists= \
            addToField('Follow',messageJson,self.server.debug)
        
        # For like activities add a 'to' field, which is a copy of
        # the actor within the object field
        messageJson,toFieldExists= \
            addToField('Like',messageJson,self.server.debug)

        beginSaveTime=time.time()
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
            if self.server.debug:
                timeDiff=int((time.time()-beginSaveTime)*1000)
                if timeDiff>200:
                    print('SLOW: slow save of inbox queue item '+queueFilename+' took '+str(timeDiff)+' mS')
            self.send_response(201)
            self.end_headers()
            self.server.POSTbusy=False
            return 0
        return 2

    def _isAuthorized(self) -> bool:
        # token based authenticated used by the web interface
        if self.headers.get('Cookie'):
            if self.headers['Cookie'].startswith('epicyon='):
                tokenStr=self.headers['Cookie'].split('=',1)[1]
                if self.server.tokensLookup.get(tokenStr):
                    nickname=self.server.tokensLookup[tokenStr]
                    # default to the inbox of the person
                    if self.path=='/':
                        self.path='/users/'+nickname+'/inbox'
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
    
    def _clearLoginDetails(self,nickname: str):
        """Clears login details for the given account
        """
        # remove any token
        if self.server.tokens.get(nickname):
            del self.server.tokensLookup[self.server.tokens[nickname]]
            del self.server.tokens[nickname]
        self.send_response(303)
        self.send_header('Content-Length', '0')
        self.send_header('Set-Cookie', 'epicyon=; SameSite=Strict')
        self.send_header('Location', \
                         self.server.httpPrefix+'://'+ \
                         self.server.domainFull+'/login')
        self.send_header('X-Robots-Tag','noindex')
        self.end_headers()

    def _benchmarkGETtimings(self,GETstartTime,GETtimings: [],getID: int):
        """Updates a list containing how long each segment of GET takes
        """
        if self.server.debug:
            timeDiff=int((time.time()-GETstartTime)*1000)
            logEvent=False
            if timeDiff>100:
                logEvent=True
            if GETtimings:
                timeDiff=int(timeDiff-int(GETtimings[-1]))
            GETtimings.append(str(timeDiff))
            if logEvent:
                ctr=1
                for timeDiff in GETtimings:
                    print('GET TIMING|'+str(ctr)+'|'+timeDiff)
                    ctr+=1

    def _benchmarkPOSTtimings(self,POSTstartTime,POSTtimings: [],postID: int):
        """Updates a list containing how long each segment of POST takes
        """
        if self.server.debug:
            timeDiff=int((time.time()-POSTstartTime)*1000)
            logEvent=False
            if timeDiff>100:
                logEvent=True
            if POSTtimings:
                timeDiff=int(timeDiff-int(POSTtimings[-1]))
            POSTtimings.append(str(timeDiff))
            if logEvent:
                ctr=1
                for timeDiff in POSTtimings:
                    print('POST TIMING|'+str(ctr)+'|'+timeDiff)
                    ctr+=1

    def do_GET(self):
        GETstartTime=time.time()
        GETtimings=[]

        # Since fediverse crawlers are quite active, make returning info to them high priority
        # get nodeinfo endpoint
        if self._nodeinfo():
            return

        self._benchmarkGETtimings(GETstartTime,GETtimings,1)

        # minimal mastodon api
        if self._mastoApi():
            return

        self._benchmarkGETtimings(GETstartTime,GETtimings,2)

        if self.path=='/logout':
            msg=htmlLogin(self.server.translate, \
                          self.server.baseDir,False).encode('utf-8')
            self._logout_headers('text/html',len(msg))
            self._write(msg)            
            return

        self._benchmarkGETtimings(GETstartTime,GETtimings,3)

        # replace https://domain/@nick with https://domain/users/nick
        if self.path.startswith('/@'):
            self.path=self.path.replace('/@','/users/')

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

        self._benchmarkGETtimings(GETstartTime,GETtimings,4)

        # check authorization
        authorized = self._isAuthorized()
        if authorized:
            if self.server.debug:
                print('GET Authorization granted')
        else:
            if self.server.debug:
                print('GET Not authorized')

        self._benchmarkGETtimings(GETstartTime,GETtimings,5)

        if not self.server.session:
            print('Starting new session')
            self.server.session= \
                createSession(self.server.useTor)

        self._benchmarkGETtimings(GETstartTime,GETtimings,6)

        # is this a html request?
        htmlGET=False
        if self.headers.get('Accept'):
            if self._requestHTTP():
                htmlGET=True
        else:
            self._400()
            return

        self._benchmarkGETtimings(GETstartTime,GETtimings,7)

        # treat shared inbox paths consistently
        if self.path=='/sharedInbox' or \
           self.path=='/users/inbox' or \
           self.path=='/actor/inbox' or \
           self.path=='/users/'+self.server.domain:
            # if shared inbox is not enabled
            if not self.server.enableSharedInbox:
                self._503()
                return
                
            self.path='/inbox'

        self._benchmarkGETtimings(GETstartTime,GETtimings,8)

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
                   donateUrl=None
                   actorJson=getPersonFromCache(self.server.baseDir,optionsActor,self.server.personCache)
                   if actorJson:
                       donateUrl=getDonationUrl(actorJson)
                   msg=htmlPersonOptions(self.server.translate, \
                                         self.server.baseDir, \
                                         self.server.domain, \
                                         originPathStr, \
                                         optionsActor, \
                                         optionsProfileUrl, \
                                         optionsLink, \
                                         pageNumber,donateUrl).encode()
                   self._set_headers('text/html',len(msg),cookie)
                   self._write(msg)
                   return
               originPathStrAbsolute=self.server.httpPrefix+'://'+self.server.domainFull+originPathStr
               self._redirect_headers(originPathStrAbsolute,cookie)
               return

        self._benchmarkGETtimings(GETstartTime,GETtimings,9)

        # remove a shared item
        if htmlGET and '?rmshare=' in self.path:
            shareName=self.path.split('?rmshare=')[1]
            shareName=shareName.replace('%20',' ').replace('%40','@').replace('%3A',':').replace('%2F','/').replace('%23','#').strip()
            actor= \
                self.server.httpPrefix+'://'+self.server.domainFull+ \
                self.path.split('?rmshare=')[0]
            msg=htmlRemoveSharedItem(self.server.translate, \
                                     self.server.baseDir, \
                                     actor,shareName).encode()
            if not msg:
               self._redirect_headers(actor+'/inbox',cookie)
               return                
            self._set_headers('text/html',len(msg),cookie)
            self._write(msg)
            return

        self._benchmarkGETtimings(GETstartTime,GETtimings,10)

        if self.path.startswith('/terms'):
            msg=htmlTermsOfService(self.server.baseDir, \
                                   self.server.httpPrefix, \
                                   self.server.domainFull).encode()
            self._login_headers('text/html',len(msg))
            self._write(msg)
            return

        self._benchmarkGETtimings(GETstartTime,GETtimings,11)

        if self.path.startswith('/about'):
            msg=htmlAbout(self.server.baseDir, \
                          self.server.httpPrefix, \
                          self.server.domainFull).encode()
            self._login_headers('text/html',len(msg))
            self._write(msg)
            return

        self._benchmarkGETtimings(GETstartTime,GETtimings,12)

        # send robots.txt if asked
        if self._robotsTxt():
            return
            
        self._benchmarkGETtimings(GETstartTime,GETtimings,13)

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
                    self.send_header('Location', \
                                     self.server.httpPrefix+'://'+ \
                                     self.server.domainFull+'/login')
                    self.send_header('Content-Length', '0')
                    self.send_header('X-Robots-Tag','noindex')
                    self.end_headers()
                    return

        self._benchmarkGETtimings(GETstartTime,GETtimings,14)

        # get css
        # Note that this comes before the busy flag to avoid conflicts
        if self.path.endswith('.css'):
            if os.path.isfile('epicyon-profile.css'):
                tries=0
                while tries<5:
                    try:
                        with open('epicyon-profile.css', 'r') as cssfile:
                            css = cssfile.read()
                            break
                    except Exception as e:
                        print(e)
                        time.sleep(1)
                        tries+=1
                msg=css.encode('utf-8')
                self._set_headers('text/css',len(msg),cookie)
                self._write(msg)
                return
            self._404()
            return

        self._benchmarkGETtimings(GETstartTime,GETtimings,15)

        # image on login screen
        if self.path=='/login.png' or \
           self.path=='/login.gif' or \
           self.path=='/login.webp' or \
           self.path=='/login.jpeg' or \
           self.path=='/login.jpg':
            mediaFilename= \
                self.server.baseDir+'/accounts'+self.path
            if os.path.isfile(mediaFilename):
                tries=0
                mediaBinary=None
                while tries<5:
                    try:
                        with open(mediaFilename, 'rb') as avFile:
                            mediaBinary = avFile.read()
                            break
                    except Exception as e:
                        print(e)
                        time.sleep(1)
                        tries+=1
                if mediaBinary:
                    self._set_headers('image/png',len(mediaBinary),cookie)
                    self._write(mediaBinary)
                    return
            self._404()
            return

        self._benchmarkGETtimings(GETstartTime,GETtimings,16)

        # login screen background image
        if self.path=='/login-background.png':
            mediaFilename= \
                self.server.baseDir+'/accounts/login-background.png'
            if os.path.isfile(mediaFilename):
                tries=0
                mediaBinary=None
                while tries<5:
                    try:
                        with open(mediaFilename, 'rb') as avFile:
                            mediaBinary = avFile.read()
                            break
                    except Exception as e:
                        print(e)
                        time.sleep(1)
                        tries+=1
                if mediaBinary:
                    self._set_headers('image/png',len(mediaBinary),cookie)
                    self._write(mediaBinary)
                    return
            self._404()
            return

        self._benchmarkGETtimings(GETstartTime,GETtimings,17)

        # follow screen background image
        if self.path=='/follow-background.png':
            mediaFilename= \
                self.server.baseDir+'/accounts/follow-background.png'
            if os.path.isfile(mediaFilename):
                tries=0
                mediaBinary=None
                while tries<5:
                    try:
                        with open(mediaFilename, 'rb') as avFile:
                            mediaBinary = avFile.read()
                            break
                    except Exception as e:
                        print(e)
                        time.sleep(1)
                        tries+=1
                if mediaBinary:
                    self._set_headers('image/png',len(mediaBinary),cookie)
                    self._write(mediaBinary)
                    return
            self._404()
            return

        self._benchmarkGETtimings(GETstartTime,GETtimings,18)

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
                    elif emojiFilename.endswith('.webp'):
                        mediaImageType='webp'
                    else:
                        mediaImageType='gif'                        
                    with open(emojiFilename, 'rb') as avFile:
                        mediaBinary = avFile.read()
                        self._set_headers('image/'+mediaImageType,len(mediaBinary),cookie)
                        self._write(mediaBinary)
                    return
            self._404()
            return

        self._benchmarkGETtimings(GETstartTime,GETtimings,19)

        # show media
        # Note that this comes before the busy flag to avoid conflicts
        if '/media/' in self.path:
            if self.path.endswith('.png') or \
               self.path.endswith('.jpg') or \
               self.path.endswith('.gif') or \
               self.path.endswith('.webp') or \
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
                    elif mediaFilename.endswith('.webp'):
                        mediaFileType='image/webp'
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
                        self._write(mediaBinary)
                    return        
            self._404()
            return

        self._benchmarkGETtimings(GETstartTime,GETtimings,20)

        # show shared item images
        # Note that this comes before the busy flag to avoid conflicts
        if '/sharefiles/' in self.path:
            if self.path.endswith('.png') or \
               self.path.endswith('.jpg') or \
               self.path.endswith('.webp') or \
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
                    elif mediaFilename.endswith('.webp'):
                        mediaFileType='webp'
                    else:
                        mediaFileType='gif'
                    with open(mediaFilename, 'rb') as avFile:
                        mediaBinary = avFile.read()
                        self._set_headers('image/'+mediaFileType,len(mediaBinary),cookie)
                        self._write(mediaBinary)
                    return        
            self._404()
            return

        self._benchmarkGETtimings(GETstartTime,GETtimings,21)

        # icon images
        # Note that this comes before the busy flag to avoid conflicts
        if self.path.startswith('/icons/'):
            if self.path.endswith('.png'):
                mediaStr=self.path.split('/icons/')[1]
                mediaFilename= \
                    self.server.baseDir+'/img/icons/'+mediaStr
                if self.server.iconsCache.get(mediaStr):
                    mediaBinary=self.server.iconsCache[mediaStr]
                    self._set_headers('image/png',len(mediaBinary),cookie)
                    self._write(mediaBinary)
                    return        
                else:
                    if os.path.isfile(mediaFilename):
                        with open(mediaFilename, 'rb') as avFile:
                            mediaBinary = avFile.read()
                            self._set_headers('image/png',len(mediaBinary),cookie)
                            self._write(mediaBinary)
                            self.server.iconsCache[mediaStr]=mediaBinary
                        return
            self._404()
            return

        self._benchmarkGETtimings(GETstartTime,GETtimings,22)

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
                        # default to jpeg
                        self._set_headers('image/jpeg',len(mediaBinary),cookie)
                        #self._404()
                        return
                    self._write(mediaBinary)
                    return        
            self._404()
            return

        self._benchmarkGETtimings(GETstartTime,GETtimings,23)

        # show avatar or background image
        # Note that this comes before the busy flag to avoid conflicts
        if '/users/' in self.path:
            if self.path.endswith('.png') or \
               self.path.endswith('.jpg') or \
               self.path.endswith('.webp') or \
               self.path.endswith('.gif'):
                avatarStr=self.path.split('/users/')[1]
                if '/' in avatarStr and '.temp.' not in self.path:
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
                        elif avatarFile.endswith('.gif'):
                            mediaImageType='gif'
                        else:
                            mediaImageType='webp'
                        with open(avatarFilename, 'rb') as avFile:
                            mediaBinary = avFile.read()
                            self._set_headers('image/'+mediaImageType, \
                                              len(mediaBinary),cookie)
                            self._write(mediaBinary)
                        return

        self._benchmarkGETtimings(GETstartTime,GETtimings,24)

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

        self._benchmarkGETtimings(GETstartTime,GETtimings,25)

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

        self._benchmarkGETtimings(GETstartTime,GETtimings,26)

        if self.path.startswith('/login') or \
           (self.path=='/' and not authorized):
            # request basic auth
            msg=htmlLogin(self.server.translate, \
                          self.server.baseDir).encode('utf-8')
            self._login_headers('text/html',len(msg))
            self._write(msg)
            self.server.GETbusy=False
            return

        self._benchmarkGETtimings(GETstartTime,GETtimings,27)

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
                self._write(msg)
                self.server.GETbusy=False
                return
            hashtagStr= \
                htmlHashtagSearch(self.server.recentPostsCache, \
                                  self.server.maxRecentPosts, \
                                  self.server.translate, \
                                  self.server.baseDir,hashtag,pageNumber, \
                                  maxPostsInFeed,self.server.session, \
                                  self.server.cachedWebfingers, \
                                  self.server.personCache, \
                                  self.server.httpPrefix, \
                                  self.server.projectVersion)
            if hashtagStr:
                msg=hashtagStr.encode()
                self._set_headers('text/html',len(msg),cookie)
                self._write(msg)
            else:
                originPathStr=self.path.split('/tags/')[0]
                originPathStrAbsolute=self.server.httpPrefix+'://'+self.server.domainFull+originPathStr
                self._redirect_headers(originPathStrAbsolute+'/search',cookie)                
            self.server.GETbusy=False
            return

        self._benchmarkGETtimings(GETstartTime,GETtimings,28)

        # search for a fediverse address, shared item or emoji
        # from the web interface by selecting search icon
        if htmlGET and '/users/' in self.path:
           if self.path.endswith('/search'):
               # show the search screen
               msg=htmlSearch(self.server.translate, \
                              self.server.baseDir,self.path).encode()
               self._set_headers('text/html',len(msg),cookie)
               self._write(msg)
               self.server.GETbusy=False
               return

        self._benchmarkGETtimings(GETstartTime,GETtimings,29)

        # Show the calendar for a user
        if htmlGET and '/users/' in self.path:
           if '/calendar' in self.path:
               # show the calendar screen
               msg=htmlCalendar(self.server.translate, \
                                self.server.baseDir,self.path, \
                                self.server.httpPrefix, \
                                self.server.domainFull).encode()
               self._set_headers('text/html',len(msg),cookie)
               self._write(msg)
               self.server.GETbusy=False
               return

        self._benchmarkGETtimings(GETstartTime,GETtimings,30)

        # search for emoji by name
        if htmlGET and '/users/' in self.path:
           if self.path.endswith('/searchemoji'):
               # show the search screen
               msg=htmlSearchEmojiTextEntry(self.server.translate, \
                                            self.server.baseDir, \
                                            self.path).encode()
               self._set_headers('text/html',len(msg),cookie)
               self._write(msg)
               self.server.GETbusy=False
               return

        self._benchmarkGETtimings(GETstartTime,GETtimings,31)

        # announce/repeat from the web interface
        if htmlGET and '?repeat=' in self.path:
            pageNumber=1
            repeatUrl=self.path.split('?repeat=')[1]
            if '?' in repeatUrl:
                repeatUrl=repeatUrl.split('?')[0]
            timelineBookmark=''
            if '?bm=' in self.path:
                timelineBookmark=self.path.split('?bm=')[1]
                if '?' in timelineBookmark:
                    timelineBookmark=timelineBookmark.split('?')[0]
                timelineBookmark='#'+timelineBookmark
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
                actorAbsolute=self.server.httpPrefix+'://'+self.server.domainFull+actor                
                self._redirect_headers(actorAbsolute+'/'+timelineStr+ \
                                       '?page='+str(pageNumber),cookie)
                return                
            if not self.server.session:
                self.server.session= \
                    createSession(self.server.useTor)                
            self.server.actorRepeat=self.path.split('?actor=')[1]
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
            actorAbsolute=self.server.httpPrefix+'://'+self.server.domainFull+actor                
            self._redirect_headers(actorAbsolute+'/'+timelineStr+'?page='+ \
                                   str(pageNumber)+ \
                                   timelineBookmark,cookie)
            return

        self._benchmarkGETtimings(GETstartTime,GETtimings,32)

        # undo an announce/repeat from the web interface
        if htmlGET and '?unrepeat=' in self.path:
            pageNumber=1
            repeatUrl=self.path.split('?unrepeat=')[1]
            if '?' in repeatUrl:
                repeatUrl=repeatUrl.split('?')[0]
            timelineBookmark=''
            if '?bm=' in self.path:
                timelineBookmark=self.path.split('?bm=')[1]
                if '?' in timelineBookmark:
                    timelineBookmark=timelineBookmark.split('?')[0]
                timelineBookmark='#'+timelineBookmark
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
                actorAbsolute=self.server.httpPrefix+'://'+self.server.domainFull+actor                
                self._redirect_headers(actorAbsolute+'/'+timelineStr+'?page='+ \
                                       str(pageNumber),cookie)
                return                
            if not self.server.session:
                self.server.session= \
                    createSession(self.server.useTor)
            undoAnnounceActor= \
                self.server.httpPrefix+'://'+self.server.domainFull+ \
                '/users/'+self.postToNickname
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
            actorAbsolute=self.server.httpPrefix+'://'+self.server.domainFull+actor                
            self._redirect_headers(actorAbsolute+'/'+timelineStr+'?page='+ \
                                   str(pageNumber)+ \
                                   timelineBookmark,cookie)
            return

        self._benchmarkGETtimings(GETstartTime,GETtimings,33)

        # send a follow request approval from the web interface
        if authorized and '/followapprove=' in self.path and \
           self.path.startswith('/users/'):
            originPathStr=self.path.split('/followapprove=')[0]
            followerNickname=originPathStr.replace('/users/','')
            followingHandle=self.path.split('/followapprove=')[1]
            if '@' in followingHandle:
                if not self.server.session:
                    self.server.session= \
                        createSession(self.server.useTor)
                manualApproveFollowRequest(self.server.session, \
                                           self.server.baseDir, \
                                           self.server.httpPrefix, \
                                           followerNickname, \
                                           self.server.domain, \
                                           self.server.port, \
                                           followingHandle, \
                                           self.server.federationList, \
                                           self.server.sendThreads, \
                                           self.server.postLog, \
                                           self.server.cachedWebfingers, \
                                           self.server.personCache, \
                                           self.server.acceptedCaps, \
                                           self.server.debug, \
                                           self.server.projectVersion)
            originPathStrAbsolute=self.server.httpPrefix+'://'+self.server.domainFull+originPathStr
            self._redirect_headers(originPathStrAbsolute,cookie)
            self.server.GETbusy=False
            return

        self._benchmarkGETtimings(GETstartTime,GETtimings,34)

        # deny a follow request from the web interface
        if authorized and '/followdeny=' in self.path and \
           self.path.startswith('/users/'):
            originPathStr=self.path.split('/followdeny=')[0]
            followerNickname=originPathStr.replace('/users/','')
            followingHandle=self.path.split('/followdeny=')[1]
            if '@' in followingHandle:
                manualDenyFollowRequest(self.server.session, \
                                        self.server.baseDir, \
                                        self.server.httpPrefix, \
                                        followerNickname, \
                                        self.server.domain, \
                                        self.server.port, \
                                        followingHandle, \
                                        self.server.federationList, \
                                        self.server.sendThreads, \
                                        self.server.postLog, \
                                        self.server.cachedWebfingers, \
                                        self.server.personCache, \
                                        self.server.debug, \
                                        self.server.projectVersion)
            originPathStrAbsolute=self.server.httpPrefix+'://'+self.server.domainFull+originPathStr
            self._redirect_headers(originPathStrAbsolute,cookie)
            self.server.GETbusy=False
            return

        self._benchmarkGETtimings(GETstartTime,GETtimings,35)

        # like from the web interface icon
        if htmlGET and '?like=' in self.path:
            pageNumber=1
            likeUrl=self.path.split('?like=')[1]
            if '?' in likeUrl:
                likeUrl=likeUrl.split('?')[0]                
            timelineBookmark=''
            if '?bm=' in self.path:
                timelineBookmark=self.path.split('?bm=')[1]
                if '?' in timelineBookmark:
                    timelineBookmark=timelineBookmark.split('?')[0]
                timelineBookmark='#'+timelineBookmark
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
                actorAbsolute=self.server.httpPrefix+'://'+self.server.domainFull+actor
                self._redirect_headers(actorAbsolute+'/'+timelineStr+ \
                                       '?page='+str(pageNumber)+ \
                                       timelineBookmark,cookie)
                return                
            if not self.server.session:
                self.server.session= \
                    createSession(self.server.useTor)
            likeActor= \
                self.server.httpPrefix+'://'+ \
                self.server.domainFull+'/users/'+self.postToNickname                    
            actorLiked=self.path.split('?actor=')[1]
            if '?' in actorLiked:
                actorLiked=actorLiked.split('?')[0]
            likeJson= {
                "@context": "https://www.w3.org/ns/activitystreams",
                'type': 'Like',
                'actor': likeActor,
                'to': [actorLiked],
                'object': likeUrl
            }    
            self._postToOutbox(likeJson,self.server.projectVersion)
            self.server.GETbusy=False
            actorAbsolute=self.server.httpPrefix+'://'+self.server.domainFull+actor
            self._redirect_headers(actorAbsolute+'/'+timelineStr+ \
                                   '?page='+str(pageNumber)+ \
                                   timelineBookmark,cookie)
            return

        self._benchmarkGETtimings(GETstartTime,GETtimings,36)

        # undo a like from the web interface icon
        if htmlGET and '?unlike=' in self.path:
            pageNumber=1
            likeUrl=self.path.split('?unlike=')[1]
            if '?' in likeUrl:
                likeUrl=likeUrl.split('?')[0]
            timelineBookmark=''
            if '?bm=' in self.path:
                timelineBookmark=self.path.split('?bm=')[1]
                if '?' in timelineBookmark:
                    timelineBookmark=timelineBookmark.split('?')[0]
                timelineBookmark='#'+timelineBookmark
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
                actorAbsolute=self.server.httpPrefix+'://'+self.server.domainFull+actor
                self._redirect_headers(actorAbsolute+'/'+timelineStr+ \
                                       '?page='+str(pageNumber),cookie)
                return                
            if not self.server.session:
                self.server.session= \
                    createSession(self.server.useTor)
            undoActor= \
                self.server.httpPrefix+'://'+ \
                self.server.domainFull+'/users/'+self.postToNickname
            actorLiked=self.path.split('?actor=')[1]
            if '?' in actorLiked:
                actorLiked=actorLiked.split('?')[0]
            undoLikeJson= {
                "@context": "https://www.w3.org/ns/activitystreams",
                'type': 'Undo',
                'actor': undoActor,
                'to': [actorLiked],
                'object': {
                    'type': 'Like',
                    'actor': undoActor,
                    'to': [actorLiked],
                    'object': likeUrl
                }
            }
            self._postToOutbox(undoLikeJson,self.server.projectVersion)
            self.server.GETbusy=False
            actorAbsolute=self.server.httpPrefix+'://'+self.server.domainFull+actor
            self._redirect_headers(actorAbsolute+'/'+timelineStr+ \
                                   '?page='+str(pageNumber)+ \
                                   timelineBookmark,cookie)
            return

        self._benchmarkGETtimings(GETstartTime,GETtimings,36)

        # bookmark from the web interface icon
        if htmlGET and '?bookmark=' in self.path:
            pageNumber=1
            bookmarkUrl=self.path.split('?bookmark=')[1]
            if '?' in bookmarkUrl:
                bookmarkUrl=bookmarkUrl.split('?')[0]                
            timelineBookmark=''
            if '?bm=' in self.path:
                timelineBookmark=self.path.split('?bm=')[1]
                if '?' in timelineBookmark:
                    timelineBookmark=timelineBookmark.split('?')[0]
                timelineBookmark='#'+timelineBookmark
            actor=self.path.split('?bookmark=')[0]
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
                actorAbsolute=self.server.httpPrefix+'://'+self.server.domainFull+actor
                self._redirect_headers(actorAbsolute+'/'+timelineStr+ \
                                       '?page='+str(pageNumber),cookie)
                return                
            if not self.server.session:
                self.server.session= \
                    createSession(self.server.useTor)
            bookmarkActor= \
                self.server.httpPrefix+'://'+ \
                self.server.domainFull+'/users/'+self.postToNickname                    
            bookmarkJson= {
                "@context": "https://www.w3.org/ns/activitystreams",
                'type': 'Bookmark',
                'actor': bookmarkActor,
                'to': [bookmarkActor],
                'object': bookmarkUrl
            }    
            self._postToOutbox(bookmarkJson,self.server.projectVersion)
            self.server.GETbusy=False
            actorAbsolute=self.server.httpPrefix+'://'+self.server.domainFull+actor
            self._redirect_headers(actorAbsolute+'/'+timelineStr+ \
                                   '?page='+str(pageNumber)+ \
                                   timelineBookmark,cookie)
            return

        # undo a bookmark from the web interface icon
        if htmlGET and '?unbookmark=' in self.path:
            pageNumber=1
            bookmarkUrl=self.path.split('?unbookmark=')[1]
            if '?' in bookmarkUrl:
                bookmarkUrl=bookmarkUrl.split('?')[0]
            timelineBookmark=''
            if '?bm=' in self.path:
                timelineBookmark=self.path.split('?bm=')[1]
                if '?' in timelineBookmark:
                    timelineBookmark=timelineBookmark.split('?')[0]
                timelineBookmark='#'+timelineBookmark
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
            actor=self.path.split('?unbookmark=')[0]
            self.postToNickname=getNicknameFromActor(actor)
            if not self.postToNickname:
                print('WARN: unable to find nickname in '+actor)
                self.server.GETbusy=False
                actorAbsolute=self.server.httpPrefix+'://'+self.server.domainFull+actor
                self._redirect_headers(actorAbsolute+'/'+timelineStr+ \
                                       '?page='+str(pageNumber),cookie)
                return                
            if not self.server.session:
                self.server.session= \
                    createSession(self.server.useTor)
            undoActor= \
                self.server.httpPrefix+'://'+ \
                self.server.domainFull+'/users/'+self.postToNickname
            undoBookmarkJson= {
                "@context": "https://www.w3.org/ns/activitystreams",
                'type': 'Undo',
                'actor': undoActor,
                'to': [undoActor],
                'object': {
                    'type': 'Bookmark',
                    'actor': undoActor,
                    'to': [undoActor],
                    'object': bookmarkUrl
                }
            }
            self._postToOutbox(undoBookmarkJson,self.server.projectVersion)
            self.server.GETbusy=False
            actorAbsolute=self.server.httpPrefix+'://'+self.server.domainFull+actor
            self._redirect_headers(actorAbsolute+'/'+timelineStr+ \
                                   '?page='+str(pageNumber)+ \
                                   timelineBookmark,cookie)
            return

        self._benchmarkGETtimings(GETstartTime,GETtimings,37)

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
            actor= \
                self.server.httpPrefix+'://'+ \
                self.server.domainFull+self.path.split('?delete=')[0]
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
                        createSession(self.server.useTor)

                deleteStr= \
                    htmlDeletePost(self.server.recentPostsCache, \
                                   self.server.maxRecentPosts, \
                                   self.server.translate,pageNumber, \
                                   self.server.session,self.server.baseDir, \
                                   deleteUrl,self.server.httpPrefix, \
                                   __version__,self.server.cachedWebfingers, \
                                   self.server.personCache)
                if deleteStr:
                    self._set_headers('text/html',len(deleteStr),cookie)
                    self._write(deleteStr.encode())
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
        replytoActor=None
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
                        if m.startswith('actor='):
                            replytoActor=m.replace('actor=','')
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
                        if m.startswith('actor='):
                            replytoActor=m.replace('actor=','')
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
                        if m.startswith('actor='):
                            replytoActor=m.replace('actor=','')
                    inReplyToUrl=mentionsList[0]
                    if inReplyToUrl.startswith('sharedesc:'):
                        shareDescription= \
                            inReplyToUrl.replace('sharedesc:','').replace('%20',' ').replace('%40','@').replace('%3A',':').replace('%2F','/').replace('%23','#')
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
                self._write(msg)
                self.server.GETbusy=False
                return

            # Various types of new post in the web interface
            if '/users/' in self.path and \
               (self.path.endswith('/newpost') or \
                self.path.endswith('/newunlisted') or \
                self.path.endswith('/newfollowers') or \
                self.path.endswith('/newdm') or \
                self.path.endswith('/newreport') or \
                self.path.endswith('/newquestion') or \
                self.path.endswith('/newshare')):
                msg=htmlNewPost(self.server.translate, \
                                self.server.baseDir, \
                                self.path,inReplyToUrl, \
                                replyToList, \
                                shareDescription, \
                                replyPageNumber).encode()
                self._set_headers('text/html',len(msg),cookie)
                self._write(msg)
                self.server.GETbusy=False
                return

        self._benchmarkGETtimings(GETstartTime,GETtimings,38)

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
                            self.server.baseDir+'/accounts/'+nickname+'@'+ \
                            self.server.domain+'/outbox/'+ \
                            self.server.httpPrefix+':##'+ \
                            self.server.domainFull+'#users#'+ \
                            nickname+'#statuses#'+statusNumber+'.json'
                        if os.path.isfile(postFilename):
                            postJsonObject=loadJson(postFilename)
                            loadedPost=False
                            if postJsonObject:
                                loadedPost=True
                            else:
                                postJsonObject={}
                            if loadedPost:                            
                                # Only authorized viewers get to see likes on posts
                                # Otherwize marketers could gain more social graph info
                                if not authorized:
                                    self._removePostInteractions(postJsonObject)
                                if self._requestHTTP():
                                    msg= \
                                        htmlIndividualPost(self.server.recentPostsCache, \
                                                           self.server.maxRecentPosts, \
                                                           self.server.translate, \
                                                           self.server.session, \
                                                           self.server.cachedWebfingers, \
                                                           self.server.personCache, \
                                                           nickname,self.server.domain, \
                                                           self.server.port, \
                                                           authorized,postJsonObject, \
                                                           self.server.httpPrefix, \
                                                           self.server.projectVersion).encode('utf-8')
                                    self._set_headers('text/html',len(msg),cookie)                    
                                    self._write(msg)
                                else:
                                    if self._fetchAuthenticated():
                                        msg=json.dumps(postJsonObject,ensure_ascii=False).encode('utf-8')
                                        self._set_headers('application/json',len(msg),None)
                                        self._write(msg)
                                    else:
                                        self._404()
                            self.server.GETbusy=False
                            return
                        else:
                            self._404()
                            self.server.GETbusy=False
                            return

        self._benchmarkGETtimings(GETstartTime,GETtimings,39)

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
                                postDir= \
                                    self.server.baseDir+'/accounts/'+ \
                                    nickname+'@'+self.server.domain+'/'+boxname
                                postRepliesFilename= \
                                    postDir+'/'+ \
                                    self.server.httpPrefix+':##'+ \
                                    self.server.domainFull+'#users#'+ \
                                    nickname+'#statuses#'+statusNumber+'.replies'
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
                                                createSession(self.server.useTor)
                                        msg=htmlPostReplies(self.server.recentPostsCache, \
                                                            self.server.maxRecentPosts, \
                                                            self.server.translate, \
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
                                        self._write(msg)
                                    else:
                                        if self._fetchAuthenticated():
                                            msg=json.dumps(repliesJson,ensure_ascii=False).encode('utf-8')
                                            self._set_headers('application/json',len(msg),None)
                                            self._write(msg)
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
                                                createSession(self.server.useTor)
                                        msg=htmlPostReplies(self.server.recentPostsCache, \
                                                            self.server.maxRecentPosts, \
                                                            self.server.translate, \
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
                                        self._write(msg)
                                    else:
                                        if self._fetchAuthenticated():
                                            msg=json.dumps(repliesJson,ensure_ascii=False).encode('utf-8')
                                            self._set_headers('application/json',len(msg),None)
                                            self._write(msg)
                                        else:
                                            self._404()
                                    self.server.GETbusy=False
                                    return

        self._benchmarkGETtimings(GETstartTime,GETtimings,40)

        if self.path.endswith('/roles') and '/users/' in self.path:
            namedStatus=self.path.split('/users/')[1]
            if '/' in namedStatus:
                postSections=namedStatus.split('/')
                nickname=postSections[0]
                actorFilename= \
                    self.server.baseDir+'/accounts/'+ \
                    nickname+'@'+self.server.domain+'.json'
                if os.path.isfile(actorFilename):
                    actorJson=loadJson(actorFilename)
                    if actorJson:                    
                        if actorJson.get('roles'):
                            if self._requestHTTP():
                                getPerson = \
                                    personLookup(self.server.domain, \
                                                 self.path.replace('/roles',''), \
                                                 self.server.baseDir)
                                if getPerson:
                                    msg=htmlProfile(self.server.recentPostsCache, \
                                                    self.server.maxRecentPosts, \
                                                    self.server.translate, \
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
                                    self._write(msg)
                            else:
                                if self._fetchAuthenticated():
                                    msg=json.dumps(actorJson['roles'],ensure_ascii=False).encode('utf-8')
                                    self._set_headers('application/json',len(msg),None)
                                    self._write(msg)
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
                actorFilename= \
                    self.server.baseDir+'/accounts/'+ \
                    nickname+'@'+self.server.domain+'.json'
                if os.path.isfile(actorFilename):
                    actorJson=loadJson(actorFilename)
                    if actorJson:                    
                        if actorJson.get('skills'):
                            if self._requestHTTP():
                                getPerson = \
                                    personLookup(self.server.domain, \
                                                 self.path.replace('/skills',''), \
                                                 self.server.baseDir)
                                if getPerson:
                                    msg=htmlProfile(self.server.recentPostsCache, \
                                                    self.server.maxRecentPosts, \
                                                    self.server.translate, \
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
                                    self._write(msg)
                            else:
                                if self._fetchAuthenticated():
                                    msg=json.dumps(actorJson['skills'],ensure_ascii=False).encode('utf-8')
                                    self._set_headers('application/json',len(msg),None)
                                    self._write(msg)
                                else:
                                    self._404()
                            self.server.GETbusy=False
                            return
            actor=self.path.replace('/skills','')
            actorAbsolute=self.server.httpPrefix+'://'+self.server.domainFull+actor
            self._redirect_headers(actorAbsolute,cookie)
            self.server.GETbusy=False
            return

        self._benchmarkGETtimings(GETstartTime,GETtimings,41)

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
                            self.server.baseDir+'/accounts/'+ \
                            nickname+'@'+self.server.domain+'/outbox/'+ \
                            self.server.httpPrefix+':##'+ \
                            self.server.domainFull+'#users#'+ \
                            nickname+'#statuses#'+statusNumber+'.json'
                        if os.path.isfile(postFilename):
                            postJsonObject=loadJson(postFilename)
                            if not postJsonObject:
                                self.send_response(429)
                                self.end_headers()
                                self.server.GETbusy=False
                                return
                            else:
                                # Only authorized viewers get to see likes on posts
                                # Otherwize marketers could gain more social graph info
                                if not authorized:
                                    self._removePostInteractions(postJsonObject)

                                if self._requestHTTP():
                                    msg=htmlIndividualPost(self.server.recentPostsCache, \
                                                           self.server.maxRecentPosts, \
                                                           self.server.translate, \
                                                           self.server.baseDir, \
                                                           self.server.session, \
                                                           self.server.cachedWebfingers, \
                                                           self.server.personCache, \
                                                           nickname, \
                                                           self.server.domain, \
                                                           self.server.port, \
                                                           authorized,postJsonObject, \
                                                           self.server.httpPrefix, \
                                                           self.server.projectVersion).encode('utf-8')
                                    self._set_headers('text/html',len(msg),cookie)
                                    self._write(msg)
                                else:
                                    if self._fetchAuthenticated():
                                        msg=json.dumps(postJsonObject,ensure_ascii=False).encode('utf-8')
                                        self._set_headers('application/json',len(msg),None)
                                        self._write(msg)
                                    else:
                                        self._404()
                            self.server.GETbusy=False
                            return
                        else:
                            self._404()
                            self.server.GETbusy=False
                            return

        self._benchmarkGETtimings(GETstartTime,GETtimings,42)

        # get the inbox for a given person
        if self.path.endswith('/inbox') or '/inbox?page=' in self.path:
            if '/users/' in self.path:
                if authorized:
                    inboxFeed= \
                        personBoxJson(self.server.recentPostsCache, \
                                      self.server.session, \
                                      self.server.baseDir, \
                                      self.server.domain, \
                                      self.server.port, \
                                      self.path, \
                                      self.server.httpPrefix, \
                                      maxPostsInFeed, 'inbox', \
                                      authorized,self.server.ocapAlways)
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
                                inboxFeed= \
                                    personBoxJson(self.server.recentPostsCache, \
                                                  self.server.session, \
                                                  self.server.baseDir, \
                                                  self.server.domain, \
                                                  self.server.port, \
                                                  self.path+'?page=1', \
                                                  self.server.httpPrefix, \
                                                  maxPostsInFeed, 'inbox', \
                                                  authorized,self.server.ocapAlways)
                            msg=htmlInbox(self.server.recentPostsCache, \
                                          self.server.maxRecentPosts, \
                                          self.server.translate, \
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
                            self._write(msg)
                        else:
                            # don't need authenticated fetch here because there is
                            # already the authorization check
                            msg=json.dumps(inboxFeed,ensure_ascii=False).encode('utf-8')
                            self._set_headers('application/json',len(msg),None)
                            self._write(msg)
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

        self._benchmarkGETtimings(GETstartTime,GETtimings,43)

        # get the direct messages for a given person
        if self.path.endswith('/dm') or '/dm?page=' in self.path:
            if '/users/' in self.path:
                if authorized:
                    inboxDMFeed= \
                        personBoxJson(self.server.recentPostsCache, \
                                      self.server.session, \
                                      self.server.baseDir, \
                                      self.server.domain, \
                                      self.server.port, \
                                      self.path, \
                                      self.server.httpPrefix, \
                                      maxPostsInFeed, 'dm', \
                                      authorized,self.server.ocapAlways)
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
                                inboxDMFeed= \
                                    personBoxJson(self.server.recentPostsCache, \
                                                  self.server.session, \
                                                  self.server.baseDir, \
                                                  self.server.domain, \
                                                  self.server.port, \
                                                  self.path+'?page=1', \
                                                  self.server.httpPrefix, \
                                                  maxPostsInFeed, 'dm', \
                                                  authorized,self.server.ocapAlways)
                            msg=htmlInboxDMs(self.server.recentPostsCache, \
                                             self.server.maxRecentPosts, \
                                             self.server.translate, \
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
                            self._write(msg)
                        else:
                            # don't need authenticated fetch here because there is
                            # already the authorization check
                            msg=json.dumps(inboxDMFeed,ensure_ascii=False).encode('utf-8')
                            self._set_headers('application/json',len(msg),None)
                            self._write(msg)
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

        self._benchmarkGETtimings(GETstartTime,GETtimings,44)

        # get the replies for a given person
        if self.path.endswith('/tlreplies') or '/tlreplies?page=' in self.path:
            if '/users/' in self.path:
                if authorized:
                    inboxRepliesFeed= \
                        personBoxJson(self.server.recentPostsCache, \
                                      self.server.session, \
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
                                personBoxJson(self.server.recentPostsCache, \
                                              self.server.session, \
                                              self.server.baseDir, \
                                              self.server.domain, \
                                              self.server.port, \
                                              self.path+'?page=1', \
                                              self.server.httpPrefix, \
                                              maxPostsInFeed, 'tlreplies', \
                                              True,self.server.ocapAlways)
                        msg=htmlInboxReplies(self.server.recentPostsCache, \
                                             self.server.maxRecentPosts, \
                                             self.server.translate, \
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
                        self._write(msg)
                    else:
                        # don't need authenticated fetch here because there is
                        # already the authorization check
                        msg=json.dumps(inboxRepliesFeed,ensure_ascii=False).encode('utf-8')
                        self._set_headers('application/json',len(msg),None)
                        self._write(msg)
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

        self._benchmarkGETtimings(GETstartTime,GETtimings,45)

        # get the media for a given person
        if self.path.endswith('/tlmedia') or '/tlmedia?page=' in self.path:
            if '/users/' in self.path:
                if authorized:
                    inboxMediaFeed= \
                        personBoxJson(self.server.recentPostsCache, \
                                      self.server.session, \
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
                                personBoxJson(self.server.recentPostsCache, \
                                              self.server.session, \
                                              self.server.baseDir, \
                                              self.server.domain, \
                                              self.server.port, \
                                              self.path+'?page=1', \
                                              self.server.httpPrefix, \
                                              maxPostsInMediaFeed, 'tlmedia', \
                                              True,self.server.ocapAlways)
                        msg=htmlInboxMedia(self.server.recentPostsCache, \
                                           self.server.maxRecentPosts, \
                                           self.server.translate, \
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
                        self._write(msg)
                    else:
                        # don't need authenticated fetch here because there is
                        # already the authorization check
                        msg=json.dumps(inboxMediaFeed,ensure_ascii=False).encode('utf-8')
                        self._set_headers('application/json',len(msg),None)
                        self._write(msg)
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

        self._benchmarkGETtimings(GETstartTime,GETtimings,46)

        # get the shared items timeline for a given person
        if self.path.endswith('/tlshares') or '/tlshares?page=' in self.path:
            if '/users/' in self.path:
                if authorized:
                    if self._requestHTTP():
                        nickname=self.path.replace('/users/','').replace('/tlshares','')
                        pageNumber=1
                        if '?page=' in nickname:
                            pageNumber=nickname.split('?page=')[1]
                            nickname=nickname.split('?page=')[0]
                            if pageNumber.isdigit():
                                pageNumber=int(pageNumber)
                            else:
                                pageNumber=1
                        msg=htmlShares(self.server.recentPostsCache, \
                                       self.server.maxRecentPosts, \
                                       self.server.translate, \
                                       pageNumber,maxPostsInFeed, \
                                       self.server.session, \
                                       self.server.baseDir, \
                                       self.server.cachedWebfingers, \
                                       self.server.personCache, \
                                       nickname, \
                                       self.server.domain, \
                                       self.server.port, \
                                       self.server.allowDeletion, \
                                       self.server.httpPrefix, \
                                       self.server.projectVersion).encode('utf-8')
                        self._set_headers('text/html',len(msg),cookie)
                        self._write(msg)
                        self.server.GETbusy=False
                        return
            # not the shares timeline
            if self.server.debug:
                print('DEBUG: GET access to shares timeline is unauthorized')
            self.send_response(405)
            self.end_headers()
            self.server.GETbusy=False
            return

        # get the bookmarks for a given person
        if self.path.endswith('/tlbookmarks') or '/tlbookmarks?page=' in self.path:
            if '/users/' in self.path:
                if authorized:
                    bookmarksFeed= \
                        personBoxJson(self.server.recentPostsCache, \
                                      self.server.session, \
                                      self.server.baseDir, \
                                      self.server.domain, \
                                      self.server.port, \
                                      self.path, \
                                      self.server.httpPrefix, \
                                      maxPostsInFeed, 'tlbookmarks', \
                                      authorized,self.server.ocapAlways)
                    if bookmarksFeed:
                        if self._requestHTTP():
                            nickname=self.path.replace('/users/','').replace('/tlbookmarks','')
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
                                bookmarksFeed= \
                                    personBoxJson(self.server.recentPostsCache, \
                                                  self.server.session, \
                                                  self.server.baseDir, \
                                                  self.server.domain, \
                                                  self.server.port, \
                                                  self.path+'?page=1', \
                                                  self.server.httpPrefix, \
                                                  maxPostsInFeed, 'tlbookmarks', \
                                                  authorized,self.server.ocapAlways)
                            msg=htmlBookmarks(self.server.recentPostsCache, \
                                              self.server.maxRecentPosts, \
                                              self.server.translate, \
                                              pageNumber,maxPostsInFeed, \
                                              self.server.session, \
                                              self.server.baseDir, \
                                              self.server.cachedWebfingers, \
                                              self.server.personCache, \
                                              nickname, \
                                              self.server.domain, \
                                              self.server.port, \
                                              bookmarksFeed, \
                                              self.server.allowDeletion, \
                                              self.server.httpPrefix, \
                                              self.server.projectVersion).encode('utf-8')
                            self._set_headers('text/html',len(msg),cookie)
                            self._write(msg)
                        else:
                            # don't need authenticated fetch here because there is
                            # already the authorization check
                            msg=json.dumps(inboxFeed,ensure_ascii=False).encode('utf-8')
                            self._set_headers('application/json',len(msg),None)
                            self._write(msg)
                        self.server.GETbusy=False
                        return
                else:
                    if self.server.debug:
                        nickname=self.path.replace('/users/','').replace('/tlbookmarks','')
                        print('DEBUG: '+nickname+ \
                              ' was not authorized to access '+self.path)
            if self.server.debug:
                print('DEBUG: GET access to bookmarks is unauthorized')
            self.send_response(405)
            self.end_headers()
            self.server.GETbusy=False
            return

        self._benchmarkGETtimings(GETstartTime,GETtimings,47)

        # get outbox feed for a person
        outboxFeed= \
            personBoxJson(self.server.recentPostsCache, \
                          self.server.session, \
                          self.server.baseDir,self.server.domain, \
                          self.server.port,self.path, \
                          self.server.httpPrefix, \
                          maxPostsInFeed, 'outbox', \
                          authorized, \
                          self.server.ocapAlways)
        if outboxFeed:
            if self._requestHTTP():
                nickname= \
                    self.path.replace('/users/','').replace('/outbox','')
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
                    outboxFeed= \
                        personBoxJson(self.server.recentPostsCache, \
                                      self.server.session, \
                                      self.server.baseDir, \
                                      self.server.domain, \
                                      self.server.port, \
                                      self.path+'?page=1', \
                                      self.server.httpPrefix, \
                                      maxPostsInFeed, 'outbox', \
                                      authorized, \
                                      self.server.ocapAlways)
                msg=htmlOutbox(self.server.recentPostsCache, \
                               self.server.maxRecentPosts, \
                               self.server.translate, \
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
                self._write(msg)
            else:
                if self._fetchAuthenticated():
                    msg=json.dumps(outboxFeed,ensure_ascii=False).encode('utf-8')
                    self._set_headers('application/json',len(msg),None)
                    self._write(msg)
                else:
                    self._404()
            self.server.GETbusy=False
            return

        self._benchmarkGETtimings(GETstartTime,GETtimings,48)

        # get the moderation feed for a moderator
        if self.path.endswith('/moderation') or \
           '/moderation?page=' in self.path:
            if '/users/' in self.path:
                if authorized:
                    moderationFeed= \
                        personBoxJson(self.server.recentPostsCache, \
                                      self.server.session, \
                                      self.server.baseDir, \
                                      self.server.domain, \
                                      self.server.port, \
                                      self.path, \
                                      self.server.httpPrefix, \
                                      maxPostsInFeed, 'moderation', \
                                      True,self.server.ocapAlways)
                    if moderationFeed:
                        if self._requestHTTP():
                            nickname= \
                                self.path.replace('/users/','').replace('/moderation','')
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
                                    personBoxJson(self.server.recentPostsCache, \
                                                  self.server.session, \
                                                  self.server.baseDir, \
                                                  self.server.domain, \
                                                  self.server.port, \
                                                  self.path+'?page=1', \
                                                  self.server.httpPrefix, \
                                                  maxPostsInFeed, 'moderation', \
                                                  True,self.server.ocapAlways)
                            msg=htmlModeration(self.server.recentPostsCache, \
                                               self.server.maxRecentPosts, \
                                               self.server.translate, \
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
                            self._write(msg)
                        else:
                            # don't need authenticated fetch here because there is
                            # already the authorization check
                            msg=json.dumps(moderationFeed,ensure_ascii=False).encode('utf-8')
                            self._set_headers('application/json',len(msg),None)
                            self._write(msg)
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
        
        self._benchmarkGETtimings(GETstartTime,GETtimings,49)

        shares= \
            getSharesFeedForPerson(self.server.baseDir, \
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
                    shares= \
                        getSharesFeedForPerson(self.server.baseDir, \
                                               self.server.domain, \
                                               self.server.port, \
                                               self.path+'?page=true', \
                                               self.server.httpPrefix, \
                                               sharesPerPage)
                else:
                    pageNumberStr=self.path.split('?page=')[1]
                    if pageNumberStr.isdigit():
                        pageNumber=int(pageNumberStr)
                    searchPath=self.path.split('?page=')[0]
                getPerson= \
                    personLookup(self.server.domain, \
                                 searchPath.replace('/shares',''), \
                                 self.server.baseDir)
                if getPerson:
                    if not self.server.session:
                        if self.server.debug:
                            print('DEBUG: creating new session')
                        self.server.session= \
                            createSession(self.server.useTor)
                    msg=htmlProfile(self.server.recentPostsCache, \
                                    self.server.maxRecentPosts, \
                                    self.server.translate, \
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
                    self._write(msg)
                    self.server.GETbusy=False
                    return
            else:
                if self._fetchAuthenticated():
                    msg=json.dumps(shares,ensure_ascii=False).encode('utf-8')
                    self._set_headers('application/json',len(msg),None)
                    self._write(msg)
                else:
                    self._404()
                self.server.GETbusy=False
                return

        self._benchmarkGETtimings(GETstartTime,GETtimings,50)

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
                    following= \
                        getFollowingFeed(self.server.baseDir,self.server.domain, \
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
                            createSession(self.server.useTor)

                    msg=htmlProfile(self.server.recentPostsCache, \
                                    self.server.maxRecentPosts, \
                                    self.server.translate, \
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
                    self._write(msg)
                    self.server.GETbusy=False
                    return
            else:
                if self._fetchAuthenticated():
                    msg=json.dumps(following,ensure_ascii=False).encode('utf-8')
                    self._set_headers('application/json',len(msg),None)
                    self._write(msg)
                else:
                    self._404()
                self.server.GETbusy=False
                return

        self._benchmarkGETtimings(GETstartTime,GETtimings,51)

        followers= \
            getFollowingFeed(self.server.baseDir,self.server.domain, \
                             self.server.port,self.path, \
                             self.server.httpPrefix, \
                             authorized,followsPerPage,'followers')
        if followers:
            if self._requestHTTP():
                pageNumber=1
                if '?page=' not in self.path:
                    searchPath=self.path
                    # get a page of followers, not the summary
                    followers= \
                        getFollowingFeed(self.server.baseDir,self.server.domain, \
                                         self.server.port,self.path+'?page=1', \
                                         self.server.httpPrefix, \
                                         authorized,followsPerPage,'followers')
                else:
                    pageNumberStr=self.path.split('?page=')[1]
                    if pageNumberStr.isdigit():
                        pageNumber=int(pageNumberStr)
                    searchPath=self.path.split('?page=')[0]
                getPerson= \
                    personLookup(self.server.domain,searchPath.replace('/followers',''), \
                                 self.server.baseDir)
                if getPerson:
                    if not self.server.session:
                        if self.server.debug:
                            print('DEBUG: creating new session')
                        self.server.session= \
                            createSession(self.server.useTor)
                    msg=htmlProfile(self.server.recentPostsCache, \
                                    self.server.maxRecentPosts, \
                                    self.server.translate, \
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
                    self._write(msg)
                    self.server.GETbusy=False
                    return
            else:
                if self._fetchAuthenticated():
                    msg=json.dumps(followers,ensure_ascii=False).encode('utf-8')
                    self._set_headers('application/json',len(msg),None)
                    self._write(msg)
                else:
                    self._404()
            self.server.GETbusy=False
            return

        self._benchmarkGETtimings(GETstartTime,GETtimings,52)

        # look up a person
        getPerson = personLookup(self.server.domain,self.path, \
                                 self.server.baseDir)
        if getPerson:
            if self._requestHTTP():
                if not self.server.session:
                    if self.server.debug:
                        print('DEBUG: creating new session')
                    self.server.session= \
                        createSession(self.server.useTor)
                msg=htmlProfile(self.server.recentPostsCache, \
                                self.server.maxRecentPosts, \
                                self.server.translate, \
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
                self._write(msg)
            else:
                if self._fetchAuthenticated():
                    msg=json.dumps(getPerson,ensure_ascii=False).encode('utf-8')
                    self._set_headers('application/json',len(msg),None)
                    self._write(msg)
                else:
                    self._404()
            self.server.GETbusy=False
            return

        self._benchmarkGETtimings(GETstartTime,GETtimings,53)

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
            return
        
        self._benchmarkGETtimings(GETstartTime,GETtimings,54)

        # check that the file exists
        filename=self.server.baseDir+self.path
        if os.path.isfile(filename):
            with open(filename, 'r', encoding='utf-8') as File:
                content = File.read()
                contentJson=json.loads(content)
                msg=json.dumps(contentJson,ensure_ascii=False).encode('utf-8')
                self._set_headers('application/json',len(msg),None)
                self._write(msg)
        else:
            if self.server.debug:
                print('DEBUG: GET Unknown file')
            self._404()
        self.server.GETbusy=False

        self._benchmarkGETtimings(GETstartTime,GETtimings,55)

    def do_HEAD(self):
        self._set_headers('application/json',0,None)

    def _receiveNewPostProcess(self,authorized: bool, \
                               postType: str,path: str,headers: {},
                               length: int,postBytes,boundary: str) -> int:
        # Note: this needs to happen synchronously
        # 0 = this is not a new post
        # 1 = new post success
        # -1 = new post failed
        # 2 = new post canceled
        if self.server.debug:
            print('DEBUG: receiving POST')

        if ' boundary=' in headers['Content-Type']:
            if self.server.debug:
                print('DEBUG: receiving POST headers '+headers['Content-Type'])
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
            if self.server.debug:
                print('DEBUG: extracting media from POST')
            mediaBytes,postBytes=extractMediaInFormPOST(postBytes,boundary,'attachpic')
            if self.server.debug:
                if mediaBytes:
                    print('DEBUG: media was found. '+str(len(mediaBytes))+' bytes')
                else:
                    print('DEBUG: no media was found in POST')

            # Note: a .temp extension is used here so that at no time is
            # an image with metadata publicly exposed, even for a few mS
            filenameBase= \
                self.server.baseDir+'/accounts/'+ \
                nickname+'@'+self.server.domain+'/upload.temp'
                    
            filename,attachmentMediaType= \
                saveMediaInFormPOST(mediaBytes,self.server.debug,filenameBase)
            if self.server.debug:
                if filename:
                    print('DEBUG: POST media filename is '+filename)
                else:
                    print('DEBUG: no media filename in POST')

            if filename:
                if filename.endswith('.png') or \
                   filename.endswith('.jpg') or \
                   filename.endswith('.gif'):
                    if self.server.debug:
                        print('DEBUG: POST media removing metadata')
                    postImageFilename=filename.replace('.temp','')
                    removeMetaData(filename,postImageFilename)
                    if os.path.isfile(postImageFilename):
                        print('POST media saved to '+postImageFilename)
                    else:
                        print('ERROR: POST media could not be saved to '+postImageFilename)
                else:
                    if os.path.isfile(filename):
                        os.rename(filename,filename.replace('.temp',''))

            fields=extractTextFieldsInPOST(postBytes,boundary,self.server.debug)
            if self.server.debug:
                if fields:
                    print('DEBUG: text field extracted from POST '+str(fields))
                else:
                    print('WARN: no text fields could be extracted from POST')

            # process the received text fields from the POST
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

            # Store a file which contains the time in seconds
            # since epoch when an attempt to post something was made.
            # This is then used for active monthly users counts
            lastUsedFilename= \
                self.server.baseDir+'/accounts/'+ \
                nickname+'@'+self.server.domain+'/.lastUsed'
            try:
                lastUsedFile=open(lastUsedFilename,'w')
                if lastUsedFile:
                    lastUsedFile.write(str(int(time.time())))
                    lastUsedFile.close()
            except:
                pass

            if postType=='newpost':
                messageJson= \
                    createPublicPost(self.server.baseDir, \
                                     nickname, \
                                     self.server.domain,self.server.port, \
                                     self.server.httpPrefix, \
                                     fields['message'],False,False,False, \
                                     filename,attachmentMediaType, \
                                     fields['imageDescription'],True, \
                                     fields['replyTo'],fields['replyTo'], \
                                     fields['subject'], \
                                     fields['eventDate'],fields['eventTime'], \
                                     fields['location'])
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
            elif postType=='newunlisted':
                messageJson= \
                    createUnlistedPost(self.server.baseDir, \
                                       nickname, \
                                       self.server.domain,self.server.port, \
                                       self.server.httpPrefix, \
                                       fields['message'],False,False,False, \
                                       filename,attachmentMediaType, \
                                       fields['imageDescription'],True, \
                                       fields['replyTo'], fields['replyTo'], \
                                       fields['subject'], \
                                       fields['eventDate'],fields['eventTime'], \
                                       fields['location'])
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
            elif postType=='newfollowers':
                messageJson= \
                    createFollowersOnlyPost(self.server.baseDir, \
                                            nickname, \
                                            self.server.domain,self.server.port, \
                                            self.server.httpPrefix, \
                                            fields['message'],True,False,False, \
                                            filename,attachmentMediaType, \
                                            fields['imageDescription'],True, \
                                            fields['replyTo'], fields['replyTo'], \
                                            fields['subject'], \
                                            fields['eventDate'],fields['eventTime'], \
                                            fields['location'])
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
            elif postType=='newdm':
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
                                                fields['eventDate'], \
                                                fields['eventTime'], \
                                                fields['location'])                    
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
            elif postType=='newreport':
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
            elif postType=='newquestion':
                if not fields.get('duration'):
                    return -1
                if not fields.get('message'):
                    return -1
                questionStr=fields['message']
                qOptions=[]
                for questionCtr in range(8):
                    if fields.get('questionOption'+str(questionCtr)):
                        qOptions.append(fields['questionOption'+str(questionCtr)])
                if not qOptions:
                    return -1
                messageJson= \
                    createQuestionPost(self.server.baseDir, \
                                       nickname, \
                                       self.server.domain,self.server.port, \
                                       self.server.httpPrefix, \
                                       fields['message'],qOptions, \
                                       False,False,False, \
                                       filename,attachmentMediaType, \
                                       fields['imageDescription'],True, \
                                       fields['subject'],int(fields['duration']))
                if messageJson:
                    self.postToNickname=nickname
                    if self.server.debug:
                        print('DEBUG: new Question')
                    if self._postToOutbox(messageJson,__version__):
                        return 1
                return -1
            elif postType=='newshare':
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
                durationStr=fields['duration']
                if durationStr:
                    if ' ' not in durationStr:
                        durationStr=durationStr+' days'
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
                         durationStr,
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
        if not authorized:
            print('Not receiving new post for '+path+' because not authorized')
            return None

        if '/users/' not in path:
            print('Not receiving new post for '+path+' because /users/ not in path')
            return None

        if '?'+postType+'?' not in path:
            print('Not receiving new post for '+path+' because ?'+postType+'? not in path')
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

        length = int(headers['Content-Length'])
        if length>self.server.maxPostLength:
            print('POST size too large')
            return None

        if not headers.get('Content-Type'):
            if headers.get('Content-type'):
                headers['Content-Type']=headers['Content-type']
            elif headers.get('content-type'):
                headers['Content-Type']=headers['content-type']
        if headers.get('Content-Type'):
            if ' boundary=' in headers['Content-Type']:
                boundary=headers['Content-Type'].split('boundary=')[1]
                if ';' in boundary:
                    boundary=boundary.split(';')[0]

                postBytes=self.rfile.read(length)
            
                # second length check from the bytes received
                # since Content-Length could be untruthful
                length=len(postBytes)
                if length>self.server.maxPostLength:
                    print('POST size too large')
                    return None
            
                # Note sending new posts needs to be synchronous, otherwise any attachments
                # can get mangled if other events happen during their decoding
                print('Creating new post: '+newPostThreadName)
                self._receiveNewPostProcess(authorized,postType,path,headers,length,postBytes,boundary)
        return pageNumber
        
    def do_POST(self):
        POSTstartTime=time.time()
        POSTtimings=[]

        if not self.server.session:
            print('Starting new session from POST')
            self.server.session= \
                createSession(self.server.useTor)

        if self.server.debug:
            print('DEBUG: POST to '+self.server.baseDir+ \
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
            self.path= \
                self.path.replace('/outbox/','/outbox').replace('/inbox/','/inbox').replace('/shares/','/shares').replace('/sharedInbox/','/sharedInbox')

        if self.path=='/inbox':
            if not self.server.enableSharedInbox:
                self._503()
                return

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

        self._benchmarkPOSTtimings(POSTstartTime,POSTtimings,1)
        
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
            loginNickname,loginPassword,register= \
                htmlGetLoginCredentials(loginParams,self.server.lastLoginTime)
            if loginNickname:
                self.server.lastLoginTime=int(time.time())
                if register:
                    if not registerAccount(self.server.baseDir, \
                                           self.server.httpPrefix, \
                                           self.server.domain, \
                                           self.server.port, \
                                           loginNickname,loginPassword):
                        self.server.POSTbusy=False
                        self._redirect_headers(self.server.httpPrefix+'://'+self.server.domainFull+'/login',cookie)
                        return
                authHeader=createBasicAuthHeader(loginNickname,loginPassword)
                if not authorizeBasic(self.server.baseDir,'/users/'+ \
                                      loginNickname+'/outbox',authHeader,False):
                    print('Login failed: '+loginNickname)
                    self._clearLoginDetails(loginNickname)
                    self.server.POSTbusy=False
                    return
                else:
                    if isSuspended(self.server.baseDir,loginNickname):
                        msg=htmlSuspended(self.server.baseDir).encode('utf-8')
                        self._login_headers('text/html',len(msg))
                        self._write(msg)
                        self.server.POSTbusy=False
                        return                 
                    # login success - redirect with authorization
                    print('Login success: '+loginNickname)
                    self.send_response(303)
                    # re-activate account if needed
                    activateAccount(self.server.baseDir,loginNickname,self.server.domain)
                    # This produces a deterministic token based on nick+password+salt
                    saltFilename= \
                        self.server.baseDir+'/accounts/'+ \
                        loginNickname+'@'+self.server.domain+'/.salt'
                    salt=createPassword(32)
                    if os.path.isfile(saltFilename):
                        try:
                            with open(saltFilename, 'r') as fp:
                                salt = fp.read()
                        except Exception as e:
                            print('WARN: Unable to read salt for '+ \
                                  loginNickname+' '+str(e))
                    else:
                        try:
                            with open(saltFilename, 'w') as fp:
                                fp.write(salt)
                        except Exception as e:
                            print('WARN: Unable to save salt for '+ \
                                  loginNickname+' '+str(e))

                    token=sha256((loginNickname+loginPassword+salt).encode('utf-8')).hexdigest()
                    self.server.tokens[loginNickname]=token
                    tokenFilename= \
                        self.server.baseDir+'/accounts/'+ \
                        loginNickname+'@'+self.server.domain+'/.token'
                    try:
                        with open(tokenFilename, 'w') as fp:
                            fp.write(token)
                    except Exception as e:
                        print('WARN: Unable to save token for '+loginNickname+' '+str(e))

                    self.server.tokensLookup[self.server.tokens[loginNickname]]=loginNickname
                    self.send_header('Set-Cookie', \
                                     'epicyon='+self.server.tokens[loginNickname]+'; SameSite=Strict')
                    self.send_header('Location', \
                                     self.server.httpPrefix+'://'+ \
                                     self.server.domainFull+ \
                                     '/users/'+loginNickname+'/inbox')
                    self.send_header('Content-Length', '0')
                    self.send_header('X-Robots-Tag','noindex')
                    self.end_headers()
                    self.server.POSTbusy=False
                    return
            self.send_response(200)
            self.end_headers()
            self.server.POSTbusy=False
            return

        self._benchmarkPOSTtimings(POSTstartTime,POSTtimings,2)

        # update of profile/avatar from web interface
        if authorized and self.path.endswith('/profiledata'):
            actorStr= \
                self.server.httpPrefix+'://'+self.server.domainFull+ \
                self.path.replace('/profiledata','').replace('/editprofile','')
            if ' boundary=' in self.headers['Content-type']:
                boundary=self.headers['Content-type'].split('boundary=')[1]
                if ';' in boundary:
                    boundary=boundary.split(';')[0]

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

                # read the bytes of the http form POST
                postBytes=self.rfile.read(length)

                # extract each image type
                actorChanged=True
                profileMediaTypes=['avatar','image','banner','instanceLogo']
                profileMediaTypesUploaded={}
                for mType in profileMediaTypes:
                    if self.server.debug:
                        print('DEBUG: profile update extracting '+mType+' image from POST')
                    mediaBytes,postBytes=extractMediaInFormPOST(postBytes,boundary,mType)
                    if mediaBytes:
                        if self.server.debug:
                            print('DEBUG: profile update '+mType+' image was found. '+str(len(mediaBytes))+' bytes')
                    else:
                        if self.server.debug:
                            print('DEBUG: profile update, no '+mType+' image was found in POST')
                        continue

                    # Note: a .temp extension is used here so that at no time is
                    # an image with metadata publicly exposed, even for a few mS
                    if mType!='instanceLogo':
                        filenameBase= \
                            self.server.baseDir+'/accounts/'+ \
                            nickname+'@'+self.server.domain+'/'+mType+'.temp'
                    else:
                        filenameBase= \
                            self.server.baseDir+'/accounts/login.temp'

                    filename,attachmentMediaType= \
                        saveMediaInFormPOST(mediaBytes,self.server.debug,filenameBase)
                    if filename:
                        if self.server.debug:
                            print('DEBUG: profile update POST '+mType+' media filename is '+filename)
                    else:
                        if self.server.debug:
                            print('DEBUG: profile update, no '+mType+' media filename in POST')
                        continue

                    if self.server.debug:
                        print('DEBUG: POST '+mType+' media removing metadata')
                    postImageFilename=filename.replace('.temp','')
                    removeMetaData(filename,postImageFilename)
                    if os.path.isfile(postImageFilename):
                        print('profile update POST '+mType+' image saved to '+postImageFilename)
                        if mType!='instanceLogo':
                            lastPartOfImageFilename=postImageFilename.split('/')[-1]
                            profileMediaTypesUploaded[mType]=lastPartOfImageFilename
                            actorChanged=True
                    else:
                        print('ERROR: profile update POST '+mType+' image could not be saved to '+postImageFilename)

                fields=extractTextFieldsInPOST(postBytes,boundary,self.server.debug)
                if self.server.debug:
                    if fields:
                        print('DEBUG: profile update text field extracted from POST '+str(fields))
                    else:
                        print('WARN: profile update, no text fields could be extracted from POST')

                actorFilename= \
                    self.server.baseDir+'/accounts/'+ \
                    nickname+'@'+self.server.domain+'.json'
                if os.path.isfile(actorFilename):
                    actorJson=loadJson(actorFilename)
                    if actorJson:

                        # update the avatar/image url file extension
                        for mType,lastPartOfImageFilename in profileMediaTypesUploaded.items():
                            if mType=='avatar':
                                lastPartOfUrl=actorJson['icon']['url'].split('/')[-1]
                                actorJson['icon']['url']= \
                                    actorJson['icon']['url'].replace('/'+lastPartOfUrl, \
                                                                     '/'+lastPartOfImageFilename)
                            elif mType=='image':
                                lastPartOfUrl=actorJson['image']['url'].split('/')[-1]
                                actorJson['image']['url']= \
                                    actorJson['image']['url'].replace('/'+lastPartOfUrl, \
                                                                      '/'+lastPartOfImageFilename)

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
                        if fields.get('password'):
                            if fields.get('passwordconfirm'):
                                if actorJson['password']==fields['passwordconfirm']:
                                    if len(actorJson['password'])>2:
                                        # set password
                                        storeBasicCredentials(self.server.baseDir,nickname,actorJson['password'])
                        if fields.get('displayNickname'):
                            if fields['displayNickname']!=actorJson['name']:
                                actorJson['name']=fields['displayNickname']
                                actorChanged=True
                        if fields.get('themeDropdown'):
                            setTheme(self.server.baseDir,fields['themeDropdown'])
                            #self.server.iconsCache={}
                        if fields.get('donateUrl'):
                            currentDonateUrl=getDonationUrl(actorJson)
                            if fields['donateUrl']!=currentDonateUrl:
                                setDonationUrl(actorJson,fields['donateUrl'])
                                actorChanged=True
                        if fields.get('instanceTitle'):
                            currInstanceTitle=getConfigParam(self.server.baseDir,'instanceTitle')
                            if fields['instanceTitle']!=currInstanceTitle:
                                setConfigParam(self.server.baseDir,'instanceTitle',fields['instanceTitle'])
                        if fields.get('instanceDescriptionShort'):
                            currInstanceDescriptionShort=getConfigParam(self.server.baseDir,'instanceDescriptionShort')
                            if fields['instanceDescriptionShort']!=currInstanceDescriptionShort:
                                setConfigParam(self.server.baseDir,'instanceDescriptionShort',fields['instanceDescriptionShort'])
                        if fields.get('instanceDescription'):
                            currInstanceDescription=getConfigParam(self.server.baseDir,'instanceDescription')
                            if fields['instanceDescription']!=currInstanceDescription:
                                setConfigParam(self.server.baseDir,'instanceDescription',fields['instanceDescription'])
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
                                        if os.path.isdir(self.server.baseDir+ \
                                                         '/accounts/'+modNick+ \
                                                         '@'+self.server.domain):
                                            modFile.write(modNick+'\n')
                                    modFile.close()
                                    for modNick in fields['moderators'].split(','):
                                        modNick=modNick.strip()
                                        if os.path.isdir(self.server.baseDir+ \
                                                         '/accounts/'+modNick+ \
                                                         '@'+self.server.domain):
                                            setRole(self.server.baseDir, \
                                                    modNick,self.server.domain, \
                                                    'instance','moderator')
                                else:
                                    # nicknames on separate lines
                                    modFile=open(moderatorsFile,"w+")
                                    for modNick in fields['moderators'].split('\n'):
                                        modNick=modNick.strip()
                                        if os.path.isdir(self.server.baseDir+ \
                                                         '/accounts/'+modNick+ \
                                                         '@'+self.server.domain):
                                            modFile.write(modNick+'\n')
                                    modFile.close()
                                    for modNick in fields['moderators'].split('\n'):
                                        modNick=modNick.strip()
                                        if os.path.isdir(self.server.baseDir+ \
                                                         '/accounts/'+modNick+ \
                                                         '@'+self.server.domain):
                                            setRole(self.server.baseDir, \
                                                    modNick,self.server.domain, \
                                                    'instance','moderator')
                                        
                        approveFollowers=False
                        if fields.get('approveFollowers'):
                            if fields['approveFollowers']=='on':
                                approveFollowers=True
                        if approveFollowers!=actorJson['manuallyApprovesFollowers']:
                            actorJson['manuallyApprovesFollowers']=approveFollowers
                            actorChanged=True                                
                        # only receive DMs from accounts you follow
                        followDMsFilename= \
                            self.server.baseDir+'/accounts/'+ \
                            nickname+'@'+self.server.domain+'/.followDMs'
                        followDMsActive=False
                        if fields.get('followDMs'):
                            if fields['followDMs']=='on':
                                followDMsActive=True
                                with open(followDMsFilename, "w") as followDMsFile:
                                    followDMsFile.write('\n')
                        if not followDMsActive:
                            if os.path.isfile(followDMsFilename):
                                os.remove(followDMsFilename)
                        # this account is a bot
                        if fields.get('isBot'):
                            if fields['isBot']=='on':
                                if actorJson['type']!='Service':
                                    actorJson['type']='Service'
                                    actorChanged=True
                        else:
                            # this account is a group
                            if fields.get('isGroup'):
                                if fields['isGroup']=='on':
                                    if actorJson['type']!='Group':
                                        actorJson['type']='Group'
                                        actorChanged=True
                            else:
                                # this account is a person (default)
                                if actorJson['type']!='Person':
                                    actorJson['type']='Person'
                                    actorChanged=True
                        # save filtered words list
                        filterFilename= \
                            self.server.baseDir+'/accounts/'+ \
                            nickname+'@'+self.server.domain+'/filters.txt'
                        if fields.get('filteredWords'):
                            with open(filterFilename, "w") as filterfile:
                                filterfile.write(fields['filteredWords'])
                        else:
                            if os.path.isfile(filterFilename):
                                os.remove(filterFilename)
                        # save blocked accounts list
                        blockedFilename= \
                            self.server.baseDir+'/accounts/'+ \
                            nickname+'@'+self.server.domain+'/blocking.txt'
                        if fields.get('blocked'):
                            with open(blockedFilename, "w") as blockedfile:
                                blockedfile.write(fields['blocked'])
                        else:
                            if os.path.isfile(blockedFilename):
                                os.remove(blockedFilename)
                        # save allowed instances list
                        allowedInstancesFilename= \
                            self.server.baseDir+'/accounts/'+ \
                            nickname+'@'+self.server.domain+'/allowedinstances.txt'
                        if fields.get('allowedInstances'):
                            with open(allowedInstancesFilename, "w") as allowedInstancesFile:
                                allowedInstancesFile.write(fields['allowedInstances'])
                        else:
                            if os.path.isfile(allowedInstancesFilename):
                                os.remove(allowedInstancesFilename)
                        # save actor json file within accounts
                        if actorChanged:
                            saveJson(actorJson,actorFilename)
                            # also copy to the actors cache and personCache in memory
                            storePersonInCache(self.server.baseDir, \
                                               actorJson['id'],actorJson, \
                                               self.server.personCache)
                            actorCacheFilename= \
                                self.server.baseDir+'/cache/actors/'+ \
                                actorJson['id'].replace('/','#')+'.json'
                            saveJson(actorJson,actorCacheFilename)
                            # send actor update to followers
                            updateActorJson={
                                'type': 'Update',
                                'actor': actorJson['id'],
                                'to': [actorJson['id']+'/followers'],
                                'cc': [],
                                'object': actorJson
                            }
                            self.postToNickname=nickname
                            self._postToOutbox(updateActorJson,__version__)
                        if fields.get('deactivateThisAccount'):
                            if fields['deactivateThisAccount']=='on':
                                deactivateAccount(self.server.baseDir,nickname,self.server.domain)
                                self._clearLoginDetails(nickname)
                                self.server.POSTbusy=False
                                return
            self._redirect_headers(actorStr,cookie)
            self.server.POSTbusy=False
            return

        self._benchmarkPOSTtimings(POSTstartTime,POSTtimings,3)

        # moderator action buttons
        if authorized and '/users/' in self.path and \
           self.path.endswith('/moderationaction'):
            actorStr= \
                self.server.httpPrefix+'://'+self.server.domainFull+ \
                self.path.replace('/moderationaction','')
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
                            moderationText= \
                                moderationStr.split('=')[1].strip()
                            moderationText= \
                                moderationText.replace('+',' ').replace('%40','@').replace('%3A',':').replace('%23','#').strip()
                    elif moderationStr.startswith('submitInfo'):
                        msg=htmlModerationInfo(self.server.translate, \
                                               self.server.baseDir).encode('utf-8')
                        self._login_headers('text/html',len(msg))
                        self._write(msg)
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
                        suspendAccount(self.server.baseDir,nickname, \
                                       self.server.domain)
                    if moderationButton=='unsuspend':
                        unsuspendAccount(self.server.baseDir,nickname)
                    if moderationButton=='block':
                        fullBlockDomain=None
                        if moderationText.startswith('http') or \
                           moderationText.startswith('dat'):
                            blockDomain,blockPort= \
                                getDomainFromActor(moderationText)
                            fullBlockDomain=blockDomain
                            if blockPort:
                                if blockPort!=80 and blockPort!=443:
                                    if ':' not in blockDomain:
                                        fullBlockDomain= \
                                            blockDomain+':'+str(blockPort)
                        if '@' in moderationText:
                            fullBlockDomain=moderationText.split('@')[1]
                        if fullBlockDomain or nickname.startswith('#'):
                            addGlobalBlock(self.server.baseDir, \
                                           nickname,fullBlockDomain)
                    if moderationButton=='unblock':
                        fullBlockDomain=None
                        if moderationText.startswith('http') or \
                           moderationText.startswith('dat'):
                            blockDomain,blockPort= \
                                getDomainFromActor(moderationText)
                            fullBlockDomain=blockDomain
                            if blockPort:
                                if blockPort!=80 and blockPort!=443:
                                    if ':' not in blockDomain:
                                        fullBlockDomain= \
                                            blockDomain+':'+str(blockPort)
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

        self._benchmarkPOSTtimings(POSTstartTime,POSTtimings,4)

        searchForEmoji=False
        if self.path.endswith('/searchhandleemoji'):
            searchForEmoji=True
            self.path=self.path.replace('/searchhandleemoji','/searchhandle')
            if self.server.debug:
                print('DEBUG: searching for emoji')
                print('authorized: '+str(authorized))

        self._benchmarkPOSTtimings(POSTstartTime,POSTtimings,5)

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
            actor= \
                self.server.httpPrefix+'://'+ \
                self.server.domainFull+self.path.replace('/question','')
            nickname=getNicknameFromActor(actor)
            if not nickname:
                self._redirect_headers(actor+'/inbox?page='+ \
                                       str(pageNumber),cookie)
                self.server.POSTbusy=False
                return
            # get the parameters
            length = int(self.headers['Content-length'])
            questionParams=self.rfile.read(length).decode('utf-8')
            questionParams= \
                questionParams.replace('+',' ').replace('%40','@').replace('%3A',':').replace('%23','#').strip()
            # post being voted on
            messageId=None
            if 'messageId=' in questionParams:
                messageId=questionParams.split('messageId=')[1]
                if '&' in messageId:
                    messageId=messageId.split('&')[0]
            answer=None
            if 'answer=' in questionParams:
                answer=questionParams.split('answer=')[1]
                if '&' in answer:
                    answer=answer.split('&')[0]
            self._sendReplyToQuestion(nickname,messageId,answer)
            self._redirect_headers(actor+'/inbox?page='+str(pageNumber),cookie)
            self.server.POSTbusy=False
            return                

        self._benchmarkPOSTtimings(POSTstartTime,POSTtimings,6)

        # a search was made
        if (authorized or searchForEmoji) and \
           (self.path.endswith('/searchhandle') or \
            '/searchhandle?page=' in self.path):
            # get the page number
            pageNumber=1
            if '/searchhandle?page=' in self.path:
                pageNumberStr=self.path.split('/searchhandle?page=')[1]
                if pageNumberStr.isdigit():
                    pageNumber=int(pageNumberStr)
                self.path=self.path.split('?page=')[0]

            actorStr= \
                self.server.httpPrefix+'://'+ \
                self.server.domainFull+ \
                self.path.replace('/searchhandle','')
            length = int(self.headers['Content-length'])
            searchParams=self.rfile.read(length).decode('utf-8')
            if 'searchtext=' in searchParams:
                searchStr=searchParams.split('searchtext=')[1]
                if '&' in searchStr:
                    searchStr=searchStr.split('&')[0]
                searchStr= \
                    searchStr.replace('%20',' ').replace('%40','@').replace('%3A',':').replace('%2F','/').replace('%23','#').strip()
                if self.server.debug:
                    print('searchStr: '+searchStr)
                if searchForEmoji:
                    searchStr=':'+searchStr+':'
                if searchStr.startswith('#'):      
                    # hashtag search
                    hashtagStr= \
                        htmlHashtagSearch(self.server.recentPostsCache, \
                                          self.server.maxRecentPosts, \
                                          self.server.translate, \
                                          self.server.baseDir,searchStr[1:],1, \
                                          maxPostsInFeed,self.server.session, \
                                          self.server.cachedWebfingers, \
                                          self.server.personCache, \
                                          self.server.httpPrefix, \
                                          self.server.projectVersion)
                    if hashtagStr:
                        msg=hashtagStr.encode('utf-8')
                        self._login_headers('text/html',len(msg))
                        self._write(msg)
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
                        self._write(msg)
                        self.server.POSTbusy=False
                        return
                elif '@' in searchStr:
                    # profile search
                    nickname=getNicknameFromActor(self.path)
                    if not self.server.session:
                        self.server.session= \
                            createSession(self.server.useTor)
                    profileStr= \
                        htmlProfileAfterSearch(self.server.recentPostsCache, \
                                               self.server.maxRecentPosts, \
                                               self.server.translate, \
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
                        self._write(msg)
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
                        searchStr= \
                            searchStr.lower().strip('\n').replace(' emoji','')
                    # emoji search
                    emojiStr= \
                        htmlSearchEmoji(self.server.translate, \
                                        self.server.baseDir,searchStr)
                    if emojiStr:
                        msg=emojiStr.encode('utf-8')
                        self._login_headers('text/html',len(msg))
                        self._write(msg)
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
                        self._write(msg)
                        self.server.POSTbusy=False
                        return
            self._redirect_headers(actorStr+'/inbox',cookie)
            self.server.POSTbusy=False
            return

        self._benchmarkPOSTtimings(POSTstartTime,POSTtimings,7)

        # removes a shared item
        if authorized and self.path.endswith('/rmshare'):
            originPathStr= \
                self.server.httpPrefix+'://'+self.server.domainFull+ \
                self.path.split('/rmshare')[0]
            length = int(self.headers['Content-length'])
            removeShareConfirmParams=self.rfile.read(length).decode('utf-8')
            if '&submitYes=' in removeShareConfirmParams:
                removeShareConfirmParams= \
                    removeShareConfirmParams.replace('%20',' ').replace('%40','@').replace('%3A',':').replace('%2F','/').replace('%23','#').replace('+',' ').strip()
                shareActor=removeShareConfirmParams.split('actor=')[1]
                if '&' in shareActor:
                    shareActor=shareActor.split('&')[0]
                shareName=removeShareConfirmParams.split('shareName=')[1]
                if '&' in shareName:
                    shareName=shareName.split('&')[0]
                shareNickname=getNicknameFromActor(shareActor)
                if shareNickname:
                    shareDomain,sharePort=getDomainFromActor(shareActor)
                    removeShare(self.server.baseDir, \
                                shareNickname,shareDomain,shareName)
            self._redirect_headers(originPathStr+'/tlshares',cookie)
            self.server.POSTbusy=False
            return

        self._benchmarkPOSTtimings(POSTstartTime,POSTtimings,8)

        # removes a post
        if authorized and self.path.endswith('/rmpost'):
            pageNumber=1
            originPathStr= \
                self.server.httpPrefix+'://'+self.server.domainFull+ \
                self.path.split('/rmpost')[0]
            length = int(self.headers['Content-length'])
            removePostConfirmParams=self.rfile.read(length).decode('utf-8')
            if '&submitYes=' in removePostConfirmParams:
                removePostConfirmParams= \
                    removePostConfirmParams.replace('%20',' ').replace('%40','@').replace('%3A',':').replace('%2F','/').replace('%23','#').strip()
                removeMessageId= \
                    removePostConfirmParams.split('messageId=')[1]
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
                    self.postToNickname=getNicknameFromActor(removePostActor)
                    if self.postToNickname:
                        self._postToOutboxThread(deleteJson)
            if pageNumber==1:
                self._redirect_headers(originPathStr+'/outbox',cookie)
            else:
                self._redirect_headers(originPathStr+'/outbox?page='+ \
                                       str(pageNumber),cookie)
            self.server.POSTbusy=False
            return

        self._benchmarkPOSTtimings(POSTstartTime,POSTtimings,9)

        # decision to follow in the web interface is confirmed
        if authorized and self.path.endswith('/followconfirm'):
            originPathStr= \
                self.server.httpPrefix+'://'+self.server.domainFull+ \
                self.path.split('/followconfirm')[0]
            followerNickname=getNicknameFromActor(originPathStr)
            length = int(self.headers['Content-length'])
            followConfirmParams=self.rfile.read(length).decode('utf-8')
            if '&submitView=' in followConfirmParams:
                followingActor= \
                    followConfirmParams.replace('%3A',':').replace('%2F','/').split('actor=')[1]
                if '&' in followingActor:
                    followingActor=followingActor.split('&')[0]
                self._redirect_headers(followingActor,cookie)
                self.server.POSTbusy=False
                return
            if '&submitYes=' in followConfirmParams:
                followingActor= \
                    followConfirmParams.replace('%3A',':').replace('%2F','/').split('actor=')[1]
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
                        print('Sending follow request from '+ \
                              followerNickname+' to '+followingActor)
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

        self._benchmarkPOSTtimings(POSTstartTime,POSTtimings,10)

        # decision to unfollow in the web interface is confirmed
        if authorized and self.path.endswith('/unfollowconfirm'):
            originPathStr= \
                self.server.httpPrefix+'://'+self.server.domainFull+ \
                self.path.split('/unfollowconfirm')[0]
            followerNickname=getNicknameFromActor(originPathStr)
            length = int(self.headers['Content-length'])
            followConfirmParams=self.rfile.read(length).decode('utf-8')
            if '&submitYes=' in followConfirmParams:
                followingActor= \
                    followConfirmParams.replace('%3A',':').replace('%2F','/').split('actor=')[1]
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
                    followActor= \
                        self.server.httpPrefix+'://'+ \
                        self.server.domainFull+ \
                        '/users/'+followerNickname
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

        self._benchmarkPOSTtimings(POSTstartTime,POSTtimings,11)

        # decision to unblock in the web interface is confirmed
        if authorized and self.path.endswith('/unblockconfirm'):
            originPathStr= \
                self.server.httpPrefix+'://'+self.server.domainFull+ \
                self.path.split('/unblockconfirm')[0]
            blockerNickname=getNicknameFromActor(originPathStr)
            if not blockerNickname:
                print('WARN: unable to find nickname in '+originPathStr)
                self._redirect_headers(originPathStr,cookie)
                self.server.POSTbusy=False
                return                
            length = int(self.headers['Content-length'])
            blockConfirmParams=self.rfile.read(length).decode('utf-8')
            if '&submitYes=' in blockConfirmParams:
                blockingActor= \
                    blockConfirmParams.replace('%3A',':').replace('%2F','/').split('actor=')[1]
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
                            blockingDomainFull= \
                                blockingDomain+':'+str(blockingPort)
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

        self._benchmarkPOSTtimings(POSTstartTime,POSTtimings,12)

        # decision to block in the web interface is confirmed
        if authorized and self.path.endswith('/blockconfirm'):
            originPathStr= \
                self.server.httpPrefix+'://'+self.server.domainFull+ \
                self.path.split('/blockconfirm')[0]
            blockerNickname=getNicknameFromActor(originPathStr)
            if not blockerNickname:
                print('WARN: unable to find nickname in '+originPathStr)
                self._redirect_headers(originPathStr,cookie)
                self.server.POSTbusy=False
                return                
            length = int(self.headers['Content-length'])
            blockConfirmParams=self.rfile.read(length).decode('utf-8')
            if '&submitYes=' in blockConfirmParams:
                blockingActor= \
                    blockConfirmParams.replace('%3A',':').replace('%2F','/').split('actor=')[1]
                if '&' in blockingActor:
                    blockingActor=blockingActor.split('&')[0]
                blockingNickname=getNicknameFromActor(blockingActor)
                if not blockingNickname:
                    print('WARN: unable to find nickname in '+blockingActor)
                    self._redirect_headers(originPathStr,cookie)
                    self.server.POSTbusy=False
                    return                    
                blockingDomain,blockingPort= \
                    getDomainFromActor(blockingActor)
                blockingDomainFull=blockingDomain
                if blockingPort:
                    if blockingPort!=80 and blockingPort!=443:
                        if ':' not in blockingDomain:
                            blockingDomainFull= \
                                blockingDomain+':'+str(blockingPort)
                if blockerNickname==blockingNickname and \
                   blockingDomain==self.server.domain and \
                   blockingPort==self.server.port:
                    if self.server.debug:
                        print('You cannot block yourself!')
                else:
                    if self.server.debug:
                        print('Adding block by '+blockerNickname+ \
                              ' of '+blockingActor)
                    addBlock(self.server.baseDir,blockerNickname, \
                             self.server.domain, \
                             blockingNickname,blockingDomainFull)
            self._redirect_headers(originPathStr,cookie)
            self.server.POSTbusy=False
            return

        self._benchmarkPOSTtimings(POSTstartTime,POSTtimings,13)

        # an option was chosen from person options screen
        # view/follow/block/report
        if authorized and self.path.endswith('/personoptions'):
            pageNumber=1
            originPathStr= \
                self.server.httpPrefix+'://'+self.server.domainFull+ \
                self.path.split('/personoptions')[0]
            chooserNickname=getNicknameFromActor(originPathStr)
            if not chooserNickname:
                print('WARN: unable to find nickname in '+originPathStr)
                self._redirect_headers(originPathStr,cookie)
                self.server.POSTbusy=False
                return                
            length = int(self.headers['Content-length'])
            optionsConfirmParams= \
                self.rfile.read(length).decode('utf-8').replace('%3A',':').replace('%2F','/')
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
                    print('Adding block by '+chooserNickname+ \
                          ' of '+optionsActor)
                addBlock(self.server.baseDir,chooserNickname, \
                         self.server.domain, \
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
                self._write(msg)
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
                self._write(msg)
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
                self._write(msg)
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
                self._write(msg)
                self.server.POSTbusy=False
                return            
            if '&submitSnooze=' in optionsConfirmParams:
                thisActor= \
                    self.server.httpPrefix+'://'+self.server.domainFull+ \
                    self.path.split('/personoptions')[0]
                if self.server.debug:
                    print('Snoozing '+optionsActor+' '+thisActor)
                if '/users/' in thisActor:
                    nickname=thisActor.split('/users/')[1]
                    personSnooze(self.server.baseDir,nickname,self.server.domain,optionsActor)
                    self._redirect_headers(thisActor+ \
                                           '/inbox?page='+str(pageNumber),cookie)
                    self.server.POSTbusy=False
                    return
            if '&submitUnSnooze=' in optionsConfirmParams:
                thisActor= \
                    self.server.httpPrefix+'://'+self.server.domainFull+ \
                    self.path.split('/personoptions')[0]
                if self.server.debug:
                    print('Unsnoozing '+optionsActor+' '+thisActor)
                if '/users/' in thisActor:
                    nickname=thisActor.split('/users/')[1]
                    personUnsnooze(self.server.baseDir,nickname,self.server.domain,optionsActor)
                    self._redirect_headers(thisActor+ \
                                           '/inbox?page='+str(pageNumber),cookie)
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
                self._write(msg)
                self.server.POSTbusy=False
                return            

            self._redirect_headers(originPathStr,cookie)
            self.server.POSTbusy=False
            return

        self._benchmarkPOSTtimings(POSTstartTime,POSTtimings,14)

        pageNumber=self._receiveNewPost(authorized,'newpost',self.path)
        if pageNumber:
            nickname=self.path.split('/users/')[1]
            if '/' in nickname:
                nickname=nickname.split('/')[0]
            self._redirect_headers(self.server.httpPrefix+'://'+self.server.domainFull+ \
                                   '/users/'+nickname+ \
                                   '/inbox?page='+str(pageNumber),cookie)
            self.server.POSTbusy=False
            return
        pageNumber=self._receiveNewPost(authorized,'newunlisted',self.path)
        if pageNumber:
            nickname=self.path.split('/users/')[1]
            if '/' in nickname:
                nickname=nickname.split('/')[0]
            self._redirect_headers(self.server.httpPrefix+'://'+self.server.domainFull+ \
                                   '/users/'+nickname+ \
                                   '/inbox?page='+str(pageNumber),cookie)
            self.server.POSTbusy=False
            return
        pageNumber=self._receiveNewPost(authorized,'newfollowers',self.path)
        if pageNumber:
            nickname=self.path.split('/users/')[1]
            if '/' in nickname:
                nickname=nickname.split('/')[0]
            self._redirect_headers(self.server.httpPrefix+'://'+self.server.domainFull+ \
                                   '/users/'+nickname+ \
                                   '/inbox?page='+str(pageNumber),cookie)
            self.server.POSTbusy=False
            return
        pageNumber=self._receiveNewPost(authorized,'newdm',self.path)
        if pageNumber:
            nickname=self.path.split('/users/')[1]
            if '/' in nickname:
                nickname=nickname.split('/')[0]
            self._redirect_headers(self.server.httpPrefix+'://'+self.server.domainFull+ \
                                   '/users/'+nickname+ \
                                   '/inbox?page='+str(pageNumber),cookie)
            self.server.POSTbusy=False
            return
        pageNumber=self._receiveNewPost(authorized,'newreport',self.path)
        if pageNumber:
            nickname=self.path.split('/users/')[1]
            if '/' in nickname:
                nickname=nickname.split('/')[0]
            self._redirect_headers(self.server.httpPrefix+'://'+self.server.domainFull+ \
                                   '/users/'+nickname+ \
                                   '/inbox?page='+str(pageNumber),cookie)
            self.server.POSTbusy=False
            return
        pageNumber=self._receiveNewPost(authorized,'newshare',self.path)
        if pageNumber:
            nickname=self.path.split('/users/')[1]
            if '/' in nickname:
                nickname=nickname.split('/')[0]
            self._redirect_headers(self.server.httpPrefix+'://'+self.server.domainFull+ \
                                   '/users/'+nickname+ \
                                   '/shares?page='+str(pageNumber),cookie)
            self.server.POSTbusy=False
            return

        self._benchmarkPOSTtimings(POSTstartTime,POSTtimings,15)

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

        self._benchmarkPOSTtimings(POSTstartTime,POSTtimings,16)

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

        self._benchmarkPOSTtimings(POSTstartTime,POSTtimings,17)

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
            accountsDir= \
                self.server.baseDir+'/accounts/'+ \
                self.postFromNickname+'@'+self.server.domain
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
            if self.headers['Content-type'].endswith('webp'):
                mediaFilename=mediaFilenameBase+'.webp'
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

        self._benchmarkPOSTtimings(POSTstartTime,POSTtimings,18)

        # check content length before reading bytes
        if self.path == '/sharedInbox' or self.path == '/inbox':
            length=0
            if self.headers.get('Content-length'):
                length = int(self.headers['Content-length'])
            elif self.headers.get('Content-Length'):
                length = int(self.headers['Content-Length'])
            elif self.headers.get('content-length'):
                length = int(self.headers['content-length'])
            if length>10240:
                print('WARN: post to shared inbox is too long '+str(length)+' bytes')
                self._400()
                self.server.POSTbusy=False
                return

        messageBytes=self.rfile.read(length)

        # check content length after reading bytes
        if self.path == '/sharedInbox' or self.path == '/inbox':
            lenMessage=len(messageBytes)
            if lenMessage>10240:
                print('WARN: post to shared inbox is too long '+str(lenMessage)+' bytes')
                self._400()
                self.server.POSTbusy=False
                return

        # convert the raw bytes to json
        messageJson=json.loads(messageBytes)
            
        self._benchmarkPOSTtimings(POSTstartTime,POSTtimings,19)

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

        self._benchmarkPOSTtimings(POSTstartTime,POSTtimings,20)

        # check the necessary properties are available
        if self.server.debug:
            print('DEBUG: Check message has params')

        if self.path.endswith('/inbox') or \
           self.path=='/sharedInbox':
            if not inboxMessageHasParams(messageJson):
                if self.server.debug:
                    print("DEBUG: inbox message doesn't have the required parameters")
                self.send_response(403)
                self.end_headers()
                self.server.POSTbusy=False
                return

        self._benchmarkPOSTtimings(POSTstartTime,POSTtimings,21)

        if not self.headers.get('signature'):
            if 'keyId=' not in self.headers['signature']:
                if self.server.debug:
                    print('DEBUG: POST to inbox has no keyId in header signature parameter')
                self.send_response(403)
                self.end_headers()
                self.server.POSTbusy=False
                return

        self._benchmarkPOSTtimings(POSTstartTime,POSTtimings,22)

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
        
        self._benchmarkPOSTtimings(POSTstartTime,POSTtimings,23)

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
                    queueStatus= \
                        self._updateInboxQueue(self.postToNickname, \
                                               messageJson,messageBytes)
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
                queueStatus= \
                    self._updateInboxQueue('inbox',messageJson,messageBytes)
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

def runPostsQueue(baseDir: str,sendThreads: [],debug: bool) -> None:
    """Manages the threads used to send posts
    """
    while True:
        time.sleep(1)
        removeDormantThreads(baseDir,sendThreads,debug)

def runSharesExpire(versionNumber: str,baseDir: str) -> None:
    """Expires shares as needed
    """
    while True:
        time.sleep(120)
        expireShares(baseDir)

def runPostsWatchdog(projectVersion: str,httpd) -> None:
    """This tries to keep the posts thread running even if it dies
    """
    print('Starting posts queue watchdog')
    postsQueueOriginal=httpd.thrPostsQueue.clone(runPostsQueue)
    httpd.thrPostsQueue.start()
    while True:
        time.sleep(20) 
        if not httpd.thrPostsQueue.isAlive():
            httpd.thrPostsQueue.kill()
            httpd.thrPostsQueue=postsQueueOriginal.clone(runPostsQueue)
            httpd.thrPostsQueue.start()
            print('Restarting posts queue...')

def runSharesExpireWatchdog(projectVersion: str,httpd) -> None:
    """This tries to keep the shares expiry thread running even if it dies
    """
    print('Starting shares expiry watchdog')
    sharesExpireOriginal=httpd.thrSharesExpire.clone(runSharesExpire)
    httpd.thrSharesExpire.start()
    while True:
        time.sleep(20) 
        if not httpd.thrSharesExpire.isAlive():
            httpd.thrSharesExpire.kill()
            httpd.thrSharesExpire=sharesExpireOriginal.clone(runSharesExpire)
            httpd.thrSharesExpire.start()
            print('Restarting shares expiry...')

def loadTokens(baseDir: str,tokensDict: {},tokensLookup: {}) -> None:
    for subdir, dirs, files in os.walk(baseDir+'/accounts'):
        for handle in dirs:
            if '@' in handle:
                tokenFilename=baseDir+'/accounts/'+handle+'/.token'
                if not os.path.isfile(tokenFilename):
                    continue
                nickname=handle.split('@')[0]
                token=None
                try:
                    with open(tokenFilename, 'r') as fp:
                        token = fp.read()
                except Exception as e:
                    print('WARN: Unable to read token for '+nickname+' '+str(e))
                if not token:
                    continue
                tokensDict[nickname]=token
                tokensLookup[token]=nickname

def runDaemon(maxRecentPosts: int, \
              enableSharedInbox: bool,registration: bool, \
              language: str,projectVersion: str, \
              instanceId: str,clientToServer: bool, \
              baseDir: str,domain: str, \
              port=80,proxyPort=80,httpPrefix='https', \
              fedList=[],maxMentions=10,maxEmoji=10, \
              authenticatedFetch=False, \
              noreply=False,nolike=False,nopics=False, \
              noannounce=False,cw=False,ocapAlways=False, \
              useTor=False,maxReplies=64, \
              domainMaxPostsPerDay=8640,accountMaxPostsPerDay=8640, \
              allowDeletion=False,debug=False,unitTest=False, \
              instanceOnlySkillsSearch=False,sendThreads=[]) -> None:
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
    httpd.systemLanguage='en'
    if not unitTest:
        if not os.path.isdir(baseDir+'/translations'):
            print('ERROR: translations directory not found')
            return
        if not language:
            systemLanguage=locale.getdefaultlocale()[0]
        else:
            systemLanguage=language
        if not systemLanguage:
            systemLanguage='en'            
        if '_' in systemLanguage:
            systemLanguage=systemLanguage.split('_')[0]
        while '/' in systemLanguage:
            systemLanguage=systemLanguage.split('/')[1]
        if '.' in systemLanguage:
            systemLanguage=systemLanguage.split('.')[0]
        translationsFile=baseDir+'/translations/'+systemLanguage+'.json'
        if not os.path.isfile(translationsFile):
            systemLanguage='en'
            translationsFile=baseDir+'/translations/'+systemLanguage+'.json'
        print('System language: '+systemLanguage)
        httpd.systemLanguage=systemLanguage
        httpd.translate=loadJson(translationsFile)

    if registration=='open':
        httpd.registration=True
    else:
        httpd.registration=False
    httpd.enableSharedInbox=enableSharedInbox
    httpd.outboxThread={}
    httpd.newPostThread={}
    httpd.projectVersion=projectVersion
    httpd.authenticatedFetch=authenticatedFetch
    # max POST size of 30M
    httpd.maxPostLength=1024*1024*30
    httpd.maxMediaSize=httpd.maxPostLength
    httpd.maxMessageLength=5000
    httpd.maxPostsInBox=32000
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
    httpd.sendThreads=sendThreads
    httpd.postLog=[]
    httpd.maxQueueLength=16
    httpd.ocapAlways=ocapAlways
    httpd.allowDeletion=allowDeletion
    httpd.lastLoginTime=0
    httpd.maxReplies=maxReplies
    httpd.tokens={}
    httpd.tokensLookup={}
    loadTokens(baseDir,httpd.tokens,httpd.tokensLookup)
    httpd.instanceOnlySkillsSearch=instanceOnlySkillsSearch
    httpd.acceptedCaps=["inbox:write","objects:read"]
    # contains threads used to send posts to followers
    httpd.followersThreads=[]
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

    print('Creating posts queue')
    httpd.thrPostsQueue= \
        threadWithTrace(target=runPostsQueue, \
                        args=(baseDir,httpd.sendThreads,debug),daemon=True)
    if not unitTest: 
        httpd.thrPostsWatchdog= \
            threadWithTrace(target=runPostsWatchdog, \
                            args=(projectVersion,httpd),daemon=True)        
        httpd.thrPostsWatchdog.start()
    else:
        httpd.thrPostsQueue.start()

    print('Creating expire thread for shared items')
    httpd.thrSharesExpire= \
        threadWithTrace(target=runSharesExpire, \
                        args=(__version__,baseDir),daemon=True)
    if not unitTest: 
        httpd.thrSharesExpireWatchdog= \
            threadWithTrace(target=runSharesExpireWatchdog, \
                            args=(projectVersion,httpd),daemon=True)        
        httpd.thrSharesExpireWatchdog.start()
    else:
        httpd.thrSharesExpire.start()

    httpd.recentPostsCache={}
    httpd.maxRecentPosts=maxRecentPosts
    httpd.iconsCache={}

    print('Creating inbox queue')
    httpd.thrInboxQueue= \
        threadWithTrace(target=runInboxQueue, \
                        args=(httpd.recentPostsCache,httpd.maxRecentPosts, \
                              projectVersion, \
                              baseDir,httpPrefix,httpd.sendThreads, \
                              httpd.postLog,httpd.cachedWebfingers, \
                              httpd.personCache,httpd.inboxQueue, \
                              domain,port,useTor,httpd.federationList, \
                              httpd.ocapAlways,maxReplies, \
                              domainMaxPostsPerDay,accountMaxPostsPerDay, \
                              allowDeletion,debug,maxMentions,maxEmoji, \
                              httpd.translate, \
                              unitTest,httpd.acceptedCaps),daemon=True)
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
