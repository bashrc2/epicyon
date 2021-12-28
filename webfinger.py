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
from utils import get_full_domain
from utils import load_json
from utils import load_json_onionify
from utils import save_json
from utils import get_protocol_prefixes
from utils import remove_domain_port
from utils import get_user_paths
from utils import get_group_paths
from utils import local_actor_url


def _parseHandle(handle: str) -> (str, str, bool):
    """Parses a handle and returns nickname and domain
    """
    group_account = False
    if '.' not in handle:
        return None, None, False
    prefixes = get_protocol_prefixes()
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
            group_account = True
        nickname, domain = handle.split('@')
        return nickname, domain, group_account

    # try for different /users/ paths
    usersPaths = get_user_paths()
    groupPaths = get_group_paths()
    for possibleUsersPath in usersPaths:
        if possibleUsersPath in handle:
            if possibleUsersPath in groupPaths:
                group_account = True
            domain, nickname = handleStr.split(possibleUsersPath)
            return nickname, domain, group_account

    return None, None, False


def webfingerHandle(session, handle: str, http_prefix: str,
                    cached_webfingers: {},
                    fromDomain: str, project_version: str,
                    debug: bool, group_account: bool,
                    signing_priv_key_pem: str) -> {}:
    """Gets webfinger result for the given ActivityPub handle
    """
    if not session:
        if debug:
            print('WARN: No session specified for webfingerHandle')
        return None

    nickname, domain, grpAccount = _parseHandle(handle)
    if not nickname:
        return None
    wfDomain = remove_domain_port(domain)

    wfHandle = nickname + '@' + wfDomain
    wf = getWebfingerFromCache(wfHandle, cached_webfingers)
    if wf:
        if debug:
            print('Webfinger from cache: ' + str(wf))
        return wf
    url = '{}://{}/.well-known/webfinger'.format(http_prefix, domain)
    hdr = {
        'Accept': 'application/jrd+json'
    }
    par = {
        'resource': 'acct:{}'.format(wfHandle)
    }
    try:
        result = \
            getJson(signing_priv_key_pem, session, url, hdr, par,
                    debug, project_version, http_prefix, fromDomain)
    except Exception as ex:
        print('ERROR: webfingerHandle ' + str(ex))
        return None

    if result:
        storeWebfingerInCache(wfHandle, result, cached_webfingers)
    else:
        if debug:
            print("WARN: Unable to webfinger " + url + ' ' +
                  'nickname: ' + str(nickname) + ' ' +
                  'domain: ' + str(wfDomain) + ' ' +
                  'headers: ' + str(hdr) + ' ' +
                  'params: ' + str(par))

    return result


def storeWebfingerEndpoint(nickname: str, domain: str, port: int,
                           base_dir: str, wfJson: {}) -> bool:
    """Stores webfinger endpoint for a user to a file
    """
    originalDomain = domain
    domain = get_full_domain(domain, port)
    handle = nickname + '@' + domain
    wfSubdir = '/wfendpoints'
    if not os.path.isdir(base_dir + wfSubdir):
        os.mkdir(base_dir + wfSubdir)
    filename = base_dir + wfSubdir + '/' + handle + '.json'
    save_json(wfJson, filename)
    if nickname == 'inbox':
        handle = originalDomain + '@' + domain
        filename = base_dir + wfSubdir + '/' + handle + '.json'
        save_json(wfJson, filename)
    return True


def createWebfingerEndpoint(nickname: str, domain: str, port: int,
                            http_prefix: str, publicKeyPem: str,
                            group_account: bool) -> {}:
    """Creates a webfinger endpoint for a user
    """
    originalDomain = domain
    domain = get_full_domain(domain, port)

    personName = nickname
    personId = local_actor_url(http_prefix, personName, domain)
    subjectStr = "acct:" + personName + "@" + originalDomain
    profilePageHref = http_prefix + "://" + domain + "/@" + nickname
    if nickname == 'inbox' or nickname == originalDomain:
        personName = 'actor'
        personId = http_prefix + "://" + domain + "/" + personName
        subjectStr = "acct:" + originalDomain + "@" + originalDomain
        profilePageHref = http_prefix + '://' + domain + \
            '/about/more?instance_actor=true'

    personLink = http_prefix + "://" + domain + "/@" + personName
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
                "href": http_prefix + "://" + domain + "/blog/" + personName,
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


def webfingerNodeInfo(http_prefix: str, domain_full: str) -> {}:
    """ /.well-known/nodeinfo endpoint
    """
    nodeinfo = {
        'links': [
            {
                'href': http_prefix + '://' + domain_full + '/nodeinfo/2.0',
                'rel': 'http://nodeinfo.diaspora.software/ns/schema/2.0'
            }
        ]
    }
    return nodeinfo


