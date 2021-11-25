__filename__ = "person.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "ActivityPub"

import time
import os
import subprocess
import shutil
import datetime
import pyqrcode
from random import randint
from pathlib import Path
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from shutil import copyfile
from webfinger import createWebfingerEndpoint
from webfinger import storeWebfingerEndpoint
from posts import getUserUrl
from posts import createDMTimeline
from posts import createRepliesTimeline
from posts import createMediaTimeline
from posts import createNewsTimeline
from posts import createBlogsTimeline
from posts import createFeaturesTimeline
from posts import createBookmarksTimeline
from posts import createInbox
from posts import createOutbox
from posts import createModeration
from auth import storeBasicCredentials
from auth import removePassword
from roles import setRole
from roles import setRolesFromList
from roles import getActorRolesList
from media import processMetaData
from utils import replaceUsersWithAt
from utils import removeLineEndings
from utils import removeDomainPort
from utils import getStatusNumber
from utils import getFullDomain
from utils import validNickname
from utils import loadJson
from utils import saveJson
from utils import setConfigParam
from utils import getConfigParam
from utils import refreshNewswire
from utils import getProtocolPrefixes
from utils import hasUsersPath
from utils import getImageExtensions
from utils import isImageFile
from utils import acctDir
from utils import getUserPaths
from utils import getGroupPaths
from utils import localActorUrl
from utils import dangerousSVG
from session import createSession
from session import getJson
from webfinger import webfingerHandle
from pprint import pprint
from cache import getPersonFromCache


def generateRSAKey() -> (str, str):
    key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    privateKeyPem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()
    )
    pubkey = key.public_key()
    publicKeyPem = pubkey.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    privateKeyPem = privateKeyPem.decode("utf-8")
    publicKeyPem = publicKeyPem.decode("utf-8")
    return privateKeyPem, publicKeyPem


def setProfileImage(baseDir: str, httpPrefix: str, nickname: str, domain: str,
                    port: int, imageFilename: str, imageType: str,
                    resolution: str, city: str,
                    contentLicenseUrl: str) -> bool:
    """Saves the given image file as an avatar or background
    image for the given person
    """
    imageFilename = imageFilename.replace('\n', '').replace('\r', '')
    if not isImageFile(imageFilename):
        print('Profile image must be png, jpg, gif or svg format')
        return False

    if imageFilename.startswith('~/'):
        imageFilename = imageFilename.replace('~/', str(Path.home()) + '/')

    domain = removeDomainPort(domain)
    fullDomain = getFullDomain(domain, port)

    handle = nickname + '@' + domain
    personFilename = baseDir + '/accounts/' + handle + '.json'
    if not os.path.isfile(personFilename):
        print('person definition not found: ' + personFilename)
        return False
    if not os.path.isdir(baseDir + '/accounts/' + handle):
        print('Account not found: ' + baseDir + '/accounts/' + handle)
        return False

    iconFilenameBase = 'icon'
    if imageType == 'avatar' or imageType == 'icon':
        iconFilenameBase = 'icon'
    else:
        iconFilenameBase = 'image'

    mediaType = 'image/png'
    iconFilename = iconFilenameBase + '.png'
    if imageFilename.endswith('.jpg') or \
       imageFilename.endswith('.jpeg'):
        mediaType = 'image/jpeg'
        iconFilename = iconFilenameBase + '.jpg'
    elif imageFilename.endswith('.gif'):
        mediaType = 'image/gif'
        iconFilename = iconFilenameBase + '.gif'
    elif imageFilename.endswith('.webp'):
        mediaType = 'image/webp'
        iconFilename = iconFilenameBase + '.webp'
    elif imageFilename.endswith('.avif'):
        mediaType = 'image/avif'
        iconFilename = iconFilenameBase + '.avif'
    elif imageFilename.endswith('.svg'):
        mediaType = 'image/svg+xml'
        iconFilename = iconFilenameBase + '.svg'
    profileFilename = baseDir + '/accounts/' + handle + '/' + iconFilename

    personJson = loadJson(personFilename)
    if personJson:
        personJson[iconFilenameBase]['mediaType'] = mediaType
        personJson[iconFilenameBase]['url'] = \
            localActorUrl(httpPrefix, nickname, fullDomain) + \
            '/' + iconFilename
        saveJson(personJson, personFilename)

        cmd = \
            '/usr/bin/convert ' + imageFilename + ' -size ' + \
            resolution + ' -quality 50 ' + profileFilename
        subprocess.call(cmd, shell=True)
        processMetaData(baseDir, nickname, domain,
                        profileFilename, profileFilename, city,
                        contentLicenseUrl)
        return True
    return False


def _accountExists(baseDir: str, nickname: str, domain: str) -> bool:
    """Returns true if the given account exists
    """
    domain = removeDomainPort(domain)
    accountDir = acctDir(baseDir, nickname, domain)
    return os.path.isdir(accountDir) or \
        os.path.isdir(baseDir + '/deactivated/' + nickname + '@' + domain)


def randomizeActorImages(personJson: {}) -> None:
    """Randomizes the filenames for avatar image and background
    This causes other instances to update their cached avatar image
    """
    personId = personJson['id']
    lastPartOfFilename = personJson['icon']['url'].split('/')[-1]
    existingExtension = lastPartOfFilename.split('.')[1]
    # NOTE: these files don't need to have cryptographically
    # secure names
    randStr = str(randint(10000000000000, 99999999999999))  # nosec
    baseUrl = personId.split('/users/')[0]
    nickname = personJson['preferredUsername']
    personJson['icon']['url'] = \
        baseUrl + '/system/accounts/avatars/' + nickname + \
        '/avatar' + randStr + '.' + existingExtension
    lastPartOfFilename = personJson['image']['url'].split('/')[-1]
    existingExtension = lastPartOfFilename.split('.')[1]
    randStr = str(randint(10000000000000, 99999999999999))  # nosec
    personJson['image']['url'] = \
        baseUrl + '/system/accounts/headers/' + nickname + \
        '/image' + randStr + '.' + existingExtension


