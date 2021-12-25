__filename__ = "webfinger.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "ActivityPub"

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
from utils import removeDomainPort
from utils import getUserPaths
from utils import getGroupPaths
from utils import localActorUrl


def _parseHandle(handle: str) -> (str, str, bool):
    """Parses a handle and returns nickname and domain
    """
    groupAccount = False
    if '.' not in handle:
        return None, None, False
    prefixes = getProtocolPrefixes()
    handleStr = handle
    for prefix in prefixes:
        handleStr = handleStr.replace(prefix, '')

    # try domain/@nick
    if '/@' in handle:
        domain, nickname = handleStr.split('/@')
        return nickname, domain, False

    # try nick@domain
    if '@' in handle:
        if handle.startswith('!'):
            handle = handle[1:]
            groupAccount = True
        nickname, domain = handle.split('@')
        return nickname, domain, groupAccount

    # try for different /users/ paths
    usersPaths = getUserPaths()
    groupPaths = getGroupPaths()
    for possibleUsersPath in usersPaths:
        if possibleUsersPath in handle:
            if possibleUsersPath in groupPaths:
                groupAccount = True
            domain, nickname = handleStr.split(possibleUsersPath)
            return nickname, domain, groupAccount

    return None, None, False


def webfingerHandle(session, handle: str, httpPrefix: str,
                    cachedWebfingers: {},
                    fromDomain: str, projectVersion: str,
                    debug: bool, groupAccount: bool,
                    signingPrivateKeyPem: str) -> {}:
    """Gets webfinger result for the given ActivityPub handle
    """
    if not session:
        if debug:
            print('WARN: No session specified for webfingerHandle')
        return None

    nickname, domain, grpAccount = _parseHandle(handle)
    if not nickname:
        return None
    wfDomain = removeDomainPort(domain)

    wfHandle = nickname + '@' + wfDomain
    wf = getWebfingerFromCache(wfHandle, cachedWebfingers)
    if wf:
        if debug:
            print('Webfinger from cache: ' + str(wf))
        return wf
    url = '{}://{}/.well-known/webfinger'.format(httpPrefix, domain)
    hdr = {
        'Accept': 'application/jrd+json'
    }
    par = {
        'resource': 'acct:{}'.format(wfHandle)
    }
    try:
        result = \
            getJson(signingPrivateKeyPem, session, url, hdr, par,
                    debug, projectVersion, httpPrefix, fromDomain)
    except Exception as ex:
        print('ERROR: webfingerHandle ' + str(ex))
        return None

    if result:
        storeWebfingerInCache(wfHandle, result, cachedWebfingers)
    else:
        if debug:
            print("WARN: Unable to webfinger " + url + ' ' +
                  'nickname: ' + str(nickname) + ' ' +
                  'domain: ' + str(wfDomain) + ' ' +
                  'headers: ' + str(hdr) + ' ' +
                  'params: ' + str(par))

    return result


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
                            httpPrefix: str, publicKeyPem: str,
                            groupAccount: bool) -> {}:
    """Creates a webfinger endpoint for a user
    """
    originalDomain = domain
    domain = getFullDomain(domain, port)

    personName = nickname
    personId = localActorUrl(httpPrefix, personName, domain)
    subjectStr = "acct:" + personName + "@" + originalDomain
    profilePageHref = httpPrefix + "://" + domain + "/@" + nickname
    if nickname == 'inbox' or nickname == originalDomain:
        personName = 'actor'
        personId = httpPrefix + "://" + domain + "/" + personName
        subjectStr = "acct:" + originalDomain + "@" + originalDomain
        profilePageHref = httpPrefix + '://' + domain + \
            '/about/more?instance_actor=true'

    personLink = httpPrefix + "://" + domain + "/@" + personName
    account = {
        "aliases": [
            personLink,
            personId
        ],
        "links": [
            {
                "href": personLink + "/avatar.png",
                "rel": "http://webfinger.net/rel/avatar",
                "type": "image/png"
            },
            {
                "href": httpPrefix + "://" + domain + "/blog/" + personName,
                "rel": "http://webfinger.net/rel/blog"
            },
            {
                "href": profilePageHref,
                "rel": "http://webfinger.net/rel/profile-page",
                "type": "text/html"
            },
            {
                "href": personId,
                "rel": "self",
                "type": "application/activity+json"
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
    metaStr = \
        "<?xml version=’1.0' encoding=’UTF-8'?>" + \
        "<XRD xmlns=’http://docs.oasis-open.org/ns/xri/xrd-1.0'" + \
        " xmlns:hm=’http://host-meta.net/xrd/1.0'>" + \
        "" + \
        "<hm:Host>" + domainFull + "</hm:Host>" + \
        "" + \
        "<Link rel=’lrdd’" + \
        " template=’" + httpPrefix + "://" + domainFull + \
        "/describe?uri={uri}'>" + \
        " <Title>Resource Descriptor</Title>" + \
        " </Link>" + \
        "</XRD>"
    return metaStr


def webfingerLookup(path: str, baseDir: str,
                    domain: str, onionDomain: str,
                    port: int, debug: bool) -> {}:
    """Lookup the webfinger endpoint for an account
    """
    if not path.startswith('/.well-known/webfinger?'):
        return None
    handle = None
    resType = 'acct'
    if 'resource=' + resType + ':' in path:
        handle = path.split('resource=' + resType + ':')[1].strip()
        handle = urllib.parse.unquote(handle)
        if debug:
            print('DEBUG: WEBFINGER handle ' + handle)
    elif 'resource=' + resType + '%3A' in path:
        handle = path.split('resource=' + resType + '%3A')[1]
        handle = urllib.parse.unquote(handle.strip())
        if debug:
            print('DEBUG: WEBFINGER handle ' + handle)
    if not handle:
        if debug:
            print('DEBUG: WEBFINGER handle missing')
        return None
    if '&' in handle:
        handle = handle.split('&')[0].strip()
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
    # instance actor
    if handle.startswith('actor@'):
        handle = handle.replace('actor@', 'inbox@', 1)
    elif handle.startswith('Actor@'):
        handle = handle.replace('Actor@', 'inbox@', 1)
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


def _webfingerUpdateAvatar(wfJson: {}, actorJson: {}) -> bool:
    """Updates the avatar image link
    """
    found = False
    avatarUrl = actorJson['icon']['url']
    mediaType = actorJson['icon']['mediaType']
    for link in wfJson['links']:
        if not link.get('rel'):
            continue
        if not link['rel'].endswith('://webfinger.net/rel/avatar'):
            continue
        found = True
        if link['href'] != avatarUrl or link['type'] != mediaType:
            link['href'] = avatarUrl
            link['type'] = mediaType
            return True
        break
    if found:
        return False
    wfJson['links'].append({
        "href": avatarUrl,
        "rel": "http://webfinger.net/rel/avatar",
        "type": mediaType
    })
    return True


def _webfingerAddBlogLink(wfJson: {}, actorJson: {}) -> bool:
    """Adds a blog link to webfinger if needed
    """
    found = False
    if '/users/' in actorJson['id']:
        blogUrl = \
            actorJson['id'].split('/users/')[0] + '/blog/' + \
            actorJson['id'].split('/users/')[1]
    else:
        blogUrl = \
            actorJson['id'].split('/@')[0] + '/blog/' + \
            actorJson['id'].split('/@')[1]
    for link in wfJson['links']:
        if not link.get('rel'):
            continue
        if not link['rel'].endswith('://webfinger.net/rel/blog'):
            continue
        found = True
        if link['href'] != blogUrl:
            link['href'] = blogUrl
            return True
        break
    if found:
        return False
    wfJson['links'].append({
        "href": blogUrl,
        "rel": "http://webfinger.net/rel/blog"
    })
    return True


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
        "briar": "briar",
        "cwtch": "cwtch",
        "jami": "jami",
        "tox": "toxId"
    }

    aliasesNotFound = []
    for name, alias in webfingerPropertyName.items():
        aliasesNotFound.append(alias)

    for propertyValue in actorJson['attachment']:
        if not propertyValue.get('name'):
            continue
        propertyName = propertyValue['name'].lower()
        found = False
        for name, alias in webfingerPropertyName.items():
            if name == propertyName:
                if alias in aliasesNotFound:
                    aliasesNotFound.remove(alias)
                found = True
                break
        if not found:
            continue
        if not propertyValue.get('type'):
            continue
        if not propertyValue.get('value'):
            continue
        if propertyValue['type'] != 'PropertyValue':
            continue

        newValue = propertyValue['value'].strip()
        if '://' in newValue:
            newValue = newValue.split('://')[1]

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

    # remove any aliases which are no longer in the actor profile
    removeAlias = []
    for alias in aliasesNotFound:
        for fullAlias in wfJson['aliases']:
            if fullAlias.startswith(alias + ':'):
                removeAlias.append(fullAlias)
    for fullAlias in removeAlias:
        wfJson['aliases'].remove(fullAlias)
        changed = True

    if _webfingerUpdateAvatar(wfJson, actorJson):
        changed = True

    if _webfingerAddBlogLink(wfJson, actorJson):
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