def webfinger_meta(http_prefix: str, domain_full: str) -> str:
    """Return /.well-known/host-meta
    """
    metaStr = \
        "<?xml version=’1.0' encoding=’UTF-8'?>" + \
        "<XRD xmlns=’http://docs.oasis-open.org/ns/xri/xrd-1.0'" + \
        " xmlns:hm=’http://host-meta.net/xrd/1.0'>" + \
        "" + \
        "<hm:Host>" + domain_full + "</hm:Host>" + \
        "" + \
        "<Link rel=’lrdd’" + \
        " template=’" + http_prefix + "://" + domain_full + \
        "/describe?uri={uri}'>" + \
        " <Title>Resource Descriptor</Title>" + \
        " </Link>" + \
        "</XRD>"
    return metaStr


def webfingerLookup(path: str, base_dir: str,
                    domain: str, onion_domain: str,
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
    handle = get_full_domain(handle, port)
    # convert @domain@domain to inbox@domain
    if '@' in handle:
        handleDomain = handle.split('@')[1]
        if handle.startswith(handleDomain + '@'):
            handle = 'inbox@' + handleDomain
    # if this is a lookup for a handle using its onion domain
    # then swap the onion domain for the clearnet version
    onionify = False
    if onion_domain:
        if onion_domain in handle:
            handle = handle.replace(onion_domain, domain)
            onionify = True
    # instance actor
    if handle.startswith('actor@'):
        handle = handle.replace('actor@', 'inbox@', 1)
    elif handle.startswith('Actor@'):
        handle = handle.replace('Actor@', 'inbox@', 1)
    filename = base_dir + '/wfendpoints/' + handle + '.json'
    if debug:
        print('DEBUG: WEBFINGER filename ' + filename)
    if not os.path.isfile(filename):
        if debug:
            print('DEBUG: WEBFINGER filename not found ' + filename)
        return None
    if not onionify:
        wfJson = load_json(filename)
    else:
        print('Webfinger request for onionified ' + handle)
        wfJson = load_json_onionify(filename, domain, onion_domain)
    if not wfJson:
        wfJson = {"nickname": "unknown"}
    return wfJson


def _webfingerUpdateAvatar(wfJson: {}, actor_json: {}) -> bool:
    """Updates the avatar image link
    """
    found = False
    avatarUrl = actor_json['icon']['url']
    mediaType = actor_json['icon']['mediaType']
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


def _webfingerAddBlogLink(wfJson: {}, actor_json: {}) -> bool:
    """Adds a blog link to webfinger if needed
    """
    found = False
    if '/users/' in actor_json['id']:
        blogUrl = \
            actor_json['id'].split('/users/')[0] + '/blog/' + \
            actor_json['id'].split('/users/')[1]
    else:
        blogUrl = \
            actor_json['id'].split('/@')[0] + '/blog/' + \
            actor_json['id'].split('/@')[1]
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


def _webfingerUpdateFromProfile(wfJson: {}, actor_json: {}) -> bool:
    """Updates webfinger Email/blog/xmpp links from profile
    Returns true if one or more tags has been changed
    """
    if not actor_json.get('attachment'):
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

    for property_value in actor_json['attachment']:
        if not property_value.get('name'):
            continue
        property_name = property_value['name'].lower()
        found = False
        for name, alias in webfingerPropertyName.items():
            if name == property_name:
                if alias in aliasesNotFound:
                    aliasesNotFound.remove(alias)
                found = True
                break
        if not found:
            continue
        if not property_value.get('type'):
            continue
        if not property_value.get('value'):
            continue
        if property_value['type'] != 'PropertyValue':
            continue

        newValue = property_value['value'].strip()
        if '://' in newValue:
            newValue = newValue.split('://')[1]

        aliasIndex = 0
        found = False
        for alias in wfJson['aliases']:
            if alias.startswith(webfingerPropertyName[property_name] + ':'):
                found = True
                break
            aliasIndex += 1
        newAlias = webfingerPropertyName[property_name] + ':' + newValue
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

    if _webfingerUpdateAvatar(wfJson, actor_json):
        changed = True

    if _webfingerAddBlogLink(wfJson, actor_json):
        changed = True

    return changed


def webfingerUpdate(base_dir: str, nickname: str, domain: str,
                    onion_domain: str,
                    cached_webfingers: {}) -> None:
    handle = nickname + '@' + domain
    wfSubdir = '/wfendpoints'
    if not os.path.isdir(base_dir + wfSubdir):
        return

    filename = base_dir + wfSubdir + '/' + handle + '.json'
    onionify = False
    if onion_domain:
        if onion_domain in handle:
            handle = handle.replace(onion_domain, domain)
            onionify = True
    if not onionify:
        wfJson = load_json(filename)
    else:
        wfJson = load_json_onionify(filename, domain, onion_domain)
    if not wfJson:
        return

    actorFilename = base_dir + '/accounts/' + handle + '.json'
    actor_json = load_json(actorFilename)
    if not actor_json:
        return

    if _webfingerUpdateFromProfile(wfJson, actor_json):
        if save_json(wfJson, filename):
            storeWebfingerInCache(handle, wfJson, cached_webfingers)
