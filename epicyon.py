__filename__ = "epicyon.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "0.0.1"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

from person import createPerson
from person import setPreferredUsername
from webfinger import webfingerHandle
from posts import getUserPosts
from session import createSession
import json
import sys
import requests
from pprint import pprint
from httpsig import testHttpsig
from daemon import runDaemon

useTor=False
session = createSession(useTor)

privateKeyPem,publicKeyPem,person,wfEndpoint=createPerson('testuser','mydomain.com',True,True)
setPreferredUsername('testuser','mydomain.com','badger')
runDaemon('mydomain.com',6227,False)

#testHttpsig()
#sys.exit()

#pprint(person)
#print('\n')
#pprint(wfEndpoint)

allowedDomains=['mastodon.social']
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
userPosts = getUserPosts(session,wfRequest,2,maxMentions,maxEmoji,maxAttachments,allowedDomains)
print(str(userPosts))
