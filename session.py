__filename__ = "session.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.0.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import os
import sys
import requests
from utils import urlPermitted
import json

baseDirectory=None

def createSession(domain: str, port: int, onionRoute: bool):
    session = requests.session()
    #if domain.startswith('127.') or domain.startswith('192.') or domain.startswith('10.'):
    #    session.mount('http://', SourceAddressAdapter(domain))
        #session.mount('http://', SourceAddressAdapter((domain, port)))
    if onionRoute:
        session.proxies = {}
        session.proxies['http'] = 'socks5h://localhost:9050'
        session.proxies['https'] = 'socks5h://localhost:9050'
    return session

def getJson(session,url: str,headers: {},params: {}, \
            version='1.0.0',httpPrefix='https',domain='testdomain') -> {}:
    if not isinstance(url, str):
        print('url: '+str(url))
        print('ERROR: getJson url should be a string')
        return None
    sessionParams={}
    sessionHeaders={}
    if headers:
        sessionHeaders=headers
    if params:
        sessionParams=params
    sessionHeaders['User-Agent']='Epicyon/'+version
    if domain:
        sessionHeaders['User-Agent']+='; +'+httpPrefix+'://'+domain+'/'
    #"Mozilla/5.0 (Linux; Android 5.1.1; Nexus 5)"
    if not session:
        print('WARN: no session specified for getJson')
    #session.cookies.clear()
    try:
        result=session.get(url, headers=sessionHeaders, params=sessionParams)
        return result.json()
    except Exception as e:
        print('ERROR: getJson failed')
        print('url: '+str(url))
        print('headers: '+str(sessionHeaders))
        print('params: '+str(sessionParams))
        print(e)
    return None

def postJson(session,postJsonObject: {},federationList: [],inboxUrl: str,headers: {},capability: str) -> str:
    """Post a json message to the inbox of another person
    Supplying a capability, such as "inbox:write"
    """

    # always allow capability requests
    if not capability.startswith('cap'):    
        # check that we are posting to a permitted domain
        if not urlPermitted(inboxUrl,federationList,capability):
            print('postJson: '+inboxUrl+' not permitted')
            return None

    postResult = session.post(url = inboxUrl, data = json.dumps(postJsonObject), headers=headers)
    if postResult:
        return postResult.text
    return None

def postJsonString(session,postJsonStr: str, \
                   federationList: [], \
                   inboxUrl: str, \
                   headers: {}, \
                   capability: str, \
                   debug: bool) -> (bool,bool):
    """Post a json message string to the inbox of another person
    Supplying a capability, such as "inbox:write"
    The second boolean returned is true if the send is unauthorized
    NOTE: Here we post a string rather than the original json so that
    conversions between string and json format don't invalidate
    the message body digest of http signatures
    """

    # always allow capability requests
    if not capability.startswith('cap'):    
        # check that we are posting to a permitted domain
        if not urlPermitted(inboxUrl,federationList,capability):
            print('postJson: '+inboxUrl+' not permitted by capabilities')
            return None,None

    postResult = session.post(url = inboxUrl, data = postJsonStr, headers=headers)
    if postResult.status_code<200 or postResult.status_code>202:
        #if postResult.status_code==400:
        #    headers['content-type']='application/ld+json; charset=utf-8'
        #    postResult = session.post(url = inboxUrl, data = postJsonStr, headers=headers)
        #    if not (postResult.status_code<200 or postResult.status_code>202):
        #        return True
        if postResult.status_code>=400 and postResult.status_code<=405 and postResult.status_code!=404:
            print('WARN: >>> Post to '+inboxUrl+' is unauthorized <<<')
            return False,True
        else:
            print('WARN: Failed to post to '+inboxUrl+' with headers '+str(headers))
            print('status code '+str(postResult.status_code))
            return False,False
    return True,False

def postImage(session,attachImageFilename: str,federationList: [],inboxUrl: str,headers: {},capability: str) -> str:
    """Post an image to the inbox of another person or outbox via c2s
    Supplying a capability, such as "inbox:write"
    """
    # always allow capability requests
    if not capability.startswith('cap'):    
        # check that we are posting to a permitted domain
        if not urlPermitted(inboxUrl,federationList,capability):
            print('postJson: '+inboxUrl+' not permitted')
            return None

    if not (attachImageFilename.endswith('.jpg') or \
            attachImageFilename.endswith('.jpeg') or \
            attachImageFilename.endswith('.png') or \
            attachImageFilename.endswith('.gif')):
        print('Image must be png, jpg, or gif')
        return None
    if not os.path.isfile(attachImageFilename):
        print('Image not found: '+attachImageFilename)
        return None
    contentType='image/jpeg'
    if attachImageFilename.endswith('.png'):
        contentType='image/png'
    if attachImageFilename.endswith('.gif'):
        contentType='image/gif'
    headers['Content-type']=contentType

    with open(attachImageFilename, 'rb') as avFile:
        mediaBinary = avFile.read()
        postResult = session.post(url=inboxUrl, data=mediaBinary, headers=headers)
        if postResult:
            return postResult.text
    return None
