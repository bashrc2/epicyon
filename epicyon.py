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
parser.add_argument('-p','--port', dest='port', type=int,default=80,
                    help='Port number to run on')
parser.add_argument('--path', dest='baseDir', type=str,default=os.getcwd(),
                    help='Directory in which to store posts')
parser.add_argument('-f','--federate', nargs='+',dest='federationList',
                    help='Specify federation list separated by spaces')
parser.add_argument("--https", type=str2bool, nargs='?',
                        const=True, default=False,
                        help="Use https")
parser.add_argument("--tor", type=str2bool, nargs='?',
                        const=True, default=False,
                        help="Route via Tor")
parser.add_argument("--tests", type=str2bool, nargs='?',
                        const=True, default=False,
                        help="Run unit tests")
args = parser.parse_args()
if args.tests:
    runAllTests()
    sys.exit()
    
print(args.domain)
print(str(args.federationList))

nickname='admin'
domain=args.domain
port=args.port
https=args.https
useTor=args.tor
baseDir=args.baseDir
if baseDir.endswith('/'):
    print("--path option should not end with '/'")
    sys.exit()

federationList=[]
if args.federationList:
    federationList=args.federationList.copy()

session = createSession(domain,port,useTor)
personCache={}
cachedWebfingers={}

privateKeyPem,publicKeyPem,person,wfEndpoint=createPerson(baseDir,nickname,domain,port,https,True)
#deleteAllPosts(baseDir,nickname,domain)
setPreferredNickname(baseDir,nickname,domain,'badger')
setBio(baseDir,nickname,domain,'Some personal info')
#createPublicPost(baseDir,nickname, domain, port,https, "G'day world!", False, True, None, None, 'Not suitable for Vogons')
#archivePosts(nickname,domain,baseDir,4)
#outboxJson=createOutbox(baseDir,nickname,domain,port,https,2,True,None)
#pprint(outboxJson)

#testPostMessageBetweenServers()
runDaemon(domain,port,https,federationList,useTor)

#testHttpsig()
sys.exit()

#pprint(person)
#print('\n')
#pprint(wfEndpoint)

handle="https://mastodon.social/@Gargron"
wfRequest = webfingerHandle(session,handle,True,cachedWebfingers)
if not wfRequest:
    sys.exit()

personUrl,pubKeyId,pubKey,personId=getPersonBox(session,wfRequest,personCache,'outbox')
#pprint(personUrl)
#sys.exit()

wfResult = json.dumps(wfRequest, indent=4, sort_keys=True)
#print(str(wfResult))
#sys.exit()

maxMentions=10
maxEmoji=10
maxAttachments=5
userPosts = getPosts(session,personUrl,30,maxMentions,maxEmoji,maxAttachments,federationList,personCache)
#print(str(userPosts))
