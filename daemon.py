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
from pprint import pprint
from session import createSession
from webfinger import webfingerMeta
from webfinger import webfingerLookup
from webfinger import webfingerHandle
from person import personLookup
from person import personBoxJson
from person import createSharedInbox
from posts import outboxMessageCreateWrap
from posts import savePostToBox
from posts import sendToFollowers
from posts import postIsAddressedToPublic
from posts import sendToNamedAddresses
from inbox import inboxPermittedMessage
from inbox import inboxMessageHasParams
from inbox import runInboxQueue
from inbox import savePostToInboxQueue
from follow import getFollowingFeed
from follow import outboxUndoFollow
from auth import authorize
from auth import createPassword
from threads import threadWithTrace
from media import getMediaPath
from media import createMediaDirs
from delete import outboxDelete
import os
import sys

# maximum number of posts to list in outbox feed
maxPostsInFeed=20

# number of follows/followers per page
followsPerPage=12

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
    def _set_headers(self,fileFormat: str) -> None:
        self.send_response(200)
        self.send_header('Content-type', fileFormat)
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
        wfResult=webfingerLookup(self.path,self.server.baseDir)
        if wfResult:
            self._set_headers('application/jrd+json')
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
                            self.server.httpPrefix+'://'+self.server.domain+'/'+mediaPath
                
        permittedOutboxTypes=[
            'Create','Announce','Like','Follow','Undo', \
            'Update','Add','Remove','Block','Delete'
        ]
        if messageJson['type'] not in permittedOutboxTypes:
            if self.server.debug:
                print('DEBUG: POST to outbox - '+messageJson['type']+ \
                      ' is not a permitted activity type')
            return False
        if messageJson.get('id'):
            postId=messageJson['id'].replace('/activity','')
        else:
            postId=None
        if self.server.debug:
            pprint(messageJson)
            print('DEBUG: savePostToBox')
        savePostToBox(self.server.baseDir, \
                      self.server.httpPrefix, \
                      postId, \
                      self.postToNickname, \
                      self.server.domain,messageJson,'outbox')
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
                        messageJson,self.server.debug)
        if self.server.debug:
            print('DEBUG: handle any unfollow requests')
        outboxUndoFollow(self.server.baseDir,messageJson,self.server.debug)
        if not self.server.nodeletion:
            if self.server.debug:
                print('DEBUG: handle delete requests')
            outboxDelete(self.server.baseDir,self.server.httpPrefix,messageJson,self.server.debug)
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
                             messageJson,self.server.debug)
        return True

    def _updateInboxQueue(self,nickname: str,messageJson: {}) -> int:
        """Update the inbox queue
        """
        # Check if the queue is full
        if len(self.server.inboxQueue)>=self.server.maxQueueLength:
            return 1

        # save the json for later queue processing
        queueFilename = \
            savePostToInboxQueue(self.server.baseDir, \
                                 self.server.httpPrefix, \
                                 nickname, \
                                 self.server.domain, \
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
        if self.server.GETbusy:
            currTimeGET=int(time.time())
            if currTimeGET-self.server.lastGET<10:
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
        # show media
        if '/media/' in self.path:
            if self.path.endswith('.png') or \
               self.path.endswith('.jpg') or \
               self.path.endswith('.gif'):
                mediaStr=self.path.split('/media/')[1]
                mediaFilename= \
                    self.server.baseDir+'/media/'+mediaStr
                if os.path.isfile(mediaFilename):
                    if mediaFilename.endswith('.png'):
                        self._set_headers('image/png')
                    elif mediaFilename.endswith('.jpg'):
                        self._set_headers('image/jpeg')
                    else:
                        self._set_headers('image/gif')
                    with open(mediaFilename, 'rb') as avFile:
                        mediaBinary = avFile.read()
                        self.wfile.write(mediaBinary)
                    self.server.GETbusy=False
                    return        
            self._404()
            self.server.GETbusy=False
            return
        # show avatar or background image
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
                            self._set_headers('image/png')
                        elif avatarFile.endswith('.jpg'):
                            self._set_headers('image/jpeg')
                        else:
                            self._set_headers('image/gif')
                        with open(avatarFilename, 'rb') as avFile:
                            avBinary = avFile.read()
                            self.wfile.write(avBinary)
                        self.server.GETbusy=False
                        return                    
        # get an individual post from the path /@nickname/statusnumber
        if '/@' in self.path:
            namedStatus=self.path.split('/@')[1]
            if '/' in namedStatus:
                postSections=namedStatus.split('/')
                if len(postSections)==2:
                    nickname=postSections[0]
                    statusNumber=postSections[1]
                    if len(statusNumber)>10 and statusNumber.isdigit():
                        domainFull=self.server.domain
                        if self.server.port!=80 and self.server.port!=443:
                            domainFull=self.server.domain+':'+str(self.server.port) 
                            postFilename= \
                                self.server.baseDir+'/accounts/'+nickname+'@'+self.server.domain+'/outbox/'+ \
                                self.server.httpPrefix+':##'+domainFull+'#users#'+nickname+'#statuses#'+statusNumber+'.json'
                            if os.path.isfile(postFilename):
                                postJsonObject={}
                                with open(postFilename, 'r') as fp:
                                    postJsonObject=commentjson.load(fp)
                                    # Only authorized viewers get to see likes on posts
                                    # Otherwize marketers could gain more social graph info
                                    if not self._isAuthorized():
                                        if postJsonObject.get('likes'):
                                            postJsonObject['likes']={}
                                    self._set_headers('application/json')
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
                                domainFull=self.server.domain
                                if self.server.port!=80 and self.server.port!=443:
                                    domainFull=self.server.domain+':'+str(self.server.port)
                                boxname='outbox'
                                postDir=self.server.baseDir+'/accounts/'+nickname+'@'+self.server.domain+'/'+boxname
                                postRepliesFilename= \
                                    postDir+'/'+ \
                                    self.server.httpPrefix+':##'+domainFull+'#users#'+nickname+'#statuses#'+statusNumber+'.replies'
                                if not os.path.isfile(postRepliesFilename):
                                    # There are no replies, so show empty collection
                                    repliesJson = {
                                        '@context': 'https://www.w3.org/ns/activitystreams',
                                        'first': self.server.httpPrefix+'://'+domainFull+'/users/'+nickname+'/statuses/'+statusNumber+'/replies?page=true',
                                        'id': self.server.httpPrefix+'://'+domainFull+'/users/'+nickname+'/statuses/'+statusNumber+'/replies',
                                        'last': self.server.httpPrefix+'://'+domainFull+'/users/'+nickname+'/statuses/'+statusNumber+'/replies?page=true',
                                        'totalItems': 0,
                                        'type': 'OrderedCollection'}
                                    self._set_headers('application/json')
                                    self.wfile.write(json.dumps(repliesJson).encode('utf-8'))
                                    self.server.GETbusy=False
                                    return
                                else:
                                    # replies exist. Itterate through the text file containing message ids
                                    repliesJson = {
                                        '@context': 'https://www.w3.org/ns/activitystreams',
                                        'id': self.server.httpPrefix+'://'+domainFull+'/users/'+nickname+'/statuses/'+statusNumber+'?page=true',
                                        'orderedItems': [
                                        ],
                                        'partOf': self.server.httpPrefix+'://'+domainFull+'/users/'+nickname+'/statuses/'+statusNumber,
                                        'type': 'OrderedCollectionPage'}
                                    # some messages could be private, so check authorization state
                                    authorized=self._isAuthorized()
                                    # populate the items list with replies
                                    repliesBoxes=['outbox','inbox']
                                    with open(postRepliesFilename,'r') as repliesFile: 
                                        for messageId in repliesFile:
                                            replyFound=False
                                            # examine inbox and outbox
                                            for boxname in repliesBoxes:
                                                searchFilename= \
                                                    self.server.baseDir+ \
                                                    '/accounts/'+nickname+'@'+ \
                                                    self.server.domain+'/'+ \
                                                    boxname+'/'+ \
                                                    messageId.replace('\n','').replace('/','#')+'.json'
                                                if os.path.isfile(searchFilename):
                                                    if authorized or \
                                                       'https://www.w3.org/ns/activitystreams#Public' in open(searchFilename).read():
                                                        with open(searchFilename, 'r') as fp:
                                                            postJsonObject=commentjson.load(fp)
                                                            if postJsonObject['object'].get('cc'):                                                            
                                                                if authorized or \
                                                                   ('https://www.w3.org/ns/activitystreams#Public' in postJsonObject['object']['to'] or \
                                                                    'https://www.w3.org/ns/activitystreams#Public' in postJsonObject['object']['cc']):
                                                                    repliesJson['orderedItems'].append(postJsonObject)
                                                                    replyFound=True
                                                            else:
                                                                if authorized or \
                                                                   'https://www.w3.org/ns/activitystreams#Public' in postJsonObject['object']['to']:
                                                                    repliesJson['orderedItems'].append(postJsonObject)
                                                                    replyFound=True
                                                    break
                                            # if not in either inbox or outbox then examine the shared inbox
                                            if not replyFound:
                                                searchFilename= \
                                                    self.server.baseDir+ \
                                                    '/accounts/inbox@'+ \
                                                    self.server.domain+'/inbox/'+ \
                                                    messageId.replace('\n','').replace('/','#')+'.json'
                                                if os.path.isfile(searchFilename):
                                                    if authorized or \
                                                       'https://www.w3.org/ns/activitystreams#Public' in open(searchFilename).read():
                                                        # get the json of the reply and append it to the collection
                                                        with open(searchFilename, 'r') as fp:
                                                            postJsonObject=commentjson.load(fp)
                                                            if postJsonObject['object'].get('cc'):                                                            
                                                                if authorized or \
                                                                   ('https://www.w3.org/ns/activitystreams#Public' in postJsonObject['object']['to'] or \
                                                                    'https://www.w3.org/ns/activitystreams#Public' in postJsonObject['object']['cc']):
                                                                    repliesJson['orderedItems'].append(postJsonObject)
                                                            else:
                                                                if authorized or \
                                                                   'https://www.w3.org/ns/activitystreams#Public' in postJsonObject['object']['to']:
                                                                    repliesJson['orderedItems'].append(postJsonObject)
                                    # send the replies json
                                    self._set_headers('application/json')
                                    self.wfile.write(json.dumps(repliesJson).encode('utf-8'))
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
                        domainFull=self.server.domain
                        if self.server.port!=80 and self.server.port!=443:
                            domainFull=self.server.domain+':'+str(self.server.port) 
                            postFilename= \
                                self.server.baseDir+'/accounts/'+nickname+'@'+self.server.domain+'/outbox/'+ \
                                self.server.httpPrefix+':##'+domainFull+'#users#'+nickname+'#statuses#'+statusNumber+'.json'
                            if os.path.isfile(postFilename):
                                postJsonObject={}
                                with open(postFilename, 'r') as fp:
                                    postJsonObject=commentjson.load(fp)
                                    # Only authorized viewers get to see likes on posts
                                    # Otherwize marketers could gain more social graph info
                                    if not self._isAuthorized():
                                        if postJsonObject.get('likes'):
                                            postJsonObject['likes']={}                                    
                                    self._set_headers('application/json')
                                    self.wfile.write(json.dumps(postJsonObject).encode('utf-8'))
                                self.server.GETbusy=False
                                return
                            else:
                                self._404()
                                self.server.GETbusy=False
                                return
        # get the inbox for a given person
        if self.path.endswith('/inbox'):
            if '/users/' in self.path:
                if self._isAuthorized():
                    inboxFeed=personBoxJson(self.server.baseDir, \
                                            self.server.domain, \
                                            self.server.port, \
                                            self.path, \
                                            self.server.httpPrefix, \
                                            maxPostsInFeed, 'inbox', \
                                            True,self.server.ocapAlways)
                    if inboxFeed:
                        self._set_headers('application/json')
                        self.wfile.write(json.dumps(inboxFeed).encode('utf-8'))
                        self.server.GETbusy=False
                        return
                else:
                    if self.server.debug:
                        print('DEBUG: '+nickname+ \
                              ' was not authorized to access '+self.path)
            if self.server.debug:
                print('DEBUG: GET access to inbox is unauthorized')
            self.send_response(405)
            self.end_headers()
            self.server.POSTbusy=False
            return
        
        # get outbox feed for a person
        outboxFeed=personBoxJson(self.server.baseDir,self.server.domain, \
                                 self.server.port,self.path, \
                                 self.server.httpPrefix, \
                                 maxPostsInFeed, 'outbox', \
                                 self._isAuthorized(), \
                                 self.server.ocapAlways)
        if outboxFeed:
            self._set_headers('application/json')
            self.wfile.write(json.dumps(outboxFeed).encode('utf-8'))
            self.server.GETbusy=False
            return
        following=getFollowingFeed(self.server.baseDir,self.server.domain, \
                                   self.server.port,self.path, \
                                   self.server.httpPrefix,followsPerPage)
        if following:
            self._set_headers('application/json')
            self.wfile.write(json.dumps(following).encode('utf-8'))
            self.server.GETbusy=False
            return            
        followers=getFollowingFeed(self.server.baseDir,self.server.domain, \
                                   self.server.port,self.path, \
                                   self.server.httpPrefix, \
                                   followsPerPage,'followers')
        if followers:
            self._set_headers('application/json')
            self.wfile.write(json.dumps(followers).encode('utf-8'))
            self.server.GETbusy=False
            return
        # look up a person
        getPerson = personLookup(self.server.domain,self.path, \
                                 self.server.baseDir)
        if getPerson:
            self._set_headers('application/json')
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
            self._set_headers('application/json')
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
        self._set_headers('application/json')

    def do_POST(self):
        if self.server.debug:
            print('DEBUG: POST to from '+self.server.baseDir+ \
                  ' path: '+self.path+' busy: '+ \
                  str(self.server.POSTbusy))
        if self.server.POSTbusy:
            currTimePOST=int(time.time())
            if currTimePOST-self.server.lastPOST<10:
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
        self.path=self.path.replace('/outbox/','/outbox').replace('/inbox/','/inbox').replace('/sharedInbox/','/sharedInbox')

        # if this is a POST to teh outbox then check authentication
        self.outboxAuthenticated=False
        self.postToNickname=None
                
        if self.path.endswith('/outbox'):
            if '/users/' in self.path:
                if self._isAuthorized():
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
                self.send_response(400)
                self.end_headers()
                self.server.POSTbusy=False
                return
        else:
            if length>self.server.maxImageSize:
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
        if self.headers['Content-type'] != 'application/json':
            print("POST is not json: "+self.headers['Content-type'])
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
            self.send_response(403)
            self.end_headers()
            self.server.POSTbusy=False
            return
        else:
            if self.path == '/sharedInbox' or self.path == '/inbox':
                print('DEBUG: POST to shared inbox')
                queueStatus-_updateInboxQueue('inbox',messageJson)
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

def runDaemon(clientToServer: bool,baseDir: str,domain: str, \
              port=80,httpPrefix='https', \
              fedList=[],noreply=False,nolike=False,nopics=False, \
              noannounce=False,cw=False,ocapAlways=False, \
              useTor=False,maxReplies=64, \
              domainMaxPostsPerDay=8640,accountMaxPostsPerDay=8640, \
              nodeletion=False,debug=False) -> None:
    if len(domain)==0:
        domain='localhost'
    if '.' not in domain:
        if domain != 'localhost':
            print('Invalid domain: ' + domain)
            return

    serverAddress = ('', port)
    httpd = ThreadingHTTPServer(serverAddress, PubServer)
    httpd.domain=domain
    httpd.port=port
    httpd.httpPrefix=httpPrefix
    httpd.debug=debug
    httpd.federationList=fedList.copy()
    httpd.baseDir=baseDir
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
    httpd.nodeletion=nodeletion
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

    print('Creating shared inbox: inbox@'+domain)
    createSharedInbox(baseDir,'inbox',domain,port,httpPrefix)

    print('Creating inbox queue')
    httpd.thrInboxQueue= \
        threadWithTrace(target=runInboxQueue, \
                        args=(baseDir,httpPrefix,httpd.sendThreads, \
                              httpd.postLog,httpd.cachedWebfingers, \
                              httpd.personCache,httpd.inboxQueue, \
                              domain,port,useTor,httpd.federationList, \
                              httpd.ocapAlways,maxReplies, \
                              domainMaxPostsPerDay,accountMaxPostsPerDay, \
                              nodeletion,debug,httpd.acceptedCaps),daemon=True)
    httpd.thrInboxQueue.start()
    if clientToServer:
        print('Running ActivityPub client on ' + domain + ' port ' + str(port))
    else:
        print('Running ActivityPub server on ' + domain + ' port ' + str(port))
    httpd.serve_forever()
