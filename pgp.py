__filename__ = "pgp.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Profile Metadata"

import os
import subprocess
from pathlib import Path
from person import getActorJson
from utils import contains_pgp_public_key
from utils import is_pgp_encrypted
from utils import get_full_domain
from utils import getStatusNumber
from utils import local_actor_url
from utils import replace_users_with_at
from webfinger import webfingerHandle
from posts import getPersonBox
from auth import createBasicAuthHeader
from session import postJson


def getEmailAddress(actor_json: {}) -> str:
    """Returns the email address for the given actor
    """
    if not actor_json.get('attachment'):
        return ''
    for property_value in actor_json['attachment']:
        if not property_value.get('name'):
            continue
        if not property_value['name'].lower().startswith('email'):
            continue
        if not property_value.get('type'):
            continue
        if not property_value.get('value'):
            continue
        if property_value['type'] != 'PropertyValue':
            continue
        if '@' not in property_value['value']:
            continue
        if '.' not in property_value['value']:
            continue
        return property_value['value']
    return ''


def getPGPpubKey(actor_json: {}) -> str:
    """Returns PGP public key for the given actor
    """
    if not actor_json.get('attachment'):
        return ''
    for property_value in actor_json['attachment']:
        if not property_value.get('name'):
            continue
        if not property_value['name'].lower().startswith('pgp'):
            continue
        if not property_value.get('type'):
            continue
        if not property_value.get('value'):
            continue
        if property_value['type'] != 'PropertyValue':
            continue
        if not contains_pgp_public_key(property_value['value']):
            continue
        return property_value['value']
    return ''


def getPGPfingerprint(actor_json: {}) -> str:
    """Returns PGP fingerprint for the given actor
    """
    if not actor_json.get('attachment'):
        return ''
    for property_value in actor_json['attachment']:
        if not property_value.get('name'):
            continue
        if not property_value['name'].lower().startswith('openpgp'):
            continue
        if not property_value.get('type'):
            continue
        if not property_value.get('value'):
            continue
        if property_value['type'] != 'PropertyValue':
            continue
        if len(property_value['value']) < 10:
            continue
        return property_value['value']
    return ''


def setEmailAddress(actor_json: {}, emailAddress: str) -> None:
    """Sets the email address for the given actor
    """
    notEmailAddress = False
    if '@' not in emailAddress:
        notEmailAddress = True
    if '.' not in emailAddress:
        notEmailAddress = True
    if '<' in emailAddress:
        notEmailAddress = True
    if emailAddress.startswith('@'):
        notEmailAddress = True

    if not actor_json.get('attachment'):
        actor_json['attachment'] = []

    # remove any existing value
    propertyFound = None
    for property_value in actor_json['attachment']:
        if not property_value.get('name'):
            continue
        if not property_value.get('type'):
            continue
        if not property_value['name'].lower().startswith('email'):
            continue
        propertyFound = property_value
        break
    if propertyFound:
        actor_json['attachment'].remove(propertyFound)
    if notEmailAddress:
        return

    for property_value in actor_json['attachment']:
        if not property_value.get('name'):
            continue
        if not property_value.get('type'):
            continue
        if not property_value['name'].lower().startswith('email'):
            continue
        if property_value['type'] != 'PropertyValue':
            continue
        property_value['value'] = emailAddress
        return

    newEmailAddress = {
        "name": "Email",
        "type": "PropertyValue",
        "value": emailAddress
    }
    actor_json['attachment'].append(newEmailAddress)


def setPGPpubKey(actor_json: {}, PGPpubKey: str) -> None:
    """Sets a PGP public key for the given actor
    """
    removeKey = False
    if not PGPpubKey:
        removeKey = True
    else:
        if not contains_pgp_public_key(PGPpubKey):
            removeKey = True
        if '<' in PGPpubKey:
            removeKey = True

    if not actor_json.get('attachment'):
        actor_json['attachment'] = []

    # remove any existing value
    propertyFound = None
    for property_value in actor_json['attachment']:
        if not property_value.get('name'):
            continue
        if not property_value.get('type'):
            continue
        if not property_value['name'].lower().startswith('pgp'):
            continue
        propertyFound = property_value
        break
    if propertyFound:
        actor_json['attachment'].remove(property_value)
    if removeKey:
        return

    for property_value in actor_json['attachment']:
        if not property_value.get('name'):
            continue
        if not property_value.get('type'):
            continue
        if not property_value['name'].lower().startswith('pgp'):
            continue
        if property_value['type'] != 'PropertyValue':
            continue
        property_value['value'] = PGPpubKey
        return

    newPGPpubKey = {
        "name": "PGP",
        "type": "PropertyValue",
        "value": PGPpubKey
    }
    actor_json['attachment'].append(newPGPpubKey)