def getActorUpdateJson(actorJson: {}) -> {}:
    """Returns the json for an Person Update
    """
    pubNumber, _ = getStatusNumber()
    manuallyApprovesFollowers = actorJson['manuallyApprovesFollowers']
    return {
        '@context': [
            "https://www.w3.org/ns/activitystreams",
            "https://w3id.org/security/v1",
            {
                "manuallyApprovesFollowers": "as:manuallyApprovesFollowers",
                "toot": "http://joinmastodon.org/ns#",
                "featured":
                {
                    "@id": "toot:featured",
                    "@type": "@id"
                },
                "featuredTags":
                {
                    "@id": "toot:featuredTags",
                    "@type": "@id"
                },
                "alsoKnownAs":
                {
                    "@id": "as:alsoKnownAs",
                    "@type": "@id"
                },
                "movedTo":
                {
                    "@id": "as:movedTo",
                    "@type": "@id"
                },
                "schema": "http://schema.org#",
                "PropertyValue": "schema:PropertyValue",
                "value": "schema:value",
                "IdentityProof": "toot:IdentityProof",
                "discoverable": "toot:discoverable",
                "Device": "toot:Device",
                "Ed25519Signature": "toot:Ed25519Signature",
                "Ed25519Key": "toot:Ed25519Key",
                "Curve25519Key": "toot:Curve25519Key",
                "EncryptedMessage": "toot:EncryptedMessage",
                "publicKeyBase64": "toot:publicKeyBase64",
                "deviceId": "toot:deviceId",
                "claim":
                {
                    "@type": "@id",
                    "@id": "toot:claim"
                },
                "fingerprintKey":
                {
                    "@type": "@id",
                    "@id": "toot:fingerprintKey"
                },
                "identityKey":
                {
                    "@type": "@id",
                    "@id": "toot:identityKey"
                },
                "devices":
                {
                    "@type": "@id",
                    "@id": "toot:devices"
                },
                "messageFranking": "toot:messageFranking",
                "messageType": "toot:messageType",
                "cipherText": "toot:cipherText",
                "suspended": "toot:suspended",
                "focalPoint":
                {
                    "@container": "@list",
                    "@id": "toot:focalPoint"
                }
            }
        ],
        'id': actorJson['id'] + '#updates/' + pubNumber,
        'type': 'Update',
        'actor': actorJson['id'],
        'to': ['https://www.w3.org/ns/activitystreams#Public'],
        'cc': [actorJson['id'] + '/followers'],
        'object': {
            'id': actorJson['id'],
            'type': actorJson['type'],
            'icon': {
                'type': 'Image',
                'url': actorJson['icon']['url']
            },
            'image': {
                'type': 'Image',
                'url': actorJson['image']['url']
            },
            'attachment': actorJson['attachment'],
            'following': actorJson['id'] + '/following',
            'followers': actorJson['id'] + '/followers',
            'inbox': actorJson['id'] + '/inbox',
            'outbox': actorJson['id'] + '/outbox',
            'featured': actorJson['id'] + '/collections/featured',
            'featuredTags': actorJson['id'] + '/collections/tags',
            'preferredUsername': actorJson['preferredUsername'],
            'name': actorJson['name'],
            'summary': actorJson['summary'],
            'url': actorJson['url'],
            'manuallyApprovesFollowers': manuallyApprovesFollowers,
            'discoverable': actorJson['discoverable'],
            'published': actorJson['published'],
            'devices': actorJson['devices'],
            "publicKey": actorJson['publicKey'],
        }
    }


def getDefaultPersonContext() -> str:
    """Gets the default actor context
    """
    return {
        'Curve25519Key': 'toot:Curve25519Key',
        'Device': 'toot:Device',
        'Ed25519Key': 'toot:Ed25519Key',
        'Ed25519Signature': 'toot:Ed25519Signature',
        'EncryptedMessage': 'toot:EncryptedMessage',
        'IdentityProof': 'toot:IdentityProof',
        'PropertyValue': 'schema:PropertyValue',
        'alsoKnownAs': {'@id': 'as:alsoKnownAs', '@type': '@id'},
        'cipherText': 'toot:cipherText',
        'claim': {'@id': 'toot:claim', '@type': '@id'},
        'deviceId': 'toot:deviceId',
        'devices': {'@id': 'toot:devices', '@type': '@id'},
        'discoverable': 'toot:discoverable',
        'featured': {'@id': 'toot:featured', '@type': '@id'},
        'featuredTags': {'@id': 'toot:featuredTags', '@type': '@id'},
        'fingerprintKey': {'@id': 'toot:fingerprintKey', '@type': '@id'},
        'focalPoint': {'@container': '@list', '@id': 'toot:focalPoint'},
        'identityKey': {'@id': 'toot:identityKey', '@type': '@id'},
        'manuallyApprovesFollowers': 'as:manuallyApprovesFollowers',
        'messageFranking': 'toot:messageFranking',
        'messageType': 'toot:messageType',
        'movedTo': {'@id': 'as:movedTo', '@type': '@id'},
        'publicKeyBase64': 'toot:publicKeyBase64',
        'schema': 'http://schema.org#',
        'suspended': 'toot:suspended',
        'toot': 'http://joinmastodon.org/ns#',
        'value': 'schema:value',
        'hasOccupation': 'schema:hasOccupation',
        'Occupation': 'schema:Occupation',
        'occupationalCategory': 'schema:occupationalCategory',
        'Role': 'schema:Role',
        'WebSite': 'schema:Project',
        'CategoryCode': 'schema:CategoryCode',
        'CategoryCodeSet': 'schema:CategoryCodeSet'
    }


