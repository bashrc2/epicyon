__filename__ = "person.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import time
import os
import subprocess
import shutil
import pyqrcode
from random import randint
from pathlib import Path
try:
    from Cryptodome.PublicKey import RSA
except ImportError:
    from Crypto.PublicKey import RSA
from shutil import copyfile
from webfinger import createWebfingerEndpoint
from webfinger import storeWebfingerEndpoint
from posts import createDMTimeline
from posts import createRepliesTimeline
from posts import createMediaTimeline
from posts import createNewsTimeline
from posts import createBlogsTimeline
from posts import createFeaturesTimeline
from posts import createBookmarksTimeline
from posts import createEventsTimeline
from posts import createInbox
from posts import createOutbox
from posts import createModeration
from auth import storeBasicCredentials
from auth import removePassword
from roles import setRole
from media import removeMetaData
from utils import getFullDomain
from utils import validNickname
from utils import loadJson
from utils import saveJson
from utils import setConfigParam
from utils import getConfigParam


def generateRSAKey() -> (str, str):
    key = RSA.generate(2048)
    privateKeyPem = key.exportKey("PEM").decode("utf-8")
    publicKeyPem = key.publickey().exportKey("PEM").decode("utf-8")
    return privateKeyPem, publicKeyPem


def setProfileImage(baseDir: str, httpPrefix: str, nickname: str, domain: str,
                    port: int, imageFilename: str, imageType: str,
                    resolution: str) -> bool:
    """Saves the given image file as an avatar or background
    image for the given person
    """
    imageFilename = imageFilename.replace('\n', '').replace('\r', '')
    if not (imageFilename.endswith('.png') or
            imageFilename.endswith('.jpg') or
            imageFilename.endswith('.jpeg') or
            imageFilename.endswith('.svg') or
            imageFilename.endswith('.gif')):
        print('Profile image must be png, jpg, gif or svg format')
        return False

    if imageFilename.startswith('~/'):
        imageFilename = imageFilename.replace('~/', str(Path.home()) + '/')

    if ':' in domain:
        domain = domain.split(':')[0]
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
    if imageFilename.endswith('.gif'):
        mediaType = 'image/gif'
        iconFilename = iconFilenameBase + '.gif'
    if imageFilename.endswith('.svg'):
        mediaType = 'image/svg+xml'
        iconFilename = iconFilenameBase + '.svg'
    profileFilename = baseDir + '/accounts/' + handle + '/' + iconFilename

    personJson = loadJson(personFilename)
    if personJson:
        personJson[iconFilenameBase]['mediaType'] = mediaType
        personJson[iconFilenameBase]['url'] = \
            httpPrefix + '://' + fullDomain + '/users/' + \
            nickname + '/'+iconFilename
        saveJson(personJson, personFilename)

        cmd = \
            '/usr/bin/convert ' + imageFilename + ' -size ' + \
            resolution + ' -quality 50 ' + profileFilename
        subprocess.call(cmd, shell=True)
        removeMetaData(profileFilename, profileFilename)
        return True
    return False


def setOrganizationScheme(baseDir: str, nickname: str, domain: str,
                          schema: str) -> bool:
    """Set the organization schema within which a person exists
    This will define how roles, skills and availability are assembled
    into organizations
    """
    # avoid giant strings
    if len(schema) > 256:
        return False
    actorFilename = baseDir + '/accounts/' + nickname + '@' + domain + '.json'
    if not os.path.isfile(actorFilename):
        return False

    actorJson = loadJson(actorFilename)
    if actorJson:
        actorJson['orgSchema'] = schema
        saveJson(actorJson, actorFilename)
    return True


def _accountExists(baseDir: str, nickname: str, domain: str) -> bool:
    """Returns true if the given account exists
    """
    if ':' in domain:
        domain = domain.split(':')[0]
    return os.path.isdir(baseDir + '/accounts/' + nickname + '@' + domain) or \
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
    personJson['icon']['url'] = \
        personId + '/avatar' + randStr + '.' + existingExtension
    lastPartOfFilename = personJson['image']['url'].split('/')[-1]
    existingExtension = lastPartOfFilename.split('.')[1]
    randStr = str(randint(10000000000000, 99999999999999))  # nosec
    personJson['image']['url'] = \
        personId + '/image' + randStr + '.' + existingExtension


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
        'value': 'schema:value'
    }


