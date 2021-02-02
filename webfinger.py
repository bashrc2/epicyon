__filename__ = "webfinger.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import base64
try:
    from Cryptodome.PublicKey import RSA
    from Cryptodome.Util import number
except ImportError:
    from Crypto.PublicKey import RSA
    from Crypto.Util import number
import os
import urllib.parse
from session import getJson
from cache import storeWebfingerInCache
from cache import getWebfingerFromCache
from utils import getFullDomain
from utils import loadJson
from utils import loadJsonOnionify
from utils import saveJson
from utils import getProtocolPrefixes


def _parseHandle(handle: str) -> (str, str):
    if '.' not in handle:
        return None, None
    prefixes = getProtocolPrefixes()
    handleStr = handle
    for prefix in prefixes:
        handleStr = handleStr.replace(prefix, '')
    if '/@' in handle:
        domain, nickname = handleStr.split('/@')
    else:
        if '/users/' in handle:
            domain, nickname = handleStr.split('/users/')
        else:
            if '@' in handle:
                nickname, domain = handle.split('@')
            else:
                return None, None
    return nickname, domain


def webfingerHandle(session, handle: str, httpPrefix: str,
                    cachedWebfingers: {},
                    fromDomain: str, projectVersion: str) -> {}:
    """Gets webfinger result for the given ActivityPub handle
    """
    if not session:
        print('WARN: No session specified for webfingerHandle')
        return None

    nickname, domain = _parseHandle(handle)
    if not nickname:
        return None
    wfDomain = domain
    if ':' in wfDomain:
        # wfPortStr=wfDomain.split(':')[1]
        # if wfPortStr.isdigit():
        #     wfPort=int(wfPortStr)
        # if wfPort==80 or wfPort==443:
        wfDomain = wfDomain.split(':')[0]
    wf = getWebfingerFromCache(nickname + '@' + wfDomain,
                               cachedWebfingers)
    if wf:
        print('Webfinger from cache: ' + str(wf))
        return wf
    url = '{}://{}/.well-known/webfinger'.format(httpPrefix, domain)
    par = {
        'resource': 'acct:{}'.format(nickname + '@' + wfDomain)
    }
    hdr = {
        'Accept': 'application/jrd+json'
    }
    try:
        result = \
            getJson(session, url, hdr, par, projectVersion,
                    httpPrefix, fromDomain)
    except Exception as e:
        print(e)
        return None

    if result:
        storeWebfingerInCache(nickname + '@' + wfDomain,
                              result, cachedWebfingers)
    else:
        print("WARN: Unable to webfinger " + url + ' ' +
              'nickname: ' + str(nickname) + ' ' +
              'domain: ' + str(wfDomain) + ' ' +
              'headers: ' + str(hdr) + ' ' +
              'params: ' + str(par))

    return result


def _generateMagicKey(publicKeyPem) -> str:
    """See magic_key method in
       https://github.com/tootsuite/mastodon/blob/
       707ddf7808f90e3ab042d7642d368c2ce8e95e6f/app/models/account.rb
    """
    privkey = RSA.importKey(publicKeyPem)
    modBytes = number.long_to_bytes(privkey.n)
    mod = base64.urlsafe_b64encode(modBytes).decode("utf-8")
    expBytes = number.long_to_bytes(privkey.e)
    pubexp = base64.urlsafe_b64encode(expBytes).decode("utf-8")
    return f"data:application/magic-public-key,RSA.{mod}.{pubexp}"


def storeWebfingerEndpoint(nickname: str, domain: str, port: int,
                           baseDir: str, wfJson: {}) -> bool:
    """Stores webfinger endpoint for a user to a file
    """
    originalDomain = domain
    domain = getFullDomain(domain, port)
    handle = nickname + '@' + domain
    wfSubdir = '/wfendpoints'
    if not os.path.isdir(baseDir + wfSubdir):
        os.mkdir(baseDir + wfSubdir)
    filename = baseDir + wfSubdir + '/' + handle + '.json'
    saveJson(wfJson, filename)
    if nickname == 'inbox':
        handle = originalDomain + '@' + domain
        filename = baseDir + wfSubdir + '/' + handle + '.json'
        saveJson(wfJson, filename)
    return True