def setPGPfingerprint(actor_json: {}, fingerprint: str) -> None:
    """Sets a PGP fingerprint for the given actor
    """
    removeFingerprint = False
    if not fingerprint:
        removeFingerprint = True
    else:
        if len(fingerprint) < 10:
            removeFingerprint = True

    if not actor_json.get('attachment'):
        actor_json['attachment'] = []

    # remove any existing value
    propertyFound = None
    for property_value in actor_json['attachment']:
        if not property_value.get('name'):
            continue
        if not property_value.get('type'):
            continue
        if not property_value['name'].lower().startswith('openpgp'):
            continue
        propertyFound = property_value
        break
    if propertyFound:
        actor_json['attachment'].remove(property_value)
    if removeFingerprint:
        return

    for property_value in actor_json['attachment']:
        if not property_value.get('name'):
            continue
        if not property_value.get('type'):
            continue
        if not property_value['name'].lower().startswith('openpgp'):
            continue
        if property_value['type'] != 'PropertyValue':
            continue
        property_value['value'] = fingerprint.strip()
        return

    newPGPfingerprint = {
        "name": "OpenPGP",
        "type": "PropertyValue",
        "value": fingerprint
    }
    actor_json['attachment'].append(newPGPfingerprint)


def extractPGPPublicKey(content: str) -> str:
    """Returns the PGP key from the given text
    """
    startBlock = '--BEGIN PGP PUBLIC KEY BLOCK--'
    endBlock = '--END PGP PUBLIC KEY BLOCK--'
    if startBlock not in content:
        return None
    if endBlock not in content:
        return None
    if '\n' not in content:
        return None
    linesList = content.split('\n')
    extracting = False
    publicKey = ''
    for line in linesList:
        if not extracting:
            if startBlock in line:
                extracting = True
        else:
            if endBlock in line:
                publicKey += line
                break
        if extracting:
            publicKey += line + '\n'
    return publicKey


def _pgpImportPubKey(recipientPubKey: str) -> str:
    """ Import the given public key
    """
    # do a dry run
    cmdImportPubKey = \
        'echo "' + recipientPubKey + '" | gpg --dry-run --import 2> /dev/null'
    proc = subprocess.Popen([cmdImportPubKey],
                            stdout=subprocess.PIPE, shell=True)
    (importResult, err) = proc.communicate()
    if err:
        return None

    # this time for real
    cmdImportPubKey = \
        'echo "' + recipientPubKey + '" | gpg --import 2> /dev/null'
    proc = subprocess.Popen([cmdImportPubKey],
                            stdout=subprocess.PIPE, shell=True)
    (importResult, err) = proc.communicate()
    if err:
        return None

    # get the key id
    cmdImportPubKey = \
        'echo "' + recipientPubKey + '" | gpg --show-keys'
    proc = subprocess.Popen([cmdImportPubKey],
                            stdout=subprocess.PIPE, shell=True)
    (importResult, err) = proc.communicate()
    if not importResult:
        return None
    importResult = importResult.decode('utf-8').split('\n')
    keyId = ''
    for line in importResult:
        if line.startswith('pub'):
            continue
        elif line.startswith('uid'):
            continue
        elif line.startswith('sub'):
            continue
        keyId = line.strip()
        break
    return keyId


def _pgpEncrypt(content: str, recipientPubKey: str) -> str:
    """ Encrypt using your default pgp key to the given recipient
    """
    keyId = _pgpImportPubKey(recipientPubKey)
    if not keyId:
        return None

    cmdEncrypt = \
        'echo "' + content + '" | gpg --encrypt --armor --recipient ' + \
        keyId + ' 2> /dev/null'
    proc = subprocess.Popen([cmdEncrypt],
                            stdout=subprocess.PIPE, shell=True)
    (encryptResult, err) = proc.communicate()
    if not encryptResult:
        return None
    encryptResult = encryptResult.decode('utf-8')
    if not is_pgp_encrypted(encryptResult):
        return None
    return encryptResult


