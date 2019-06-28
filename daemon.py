__filename__ = "daemon.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "0.0.1"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

from http.server import BaseHTTPRequestHandler, HTTPServer
#import socketserver
import json
import cgi
from pprint import pprint
from session import createSession
from httpsig import testHttpsig
from webfinger import webfingerMeta
from webfinger import webfingerLookup
from person import personLookup
from person import personKeyLookup
from inbox import inboxPermittedMessage
import os
import sys

# domain name of this server
thisDomain=''

# List of domains to federate with
federationList=[]

# Avoid giant messages
maxMessageLength=5000

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
        if not self.path.startswith('/.well-known'):
            return False

        if self.path.startswith('/.well-known/host-meta'):
            wfResult=webfingerMeta()
            if wfResult:
                self._set_headers('application/xrd+xml')
                self.wfile.write(wfResult.encode('utf-8'))
            return

        wfResult=webfingerLookup(self.path)
        if wfResult:
            self._set_headers('application/json')
            self.wfile.write(json.dumps(wfResult).encode('utf-8'))
        else:
            self._404()
        return True

    def _permittedDir(self,path):
        if path.startswith('/wfendpoints') or \
           path.startswith('/keys') or \
           path.startswith('/accounts'):
            return False
        return True

    def do_GET(self):
        if not self._permittedDir(self.path):
            self._404()
            return
        # get webfinger endpoint for a person
        if self._webfinger():
            return
        # look up a person
        getPerson = personLookup(thisDomain,self.path)
        if getPerson:
            self._set_headers('application/json')
            self.wfile.write(json.dumps(getPerson).encode('utf-8'))
            return
        getPersonKey = personKeyLookup(thisDomain,self.path)
        if getPersonKey:
            self._set_headers('text/html; charset=utf-8')
            self.wfile.write(getPersonKey.encode('utf-8'))
            return
        # check that a json file was requested
        baseDir=os.getcwd()
        if not self.path.endswith('.json'):
            self._404()
            return
        # check that the file exists
        filename=baseDir+self.path
        if os.path.isfile(filename):
            self._set_headers('application/json')
            with open(filename, 'r', encoding='utf8') as File:
                content = File.read()
                contentJson=json.loads(content)
                self.wfile.write(json.dumps(contentJson).encode('utf8'))
        else:
            self._404()

    def do_HEAD(self):
        self._set_headers('application/json')
        
    def do_POST(self):
        ctype, pdict = cgi.parse_header(self.headers.getheader('content-type'))
        
        # refuse to receive non-json content
        if ctype != 'application/json':
            self.send_response(400)
            self.end_headers()
            return
            
        # read the message and convert it into a python dictionary
        length = int(self.headers.getheader('content-length'))
        if length>maxMessageLength:
            self.send_response(400)
            self.end_headers()
            return
        message = json.loads(self.rfile.read(length))        

        if not inboxPermittedMessage(message,federationList):
            self.send_response(403)
            self.end_headers()
        else:                
            # add a property to the object, just to mess with data
            message['received'] = 'ok'
        
            # send the message back
            self._set_headers('application/json')
            self.wfile.write(json.dumps(message).encode('utf-8'))

def runDaemon(domain: str,port=80,fedList=[],useTor=False) -> None:
    global thisDomain
    global federationList
    thisDomain=domain
    federationList=fedList.copy()

    if len(domain)==0:
        domain='127.0.0.1'
    if '.' not in domain:
        print('Invalid domain: ' + domain)
        return
    session = createSession(useTor)

    print('Running tests...')
    testHttpsig()
    print('Tests succeeded\n')

    serverAddress = ('', port)
    httpd = HTTPServer(serverAddress, PubServer)
    print('Running ActivityPub daemon on ' + thisDomain + ' port ' + str(port))
    httpd.serve_forever()