def _createPersonBase(baseDir: str, nickname: str, domain: str, port: int,
                      httpPrefix: str, saveToFile: bool,
                      manualFollowerApproval: bool,
                      groupAccount: bool,
                      password: str) -> (str, str, {}, {}):
    """Returns the private key, public key, actor and webfinger endpoint
    """
    privateKeyPem, publicKeyPem = generateRSAKey()
    webfingerEndpoint = \
        createWebfingerEndpoint(nickname, domain, port,
                                httpPrefix, publicKeyPem,
                                groupAccount)
    if saveToFile:
        storeWebfingerEndpoint(nickname, domain, port,
                               baseDir, webfingerEndpoint)

    handle = nickname + '@' + domain
    originalDomain = domain
    domain = getFullDomain(domain, port)

    personType = 'Person'
    if groupAccount:
        personType = 'Group'
    # Enable follower approval by default
    approveFollowers = manualFollowerApproval
    personName = nickname
    personId = localActorUrl(httpPrefix, nickname, domain)
    inboxStr = personId + '/inbox'
    personUrl = httpPrefix + '://' + domain + '/@' + personName
    if nickname == 'inbox':
        # shared inbox
        inboxStr = httpPrefix + '://' + domain + '/actor/inbox'
        personId = httpPrefix + '://' + domain + '/actor'
        personUrl = httpPrefix + '://' + domain + \
            '/about/more?instance_actor=true'
        personName = originalDomain
        approveFollowers = True
        personType = 'Application'
    elif nickname == 'news':
        personUrl = httpPrefix + '://' + domain + \
            '/about/more?news_actor=true'
        approveFollowers = True
        personType = 'Application'

    # NOTE: these image files don't need to have
    # cryptographically secure names

    imageUrl = \
        personId + '/image' + \
        str(randint(10000000000000, 99999999999999)) + '.png'  # nosec

    iconUrl = \
        personId + '/avatar' + \
        str(randint(10000000000000, 99999999999999)) + '.png'  # nosec

    statusNumber, published = getStatusNumber()
    newPerson = {
        '@context': [
            'https://www.w3.org/ns/activitystreams',
            'https://w3id.org/security/v1',
            getDefaultPersonContext()
        ],
        'published': published,
        'alsoKnownAs': [],
        'attachment': [],
        'devices': personId + '/collections/devices',
        'endpoints': {
            'id': personId + '/endpoints',
            'sharedInbox': httpPrefix + '://' + domain + '/inbox',
        },
        'featured': personId + '/collections/featured',
        'featuredTags': personId + '/collections/tags',
        'followers': personId + '/followers',
        'following': personId + '/following',
        'tts': personId + '/speaker',
        'shares': personId + '/catalog',
        'hasOccupation': [
            {
                '@type': 'Occupation',
                'name': "",
                "occupationLocation": {
                    "@type": "City",
                    "name": "Fediverse"
                },
                'skills': []
            }
        ],
        'availability': None,
        'icon': {
            'mediaType': 'image/png',
            'type': 'Image',
            'url': iconUrl
        },
        'id': personId,
        'image': {
            'mediaType': 'image/png',
            'type': 'Image',
            'url': imageUrl
        },
        'inbox': inboxStr,
        'manuallyApprovesFollowers': approveFollowers,
        'discoverable': True,
        'name': personName,
        'outbox': personId + '/outbox',
        'preferredUsername': personName,
        'summary': '',
        'publicKey': {
            'id': personId + '#main-key',
            'owner': personId,
            'publicKeyPem': publicKeyPem
        },
        'tag': [],
        'type': personType,
        'url': personUrl
    }

    if nickname == 'inbox':
        # fields not needed by the shared inbox
        del newPerson['outbox']
        del newPerson['icon']
        del newPerson['image']
        if newPerson.get('skills'):
            del newPerson['skills']
        del newPerson['shares']
        if newPerson.get('roles'):
            del newPerson['roles']
        del newPerson['tag']
        del newPerson['availability']
        del newPerson['followers']
        del newPerson['following']
        del newPerson['attachment']

    if saveToFile:
        # save person to file
        peopleSubdir = '/accounts'
        if not os.path.isdir(baseDir + peopleSubdir):
            os.mkdir(baseDir + peopleSubdir)
        if not os.path.isdir(baseDir + peopleSubdir + '/' + handle):
            os.mkdir(baseDir + peopleSubdir + '/' + handle)
        if not os.path.isdir(baseDir + peopleSubdir + '/' + handle + '/inbox'):
            os.mkdir(baseDir + peopleSubdir + '/' + handle + '/inbox')
        if not os.path.isdir(baseDir + peopleSubdir + '/' +
                             handle + '/outbox'):
            os.mkdir(baseDir + peopleSubdir + '/' + handle + '/outbox')
        if not os.path.isdir(baseDir + peopleSubdir + '/' + handle + '/queue'):
            os.mkdir(baseDir + peopleSubdir + '/' + handle + '/queue')
        filename = baseDir + peopleSubdir + '/' + handle + '.json'
        saveJson(newPerson, filename)

        # save to cache
        if not os.path.isdir(baseDir + '/cache'):
            os.mkdir(baseDir + '/cache')
        if not os.path.isdir(baseDir + '/cache/actors'):
            os.mkdir(baseDir + '/cache/actors')
        cacheFilename = baseDir + '/cache/actors/' + \
            newPerson['id'].replace('/', '#') + '.json'
        saveJson(newPerson, cacheFilename)

        # save the private key
        privateKeysSubdir = '/keys/private'
        if not os.path.isdir(baseDir + '/keys'):
            os.mkdir(baseDir + '/keys')
        if not os.path.isdir(baseDir + privateKeysSubdir):
            os.mkdir(baseDir + privateKeysSubdir)
        filename = baseDir + privateKeysSubdir + '/' + handle + '.key'
        try:
            with open(filename, 'w+') as text_file:
                print(privateKeyPem, file=text_file)
        except OSError:
            print('EX: unable to save ' + filename)

        # save the public key
        publicKeysSubdir = '/keys/public'
        if not os.path.isdir(baseDir + publicKeysSubdir):
            os.mkdir(baseDir + publicKeysSubdir)
        filename = baseDir + publicKeysSubdir + '/' + handle + '.pem'
        try:
            with open(filename, 'w+') as text_file:
                print(publicKeyPem, file=text_file)
        except OSError:
            print('EX: unable to save 2 ' + filename)

        if password:
            password = removeLineEndings(password)
            storeBasicCredentials(baseDir, nickname, password)

    return privateKeyPem, publicKeyPem, newPerson, webfingerEndpoint


def registerAccount(baseDir: str, httpPrefix: str, domain: str, port: int,
                    nickname: str, password: str,
                    manualFollowerApproval: bool) -> bool:
    """Registers a new account from the web interface
    """
    if _accountExists(baseDir, nickname, domain):
        return False
    if not validNickname(domain, nickname):
        print('REGISTER: Nickname ' + nickname + ' is invalid')
        return False
    if len(password) < 8:
        print('REGISTER: Password should be at least 8 characters')
        return False
    (privateKeyPem, publicKeyPem,
     newPerson, webfingerEndpoint) = createPerson(baseDir, nickname,
                                                  domain, port,
                                                  httpPrefix, True,
                                                  manualFollowerApproval,
                                                  password)
    if privateKeyPem:
        return True
    return False


def createGroup(baseDir: str, nickname: str, domain: str, port: int,
                httpPrefix: str, saveToFile: bool,
                password: str = None) -> (str, str, {}, {}):
    """Returns a group
    """
    (privateKeyPem, publicKeyPem,
     newPerson, webfingerEndpoint) = createPerson(baseDir, nickname,
                                                  domain, port,
                                                  httpPrefix, saveToFile,
                                                  False, password, True)

    return privateKeyPem, publicKeyPem, newPerson, webfingerEndpoint


def savePersonQrcode(baseDir: str,
                     nickname: str, domain: str, port: int,
                     scale=6) -> None:
    """Saves a qrcode image for the handle of the person
    This helps to transfer onion or i2p handles to a mobile device
    """
    qrcodeFilename = acctDir(baseDir, nickname, domain) + '/qrcode.png'
    if os.path.isfile(qrcodeFilename):
        return
    handle = getFullDomain('@' + nickname + '@' + domain, port)
    url = pyqrcode.create(handle)
    url.png(qrcodeFilename, scale)