def _getPGPPublicKeyFromActor(signing_priv_key_pem: str,
                              domain: str, handle: str,
                              actor_json: {} = None) -> str:
    """Searches tags on the actor to see if there is any PGP
    public key specified
    """
    if not actor_json:
        actor_json, asHeader = \
            getActorJson(domain, handle, False, False, False, True,
                         signing_priv_key_pem, None)
    if not actor_json:
        return None
    if not actor_json.get('attachment'):
        return None
    if not isinstance(actor_json['attachment'], list):
        return None
    # search through the tags on the actor
    for tag in actor_json['attachment']:
        if not isinstance(tag, dict):
            continue
        if not tag.get('value'):
            continue
        if not isinstance(tag['value'], str):
            continue
        if contains_pgp_public_key(tag['value']):
            return tag['value']
    return None


def hasLocalPGPkey() -> bool:
    """Returns true if there is a local .gnupg directory
    """
    homeDir = str(Path.home())
    gpgDir = homeDir + '/.gnupg'
    if os.path.isdir(gpgDir):
        keyId = pgpLocalPublicKey()
        if keyId:
            return True
    return False


def pgpEncryptToActor(domain: str, content: str, toHandle: str,
                      signing_priv_key_pem: str) -> str:
    """PGP encrypt a message to the given actor or handle
    """
    # get the actor and extract the pgp public key from it
    recipientPubKey = \
        _getPGPPublicKeyFromActor(signing_priv_key_pem, domain, toHandle)
    if not recipientPubKey:
        return None
    # encrypt using the recipient public key
    return _pgpEncrypt(content, recipientPubKey)


def pgpDecrypt(domain: str, content: str, fromHandle: str,
               signing_priv_key_pem: str) -> str:
    """ Encrypt using your default pgp key to the given recipient
    fromHandle can be a handle or actor url
    """
    if not is_pgp_encrypted(content):
        return content

    # if the public key is also included within the message then import it
    if contains_pgp_public_key(content):
        pubKey = extractPGPPublicKey(content)
    else:
        pubKey = \
            _getPGPPublicKeyFromActor(signing_priv_key_pem,
                                      domain, content, fromHandle)
    if pubKey:
        _pgpImportPubKey(pubKey)

    cmdDecrypt = \
        'echo "' + content + '" | gpg --decrypt --armor 2> /dev/null'
    proc = subprocess.Popen([cmdDecrypt],
                            stdout=subprocess.PIPE, shell=True)
    (decryptResult, err) = proc.communicate()
    if not decryptResult:
        return content
    decryptResult = decryptResult.decode('utf-8').strip()
    return decryptResult


def _pgpLocalPublicKeyId() -> str:
    """Gets the local pgp public key ID
    """
    cmdStr = \
        "gpgconf --list-options gpg | " + \
        "awk -F: '$1 == \"default-key\" {print $10}'"
    proc = subprocess.Popen([cmdStr],
                            stdout=subprocess.PIPE, shell=True)
    (result, err) = proc.communicate()
    if err:
        return None
    if not result:
        return None
    if len(result) < 5:
        return None
    return result.decode('utf-8').replace('"', '').strip()


def pgpLocalPublicKey() -> str:
    """Gets the local pgp public key
    """
    keyId = _pgpLocalPublicKeyId()
    if not keyId:
        keyId = ''
    cmdStr = "gpg --armor --export " + keyId
    proc = subprocess.Popen([cmdStr],
                            stdout=subprocess.PIPE, shell=True)
    (result, err) = proc.communicate()
    if err:
        return None
    if not result:
        return None
    return extractPGPPublicKey(result.decode('utf-8'))