def _createPersonBase(baseDir: str, nickname: str, domain: str, port: int,
                      httpPrefix: str, saveToFile: bool,
                      manualFollowerApproval: bool,
                      password=None) -> (str, str, {}, {}):
    """Returns the private key, public key, actor and webfinger endpoint
    """
    privateKeyPem, publicKeyPem = generateRSAKey()
    webfingerEndpoint = \
        createWebfingerEndpoint(nickname, domain, port,
                                httpPrefix, publicKeyPem)
    if saveToFile:
        storeWebfingerEndpoint(nickname, domain, port,
                               baseDir, webfingerEndpoint)

    handle = nickname + '@' + domain
    originalDomain = domain
    domain = getFullDomain(domain, port)

    personType = 'Person'
    # Enable follower approval by default
    approveFollowers = manualFollowerApproval
    personName = nickname
    personId = httpPrefix + '://' + domain + '/users/' + nickname
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

    newPerson = {
        '@context': [
            'https://www.w3.org/ns/activitystreams',
            'https://w3id.org/security/v1',
            getDefaultPersonContext()
        ],
        'alsoKnownAs': [],
        'attachment': [],
        'devices': personId + '/collections/devices',
        'endpoints': {
            'id': personId + '/endpoints',
            'sharedInbox': httpPrefix+'://' + domain + '/inbox',
        },
        'featured': personId + '/collections/featured',
        'featuredTags': personId + '/collections/tags',
        'followers': personId + '/followers',
        'following': personId + '/following',
        'shares': personId + '/shares',
        'orgSchema': None,
        'skills': {},
        'roles': {},
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
        del newPerson['skills']
        del newPerson['shares']
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
        with open(filename, 'w+') as text_file:
            print(privateKeyPem, file=text_file)

        # save the public key
        publicKeysSubdir = '/keys/public'
        if not os.path.isdir(baseDir + publicKeysSubdir):
            os.mkdir(baseDir + publicKeysSubdir)
        filename = baseDir + publicKeysSubdir + '/' + handle + '.pem'
        with open(filename, 'w+') as text_file:
            print(publicKeyPem, file=text_file)

        if password:
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
                password=None) -> (str, str, {}, {}):
    """Returns a group
    """
    (privateKeyPem, publicKeyPem,
     newPerson, webfingerEndpoint) = createPerson(baseDir, nickname,
                                                  domain, port,
                                                  httpPrefix, saveToFile,
                                                  False, password)
    newPerson['type'] = 'Group'
    return privateKeyPem, publicKeyPem, newPerson, webfingerEndpoint


def savePersonQrcode(baseDir: str,
                     nickname: str, domain: str, port: int,
                     scale=6) -> None:
    """Saves a qrcode image for the handle of the person
    This helps to transfer onion or i2p handles to a mobile device
    """
    qrcodeFilename = baseDir + '/accounts/' + \
        nickname + '@' + domain + '/qrcode.png'
    if os.path.isfile(qrcodeFilename):
        return
    handle = getFullDomain('@' + nickname + '@' + domain, port)
    url = pyqrcode.create(handle)
    url.png(qrcodeFilename, scale)


