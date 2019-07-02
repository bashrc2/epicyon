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
from person import personKeyLookup
from person import personOutboxJson
from posts import getPersonPubKey
from inbox import inboxPermittedMessage
from inbox import inboxMessageHasParams
from follow import getFollowingFeed
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
            username,domain = parseHandle(u)
            if username:
                followlist.append(username+'@'+domain)
    followUsers.close()
    return followlist

class PubServer(BaseHTTPRequestHandler):
    def _set_headers(self,fileFormat):
        self.send_response(200)
        self.send_header('Content-type', fileFormat)
        self.end_headers()

    def _404(self):
        self.send_response(404)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write("<html><head></head><body><h1>404 Not Found</h1></body></html>".encode('utf-8'))

    def _webfinger(self) -> bool:
        print('############### _webfinger well-known')
        if not self.path.startswith('/.well-known'):
            return False

        print('############### _webfinger host-meta')
        if self.path.startswith('/.well-known/host-meta'):
            wfResult=webfingerMeta()
            if wfResult:
                self._set_headers('application/xrd+xml')
                self.wfile.write(wfResult.encode('utf-8'))
            return

        print('############### _webfinger lookup '+self.path+' '+str(self.server.baseDir))
        wfResult=webfingerLookup(self.path,self.server.baseDir)
        if wfResult:
            self._set_headers('application/jrd+json')
            self.wfile.write(json.dumps(wfResult).encode('utf-8'))
        else:
            print('############### _webfinger lookup 404 '+self.path)
            self._404()
        return True

    def _permittedDir(self,path):
        if path.startswith('/wfendpoints') or \
           path.startswith('/keys') or \
           path.startswith('/accounts'):
            return False
        return True

    def do_GET(self):
        print('############### GET from '+self.server.baseDir+' path: '+self.path)
        if self.server.GETbusy:
            currTimeGET=int(time.time())
            if currTimeGET-self.server.lastGET<10:
                print('############### Busy')
                self.send_response(429)
                self.end_headers()
                return
            self.server.lastGET=currTimeGET
        self.server.GETbusy=True

        print('############### _permittedDir')
        if not self._permittedDir(self.path):
            print('############# Not permitted')
            self._404()
            self.server.GETbusy=False
            return
        # get webfinger endpoint for a person
        print('############### _webfinger')
        if self._webfinger():
            self.server.GETbusy=False
            return
        print('############### _webfinger end')
        # get outbox feed for a person
        outboxFeed=personOutboxJson(self.server.baseDir,self.server.domain, \
                                    self.server.port,self.path, \
                                    self.server.https,maxPostsInFeed)
        if outboxFeed:
            self._set_headers('application/json')
            self.wfile.write(json.dumps(outboxFeed).encode('utf-8'))
            self.server.GETbusy=False
            return
        following=getFollowingFeed(self.server.baseDir,self.server.domain, \
                                   self.server.port,self.path, \
                                   self.server.https,followsPerPage)
        if following:
            self._set_headers('application/json')
            self.wfile.write(json.dumps(following).encode('utf-8'))
            self.server.GETbusy=False
            return            
        followers=getFollowingFeed(self.server.baseDir,self.server.domain, \
                                   self.server.port,self.path, \
                                   self.server.https,followsPerPage,'followers')
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
        personKey = personKeyLookup(self.server.domain,self.path, \
                                    self.server.baseDir)
        if personKey:
            self._set_headers('text/html; charset=utf-8')
            self.wfile.write(personKey.encode('utf-8'))
            self.server.GETbusy=False
            return
        # check that a json file was requested
        if not self.path.endswith('.json'):
            print('############# Not json: '+self.path+' '+self.server.baseDir)
            self._404()
            self.server.GETbusy=False
            return
        # check that the file exists
        filename=self.server.baseDir+self.path
        if os.path.isfile(filename):
            self._set_headers('application/json')
            with open(filename, 'r', encoding='utf8') as File:
                content = File.read()
                contentJson=json.loads(content)
                self.wfile.write(json.dumps(contentJson).encode('utf8'))
        else:
            print('############# Unknown file')
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
        print('**************** POST ready to receive')
        self.server.POSTbusy=True
        if not self.headers.get('Content-type'):
            print('**************** No Content-type')
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy=False
            return
        print('*****************headers: '+str(self.headers))
        
        # refuse to receive non-json content
        if self.headers['Content-type'] != 'application/json':
            print("**************** That's no Json!")
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy=False
            return
            
        # read the message and convert it into a python dictionary
        length = int(self.headers['Content-length'])
        print('**************** content-length: '+str(length))
        if length>maxMessageLength:
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy=False
            return
        print('**************** Reading message')
        messageBytes=self.rfile.read(length)
        messageJson = json.loads(messageBytes)

        # check the necessary properties are available
        print('**************** Check message has params')
        if not inboxMessageHasParams(messageJson):
            self.send_response(403)
            self.end_headers()
            self.server.POSTbusy=False
            return

        if not inboxPermittedMessage(self.server.domain,messageJson,self.server.federationList):
            print('**************** Ah Ah Ah')
            self.send_response(403)
            self.end_headers()
            self.server.POSTbusy=False
            return

        pprint(messageJson)

        print('**************** POST create session')
        currSessionTime=int(time.time())
        if currSessionTime-self.server.sessionLastUpdate>1200:
            self.server.sessionLastUpdate=currSessionTime
            self.server.session = \
                createSession(self.server.domain,self.server.port, \
                              self.server.useTor)
            print('**************** POST started new session')

        print('**************** POST get actor url from '+self.server.baseDir)
        personUrl=messageJson['actor']
        print('**************** POST get public key of '+personUrl+' from '+self.server.baseDir)
        pubKey=getPersonPubKey(self.server.session,personUrl, \
                               self.server.personCache)
        if not pubKey:
            print('**************** POST no sender public key')
            self.send_response(401)
            self.end_headers()
            self.server.POSTbusy=False
            return
        print('**************** POST check signature')
        if not verifyPostHeaders(self.server.https, pubKey, self.headers, \
                                 '/inbox' ,False, json.dumps(messageJson)):
            print('**************** POST signature verification failed')
            self.send_response(401)
            self.end_headers()
            self.server.POSTbusy=False
            return            
        print('**************** POST valid')
        if receiveFollowRequest(self.server.baseDir,messageJson, \
                                self.server.federationList):
            self.send_response(200)
            self.end_headers()
            self.server.POSTbusy=False
            return            

        pprint(messageJson)
        # add a property to the object, just to mess with data
        #message['received'] = 'ok'
        
        # send the message back
        #self._set_headers('application/json')
        #self.wfile.write(json.dumps(message).encode('utf-8'))

        self.server.receivedMessage=True
        self.send_response(200)
        self.end_headers()
        self.server.POSTbusy=False

def runDaemon(domain: str,port=80,https=True,fedList=[],useTor=False) -> None:
    if len(domain)==0:
        domain='127.0.0.1'
    if '.' not in domain:
        print('Invalid domain: ' + domain)
        return

    serverAddress = (domain, port)
    httpd = ThreadingHTTPServer(serverAddress, PubServer)
    httpd.domain=domain
    httpd.port=port
    httpd.https=https
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
    print('Running ActivityPub daemon on ' + domain + ' port ' + str(port))
    httpd.serve_forever()
