__filename__ = "epicyon.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "0.0.1"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

from person import createPerson
from person import setPreferredUsername
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

runAllTests()

federationList=['mastodon.social','wild.com','trees.com','127.0.0.1']
username='testuser'
#domain=socket.gethostname()
domain='127.0.0.1'
port=6227
https=False
useTor=False
baseDir=os.getcwd()
session = createSession(domain,port,useTor)
personCache={}
cachedWebfingers={}

clearFollows(baseDir,username,domain)
followPerson(baseDir,username,domain,'badger','wild.com',federationList)
followPerson(baseDir,username,domain,'squirrel','secret.com',federationList)
followPerson(baseDir,username,domain,'rodent','drainpipe.com',federationList)
followPerson(baseDir,username,domain,'batman','mesh.com',federationList)
followPerson(baseDir,username,domain,'giraffe','trees.com',federationList)

clearFollowers(baseDir,username,domain)
followerOfPerson(baseDir,username,domain,'badger','wild.com',federationList)
followerOfPerson(baseDir,username,domain,'squirrel','secret.com',federationList)
followerOfPerson(baseDir,username,domain,'rodent','drainpipe.com',federationList)
followerOfPerson(baseDir,username,domain,'batman','mesh.com',federationList)
followerOfPerson(baseDir,username,domain,'giraffe','trees.com',federationList)

#unfollowPerson(username,domain,'squirrel','secret.com')
#sys.exit()

#asHeader = {'Accept': 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"'}
#userFollowing = getJson(session,"https://mastodon.social/users/Gargron/followers?page=true",asHeader,None)
#userFollowing = getJson(session,"https://mastodon.social/users/Gargron/following",asHeader,None)
#userFollowing = getJson(session,"https://mastodon.social/users/Gargron/following?page=1",asHeader,None)
#pprint(userFollowing)
#sys.exit()


privateKeyPem,publicKeyPem,person,wfEndpoint=createPerson(baseDir,username,domain,port,https,True)
#deleteAllPosts(username,domain)
setPreferredUsername(baseDir,username,domain,'badger')
setBio(baseDir,username,domain,'Some personal info')
#createPublicPost(baseDir,username, domain, port,https, "G'day world!", False, True, None, None, 'Not suitable for Vogons')
#archivePosts(username,domain,baseDir,4)
#outboxJson=createOutbox(baseDir,username,domain,port,https,2,True,None)
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
userPosts = getPosts(session,personUrl,10,maxMentions,maxEmoji,maxAttachments,federationList,personCache)
#print(str(userPosts))
