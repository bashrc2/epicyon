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
from auth import storeBasicCredentials

def generateRSAKey() -> (str,str):
    key = RSA.generate(2048)
    privateKeyPem = key.exportKey("PEM").decode("utf-8")
    publicKeyPem = key.publickey().exportKey("PEM").decode("utf-8")
    return privateKeyPem,publicKeyPem

def createPersonBase(baseDir: str,nickname: str,domain: str,port: int, \
                     httpPrefix: str, saveToFile: bool,password=None) -> (str,str,{},{}):
    """Returns the private key, public key, actor and webfinger endpoint
    """
    privateKeyPem,publicKeyPem=generateRSAKey()
    webfingerEndpoint= \
        createWebfingerEndpoint(nickname,domain,port,httpPrefix,publicKeyPem)
    if saveToFile:
        storeWebfingerEndpoint(nickname,domain,baseDir,webfingerEndpoint)

    handle=nickname.lower()+'@'+domain.lower()
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
                 'endpoints': {
                     'id': httpPrefix+'://'+domain+'/users/'+nickname+'/endpoints',
                     'sharedInbox': httpPrefix+'://'+domain+'/inbox',
                     'uploadMedia': httpPrefix+'://'+domain+'/users/'+nickname+'/endpoints/uploadMedia',
                 },
                 'capabilityAcquisitionEndpoint': httpPrefix+'://'+domain+'/caps/new'
                 'featured': httpPrefix+'://'+domain+'/users/'+nickname+'/collections/featured',
                 'followers': httpPrefix+'://'+domain+'/users/'+nickname+'/followers',
                 'following': httpPrefix+'://'+domain+'/users/'+nickname+'/following',
                 'icon': {'mediaType': 'image/png',
                          'type': 'Image',
                          'url': httpPrefix+'://'+domain+'/users/'+nickname+'_icon.png'},
                 'id': httpPrefix+'://'+domain+'/users/'+nickname,
                 'image': {'mediaType': 'image/png',
                           'type': 'Image',
                           'url': httpPrefix+'://'+domain+'/users/'+nickname+'.png'},
                 'inbox': httpPrefix+'://'+domain+'/users/'+nickname+'/inbox',
                 'manuallyApprovesFollowers': False,
                 'name': nickname,
                 'outbox': httpPrefix+'://'+domain+'/users/'+nickname+'/outbox',
                 'preferredUsername': ''+nickname,
                 'publicKey': {'id': httpPrefix+'://'+domain+'/users/'+nickname+'#main-key',
                               'owner': httpPrefix+'://'+domain+'/users/'+nickname,
                               'publicKeyPem': publicKeyPem,
                               'summary': '',
                               'tag': [],
                               'type': 'Person',
                               'url': httpPrefix+'://'+domain+'/@'+nickname}
    }

    if saveToFile:
        # save person to file
        peopleSubdir='/accounts'
        if not os.path.isdir(baseDir+peopleSubdir):
            os.mkdir(baseDir+peopleSubdir)
        if not os.path.isdir(baseDir+peopleSubdir+'/'+handle):
            os.mkdir(baseDir+peopleSubdir+'/'+handle)
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

        if password:
            storeBasicCredentials(baseDir,nickname,password)

    return privateKeyPem,publicKeyPem,newPerson,webfingerEndpoint

def createPerson(baseDir: str,nickname: str,domain: str,port: int, \
                 httpPrefix: str, saveToFile: bool,password=None) -> (str,str,{},{}):
    """Returns the private key, public key, actor and webfinger endpoint
    """
    if not validNickname(nickname):
       return None,None,None,None
    return createPersonBase(baseDir,nickname,domain,port,httpPrefix,saveToFile,password)

def createSharedInbox(baseDir: str,nickname: str,domain: str,port: int, \
                      httpPrefix: str) -> (str,str,{},{}):
    """Generates the shared inbox
    """
    return createPersonBase(baseDir,nickname,domain,port,httpPrefix,True,None)