def createWebfingerEndpoint(nickname: str, domain: str, port: int,
                            httpPrefix: str, publicKeyPem) -> {}:
    """Creates a webfinger endpoint for a user
    """
    originalDomain = domain
    domain = getFullDomain(domain, port)

    personName = nickname
    personId = httpPrefix + "://" + domain + "/users/" + personName
    subjectStr = "acct:" + personName + "@" + originalDomain
    profilePageHref = httpPrefix + "://" + domain + "/@" + nickname
    if nickname == 'inbox' or nickname == originalDomain:
        personName = 'actor'
        personId = httpPrefix + "://" + domain + "/" + personName
        subjectStr = "acct:" + originalDomain + "@" + originalDomain
        profilePageHref = httpPrefix + '://' + domain + \
            '/about/more?instance_actor=true'

    actor = httpPrefix + "://" + domain + "/users/" + nickname
    account = {
        "aliases": [
            httpPrefix + "://" + domain + "/@" + personName,
            personId
        ],
        "links": [
            {
                "href": profilePageHref,
                "rel": "http://webfinger.net/rel/profile-page",
                "type": "text/html"
            },
            {
                "href": actor + ".atom",
                "rel": "http://schemas.google.com/g/2010#updates-from",
                "type": "application/atom+xml"
            },
            {
                "href": personId,
                "rel": "self",
                "type": "application/activity+json"
            },
            {
                "href": _generateMagicKey(publicKeyPem),
                "rel": "magic-public-key"
            }
        ],
        "subject": subjectStr
    }
    return account


def webfingerNodeInfo(httpPrefix: str, domainFull: str) -> {}:
    """ /.well-known/nodeinfo endpoint
    """
    nodeinfo = {
        'links': [
            {
                'href': httpPrefix + '://' + domainFull + '/nodeinfo/2.0',
                'rel': 'http://nodeinfo.diaspora.software/ns/schema/2.0'
            }
        ]
    }
    return nodeinfo


def webfingerMeta(httpPrefix: str, domainFull: str) -> str:
    """Return /.well-known/host-meta
    """
    metaStr = "<?xml version=’1.0' encoding=’UTF-8'?>"
    metaStr += "<XRD xmlns=’http://docs.oasis-open.org/ns/xri/xrd-1.0'"
    metaStr += " xmlns:hm=’http://host-meta.net/xrd/1.0'>"
    metaStr += ""
    metaStr += "<hm:Host>" + domainFull + "</hm:Host>"
    metaStr += ""
    metaStr += "<Link rel=’lrdd’"
    metaStr += " template=’" + httpPrefix + "://" + domainFull + \
        "/describe?uri={uri}'>"
    metaStr += " <Title>Resource Descriptor</Title>"
    metaStr += " </Link>"
    metaStr += "</XRD>"
    return metaStr


