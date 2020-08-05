__filename__ = "devices.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.1.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import os
from utils import loadJson
from utils import saveJson


def removeDevice(baseDir: str, nickname: str, domain: str,
                 deviceId: str) -> bool:
    """Unregisters a device for e2ee
    """
    personDir = baseDir + '/accounts/' + nickname + '@' + domain
    deviceFilename = personDir + '/devices/' + deviceId + '.json'
    if os.path.isfile(deviceFilename):
        os.remove(deviceFilename)
        return True
    return False


def addDevice(baseDir: str, nickname: str, domain: str,
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
    personDir = baseDir + '/accounts/' + nickname + '@' + domain
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


def devicesCollection(baseDir: str, nickname: str, domain: str,
                      domainFull: str, httpPrefix: str) -> {}:
    """Returns a list of registered devices
    """
    personDir = baseDir + '/accounts/' + nickname + '@' + domain
    if not os.path.isdir(personDir):
        return {}
    personId = httpPrefix + '://' + domainFull + '/users/' + nickname
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

    devicesDict = {
        'id': personId + '/collections/devices',
        'type': 'Collection',
        'totalItems': len(deviceList),
        'items': deviceList
    }
    return devicesDict


def decryptMessageFromDevice(messageJson: {}) -> str:
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