def createPerson(baseDir: str, nickname: str, domain: str, port: int,
                 httpPrefix: str, saveToFile: bool,
                 manualFollowerApproval: bool,
                 password: str,
                 groupAccount: bool = False) -> (str, str, {}, {}):
    """Returns the private key, public key, actor and webfinger endpoint
    """
    if not validNickname(domain, nickname):
        return None, None, None, None

    # If a config.json file doesn't exist then don't decrement
    # remaining registrations counter
    if nickname != 'news':
        remainingConfigExists = \
            getConfigParam(baseDir, 'registrationsRemaining')
        if remainingConfigExists:
            registrationsRemaining = int(remainingConfigExists)
            if registrationsRemaining <= 0:
                return None, None, None, None
    else:
        if os.path.isdir(baseDir + '/accounts/news@' + domain):
            # news account already exists
            return None, None, None, None

    (privateKeyPem, publicKeyPem,
     newPerson, webfingerEndpoint) = _createPersonBase(baseDir, nickname,
                                                       domain, port,
                                                       httpPrefix,
                                                       saveToFile,
                                                       manualFollowerApproval,
                                                       groupAccount,
                                                       password)
    if not getConfigParam(baseDir, 'admin'):
        if nickname != 'news':
            # print(nickname+' becomes the instance admin and a moderator')
            setConfigParam(baseDir, 'admin', nickname)
            setRole(baseDir, nickname, domain, 'admin')
            setRole(baseDir, nickname, domain, 'moderator')
            setRole(baseDir, nickname, domain, 'editor')

    if not os.path.isdir(baseDir + '/accounts'):
        os.mkdir(baseDir + '/accounts')
    accountDir = acctDir(baseDir, nickname, domain)
    if not os.path.isdir(accountDir):
        os.mkdir(accountDir)

    if manualFollowerApproval:
        followDMsFilename = acctDir(baseDir, nickname, domain) + '/.followDMs'
        try:
            with open(followDMsFilename, 'w+') as fFile:
                fFile.write('\n')
        except OSError:
            print('EX: unable to write ' + followDMsFilename)

    # notify when posts are liked
    if nickname != 'news':
        notifyLikesFilename = \
            acctDir(baseDir, nickname, domain) + '/.notifyLikes'
        try:
            with open(notifyLikesFilename, 'w+') as nFile:
                nFile.write('\n')
        except OSError:
            print('EX: unable to write ' + notifyLikesFilename)

    # notify when posts have emoji reactions
    if nickname != 'news':
        notifyReactionsFilename = \
            acctDir(baseDir, nickname, domain) + '/.notifyReactions'
        try:
            with open(notifyReactionsFilename, 'w+') as nFile:
                nFile.write('\n')
        except OSError:
            print('EX: unable to write ' + notifyReactionsFilename)

    theme = getConfigParam(baseDir, 'theme')
    if not theme:
        theme = 'default'

    if nickname != 'news':
        if os.path.isfile(baseDir + '/img/default-avatar.png'):
            accountDir = acctDir(baseDir, nickname, domain)
            copyfile(baseDir + '/img/default-avatar.png',
                     accountDir + '/avatar.png')
    else:
        newsAvatar = baseDir + '/theme/' + theme + '/icons/avatar_news.png'
        if os.path.isfile(newsAvatar):
            accountDir = acctDir(baseDir, nickname, domain)
            copyfile(newsAvatar, accountDir + '/avatar.png')

    defaultProfileImageFilename = baseDir + '/theme/default/image.png'
    if theme:
        if os.path.isfile(baseDir + '/theme/' + theme + '/image.png'):
            defaultProfileImageFilename = \
                baseDir + '/theme/' + theme + '/image.png'
    if os.path.isfile(defaultProfileImageFilename):
        accountDir = acctDir(baseDir, nickname, domain)
        copyfile(defaultProfileImageFilename, accountDir + '/image.png')
    defaultBannerFilename = baseDir + '/theme/default/banner.png'
    if theme:
        if os.path.isfile(baseDir + '/theme/' + theme + '/banner.png'):
            defaultBannerFilename = baseDir + '/theme/' + theme + '/banner.png'
    if os.path.isfile(defaultBannerFilename):
        accountDir = acctDir(baseDir, nickname, domain)
        copyfile(defaultBannerFilename, accountDir + '/banner.png')
    if nickname != 'news' and remainingConfigExists:
        registrationsRemaining -= 1
        setConfigParam(baseDir, 'registrationsRemaining',
                       str(registrationsRemaining))
    savePersonQrcode(baseDir, nickname, domain, port)
    return privateKeyPem, publicKeyPem, newPerson, webfingerEndpoint


def createSharedInbox(baseDir: str, nickname: str, domain: str, port: int,
                      httpPrefix: str) -> (str, str, {}, {}):
    """Generates the shared inbox
    """
    return _createPersonBase(baseDir, nickname, domain, port, httpPrefix,
                             True, True, False, None)


def createNewsInbox(baseDir: str, domain: str, port: int,
                    httpPrefix: str) -> (str, str, {}, {}):
    """Generates the news inbox
    """
    return createPerson(baseDir, 'news', domain, port,
                        httpPrefix, True, True, None)


def personUpgradeActor(baseDir: str, personJson: {},
                       handle: str, filename: str) -> None:
    """Alter the actor to add any new properties
    """
    updateActor = False
    if not os.path.isfile(filename):
        print('WARN: actor file not found ' + filename)
        return
    if not personJson:
        personJson = loadJson(filename)

    # add a speaker endpoint
    if not personJson.get('tts'):
        personJson['tts'] = personJson['id'] + '/speaker'
        updateActor = True

    if not personJson.get('published'):
        statusNumber, published = getStatusNumber()
        personJson['published'] = published
        updateActor = True

    if personJson.get('shares'):
        if personJson['shares'].endswith('/shares'):
            personJson['shares'] = personJson['id'] + '/catalog'
            updateActor = True

    occupationName = ''
    if personJson.get('occupationName'):
        occupationName = personJson['occupationName']
        del personJson['occupationName']
        updateActor = True
    if personJson.get('occupation'):
        occupationName = personJson['occupation']
        del personJson['occupation']
        updateActor = True

    # if the older skills format is being used then switch
    # to the new one
    if not personJson.get('hasOccupation'):
        personJson['hasOccupation'] = [{
            '@type': 'Occupation',
            'name': occupationName,
            "occupationLocation": {
                "@type": "City",
                "name": "Fediverse"
            },
            'skills': []
        }]
        updateActor = True

    # remove the old skills format
    if personJson.get('skills'):
        del personJson['skills']
        updateActor = True

    # if the older roles format is being used then switch
    # to the new one
    if personJson.get('affiliation'):
        del personJson['affiliation']
        updateActor = True

    if not isinstance(personJson['hasOccupation'], list):
        personJson['hasOccupation'] = [{
            '@type': 'Occupation',
            'name': occupationName,
            'occupationLocation': {
                '@type': 'City',
                'name': 'Fediverse'
            },
            'skills': []
        }]
        updateActor = True
    else:
        # add location if it is missing
        for index in range(len(personJson['hasOccupation'])):
            ocItem = personJson['hasOccupation'][index]
            if ocItem.get('hasOccupation'):
                ocItem = ocItem['hasOccupation']
            if ocItem.get('location'):
                del ocItem['location']
                updateActor = True
            if not ocItem.get('occupationLocation'):
                ocItem['occupationLocation'] = {
                    "@type": "City",
                    "name": "Fediverse"
                }
                updateActor = True
            else:
                if ocItem['occupationLocation']['@type'] != 'City':
                    ocItem['occupationLocation'] = {
                        "@type": "City",
                        "name": "Fediverse"
                    }
                    updateActor = True

    # if no roles are defined then ensure that the admin
    # roles are configured
    rolesList = getActorRolesList(personJson)
    if not rolesList:
        adminName = getConfigParam(baseDir, 'admin')
        if personJson['id'].endswith('/users/' + adminName):
            rolesList = ["admin", "moderator", "editor"]
            setRolesFromList(personJson, rolesList)
            updateActor = True

    # remove the old roles format
    if personJson.get('roles'):
        del personJson['roles']
        updateActor = True

    if updateActor:
        personJson['@context'] = [
            'https://www.w3.org/ns/activitystreams',
            'https://w3id.org/security/v1',
            getDefaultPersonContext()
        ],

        saveJson(personJson, filename)

        # also update the actor within the cache
        actorCacheFilename = \
            baseDir + '/accounts/cache/actors/' + \
            personJson['id'].replace('/', '#') + '.json'
        if os.path.isfile(actorCacheFilename):
            saveJson(personJson, actorCacheFilename)

        # update domain/@nickname in actors cache
        actorCacheFilename = \
            baseDir + '/accounts/cache/actors/' + \
            replaceUsersWithAt(personJson['id']).replace('/', '#') + \
            '.json'
        if os.path.isfile(actorCacheFilename):
            saveJson(personJson, actorCacheFilename)


