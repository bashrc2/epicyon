__filename__ = "epicyon.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "0.0.1"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

from person import createPerson
from person import createSharedInbox
from person import setPreferredNickname
from person import setBio
from webfinger import webfingerHandle
from posts import getPosts
from posts import createPublicPost
from posts import deleteAllPosts
from posts import createOutbox
from posts import archivePosts
from posts import sendPost
from posts import getPublicPostsOfPerson
from posts import getUserUrl
from session import createSession
from session import getJson
import json
import os
import shutil
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
from follow import getFollowersOfPerson
from tests import testPostMessageBetweenServers
from tests import runAllTests
from config import setConfigParam
from config import getConfigParam
from auth import storeBasicCredentials
from auth import removePassword
from auth import createPassword
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
parser.add_argument('-d','--domain', dest='domain', type=str,default=None,
                    help='Domain name of the server')
parser.add_argument('-p','--port', dest='port', type=int,default=None,
                    help='Port number to run on')
parser.add_argument('--path', dest='baseDir', type=str,default=os.getcwd(),
                    help='Directory in which to store posts')
parser.add_argument('-a','--addaccount', dest='addaccount', type=str,default=None,
                    help='Adds a new account')
parser.add_argument('-r','--rmaccount', dest='rmaccount', type=str,default=None,
                    help='Remove an account')
parser.add_argument('--pass','--password', dest='password', type=str,default=None,
                    help='Set a password for an account')
parser.add_argument('--chpass','--changepassword', nargs='+',dest='changepassword',
                    help='Change the password for an account')
parser.add_argument('--actor', dest='actor', type=str,default=None,
                    help='Show the json actor the given handle')
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
    if '@' not in args.posts:
        print('Syntax: --posts nickname@domain')
        sys.exit()        
    nickname=args.posts.split('@')[0]
    domain=args.posts.split('@')[1]
    getPublicPostsOfPerson(nickname,domain,False,True)
    sys.exit()

if args.postsraw:
    if '@' not in args.posts:
        print('Syntax: --postsraw nickname@domain')
        sys.exit()        
    nickname=args.postsraw.split('@')[0]
    domain=args.postsraw.split('@')[1]
    getPublicPostsOfPerson(nickname,domain,True,False)
    sys.exit()

baseDir=args.baseDir
if baseDir.endswith('/'):
    print("--path option should not end with '/'")
    sys.exit()

# get domain name from configuration
configDomain=getConfigParam(baseDir,'domain')
if configDomain:
    domain=configDomain
else:
    domain='localhost'

# get port number from configuration
configPort=getConfigParam(baseDir,'port')
if configPort:
    port=configPort
else:
    port=8085

nickname='admin'
if args.domain:
    domain=args.domain
    setConfigParam(baseDir,'domain',domain)
if args.port:
    port=args.port
    setConfigParam(baseDir,'port',port)
httpPrefix='https'
if args.http:
    httpPrefix='http'
if args.dat:
    httpPrefix='dat'
useTor=args.tor
if domain.endswith('.onion'):
    useTor=True

