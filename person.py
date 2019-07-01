__filename__ = "person.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "0.0.1"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import json
import commentjson
import os
import fileinput
from Crypto.PublicKey import RSA
from webfinger import createWebfingerEndpoint
from webfinger import storeWebfingerEndpoint
from posts import createOutbox

def generateRSAKey() -> (str,str):
    key = RSA.generate(2048)
    privateKeyPem = key.exportKey("PEM").decode("utf-8")
    publicKeyPem = key.publickey().exportKey("PEM").decode("utf-8")
    return privateKeyPem,publicKeyPem

def createPerson(baseDir: str,username: str,domain: str,port: int,https: bool, saveToFile: bool) -> (str,str,{},{}):
    """Returns the private key, public key, actor and webfinger endpoint
    """
    prefix='https'
    if not https:
        prefix='http'

    privateKeyPem,publicKeyPem=generateRSAKey()
    webfingerEndpoint=createWebfingerEndpoint(username,domain,port,https,publicKeyPem)
    if saveToFile:
        storeWebfingerEndpoint(username,domain,baseDir,webfingerEndpoint)

    handle=username.lower()+'@'+domain.lower()
    if port!=80 and port!=443:
        domain=domain+':'+str(port)

    newPerson = {'@context': ['https://www.w3.org/ns/activitystreams',
                              'https://w3id.org/security/v1',
                              {'Emoji': 'toot:Emoji',
                               'Hashtag': 'as:Hashtag',
                               'IdentityProof': 'toot:IdentityProof',
                               'PropertyValue': 'schema:PropertyValue',
                               'alsoKnownAs': {'@id': 'as:alsoKnownAs', '@type': '@id'},
                               'featured': {'@id': 'toot:featured', '@type': '@id'},
                               'focalPoint': {'@container': '@list', '@id': 'toot:focalPoint'},
                               'manuallyApprovesFollowers': 'as:manuallyApprovesFollowers',
                               'movedTo': {'@id': 'as:movedTo', '@type': '@id'},
                               'schema': 'http://schema.org#',
                               'toot': 'http://joinmastodon.org/ns#',
                               'value': 'schema:value'}],
                 'attachment': [],
                 'endpoints': {'sharedInbox': prefix+'://'+domain+'/inbox'},
                 'featured': prefix+'://'+domain+'/users/'+username+'/collections/featured',
                 'followers': prefix+'://'+domain+'/users/'+username+'/followers',
                 'following': prefix+'://'+domain+'/users/'+username+'/following',
                 'icon': {'mediaType': 'image/png',
                          'type': 'Image',
                          'url': prefix+'://'+domain+'/users/'+username+'_icon.png'},
                 'id': prefix+'://'+domain+'/users/'+username,
                 'image': {'mediaType': 'image/png',
                           'type': 'Image',
                           'url': prefix+'://'+domain+'/users/'+username+'.png'},
                 'inbox': prefix+'://'+domain+'/users/'+username+'/inbox',
                 'manuallyApprovesFollowers': False,
                 'name': username,
                 'outbox': prefix+'://'+domain+'/users/'+username+'/outbox',
                 'preferredUsername': ''+username,
                 'publicKey': {'id': prefix+'://'+domain+'/users/'+username+'/main-key',
                               'owner': prefix+'://'+domain+'/users/'+username,
                               'publicKeyPem': publicKeyPem,
                               'summary': '',
                               'tag': [],
                               'type': 'Person',
                               'url': prefix+'://'+domain+'/@'+username}
    }

    if saveToFile:
        # save person to file
        peopleSubdir='/accounts'
        if not os.path.isdir(baseDir+peopleSubdir):
            os.mkdir(baseDir+peopleSubdir)
        filename=baseDir+peopleSubdir+'/'+handle+'.json'
        with open(filename, 'w') as fp:
            commentjson.dump(newPerson, fp, indent=4, sort_keys=False)

        # save the private key
        privateKeysSubdir='/keys/private'
        if not os.path.isdir(baseDir+'/keys'):
            os.mkdir(baseDir+'/keys')
        if not os.path.isdir(baseDir+privateKeysSubdir):
            os.mkdir(baseDir+privateKeysSubdir)
        filename=baseDir+privateKeysSubdir+'/'+handle+'.key'
        with open(filename, "w") as text_file:
            print(privateKeyPem, file=text_file)

        # save the public key
        publicKeysSubdir='/keys/public'
        if not os.path.isdir(baseDir+publicKeysSubdir):
            os.mkdir(baseDir+publicKeysSubdir)
        filename=baseDir+publicKeysSubdir+'/'+handle+'.pem'
        with open(filename, "w") as text_file:
            print(publicKeyPem, file=text_file)

    return privateKeyPem,publicKeyPem,newPerson,webfingerEndpoint