def personLookup(domain: str, path: str, baseDir: str) -> {}:
    """Lookup the person for an given nickname
    """
    if path.endswith('#main-key'):
        path = path.replace('#main-key', '')
    # is this a shared inbox lookup?
    isSharedInbox = False
    if path == '/inbox' or path == '/users/inbox' or path == '/sharedInbox':
        # shared inbox actor on @domain@domain
        path = '/users/inbox'
        isSharedInbox = True
    else:
        notPersonLookup = ('/inbox', '/outbox', '/outboxarchive',
                           '/followers', '/following', '/featured',
                           '.png', '.jpg', '.gif', '.svg', '.mpv')
        for ending in notPersonLookup:
            if path.endswith(ending):
                return None
    nickname = None
    if path.startswith('/users/'):
        nickname = path.replace('/users/', '', 1)
    if path.startswith('/@'):
        nickname = path.replace('/@', '', 1)
    if not nickname:
        return None
    if not isSharedInbox and not validNickname(domain, nickname):
        return None
    domain = removeDomainPort(domain)
    handle = nickname + '@' + domain
    filename = baseDir + '/accounts/' + handle + '.json'
    if not os.path.isfile(filename):
        return None
    personJson = loadJson(filename)
    if not isSharedInbox:
        personUpgradeActor(baseDir, personJson, handle, filename)
    # if not personJson:
    #     personJson={"user": "unknown"}
    return personJson


def personBoxJson(recentPostsCache: {},
                  session, baseDir: str, domain: str, port: int, path: str,
                  httpPrefix: str, noOfItems: int, boxname: str,
                  authorized: bool,
                  newswireVotesThreshold: int, positiveVoting: bool,
                  votingTimeMins: int) -> {}:
    """Obtain the inbox/outbox/moderation feed for the given person
    """
    if boxname != 'inbox' and boxname != 'dm' and \
       boxname != 'tlreplies' and boxname != 'tlmedia' and \
       boxname != 'tlblogs' and boxname != 'tlnews' and \
       boxname != 'tlfeatures' and \
       boxname != 'outbox' and boxname != 'moderation' and \
       boxname != 'tlbookmarks' and boxname != 'bookmarks':
        print('ERROR: personBoxJson invalid box name ' + boxname)
        return None

    if not '/' + boxname in path:
        return None

    # Only show the header by default
    headerOnly = True

    # handle page numbers
    pageNumber = None
    if '?page=' in path:
        pageNumber = path.split('?page=')[1]
        if pageNumber == 'true':
            pageNumber = 1
        else:
            try:
                pageNumber = int(pageNumber)
            except BaseException:
                print('EX: personBoxJson unable to convert to int ' +
                      str(pageNumber))
                pass
        path = path.split('?page=')[0]
        headerOnly = False

    if not path.endswith('/' + boxname):
        return None
    nickname = None
    if path.startswith('/users/'):
        nickname = path.replace('/users/', '', 1).replace('/' + boxname, '')
    if path.startswith('/@'):
        nickname = path.replace('/@', '', 1).replace('/' + boxname, '')
    if not nickname:
        return None
    if not validNickname(domain, nickname):
        return None
    if boxname == 'inbox':
        return createInbox(recentPostsCache,
                           session, baseDir, nickname, domain, port,
                           httpPrefix,
                           noOfItems, headerOnly, pageNumber)
    elif boxname == 'dm':
        return createDMTimeline(recentPostsCache,
                                session, baseDir, nickname, domain, port,
                                httpPrefix,
                                noOfItems, headerOnly, pageNumber)
    elif boxname == 'tlbookmarks' or boxname == 'bookmarks':
        return createBookmarksTimeline(session, baseDir, nickname, domain,
                                       port, httpPrefix,
                                       noOfItems, headerOnly,
                                       pageNumber)
    elif boxname == 'tlreplies':
        return createRepliesTimeline(recentPostsCache,
                                     session, baseDir, nickname, domain,
                                     port, httpPrefix,
                                     noOfItems, headerOnly,
                                     pageNumber)
    elif boxname == 'tlmedia':
        return createMediaTimeline(session, baseDir, nickname, domain, port,
                                   httpPrefix, noOfItems, headerOnly,
                                   pageNumber)
    elif boxname == 'tlnews':
        return createNewsTimeline(session, baseDir, nickname, domain, port,
                                  httpPrefix, noOfItems, headerOnly,
                                  newswireVotesThreshold, positiveVoting,
                                  votingTimeMins, pageNumber)
    elif boxname == 'tlfeatures':
        return createFeaturesTimeline(session, baseDir, nickname, domain, port,
                                      httpPrefix, noOfItems, headerOnly,
                                      pageNumber)
    elif boxname == 'tlblogs':
        return createBlogsTimeline(session, baseDir, nickname, domain, port,
                                   httpPrefix, noOfItems, headerOnly,
                                   pageNumber)
    elif boxname == 'outbox':
        return createOutbox(session, baseDir, nickname, domain, port,
                            httpPrefix,
                            noOfItems, headerOnly, authorized,
                            pageNumber)
    elif boxname == 'moderation':
        return createModeration(baseDir, nickname, domain, port,
                                httpPrefix,
                                noOfItems, headerOnly,
                                pageNumber)
    return None


def setDisplayNickname(baseDir: str, nickname: str, domain: str,
                       displayName: str) -> bool:
    if len(displayName) > 32:
        return False
    handle = nickname + '@' + domain
    filename = baseDir + '/accounts/' + handle + '.json'
    if not os.path.isfile(filename):
        return False

    personJson = loadJson(filename)
    if not personJson:
        return False
    personJson['name'] = displayName
    saveJson(personJson, filename)
    return True


def setBio(baseDir: str, nickname: str, domain: str, bio: str) -> bool:
    if len(bio) > 32:
        return False
    handle = nickname + '@' + domain
    filename = baseDir + '/accounts/' + handle + '.json'
    if not os.path.isfile(filename):
        return False

    personJson = loadJson(filename)
    if not personJson:
        return False
    if not personJson.get('summary'):
        return False
    personJson['summary'] = bio

    saveJson(personJson, filename)
    return True


def reenableAccount(baseDir: str, nickname: str) -> None:
    """Removes an account suspention
    """
    suspendedFilename = baseDir + '/accounts/suspended.txt'
    if os.path.isfile(suspendedFilename):
        lines = []
        with open(suspendedFilename, 'r') as f:
            lines = f.readlines()
        try:
            with open(suspendedFilename, 'w+') as suspendedFile:
                for suspended in lines:
                    if suspended.strip('\n').strip('\r') != nickname:
                        suspendedFile.write(suspended)
        except OSError as e:
            print('EX: unable to save ' + suspendedFilename +
                  ' ' + str(e))


