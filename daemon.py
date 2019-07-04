__filename__ = "daemon.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "0.0.1"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
#import socketserver
import json
import time
from pprint import pprint
from session import createSession
from webfinger import webfingerMeta
from webfinger import webfingerLookup
from webfinger import webfingerHandle
from person import personLookup
from person import personBoxJson
from posts import getPersonPubKey
from posts import outboxMessageCreateWrap
from posts import savePostToBox
from inbox import inboxPermittedMessage
from inbox import inboxMessageHasParams
from inbox import runInboxQueue
from inbox import savePostToInboxQueue
from follow import getFollowingFeed
from auth import authorize
from threads import threadWithTrace
import os
import sys

# Avoid giant messages
maxMessageLength=5000

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

    def _postToOutbox(messageJson: {}) -> bool:
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
                                            self.server.domain,messageJson)
        if messageJson['type']=='Create':
            if not (messageJson.get('id') and \
                    messageJson.get('type') and \
                    messageJson.get('actor') and \
                    messageJson.get('object') and \
                    messageJson.get('atomUri') and \
                    messageJson.get('to')):
                if self.server.debug:
                    print('DEBUG: POST to outbox - Create does not have the required parameters')
                return False
            # https://www.w3.org/TR/activitypub/#create-activity-outbox
            messageJson['object']['attributedTo']=messageJson['actor']
        permittedOutboxTypes=['Create','Announce','Like','Follow','Undo','Update','Add','Remove','Block','Delete']
        if messageJson['type'] not in permittedOutboxTypes:
            if self.server.debug:
                print('DEBUG: POST to outbox - '+messageJson['type']+' is not a permitted activity type')
            return False
        if messageJson.get('id'):
            postId=messageJson['id']
        else:
            postId=None
        savePostToBox(self.server.baseDir,postId,self.postToNickname,self.server.domain,messageJson,'outbox')
        return True

    def do_GET(self):
        if self.server.debug:
            print('DEBUG: GET from '+self.server.baseDir+' path: '+self.path)
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

        if self.server.debug:
            print('DEBUG: GET _permittedDir')
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
        # get the inbox for a given person
        if self.path.endswith('/inbox'):
            if '/users/' in self.path:
                if self.headers.get('Authorization'):
                    if authorize(self.server.baseDir,self.path, \
                                 self.headers['Authorization'], \
                                 self.server.debug):
                        inboxFeed=personBoxJson(self.server.baseDir, \
                                                self.server.domain, \
                                                self.server.port, \
                                                self.path, \
                                                self.server.httpPrefix, \
                                                maxPostsInFeed, 'inbox')
                        if inboxFeed:
                            self._set_headers('application/json')
                            self.wfile.write(json.dumps(inboxFeed).encode('utf-8'))
                            self.server.GETbusy=False
                            return
                    else:
                        if self.server.debug:
                            print('DEBUG: '+nickname+' was not authorized to access '+self.path)
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
                                 maxPostsInFeed, 'outbox')
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
                                   self.server.httpPrefix,followsPerPage,'followers')
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
        
        # refuse to receive non-json content
        if self.headers['Content-type'] != 'application/json':
            print("POST is not json: "+self.headers['Content-type'])
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy=False
            return

        # remove any trailing slashes from the path
        self.path=self.path.replace('/outbox/','/outbox').replace('/inbox/','/inbox')

        # if this is a POST to teh outbox then check authentication
        self.outboxAuthenticated=False
        self.postToNickname=None
                
        if self.path.endswith('/outbox'):
            if '/users/' in self.path:
                if self.headers.get('Authorization'):
                    if authorize(self.server.baseDir,self.path,self.headers['Authorization'],self.server.debug):
                        self.outboxAuthenticated=True
                        pathUsersSection=path.split('/users/')[1]
                        self.postToNickname=pathUsersSection.split('/')[0]
                        # TODO
                        print('c2s posts not supported yet')
                        self.send_response(405)
                        self.end_headers()
                        self.server.POSTbusy=False
                        return
            if not self.outboxAuthenticated:
                self.send_response(405)
                self.end_headers()
                self.server.POSTbusy=False
                return

        # check that the post is to an expected path
        if not (self.path.endswith('/outbox') or self.path.endswith('/inbox')):
            print('Attempt to POST to invalid path '+self.path)
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy=False
            return

        # read the message and convert it into a python dictionary
        length = int(self.headers['Content-length'])
        if self.server.debug:
            print('DEBUG: content-length: '+str(length))
        if length>maxMessageLength:
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy=False
            return

        if self.server.debug:
            print('DEBUG: Reading message')

        messageBytes=self.rfile.read(length)
        messageJson = json.loads(messageBytes)

        # https://www.w3.org/TR/activitypub/#object-without-create
        if self.outboxAuthenticated:
            if self._postToOutbox(messageJson):
                self.send_header('Location',messageJson['object']['atomUri'])
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

        if self.path.endswith('/inbox'):
            if not inboxMessageHasParams(messageJson):
                self.send_response(403)
                self.end_headers()
                self.server.POSTbusy=False
                return

        if not inboxPermittedMessage(self.server.domain,messageJson,self.server.federationList):
            if self.server.debug:
                print('DEBUG: Ah Ah Ah')
            self.send_response(403)
            self.end_headers()
            self.server.POSTbusy=False
            return

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
            print('DEBUG: POST saving to inbox cache')
        if '/users/' in self.path:
            pathUsersSection=self.path.split('/users/')[1]
            if '/' not in pathUsersSection:
                if self.server.debug:
                    print('DEBUG: This is not a users endpoint')
            else:
                self.postToNickname=pathUsersSection.split('/')[0]
                if self.postToNickname:
                    cacheFilename = \
                        savePostToInboxQueue(self.server.baseDir, \
                                             self.server.httpPrefix, \
                                             self.postToNickname, \
                                             self.server.domain, \
                                             messageJson,
                                             self.headers['signature'])
                    if cacheFilename:
                        if cacheFilename not in self.server.inboxQueue:
                            self.server.inboxQueue.append(cacheFilename)
                        self.send_response(201)
                        self.end_headers()
                        self.server.POSTbusy=False
                        return
            self.send_response(403)
            self.end_headers()
            self.server.POSTbusy=False
            return
        else:
            print('DEBUG: POST to shared inbox')
            self.send_response(201)
            self.end_headers()
            self.server.POSTbusy=False
            return

def runDaemon(baseDir: str,domain: str,port=80,httpPrefix='https',fedList=[],useTor=False,debug=False) -> None:
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
    httpd.baseDir=os.getcwd()
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
    print('Running ActivityPub daemon on ' + domain + ' port ' + str(port))
    httpd.thrInboxQueue=threadWithTrace(target=runInboxQueue,args=(baseDir,httpPrefix,httpd.personCache,httpd.inboxQueue,domain,port,useTor,httpd.federationList,debug),daemon=True)
    httpd.thrInboxQueue.start()
    httpd.serve_forever()