def validUsername(username):
    forbiddenChars=['.',' ','/','?',':',';','@']
    for c in forbiddenChars:
        if c in username:
            return False
    return True

def personKeyLookup(domain: str,path: str,baseDir: str) -> str:
    """Lookup the public key of the person with a given username
    """
    if not path.endswith('/main-key'):
        return None
    if not path.startswith('/users/'):
        return None
    username=path.replace('/users/','',1).replace('/main-key','')
    if not validUsername(username):
        return None
    handle=username.lower()+'@'+domain.lower()
    filename=baseDir+'/accounts/'+handle.lower()+'.json'
    if not os.path.isfile(filename):
        return None
    personJson={"user": "unknown"}
    with open(filename, 'r') as fp:
        personJson=commentjson.load(fp)
    if personJson.get('publicKey'):
        if personJson['publicKey'].get('publicKeyPem'):
            return personJson['publicKey']['publicKeyPem']
    return None
    
def personLookup(domain: str,path: str,baseDir: str) -> {}:
    """Lookup the person for an given username
    """
    notPersonLookup=['/inbox','/outbox','/outboxarchive','/followers','/following','/featured','.png','.jpg','.gif','.mpv','#main-key','/main-key']
    for ending in notPersonLookup:        
        if path.endswith(ending):
            return None
    username=None
    if path.startswith('/users/'):
        username=path.replace('/users/','',1)
    if path.startswith('/@'):
        username=path.replace('/@','',1)
    if not username:
        return None
    if not validUsername(username):
        return None
    handle=username.lower()+'@'+domain.lower()
    filename=baseDir+'/accounts/'+handle.lower()+'.json'
    if not os.path.isfile(filename):
        return None
    personJson={"user": "unknown"}
    with open(filename, 'r') as fp:
        personJson=commentjson.load(fp)
    return personJson

def personOutboxJson(baseDir: str,domain: str,port: int,path: str,https: bool,noOfItems: int) -> []:
    """Obtain the outbox feed for the given person
    """
    if not '/outbox' in path:
        return None

    # Only show the header by default
    headerOnly=True

    # handle page numbers
    pageNumber=None    
    if '?page=' in path:
        pageNumber=path.split('?page=')[1]
        if pageNumber=='true':
            pageNumber=1
        else:
            try:
                pageNumber=int(pageNumber)
            except:
                pass
        path=path.split('?page=')[0]
        headerOnly=False

    if not path.endswith('/outbox'):
        return None
    username=None
    if path.startswith('/users/'):
        username=path.replace('/users/','',1).replace('/outbox','')
    if path.startswith('/@'):
        username=path.replace('/@','',1).replace('/outbox','')
    if not username:
        return None
    if not validUsername(username):
        return None
    return createOutbox(baseDir,username,domain,port,https,noOfItems,headerOnly,pageNumber)

def setPreferredUsername(baseDir: str,username: str, domain: str, preferredName: str) -> bool:
    if len(preferredName)>32:
        return False
    handle=username.lower()+'@'+domain.lower()
    filename=baseDir+'/accounts/'+handle.lower()+'.json'
    if not os.path.isfile(filename):
        return False
    personJson=None
    with open(filename, 'r') as fp:
        personJson=commentjson.load(fp)
    if not personJson:
        return False
    personJson['preferredUsername']=preferredName
    with open(filename, 'w') as fp:
        commentjson.dump(personJson, fp, indent=4, sort_keys=False)
    return True

def setBio(baseDir: str,username: str, domain: str, bio: str) -> bool:
    if len(bio)>32:
        return False
    handle=username.lower()+'@'+domain.lower()
    filename=baseDir+'/accounts/'+handle.lower()+'.json'
    if not os.path.isfile(filename):
        return False
    personJson=None
    with open(filename, 'r') as fp:
        personJson=commentjson.load(fp)
    if not personJson:
        return False
    if not personJson.get('publicKey'):
        return False
    personJson['publicKey']['summary']=bio
    with open(filename, 'w') as fp:
        commentjson.dump(personJson, fp, indent=4, sort_keys=False)
    return True