def suspendAccount(baseDir: str, nickname: str, domain: str) -> None:
    """Suspends the given account
    """
    # Don't suspend the admin
    adminNickname = getConfigParam(baseDir, 'admin')
    if not adminNickname:
        return
    if nickname == adminNickname:
        return

    # Don't suspend moderators
    moderatorsFile = baseDir + '/accounts/moderators.txt'
    if os.path.isfile(moderatorsFile):
        with open(moderatorsFile, 'r') as f:
            lines = f.readlines()
        for moderator in lines:
            if moderator.strip('\n').strip('\r') == nickname:
                return

    saltFilename = acctDir(baseDir, nickname, domain) + '/.salt'
    if os.path.isfile(saltFilename):
        try:
            os.remove(saltFilename)
        except OSError:
            print('EX: suspendAccount unable to delete ' + saltFilename)
    tokenFilename = acctDir(baseDir, nickname, domain) + '/.token'
    if os.path.isfile(tokenFilename):
        try:
            os.remove(tokenFilename)
        except OSError:
            print('EX: suspendAccount unable to delete ' + tokenFilename)

    suspendedFilename = baseDir + '/accounts/suspended.txt'
    if os.path.isfile(suspendedFilename):
        with open(suspendedFilename, 'r') as f:
            lines = f.readlines()
        for suspended in lines:
            if suspended.strip('\n').strip('\r') == nickname:
                return
        try:
            with open(suspendedFilename, 'a+') as suspendedFile:
                suspendedFile.write(nickname + '\n')
        except OSError:
            print('EX: unable to append ' + suspendedFilename)
    else:
        try:
            with open(suspendedFilename, 'w+') as suspendedFile:
                suspendedFile.write(nickname + '\n')
        except OSError:
            print('EX: unable to write ' + suspendedFilename)


def canRemovePost(baseDir: str, nickname: str,
                  domain: str, port: int, postId: str) -> bool:
    """Returns true if the given post can be removed
    """
    if '/statuses/' not in postId:
        return False

    domainFull = getFullDomain(domain, port)

    # is the post by the admin?
    adminNickname = getConfigParam(baseDir, 'admin')
    if not adminNickname:
        return False
    if domainFull + '/users/' + adminNickname + '/' in postId:
        return False

    # is the post by a moderator?
    moderatorsFile = baseDir + '/accounts/moderators.txt'
    if os.path.isfile(moderatorsFile):
        with open(moderatorsFile, 'r') as f:
            lines = f.readlines()
        for moderator in lines:
            if domainFull + '/users/' + moderator.strip('\n') + '/' in postId:
                return False
    return True


def _removeTagsForNickname(baseDir: str, nickname: str,
                           domain: str, port: int) -> None:
    """Removes tags for a nickname
    """
    if not os.path.isdir(baseDir + '/tags'):
        return
    domainFull = getFullDomain(domain, port)
    matchStr = domainFull + '/users/' + nickname + '/'
    directory = os.fsencode(baseDir + '/tags/')
    for f in os.scandir(directory):
        f = f.name
        filename = os.fsdecode(f)
        if not filename.endswith(".txt"):
            continue
        try:
            tagFilename = os.path.join(directory, filename)
        except BaseException:
            print('EX: _removeTagsForNickname unable to join ' +
                  str(directory) + ' ' + str(filename))
            continue
        if not os.path.isfile(tagFilename):
            continue
        if matchStr not in open(tagFilename).read():
            continue
        lines = []
        with open(tagFilename, 'r') as f:
            lines = f.readlines()
        try:
            with open(tagFilename, 'w+') as tagFile:
                for tagline in lines:
                    if matchStr not in tagline:
                        tagFile.write(tagline)
        except OSError:
            print('EX: unable to write ' + tagFilename)


def removeAccount(baseDir: str, nickname: str,
                  domain: str, port: int) -> bool:
    """Removes an account
    """
    # Don't remove the admin
    adminNickname = getConfigParam(baseDir, 'admin')
    if not adminNickname:
        return False
    if nickname == adminNickname:
        return False

    # Don't remove moderators
    moderatorsFile = baseDir + '/accounts/moderators.txt'
    if os.path.isfile(moderatorsFile):
        with open(moderatorsFile, 'r') as f:
            lines = f.readlines()
        for moderator in lines:
            if moderator.strip('\n') == nickname:
                return False

    reenableAccount(baseDir, nickname)
    handle = nickname + '@' + domain
    removePassword(baseDir, nickname)
    _removeTagsForNickname(baseDir, nickname, domain, port)
    if os.path.isdir(baseDir + '/deactivated/' + handle):
        shutil.rmtree(baseDir + '/deactivated/' + handle,
                      ignore_errors=False, onerror=None)
    if os.path.isdir(baseDir + '/accounts/' + handle):
        shutil.rmtree(baseDir + '/accounts/' + handle,
                      ignore_errors=False, onerror=None)
    if os.path.isfile(baseDir + '/accounts/' + handle + '.json'):
        try:
            os.remove(baseDir + '/accounts/' + handle + '.json')
        except OSError:
            print('EX: removeAccount unable to delete ' +
                  baseDir + '/accounts/' + handle + '.json')
    if os.path.isfile(baseDir + '/wfendpoints/' + handle + '.json'):
        try:
            os.remove(baseDir + '/wfendpoints/' + handle + '.json')
        except OSError:
            print('EX: removeAccount unable to delete ' +
                  baseDir + '/wfendpoints/' + handle + '.json')
    if os.path.isfile(baseDir + '/keys/private/' + handle + '.key'):
        try:
            os.remove(baseDir + '/keys/private/' + handle + '.key')
        except OSError:
            print('EX: removeAccount unable to delete ' +
                  baseDir + '/keys/private/' + handle + '.key')
    if os.path.isfile(baseDir + '/keys/public/' + handle + '.pem'):
        try:
            os.remove(baseDir + '/keys/public/' + handle + '.pem')
        except OSError:
            print('EX: removeAccount unable to delete ' +
                  baseDir + '/keys/public/' + handle + '.pem')
    if os.path.isdir(baseDir + '/sharefiles/' + nickname):
        shutil.rmtree(baseDir + '/sharefiles/' + nickname,
                      ignore_errors=False, onerror=None)
    if os.path.isfile(baseDir + '/wfdeactivated/' + handle + '.json'):
        try:
            os.remove(baseDir + '/wfdeactivated/' + handle + '.json')
        except OSError:
            print('EX: removeAccount unable to delete ' +
                  baseDir + '/wfdeactivated/' + handle + '.json')
    if os.path.isdir(baseDir + '/sharefilesdeactivated/' + nickname):
        shutil.rmtree(baseDir + '/sharefilesdeactivated/' + nickname,
                      ignore_errors=False, onerror=None)

    refreshNewswire(baseDir)

    return True


