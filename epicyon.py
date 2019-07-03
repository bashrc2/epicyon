__filename__ = "epicyon.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "0.0.1"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

from person import createPerson
from person import setPreferredNickname
from person import setBio
from webfinger import webfingerHandle
from posts import getPosts
from posts import createPublicPost
from posts import deleteAllPosts
from posts import createOutbox
from posts import archivePosts
from posts import sendPost
from posts import getPersonBox
from posts import getPublicPostsOfPerson
from session import createSession
from session import getJson
import json
import os
import sys
import requests
from pprint import pprint
from tests import testHttpsig
from daemon import runDaemon
import socket
from follow import clearFollows
from follow import clearFollowers
from follow import followPerson
from follow import followerOfPerson
from follow import unfollowPerson
from follow import unfollowerOfPerson
from tests import testPostMessageBetweenServers
from tests import runAllTests
import argparse

def str2bool(v):
    if isinstance(v, bool):
       return v
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')
    
parser = argparse.ArgumentParser(description='ActivityPub Server')
parser.add_argument('-d','--domain', dest='domain', type=str,default='localhost',
                    help='Domain name of the server')
parser.add_argument('-p','--port', dest='port', type=int,default=8085,
                    help='Port number to run on')
parser.add_argument('--path', dest='baseDir', type=str,default=os.getcwd(),
                    help='Directory in which to store posts')
parser.add_argument('--posts', dest='posts', type=str,default=None,
                    help='Show posts for the given handle')
parser.add_argument('--postsraw', dest='postsraw', type=str,default=None,
                    help='Show raw json of posts for the given handle')
parser.add_argument('-f','--federate', nargs='+',dest='federationList',
                    help='Specify federation list separated by spaces')
parser.add_argument("--debug", type=str2bool, nargs='?',
                        const=True, default=False,
                        help="Show debug messages")
parser.add_argument("--http", type=str2bool, nargs='?',
                        const=True, default=False,
                        help="Use http only")
parser.add_argument("--dat", type=str2bool, nargs='?',
                        const=True, default=False,
                        help="Use dat protocol only")
parser.add_argument("--tor", type=str2bool, nargs='?',
                        const=True, default=False,
                        help="Route via Tor")
parser.add_argument("--tests", type=str2bool, nargs='?',
                        const=True, default=False,
                        help="Run unit tests")
parser.add_argument("--testsnetwork", type=str2bool, nargs='?',
                        const=True, default=False,
                        help="Run network unit tests")
args = parser.parse_args()

debug=False
if args.debug:
    debug=True

if args.tests:
    runAllTests()
    sys.exit()

if args.testsnetwork:
    print('Network Tests')
    testPostMessageBetweenServers()
    sys.exit()

if args.posts:
    nickname=args.posts.split('@')[0]
    domain=args.posts.split('@')[1]
    getPublicPostsOfPerson(nickname,domain,False,True)
    sys.exit()

if args.postsraw:
    nickname=args.postsraw.split('@')[0]
    domain=args.postsraw.split('@')[1]
    getPublicPostsOfPerson(nickname,domain,True,False)
    sys.exit()

if not args.domain:
    print('Specify a domain with --domain [name]')
    sys.exit()

nickname='admin'
domain=args.domain
port=args.port
httpPrefix='https'
if args.http:
    httpPrefix='http'
if args.dat:
    httpPrefix='dat'
useTor=args.tor
baseDir=args.baseDir
if baseDir.endswith('/'):
    print("--path option should not end with '/'")
    sys.exit()

federationList=[]
if args.federationList:
    federationList=args.federationList.copy()
    print('Federating with: '+str(federationList))

if not os.path.isdir(baseDir+'/accounts/'+nickname+'@'+domain):
    print('Creating default admin account '+nickname+'@'+domain)
    privateKeyPem,publicKeyPem,person,wfEndpoint=createPerson(baseDir,nickname,domain,port,httpPrefix,True)

runDaemon(domain,port,httpPrefix,federationList,useTor,debug)
