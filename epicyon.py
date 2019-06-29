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
from posts import getUserPosts
from posts import createPublicPost
from posts import deleteAllPosts
from posts import createOutbox
from posts import archivePosts
from session import createSession
import json
import sys
import requests
from pprint import pprint
from httpsig import testHttpsig
from daemon import runDaemon
import socket

federationList=['mastodon.social']
username='testuser'
#domain=socket.gethostname()
domain='mydomain.com'
port=6227
https=True
useTor=False
session = createSession(useTor)

#asHeader = {'Accept': 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"'}
#userFollowing = getJson(session,"",asHeader,None)


privateKeyPem,publicKeyPem,person,wfEndpoint=createPerson(username,domain,https,True)
#deleteAllPosts(username,domain)
setPreferredUsername(username,domain,'badger')
setBio(username,domain,'Some personal info')
#createPublicPost(username, domain, https, "G'day world!", False, True, None, None, 'Not suitable for Vogons')
#archivePosts(username,domain,4)
#outboxJson=createOutbox(username,domain,https,3,None)
#pprint(outboxJson)

runDaemon(domain,port,federationList,useTor)

#testHttpsig()
#sys.exit()

#pprint(person)
#print('\n')
#pprint(wfEndpoint)

handle="https://mastodon.social/@Gargron"
wfRequest = webfingerHandle(session,handle,True)
if not wfRequest:
    sys.exit()
#wfResult = json.dumps(wfRequest, indent=4, sort_keys=True)
#print(str(wfResult))
#sys.exit()

maxMentions=10
maxEmoji=10
maxAttachments=5
userPosts = getUserPosts(session,wfRequest,2,maxMentions,maxEmoji,maxAttachments,federationList)
#print(str(userPosts))
