__filename__ = "pgp.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import subprocess


def getEmailAddress(actorJson: {}) -> str:
    """Returns the email address for the given actor
    """
    if not actorJson.get('attachment'):
        return ''
    for propertyValue in actorJson['attachment']:
        if not propertyValue.get('name'):
            continue
        if not propertyValue['name'].lower().startswith('email'):
            continue
        if not propertyValue.get('type'):
            continue
        if not propertyValue.get('value'):
            continue
        if propertyValue['type'] != 'PropertyValue':
            continue
        if '@' not in propertyValue['value']:
            continue
        if '.' not in propertyValue['value']:
            continue
        return propertyValue['value']
    return ''


def getPGPpubKey(actorJson: {}) -> str:
    """Returns PGP public key for the given actor
    """
    if not actorJson.get('attachment'):
        return ''
    for propertyValue in actorJson['attachment']:
        if not propertyValue.get('name'):
            continue
        if not propertyValue['name'].lower().startswith('pgp'):
            continue
        if not propertyValue.get('type'):
            continue
        if not propertyValue.get('value'):
            continue
        if propertyValue['type'] != 'PropertyValue':
            continue
        if '--BEGIN PGP PUBLIC KEY' not in propertyValue['value']:
            continue
        return propertyValue['value']
    return ''


def getPGPfingerprint(actorJson: {}) -> str:
    """Returns PGP fingerprint for the given actor
    """
    if not actorJson.get('attachment'):
        return ''
    for propertyValue in actorJson['attachment']:
        if not propertyValue.get('name'):
            continue
        if not propertyValue['name'].lower().startswith('openpgp'):
            continue
        if not propertyValue.get('type'):
            continue
        if not propertyValue.get('value'):
            continue
        if propertyValue['type'] != 'PropertyValue':
            continue
        if len(propertyValue['value']) < 10:
            continue
        return propertyValue['value']
    return ''


def setEmailAddress(actorJson: {}, emailAddress: str) -> None:
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

    if not actorJson.get('attachment'):
        actorJson['attachment'] = []

    # remove any existing value
    propertyFound = None
    for propertyValue in actorJson['attachment']:
        if not propertyValue.get('name'):
            continue
        if not propertyValue.get('type'):
            continue
        if not propertyValue['name'].lower().startswith('email'):
            continue
        propertyFound = propertyValue
        break
    if propertyFound:
        actorJson['attachment'].remove(propertyFound)
    if notEmailAddress:
        return

    for propertyValue in actorJson['attachment']:
        if not propertyValue.get('name'):
            continue
        if not propertyValue.get('type'):
            continue
        if not propertyValue['name'].lower().startswith('email'):
            continue
        if propertyValue['type'] != 'PropertyValue':
            continue
        propertyValue['value'] = emailAddress
        return

    newEmailAddress = {
        "name": "Email",
        "type": "PropertyValue",
        "value": emailAddress
    }
    actorJson['attachment'].append(newEmailAddress)


def setPGPpubKey(actorJson: {}, PGPpubKey: str) -> None:
    """Sets a PGP public key for the given actor
    """
    removeKey = False
    if not PGPpubKey:
        removeKey = True
    else:
        if '--BEGIN PGP PUBLIC KEY' not in PGPpubKey:
            removeKey = True
        if '<' in PGPpubKey:
            removeKey = True

    if not actorJson.get('attachment'):
        actorJson['attachment'] = []

    # remove any existing value
    propertyFound = None
    for propertyValue in actorJson['attachment']:
        if not propertyValue.get('name'):
            continue
        if not propertyValue.get('type'):
            continue
        if not propertyValue['name'].lower().startswith('pgp'):
            continue
        propertyFound = propertyValue
        break
    if propertyFound:
        actorJson['attachment'].remove(propertyValue)
    if removeKey:
        return

    for propertyValue in actorJson['attachment']:
        if not propertyValue.get('name'):
            continue
        if not propertyValue.get('type'):
            continue
        if not propertyValue['name'].lower().startswith('pgp'):
            continue
        if propertyValue['type'] != 'PropertyValue':
            continue
        propertyValue['value'] = PGPpubKey
        return

    newPGPpubKey = {
        "name": "PGP",
        "type": "PropertyValue",
        "value": PGPpubKey
    }
    actorJson['attachment'].append(newPGPpubKey)


def setPGPfingerprint(actorJson: {}, fingerprint: str) -> None:
    """Sets a PGP fingerprint for the given actor
    """
    removeFingerprint = False
    if not fingerprint:
        removeFingerprint = True
    else:
        if len(fingerprint) < 10:
            removeFingerprint = True

    if not actorJson.get('attachment'):
        actorJson['attachment'] = []

    # remove any existing value
    propertyFound = None
    for propertyValue in actorJson['attachment']:
        if not propertyValue.get('name'):
            continue
        if not propertyValue.get('type'):
            continue
        if not propertyValue['name'].lower().startswith('openpgp'):
            continue
        propertyFound = propertyValue
        break
    if propertyFound:
        actorJson['attachment'].remove(propertyValue)
    if removeFingerprint:
        return

    for propertyValue in actorJson['attachment']:
        if not propertyValue.get('name'):
            continue
        if not propertyValue.get('type'):
            continue
        if not propertyValue['name'].lower().startswith('openpgp'):
            continue
        if propertyValue['type'] != 'PropertyValue':
            continue
        propertyValue['value'] = fingerprint.strip()
        return

    newPGPfingerprint = {
        "name": "OpenPGP",
        "type": "PropertyValue",
        "value": fingerprint
    }
    actorJson['attachment'].append(newPGPfingerprint)


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


def pgpEncrypt(content: str, recipientPubKey: str) -> str:
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
    if '--BEGIN PGP MESSAGE--' not in encryptResult:
        return None
    return encryptResult


def pgpDecrypt(content: str) -> str:
    """ Encrypt using your default pgp key to the given recipient
    """
    if '--BEGIN PGP MESSAGE--' not in content:
        return content

    # if the public key is also included within the message then import it
    startBlock = '--BEGIN PGP PUBLIC KEY BLOCK--'
    if startBlock in content:
        pubKey = extractPGPPublicKey(content)
        if pubKey:
            _pgpImportPubKey(pubKey)

    cmdDecrypt = \
        'echo "' + content + '" | gpg --decrypt --armor 2> /dev/null'
    proc = subprocess.Popen([cmdDecrypt],
                            stdout=subprocess.PIPE, shell=True)
    (decryptResult, err) = proc.communicate()
    if not decryptResult:
        return content
    decryptResult = decryptResult.decode('utf-8')
    return decryptResult