def pgpPublicKeyUpload(base_dir: str, session,
                       nickname: str, password: str,
                       domain: str, port: int,
                       http_prefix: str,
                       cached_webfingers: {}, person_cache: {},
                       debug: bool, test: str,
                       signing_priv_key_pem: str) -> {}:
    if debug:
        print('pgpPublicKeyUpload')

    if not session:
        if debug:
            print('WARN: No session for pgpPublicKeyUpload')
        return None

    if not test:
        if debug:
            print('Getting PGP public key')
        PGPpubKey = pgpLocalPublicKey()
        if not PGPpubKey:
            return None
        PGPpubKeyId = _pgpLocalPublicKeyId()
    else:
        if debug:
            print('Testing with PGP public key ' + test)
        PGPpubKey = test
        PGPpubKeyId = None

    domain_full = get_full_domain(domain, port)
    if debug:
        print('PGP test domain: ' + domain_full)

    handle = nickname + '@' + domain_full

    if debug:
        print('Getting actor for ' + handle)

    actor_json, asHeader = \
        getActorJson(domain_full, handle, False, False, debug, True,
                     signing_priv_key_pem, session)
    if not actor_json:
        if debug:
            print('No actor returned for ' + handle)
        return None

    if debug:
        print('Actor for ' + handle + ' obtained')

    actor = local_actor_url(http_prefix, nickname, domain_full)
    handle = replace_users_with_at(actor)

    # check that this looks like the correct actor
    if not actor_json.get('id'):
        if debug:
            print('Actor has no id')
        return None
    if not actor_json.get('url'):
        if debug:
            print('Actor has no url')
        return None
    if not actor_json.get('type'):
        if debug:
            print('Actor has no type')
        return None
    if actor_json['id'] != actor:
        if debug:
            print('Actor id is not ' + actor +
                  ' instead is ' + actor_json['id'])
        return None
    if actor_json['url'] != handle:
        if debug:
            print('Actor url is not ' + handle)
        return None
    if actor_json['type'] != 'Person':
        if debug:
            print('Actor type is not Person')
        return None

    # set the pgp details
    if PGPpubKeyId:
        setPGPfingerprint(actor_json, PGPpubKeyId)
    else:
        if debug:
            print('No PGP key Id. Continuing anyway.')

    if debug:
        print('Setting PGP key within ' + actor)
    setPGPpubKey(actor_json, PGPpubKey)

    # create an actor update
    statusNumber, published = getStatusNumber()
    actorUpdate = {
        '@context': 'https://www.w3.org/ns/activitystreams',
        'id': actor + '#updates/' + statusNumber,
        'type': 'Update',
        'actor': actor,
        'to': [actor],
        'cc': [],
        'object': actor_json
    }
    if debug:
        print('actor update is ' + str(actorUpdate))

    # lookup the inbox for the To handle
    wfRequest = \
        webfingerHandle(session, handle, http_prefix, cached_webfingers,
                        domain, __version__, debug, False,
                        signing_priv_key_pem)
    if not wfRequest:
        if debug:
            print('DEBUG: pgp actor update webfinger failed for ' +
                  handle)
        return None
    if not isinstance(wfRequest, dict):
        if debug:
            print('WARN: Webfinger for ' + handle +
                  ' did not return a dict. ' + str(wfRequest))
        return None

    postToBox = 'outbox'

    # get the actor inbox for the To handle
    originDomain = domain
    (inboxUrl, pubKeyId, pubKey, fromPersonId, sharedInbox, avatarUrl,
     displayName, _) = getPersonBox(signing_priv_key_pem, originDomain,
                                    base_dir, session, wfRequest, person_cache,
                                    __version__, http_prefix, nickname,
                                    domain, postToBox, 35725)

    if not inboxUrl:
        if debug:
            print('DEBUG: No ' + postToBox + ' was found for ' + handle)
        return None
    if not fromPersonId:
        if debug:
            print('DEBUG: No actor was found for ' + handle)
        return None

    authHeader = createBasicAuthHeader(nickname, password)

    headers = {
        'host': domain,
        'Content-type': 'application/json',
        'Authorization': authHeader
    }
    quiet = not debug
    tries = 0
    while tries < 4:
        postResult = \
            postJson(http_prefix, domain_full,
                     session, actorUpdate, [], inboxUrl,
                     headers, 5, quiet)
        if postResult:
            break
        tries += 1

    if postResult is None:
        if debug:
            print('DEBUG: POST pgp actor update failed for c2s to ' +
                  inboxUrl)
        return None

    if debug:
        print('DEBUG: c2s POST pgp actor update success')

    return actorUpdate