if args.actor:
    if '@' not in args.actor:
        print('Syntax: --actor nickname@domain')
        sys.exit()        
    nickname=args.actor.split('@')[0]
    domain=args.actor.split('@')[1].replace('\n','')
    wfCache={}
    if domain.endswith('.onion'):
        httpPrefix='http'
        port=80
    else:
        httpPrefix='https'
        port=443
    session = createSession(domain,port,useTor)
    wfRequest = webfingerHandle(session,nickname+'@'+domain,httpPrefix,wfCache)
    if not wfRequest:
        print('Unable to webfinger '+nickname+'@'+domain)
        sys.exit()
    asHeader = {'Accept': 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"'}
    personUrl = getUserUrl(wfRequest)
    personJson = getJson(session,personUrl,asHeader,None)
    if personJson:
        pprint(personJson)
    else:
        print('Failed to get '+personUrl)
    sys.exit()

if args.addaccount:
    if '@' in args.addaccount:
        nickname=args.addaccount.split('@')[0]
        domain=args.addaccount.split('@')[1]
    else:
        nickname=args.addaccount
        if not args.domain or not getConfigParam(baseDir,'domain'):
            print('Use the --domain option to set the domain name')
            sys.exit()
    if not args.password:
        print('Use the --password option to set the password for '+nickname)
        sys.exit()
    if len(args.password.strip())<8:
        print('Password should be at least 8 characters')
        sys.exit()            
    if os.path.isdir(baseDir+'/accounts/'+nickname+'@'+domain):
        print('Account already exists')
        sys.exit()
    createPerson(baseDir,nickname,domain,port,httpPrefix,True,args.password.strip())
    if os.path.isdir(baseDir+'/accounts/'+nickname+'@'+domain):
        print('Account created for '+nickname+'@'+domain)
    else:
        print('Account creation failed')
    sys.exit()

if args.rmaccount:
    if '@' in args.rmaccount:
        nickname=args.rmaccount.split('@')[0]
        domain=args.rmaccount.split('@')[1]
    else:
        nickname=args.rmaccount
        if not args.domain or not getConfigParam(baseDir,'domain'):
            print('Use the --domain option to set the domain name')
            sys.exit()
    handle=nickname+'@'+domain
    accountRemoved=False
    removePassword(baseDir,nickname)
    if os.path.isdir(baseDir+'/accounts/'+handle):
        shutil.rmtree(baseDir+'/accounts/'+handle)
        accountRemoved=True
    if os.path.isfile(baseDir+'/accounts/'+handle+'.json'):
        os.remove(baseDir+'/accounts/'+handle+'.json')
        accountRemoved=True
    if os.path.isfile(baseDir+'/wfendpoints/'+handle+'.json'):
        os.remove(baseDir+'/wfendpoints/'+handle+'.json')
        accountRemoved=True
    if os.path.isfile(baseDir+'/keys/private/'+handle+'.key'):
        os.remove(baseDir+'/keys/private/'+handle+'.key')
        accountRemoved=True
    if os.path.isfile(baseDir+'/keys/public/'+handle+'.pem'):
        os.remove(baseDir+'/keys/public/'+handle+'.pem')
        accountRemoved=True
    if accountRemoved:
        print('Account for '+handle+' was removed')
    sys.exit()

if args.changepassword:
    if len(args.changepassword)!=2:
        print('--changepassword [nickname] [new password]')
        sys.exit()
    if '@' in args.changepassword[0]:
        nickname=args.changepassword[0].split('@')[0]
        domain=args.changepassword[0].split('@')[1]
    else:
        nickname=args.changepassword[0]
        if not args.domain or not getConfigParam(baseDir,'domain'):
            print('Use the --domain option to set the domain name')
            sys.exit()
    newPassword=args.changepassword[1]
    if len(newPassword)<8:
        print('Password should be at least 8 characters')
        sys.exit()
    if not os.path.isdir(baseDir+'/accounts/'+nickname+'@'+domain):
        print('Account '+nickname+'@'+domain+' not found')
        sys.exit()
    passwordFile=baseDir+'/accounts/passwords'
    if os.path.isfile(passwordFile):
        if nickname+':' in open(passwordFile).read():
            storeBasicCredentials(baseDir,nickname,newPassword)
            print('Password for '+nickname+' was changed')
        else:
            print(nickname+' is not in the passwords file')
    else:
        print('Passwords file not found')
    sys.exit()

if not args.domain and not domain:
    print('Specify a domain with --domain [name]')
    sys.exit()

federationList=[]
if args.federationList:
    if len(args.federationList)==1:
        if not (args.federationList[0].lower()=='any' or \
                args.federationList[0].lower()=='all' or \
                args.federationList[0].lower()=='*'):
            for federationDomain in args.federationList:
                if '@' in federationDomain:
                    print(federationDomain+': Federate with domains, not individual accounts')
                    sys.exit()
            federationList=args.federationList.copy()
        setConfigParam(baseDir,'federationList',federationList)
else:
    configFederationList=getConfigParam(baseDir,'federationList')
    if configFederationList:
        federationList=configFederationList

if federationList:
    print('Federating with: '+str(federationList))

if not os.path.isdir(baseDir+'/accounts/'+nickname+'@'+domain):
    print('Creating default admin account '+nickname+'@'+domain)
    print('See config.json for the password. You can remove the password from config.json after moving it elsewhere.')
    adminPassword=createPassword(10)
    setConfigParam(baseDir,'adminPassword',adminPassword)
    createPerson(baseDir,nickname,domain,port,httpPrefix,True,adminPassword)

if not os.path.isdir(baseDir+'/accounts/sharedinbox@'+domain):
    print('Creating shared inbox')
    createSharedInbox(baseDir,'sharedinbox',domain,port,httpPrefix)

runDaemon(baseDir,domain,port,httpPrefix,federationList,useTor,debug)