def createPerson(baseDir: str, nickname: str, domain: str, port: int,
                 httpPrefix: str, saveToFile: bool,
                 manualFollowerApproval: bool,
                 password=None) -> (str, str, {}, {}):
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
                                                       password)
    if not getConfigParam(baseDir, 'admin'):
        if nickname != 'news':
            # print(nickname+' becomes the instance admin and a moderator')
            setConfigParam(baseDir, 'admin', nickname)
            setRole(baseDir, nickname, domain, 'instance', 'admin')
            setRole(baseDir, nickname, domain, 'instance', 'moderator')
            setRole(baseDir, nickname, domain, 'instance', 'editor')
            setRole(baseDir, nickname, domain, 'instance', 'delegator')

    if not os.path.isdir(baseDir + '/accounts'):
        os.mkdir(baseDir + '/accounts')
    if not os.path.isdir(baseDir + '/accounts/' + nickname + '@' + domain):
        os.mkdir(baseDir + '/accounts/' + nickname + '@' + domain)

    if manualFollowerApproval:
        followDMsFilename = baseDir + '/accounts/' + \
            nickname + '@' + domain + '/.followDMs'
        with open(followDMsFilename, 'w+') as fFile:
            fFile.write('\n')

    # notify when posts are liked
    if nickname != 'news':
        notifyLikesFilename = baseDir + '/accounts/' + \
            nickname + '@' + domain + '/.notifyLikes'
        with open(notifyLikesFilename, 'w+') as nFile:
            nFile.write('\n')

    theme = getConfigParam(baseDir, 'theme')
    if not theme:
        theme = 'default'

    if nickname != 'news':
        if os.path.isfile(baseDir + '/img/default-avatar.png'):
            copyfile(baseDir + '/img/default-avatar.png',
                     baseDir + '/accounts/' + nickname + '@' + domain +
                     '/avatar.png')
    else:
        newsAvatar = baseDir + '/theme/' + theme + '/icons/avatar_news.png'
        if os.path.isfile(newsAvatar):
            copyfile(newsAvatar,
                     baseDir + '/accounts/' + nickname + '@' + domain +
                     '/avatar.png')

    defaultProfileImageFilename = baseDir + '/theme/default/image.png'
    if theme:
        if os.path.isfile(baseDir + '/theme/' + theme + '/image.png'):
            defaultProfileImageFilename = \
                baseDir + '/theme/' + theme + '/image.png'
    if os.path.isfile(defaultProfileImageFilename):
        copyfile(defaultProfileImageFilename, baseDir +
                 '/accounts/' + nickname + '@' + domain + '/image.png')
    defaultBannerFilename = baseDir + '/theme/default/banner.png'
    if theme:
        if os.path.isfile(baseDir + '/theme/' + theme + '/banner.png'):
            defaultBannerFilename = baseDir + '/theme/' + theme + '/banner.png'
    if os.path.isfile(defaultBannerFilename):
        copyfile(defaultBannerFilename, baseDir + '/accounts/' +
                 nickname + '@' + domain + '/banner.png')
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
                             True, True, None)


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

    if updateActor:
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
            personJson['id'].replace('/users/', '/@').replace('/', '#') + \
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
        path = '/users/' + domain
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
    if ':' in domain:
        domain = domain.split(':')[0]
    handle = nickname + '@' + domain
    filename = baseDir + '/accounts/' + handle + '.json'
    if not os.path.isfile(filename):
        return None
    personJson = loadJson(filename)
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
       boxname != 'tlbookmarks' and boxname != 'bookmarks' and \
       boxname != 'tlevents':
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
    elif boxname == 'tlevents':
        return createEventsTimeline(recentPostsCache,
                                    session, baseDir, nickname, domain,
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
        with open(suspendedFilename, "r") as f:
            lines = f.readlines()
        suspendedFile = open(suspendedFilename, "w+")
        for suspended in lines:
            if suspended.strip('\n').strip('\r') != nickname:
                suspendedFile.write(suspended)
        suspendedFile.close()


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
        with open(moderatorsFile, "r") as f:
            lines = f.readlines()
        for moderator in lines:
            if moderator.strip('\n').strip('\r') == nickname:
                return

    saltFilename = baseDir + '/accounts/' + \
        nickname + '@' + domain + '/.salt'
    if os.path.isfile(saltFilename):
        os.remove(saltFilename)
    tokenFilename = baseDir + '/accounts/' + \
        nickname + '@' + domain + '/.token'
    if os.path.isfile(tokenFilename):
        os.remove(tokenFilename)

    suspendedFilename = baseDir + '/accounts/suspended.txt'
    if os.path.isfile(suspendedFilename):
        with open(suspendedFilename, "r") as f:
            lines = f.readlines()
        for suspended in lines:
            if suspended.strip('\n').strip('\r') == nickname:
                return
        suspendedFile = open(suspendedFilename, 'a+')
        if suspendedFile:
            suspendedFile.write(nickname + '\n')
            suspendedFile.close()
    else:
        suspendedFile = open(suspendedFilename, 'w+')
        if suspendedFile:
            suspendedFile.write(nickname + '\n')
            suspendedFile.close()


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
        with open(moderatorsFile, "r") as f:
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
            continue
        if not os.path.isfile(tagFilename):
            continue
        if matchStr not in open(tagFilename).read():
            continue
        with open(tagFilename, "r") as f:
            lines = f.readlines()
        tagFile = open(tagFilename, "w+")
        if tagFile:
            for tagline in lines:
                if matchStr not in tagline:
                    tagFile.write(tagline)
            tagFile.close()


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
        with open(moderatorsFile, "r") as f:
            lines = f.readlines()
        for moderator in lines:
            if moderator.strip('\n') == nickname:
                return False

    reenableAccount(baseDir, nickname)
    handle = nickname + '@' + domain
    removePassword(baseDir, nickname)
    _removeTagsForNickname(baseDir, nickname, domain, port)
    if os.path.isdir(baseDir + '/deactivated/' + handle):
        shutil.rmtree(baseDir + '/deactivated/' + handle)
    if os.path.isdir(baseDir + '/accounts/' + handle):
        shutil.rmtree(baseDir + '/accounts/' + handle)
    if os.path.isfile(baseDir + '/accounts/' + handle + '.json'):
        os.remove(baseDir + '/accounts/' + handle + '.json')
    if os.path.isfile(baseDir + '/wfendpoints/' + handle + '.json'):
        os.remove(baseDir + '/wfendpoints/' + handle + '.json')
    if os.path.isfile(baseDir + '/keys/private/' + handle + '.key'):
        os.remove(baseDir + '/keys/private/' + handle + '.key')
    if os.path.isfile(baseDir + '/keys/public/' + handle + '.pem'):
        os.remove(baseDir + '/keys/public/' + handle + '.pem')
    if os.path.isdir(baseDir + '/sharefiles/' + nickname):
        shutil.rmtree(baseDir + '/sharefiles/' + nickname)
    if os.path.isfile(baseDir + '/wfdeactivated/' + handle + '.json'):
        os.remove(baseDir + '/wfdeactivated/' + handle + '.json')
    if os.path.isdir(baseDir + '/sharefilesdeactivated/' + nickname):
        shutil.rmtree(baseDir + '/sharefilesdeactivated/' + nickname)
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


def isPersonSnoozed(baseDir: str, nickname: str, domain: str,
                    snoozeActor: str) -> bool:
    """Returns true if the given actor is snoozed
    """
    snoozedFilename = baseDir + '/accounts/' + \
        nickname + '@' + domain + '/snoozed.txt'
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
            writeSnoozedFile = open(snoozedFilename, 'w+')
            if writeSnoozedFile:
                writeSnoozedFile.write(content)
                writeSnoozedFile.close()

    if snoozeActor + ' ' in open(snoozedFilename).read():
        return True
    return False


def personSnooze(baseDir: str, nickname: str, domain: str,
                 snoozeActor: str) -> None:
    """Temporarily ignores the given actor
    """
    accountDir = baseDir + '/accounts/' + nickname + '@' + domain
    if not os.path.isdir(accountDir):
        print('ERROR: unknown account ' + accountDir)
        return
    snoozedFilename = accountDir + '/snoozed.txt'
    if os.path.isfile(snoozedFilename):
        if snoozeActor + ' ' in open(snoozedFilename).read():
            return
    snoozedFile = open(snoozedFilename, "a+")
    if snoozedFile:
        snoozedFile.write(snoozeActor + ' ' +
                          str(int(time.time())) + '\n')
        snoozedFile.close()


def personUnsnooze(baseDir: str, nickname: str, domain: str,
                   snoozeActor: str) -> None:
    """Undoes a temporarily ignore of the given actor
    """
    accountDir = baseDir + '/accounts/' + nickname + '@' + domain
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
            writeSnoozedFile = open(snoozedFilename, 'w+')
            if writeSnoozedFile:
                writeSnoozedFile.write(content)
                writeSnoozedFile.close()


def setPersonNotes(baseDir: str, nickname: str, domain: str,
                   handle: str, notes: str) -> bool:
    """Adds notes about a person
    """
    if '@' not in handle:
        return False
    if handle.startswith('@'):
        handle = handle[1:]
    notesDir = baseDir + '/accounts/' + \
        nickname + '@' + domain + '/notes'
    if not os.path.isdir(notesDir):
        os.mkdir(notesDir)
    notesFilename = notesDir + '/' + handle + '.txt'
    with open(notesFilename, 'w+') as notesFile:
        notesFile.write(notes)
    return True