def webfingerLookup(path: str, baseDir: str,
                    domain: str, onionDomain: str,
                    port: int, debug: bool) -> {}:
    """Lookup the webfinger endpoint for an account
    """
    if not path.startswith('/.well-known/webfinger?'):
        return None
    handle = None
    if 'resource=acct:' in path:
        handle = path.split('resource=acct:')[1].strip()
        handle = urllib.parse.unquote(handle)
        if debug:
            print('DEBUG: WEBFINGER handle ' + handle)
    else:
        if 'resource=acct%3A' in path:
            handle = path.split('resource=acct%3A')[1]
            handle = urllib.parse.unquote(handle.strip())
            if debug:
                print('DEBUG: WEBFINGER handle ' + handle)
    if not handle:
        if debug:
            print('DEBUG: WEBFINGER handle missing')
        return None
    if '&' in handle:
        handle = handle.split('&')[0].strip()
        if debug:
            print('DEBUG: WEBFINGER handle with & removed ' + handle)
    if '@' not in handle:
        if debug:
            print('DEBUG: WEBFINGER no @ in handle ' + handle)
        return None
    handle = getFullDomain(handle, port)
    # convert @domain@domain to inbox@domain
    if '@' in handle:
        handleDomain = handle.split('@')[1]
        if handle.startswith(handleDomain + '@'):
            handle = 'inbox@' + handleDomain
    # if this is a lookup for a handle using its onion domain
    # then swap the onion domain for the clearnet version
    onionify = False
    if onionDomain:
        if onionDomain in handle:
            handle = handle.replace(onionDomain, domain)
            onionify = True
    filename = baseDir + '/wfendpoints/' + handle + '.json'
    if debug:
        print('DEBUG: WEBFINGER filename ' + filename)
    if not os.path.isfile(filename):
        if debug:
            print('DEBUG: WEBFINGER filename not found ' + filename)
        return None
    if not onionify:
        wfJson = loadJson(filename)
    else:
        print('Webfinger request for onionified ' + handle)
        wfJson = loadJsonOnionify(filename, domain, onionDomain)
    if not wfJson:
        wfJson = {"nickname": "unknown"}
    return wfJson


def _webfingerUpdateFromProfile(wfJson: {}, actorJson: {}) -> bool:
    """Updates webfinger Email/blog/xmpp links from profile
    Returns true if one or more tags has been changed
    """
    if not actorJson.get('attachment'):
        return False

    changed = False

    webfingerPropertyName = {
        "xmpp": "xmpp",
        "matrix": "matrix",
        "email": "mailto",
        "ssb": "ssb",
        "tox": "toxId"
    }

    for propertyValue in actorJson['attachment']:
        if not propertyValue.get('name'):
            continue
        propertyName = propertyValue['name'].lower()
        if not (propertyName.startswith('ssb') or
                propertyName.startswith('xmpp') or
                propertyName.startswith('matrix') or
                propertyName.startswith('email') or
                propertyName.startswith('tox')):
            continue
        if not propertyValue.get('type'):
            continue
        if not propertyValue.get('value'):
            continue
        if propertyValue['type'] != 'PropertyValue':
            continue

        newValue = propertyValue['value'].strip()
        aliasIndex = 0
        found = False
        for alias in wfJson['aliases']:
            if alias.startswith(webfingerPropertyName[propertyName] + ':'):
                found = True
                break
            aliasIndex += 1
        newAlias = webfingerPropertyName[propertyName] + ':' + newValue
        if found:
            if wfJson['aliases'][aliasIndex] != newAlias:
                changed = True
                wfJson['aliases'][aliasIndex] = newAlias
        else:
            wfJson['aliases'].append(newAlias)
            changed = True
    return changed


def webfingerUpdate(baseDir: str, nickname: str, domain: str,
                    onionDomain: str,
                    cachedWebfingers: {}) -> None:
    handle = nickname + '@' + domain
    wfSubdir = '/wfendpoints'
    if not os.path.isdir(baseDir + wfSubdir):
        return

    filename = baseDir + wfSubdir + '/' + handle + '.json'
    onionify = False
    if onionDomain:
        if onionDomain in handle:
            handle = handle.replace(onionDomain, domain)
            onionify = True
    if not onionify:
        wfJson = loadJson(filename)
    else:
        wfJson = loadJsonOnionify(filename, domain, onionDomain)
    if not wfJson:
        return

    actorFilename = baseDir + '/accounts/' + handle + '.json'
    actorJson = loadJson(actorFilename)
    if not actorJson:
        return

    if _webfingerUpdateFromProfile(wfJson, actorJson):
        if saveJson(wfJson, filename):
            storeWebfingerInCache(handle, wfJson, cachedWebfingers)