def createCapabilitiesInbox(baseDir: str,nickname: str,domain: str,port: int, \
                            httpPrefix: str) -> (str,str,{},{}):
    """Generates the capabilities inbox to sign requests
    """
    return createPersonBase(baseDir,nickname,domain,port,httpPrefix,True,None)
   
def validNickname(nickname: str) -> bool:
    forbiddenChars=['.',' ','/','?',':',';','@']
    for c in forbiddenChars:
        if c in nickname:
            return False
    reservedNames=['inbox','outbox','following','followers','sharedinbox','capabilities']
    if nickname in reservedNames:
        return False
    return True
    
def personLookup(domain: str,path: str,baseDir: str) -> {}:
    """Lookup the person for an given nickname
    """
    if path.endswith('#main-key'):
        path=path.replace('#main-key','')
    notPersonLookup=['/inbox','/outbox','/outboxarchive', \
                     '/followers','/following','/featured', \
                     '.png','.jpg','.gif','.mpv']
    for ending in notPersonLookup:        
        if path.endswith(ending):
            return None
    nickname=None
    if path.startswith('/users/'):
        nickname=path.replace('/users/','',1)
    if path.startswith('/@'):
        nickname=path.replace('/@','',1)
    if not nickname:
        return None
    if not validNickname(nickname):
        return None
    if ':' in domain:
        domain=domain.split(':')[0]
    handle=nickname.lower()+'@'+domain.lower()
    filename=baseDir+'/accounts/'+handle.lower()+'.json'
    if not os.path.isfile(filename):
        return None
    personJson={"user": "unknown"}
    with open(filename, 'r') as fp:
        personJson=commentjson.load(fp)
    return personJson

def personBoxJson(baseDir: str,domain: str,port: int,path: str, \
                  httpPrefix: str,noOfItems: int,boxname: str) -> []:
    """Obtain the inbox/outbox feed for the given person
    """
    if boxname!='inbox' and boxname!='outbox':
        return None

    if not '/'+boxname in path:
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

    if not path.endswith('/'+boxname):
        return None
    nickname=None
    if path.startswith('/users/'):
        nickname=path.replace('/users/','',1).replace('/'+boxname,'')
    if path.startswith('/@'):
        nickname=path.replace('/@','',1).replace('/'+boxname,'')
    if not nickname:
        return None
    if not validNickname(nickname):
        return None
    if boxname=='inbox':
        return createInbox(baseDir,nickname,domain,port,httpPrefix, \
                           noOfItems,headerOnly,pageNumber)
    return createOutbox(baseDir,nickname,domain,port,httpPrefix, \
                        noOfItems,headerOnly,pageNumber)

def personInboxJson(baseDir: str,domain: str,port: int,path: str, \
                    httpPrefix: str,noOfItems: int) -> []:
    """Obtain the inbox feed for the given person
    Authentication is expected to have already happened
    """
    if not '/inbox' in path:
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

    if not path.endswith('/inbox'):
        return None
    nickname=None
    if path.startswith('/users/'):
        nickname=path.replace('/users/','',1).replace('/inbox','')
    if path.startswith('/@'):
        nickname=path.replace('/@','',1).replace('/inbox','')
    if not nickname:
        return None
    if not validNickname(nickname):
        return None
    return createInbox(baseDir,nickname,domain,port,httpPrefix, \
                       noOfItems,headerOnly,pageNumber)

def setPreferredNickname(baseDir: str,nickname: str, domain: str, \
                         preferredName: str) -> bool:
    if len(preferredName)>32:
        return False
    handle=nickname.lower()+'@'+domain.lower()
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

def setBio(baseDir: str,nickname: str, domain: str, bio: str) -> bool:
    if len(bio)>32:
        return False
    handle=nickname.lower()+'@'+domain.lower()
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
