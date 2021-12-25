__filename__ = "devices.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Security"

# REST API overview
#
# To support Olm, the following APIs are required:
#
#  * Uploading keys for a device (current app)
#    POST /api/v1/crypto/keys/upload
#
#  * Querying available devices of people you want to establish a session with
#    POST /api/v1/crypto/keys/query
#
#  * Claiming a pre-key (one-time-key) for each device you want to establish
#    a session with
#    POST /api/v1/crypto/keys/claim
#
#  * Sending encrypted messages directly to specific devices of other people
#    POST /api/v1/crypto/delivery
#
#  * Collect encrypted messages addressed to the current device
#    GET /api/v1/crypto/encrypted_messages
#
#  * Clear all encrypted messages addressed to the current device
#    POST /api/v1/crypto/encrypted_messages/clear

import os
from utils import loadJson
from utils import saveJson
from utils import acctDir
from utils import localActorUrl


def E2EEremoveDevice(base_dir: str, nickname: str, domain: str,
                     deviceId: str) -> bool:
    """Unregisters a device for e2ee
    """
    personDir = acctDir(base_dir, nickname, domain)
    deviceFilename = personDir + '/devices/' + deviceId + '.json'
    if os.path.isfile(deviceFilename):
        try:
            os.remove(deviceFilename)
        except OSError:
            print('EX: E2EEremoveDevice unable to delete ' + deviceFilename)
        return True
    return False


def E2EEvalidDevice(deviceJson: {}) -> bool:
    """Returns true if the given json contains valid device keys
    """
    if not isinstance(deviceJson, dict):
        return False
    if not deviceJson.get('deviceId'):
        return False
    if not isinstance(deviceJson['deviceId'], str):
        return False
    if not deviceJson.get('type'):
        return False
    if not isinstance(deviceJson['type'], str):
        return False
    if not deviceJson.get('name'):
        return False
    if not isinstance(deviceJson['name'], str):
        return False
    if deviceJson['type'] != 'Device':
        return False
    if not deviceJson.get('claim'):
        return False
    if not isinstance(deviceJson['claim'], str):
        return False
    if not deviceJson.get('fingerprintKey'):
        return False
    if not isinstance(deviceJson['fingerprintKey'], dict):
        return False
    if not deviceJson['fingerprintKey'].get('type'):
        return False
    if not isinstance(deviceJson['fingerprintKey']['type'], str):
        return False
    if not deviceJson['fingerprintKey'].get('publicKeyBase64'):
        return False
    if not isinstance(deviceJson['fingerprintKey']['publicKeyBase64'], str):
        return False
    if not deviceJson.get('identityKey'):
        return False
    if not isinstance(deviceJson['identityKey'], dict):
        return False
    if not deviceJson['identityKey'].get('type'):
        return False
    if not isinstance(deviceJson['identityKey']['type'], str):
        return False
    if not deviceJson['identityKey'].get('publicKeyBase64'):
        return False
    if not isinstance(deviceJson['identityKey']['publicKeyBase64'], str):
        return False
    return True


def E2EEaddDevice(base_dir: str, nickname: str, domain: str,
                  deviceId: str, name: str, claimUrl: str,
                  fingerprintPublicKey: str,
                  identityPublicKey: str,
                  fingerprintKeyType="Ed25519Key",
                  identityKeyType="Curve25519Key") -> bool:
    """Registers a device for e2ee
    claimUrl could be something like:
        http://localhost:3000/users/admin/claim?id=11119
    """
    if ' ' in deviceId or '/' in deviceId or \
       '?' in deviceId or '#' in deviceId or \
       '.' in deviceId:
        return False
    personDir = acctDir(base_dir, nickname, domain)
    if not os.path.isdir(personDir):
        return False
    if not os.path.isdir(personDir + '/devices'):
        os.mkdir(personDir + '/devices')
    deviceDict = {
        "deviceId": deviceId,
        "type": "Device",
        "name": name,
        "claim": claimUrl,
        "fingerprintKey": {
            "type": fingerprintKeyType,
            "publicKeyBase64": fingerprintPublicKey
        },
        "identityKey": {
            "type": identityKeyType,
            "publicKeyBase64": identityPublicKey
        }
    }
    deviceFilename = personDir + '/devices/' + deviceId + '.json'
    return saveJson(deviceDict, deviceFilename)


def E2EEdevicesCollection(base_dir: str, nickname: str, domain: str,
                          domainFull: str, httpPrefix: str) -> {}:
    """Returns a list of registered devices
    """
    personDir = acctDir(base_dir, nickname, domain)
    if not os.path.isdir(personDir):
        return {}
    personId = localActorUrl(httpPrefix, nickname, domainFull)
    if not os.path.isdir(personDir + '/devices'):
        os.mkdir(personDir + '/devices')
    deviceList = []
    for subdir, dirs, files in os.walk(personDir + '/devices/'):
        for dev in files:
            if not dev.endswith('.json'):
                continue
            deviceFilename = os.path.join(personDir + '/devices', dev)
            devJson = loadJson(deviceFilename)
            if devJson:
                deviceList.append(devJson)
        break

    devicesDict = {
        'id': personId + '/collections/devices',
        'type': 'Collection',
        'totalItems': len(deviceList),
        'items': deviceList
    }
    return devicesDict


def E2EEdecryptMessageFromDevice(messageJson: {}) -> str:
    """Locally decrypts a message on the device.
    This should probably be a link to a local script
    or native app, such that what the user sees isn't
    something which the server could get access to.
    """
    # TODO
    #  {
    #    "type": "EncryptedMessage",
    #    "messageType": 0,
    #    "cipherText": "...",
    #    "digest": {
    #      "type": "Digest",
    #      "digestAlgorithm": "http://www.w3.org/2000/09/xmldsig#hmac-sha256",
    #      "digestValue": "5f6ad31acd64995483d75c7..."
    #    },
    #    "messageFranking": "...",
    #    "attributedTo": {
    #      "type": "Device",
    #      "deviceId": "11119"
    #    },
    #    "to": {
    #      "type": "Device",
    #      "deviceId": "11876"
    #    }
    #  }
    return ''