def deactivateAccount(baseDir: str, nickname: str, domain: str) -> bool:
    """Makes an account temporarily unavailable
    """
    handle = nickname + '@' + domain

    accountDir = baseDir + '/accounts/' + handle
    if not os.path.isdir(accountDir):
        return False
    deactivatedDir = baseDir + '/deactivated'
    if not os.path.isdir(deactivatedDir):
        os.mkdir(deactivatedDir)
    shutil.move(accountDir, deactivatedDir + '/' + handle)

    if os.path.isfile(baseDir + '/wfendpoints/' + handle + '.json'):
        deactivatedWebfingerDir = baseDir + '/wfdeactivated'
        if not os.path.isdir(deactivatedWebfingerDir):
            os.mkdir(deactivatedWebfingerDir)
        shutil.move(baseDir + '/wfendpoints/' + handle + '.json',
                    deactivatedWebfingerDir + '/' + handle + '.json')

    if os.path.isdir(baseDir + '/sharefiles/' + nickname):
        deactivatedSharefilesDir = baseDir + '/sharefilesdeactivated'
        if not os.path.isdir(deactivatedSharefilesDir):
            os.mkdir(deactivatedSharefilesDir)
        shutil.move(baseDir + '/sharefiles/' + nickname,
                    deactivatedSharefilesDir + '/' + nickname)

    refreshNewswire(baseDir)

    return os.path.isdir(deactivatedDir + '/' + nickname + '@' + domain)


def activateAccount(baseDir: str, nickname: str, domain: str) -> None:
    """Makes a deactivated account available
    """
    handle = nickname + '@' + domain

    deactivatedDir = baseDir + '/deactivated'
    deactivatedAccountDir = deactivatedDir + '/' + handle
    if os.path.isdir(deactivatedAccountDir):
        accountDir = baseDir + '/accounts/' + handle
        if not os.path.isdir(accountDir):
            shutil.move(deactivatedAccountDir, accountDir)

    deactivatedWebfingerDir = baseDir + '/wfdeactivated'
    if os.path.isfile(deactivatedWebfingerDir + '/' + handle + '.json'):
        shutil.move(deactivatedWebfingerDir + '/' + handle + '.json',
                    baseDir + '/wfendpoints/' + handle + '.json')

    deactivatedSharefilesDir = baseDir + '/sharefilesdeactivated'
    if os.path.isdir(deactivatedSharefilesDir + '/' + nickname):
        if not os.path.isdir(baseDir + '/sharefiles/' + nickname):
            shutil.move(deactivatedSharefilesDir + '/' + nickname,
                        baseDir + '/sharefiles/' + nickname)

    refreshNewswire(baseDir)


def isPersonSnoozed(baseDir: str, nickname: str, domain: str,
                    snoozeActor: str) -> bool:
    """Returns true if the given actor is snoozed
    """
    snoozedFilename = acctDir(baseDir, nickname, domain) + '/snoozed.txt'
    if not os.path.isfile(snoozedFilename):
        return False
    if snoozeActor + ' ' not in open(snoozedFilename).read():
        return False
    # remove the snooze entry if it has timed out
    replaceStr = None
    with open(snoozedFilename, 'r') as snoozedFile:
        for line in snoozedFile:
            # is this the entry for the actor?
            if line.startswith(snoozeActor + ' '):
                snoozedTimeStr = \
                    line.split(' ')[1].replace('\n', '').replace('\r', '')
                # is there a time appended?
                if snoozedTimeStr.isdigit():
                    snoozedTime = int(snoozedTimeStr)
                    currTime = int(time.time())
                    # has the snooze timed out?
                    if int(currTime - snoozedTime) > 60 * 60 * 24:
                        replaceStr = line
                else:
                    replaceStr = line
                break
    if replaceStr:
        content = None
        with open(snoozedFilename, 'r') as snoozedFile:
            content = snoozedFile.read().replace(replaceStr, '')
        if content:
            try:
                with open(snoozedFilename, 'w+') as writeSnoozedFile:
                    writeSnoozedFile.write(content)
            except OSError:
                print('EX: unable to write ' + snoozedFilename)

    if snoozeActor + ' ' in open(snoozedFilename).read():
        return True
    return False


def personSnooze(baseDir: str, nickname: str, domain: str,
                 snoozeActor: str) -> None:
    """Temporarily ignores the given actor
    """
    accountDir = acctDir(baseDir, nickname, domain)
    if not os.path.isdir(accountDir):
        print('ERROR: unknown account ' + accountDir)
        return
    snoozedFilename = accountDir + '/snoozed.txt'
    if os.path.isfile(snoozedFilename):
        if snoozeActor + ' ' in open(snoozedFilename).read():
            return
    try:
        with open(snoozedFilename, 'a+') as snoozedFile:
            snoozedFile.write(snoozeActor + ' ' +
                              str(int(time.time())) + '\n')
    except OSError:
        print('EX: unable to append ' + snoozedFilename)


def personUnsnooze(baseDir: str, nickname: str, domain: str,
                   snoozeActor: str) -> None:
    """Undoes a temporarily ignore of the given actor
    """
    accountDir = acctDir(baseDir, nickname, domain)
    if not os.path.isdir(accountDir):
        print('ERROR: unknown account ' + accountDir)
        return
    snoozedFilename = accountDir + '/snoozed.txt'
    if not os.path.isfile(snoozedFilename):
        return
    if snoozeActor + ' ' not in open(snoozedFilename).read():
        return
    replaceStr = None
    with open(snoozedFilename, 'r') as snoozedFile:
        for line in snoozedFile:
            if line.startswith(snoozeActor + ' '):
                replaceStr = line
                break
    if replaceStr:
        content = None
        with open(snoozedFilename, 'r') as snoozedFile:
            content = snoozedFile.read().replace(replaceStr, '')
        if content:
            try:
                with open(snoozedFilename, 'w+') as writeSnoozedFile:
                    writeSnoozedFile.write(content)
            except OSError:
                print('EX: unable to write ' + snoozedFilename)


def setPersonNotes(baseDir: str, nickname: str, domain: str,
                   handle: str, notes: str) -> bool:
    """Adds notes about a person
    """
    if '@' not in handle:
        return False
    if handle.startswith('@'):
        handle = handle[1:]
    notesDir = acctDir(baseDir, nickname, domain) + '/notes'
    if not os.path.isdir(notesDir):
        os.mkdir(notesDir)
    notesFilename = notesDir + '/' + handle + '.txt'
    try:
        with open(notesFilename, 'w+') as notesFile:
            notesFile.write(notes)
    except OSError:
        print('EX: unable to write ' + notesFilename)
        return False
    return True


def _detectUsersPath(url: str) -> str:
    """Tries to detect the /users/ path
    """
    if '/' not in url:
        return '/users/'
    usersPaths = getUserPaths()
    for possibleUsersPath in usersPaths:
        if possibleUsersPath in url:
            return possibleUsersPath
    return '/users/'


def getActorJson(hostDomain: str, handle: str, http: bool, gnunet: bool,
                 debug: bool, quiet: bool,
                 signingPrivateKeyPem: str) -> ({}, {}):
    """Returns the actor json
    """
    if debug:
        print('getActorJson for ' + handle)
    originalActor = handle
    groupAccount = False

    # try to determine the users path
    detectedUsersPath = _detectUsersPath(handle)
    if '/@' in handle or \
       detectedUsersPath in handle or \
       handle.startswith('http') or \
       handle.startswith('hyper'):
        groupPaths = getGroupPaths()
        if detectedUsersPath in groupPaths:
            groupAccount = True
        # format: https://domain/@nick
        originalHandle = handle
        if not hasUsersPath(originalHandle):
            if not quiet or debug:
                print('getActorJson: Expected actor format: ' +
                      'https://domain/@nick or https://domain' +
                      detectedUsersPath + 'nick')
            return None, None
        prefixes = getProtocolPrefixes()
        for prefix in prefixes:
            handle = handle.replace(prefix, '')
        handle = handle.replace('/@', detectedUsersPath)
        paths = getUserPaths()
        userPathFound = False
        for userPath in paths:
            if userPath in handle:
                nickname = handle.split(userPath)[1]
                nickname = nickname.replace('\n', '').replace('\r', '')
                domain = handle.split(userPath)[0]
                userPathFound = True
                break
        if not userPathFound and '://' in originalHandle:
            domain = originalHandle.split('://')[1]
            if '/' in domain:
                domain = domain.split('/')[0]
            if '://' + domain + '/' not in originalHandle:
                return None, None
            nickname = originalHandle.split('://' + domain + '/')[1]
            if '/' in nickname or '.' in nickname:
                return None, None
    else:
        # format: @nick@domain
        if '@' not in handle:
            if not quiet:
                print('getActorJson Syntax: --actor nickname@domain')
            return None, None
        if handle.startswith('@'):
            handle = handle[1:]
        elif handle.startswith('!'):
            # handle for a group
            handle = handle[1:]
            groupAccount = True
        if '@' not in handle:
            if not quiet:
                print('getActorJsonSyntax: --actor nickname@domain')
            return None, None
        nickname = handle.split('@')[0]
        domain = handle.split('@')[1]
        domain = domain.replace('\n', '').replace('\r', '')

    cachedWebfingers = {}
    proxyType = None
    if http or domain.endswith('.onion'):
        httpPrefix = 'http'
        proxyType = 'tor'
    elif domain.endswith('.i2p'):
        httpPrefix = 'http'
        proxyType = 'i2p'
    elif gnunet:
        httpPrefix = 'gnunet'
        proxyType = 'gnunet'
    else:
        if '127.0.' not in domain and '192.168.' not in domain:
            httpPrefix = 'https'
        else:
            httpPrefix = 'http'
    session = createSession(proxyType)
    if nickname == 'inbox':
        nickname = domain

    personUrl = None
    wfRequest = None

    if '://' in originalActor and \
       originalActor.lower().endswith('/actor'):
        if debug:
            print(originalActor + ' is an instance actor')
        personUrl = originalActor
    elif '://' in originalActor and groupAccount:
        if debug:
            print(originalActor + ' is a group actor')
        personUrl = originalActor
    else:
        handle = nickname + '@' + domain
        wfRequest = webfingerHandle(session, handle,
                                    httpPrefix, cachedWebfingers,
                                    hostDomain, __version__, debug,
                                    groupAccount, signingPrivateKeyPem)
        if not wfRequest:
            if not quiet:
                print('getActorJson Unable to webfinger ' + handle)
            return None, None
        if not isinstance(wfRequest, dict):
            if not quiet:
                print('getActorJson Webfinger for ' + handle +
                      ' did not return a dict. ' + str(wfRequest))
            return None, None

        if not quiet:
            pprint(wfRequest)

        if wfRequest.get('errors'):
            if not quiet or debug:
                print('getActorJson wfRequest error: ' +
                      str(wfRequest['errors']))
            if hasUsersPath(handle):
                personUrl = originalActor
            else:
                if debug:
                    print('No users path in ' + handle)
                return None, None

    profileStr = 'https://www.w3.org/ns/activitystreams'
    headersList = (
        "activity+json", "ld+json", "jrd+json"
    )
    if not personUrl and wfRequest:
        personUrl = getUserUrl(wfRequest, 0, debug)
    if nickname == domain:
        paths = getUserPaths()
        for userPath in paths:
            personUrl = personUrl.replace(userPath, '/actor/')
    if not personUrl and groupAccount:
        personUrl = httpPrefix + '://' + domain + '/c/' + nickname
    if not personUrl:
        # try single user instance
        personUrl = httpPrefix + '://' + domain + '/' + nickname
        headersList = (
            "ld+json", "jrd+json", "activity+json"
        )
        if debug:
            print('Trying single user instance ' + personUrl)
    if '/channel/' in personUrl or '/accounts/' in personUrl:
        headersList = (
            "ld+json", "jrd+json", "activity+json"
        )
    if debug:
        print('personUrl: ' + personUrl)
    for headerType in headersList:
        headerMimeType = 'application/' + headerType
        asHeader = {
            'Accept': headerMimeType + '; profile="' + profileStr + '"'
        }
        personJson = \
            getJson(signingPrivateKeyPem, session, personUrl, asHeader, None,
                    debug, __version__, httpPrefix, hostDomain, 20, quiet)
        if personJson:
            if not quiet:
                pprint(personJson)
            return personJson, asHeader
    return None, None


def getPersonAvatarUrl(baseDir: str, personUrl: str, personCache: {},
                       allowDownloads: bool) -> str:
    """Returns the avatar url for the person
    """
    personJson = \
        getPersonFromCache(baseDir, personUrl, personCache, allowDownloads)
    if not personJson:
        return None

    # get from locally stored image
    if not personJson.get('id'):
        return None
    actorStr = personJson['id'].replace('/', '-')
    avatarImagePath = baseDir + '/cache/avatars/' + actorStr

    imageExtension = getImageExtensions()
    for ext in imageExtension:
        imFilename = avatarImagePath + '.' + ext
        imPath = '/avatars/' + actorStr + '.' + ext
        if not os.path.isfile(imFilename):
            imFilename = avatarImagePath.lower() + '.' + ext
            imPath = '/avatars/' + actorStr.lower() + '.' + ext
            if not os.path.isfile(imFilename):
                continue
        if ext != 'svg':
            return imPath
        else:
            content = ''
            with open(imFilename, 'r') as fp:
                content = fp.read()
            if not dangerousSVG(content, False):
                return imPath

    if personJson.get('icon'):
        if personJson['icon'].get('url'):
            if '.svg' not in personJson['icon']['url'].lower():
                return personJson['icon']['url']
    return None


def addActorUpdateTimestamp(actorJson: {}) -> None:
    """Adds 'updated' fields with a timestamp
    """
    updatedTime = datetime.datetime.utcnow()
    currDateStr = updatedTime.strftime("%Y-%m-%dT%H:%M:%SZ")
    actorJson['updated'] = currDateStr
    # add updated timestamp to avatar and banner
    actorJson['icon']['updated'] = currDateStr
    actorJson['image']['updated'] = currDateStr
