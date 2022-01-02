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
from utils import load_json
from utils import save_json
from utils import acct_dir
from utils import local_actor_url


def e2e_eremove_device(base_dir: str, nickname: str, domain: str,
                       device_id: str) -> bool:
    """Unregisters a device for e2ee
    """
    person_dir = acct_dir(base_dir, nickname, domain)
    device_filename = person_dir + '/devices/' + device_id + '.json'
    if os.path.isfile(device_filename):
        try:
            os.remove(device_filename)
        except OSError:
            print('EX: e2e_eremove_device unable to delete ' + device_filename)
        return True
    return False


def e2e_evalid_device(deviceJson: {}) -> bool:
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


def e2e_eadd_device(base_dir: str, nickname: str, domain: str,
                    device_id: str, name: str, claim_url: str,
                    fingerprint_public_key: str,
                    identity_public_key: str,
                    fingerprint_key_type="Ed25519Key",
                    identity_key_type="Curve25519Key") -> bool:
    """Registers a device for e2ee
    claim_url could be something like:
        http://localhost:3000/users/admin/claim?id=11119
    """
    if ' ' in device_id or '/' in device_id or \
       '?' in device_id or '#' in device_id or \
       '.' in device_id:
        return False
    person_dir = acct_dir(base_dir, nickname, domain)
    if not os.path.isdir(person_dir):
        return False
    if not os.path.isdir(person_dir + '/devices'):
        os.mkdir(person_dir + '/devices')
    device_dict = {
        "deviceId": device_id,
        "type": "Device",
        "name": name,
        "claim": claim_url,
        "fingerprintKey": {
            "type": fingerprint_key_type,
            "publicKeyBase64": fingerprint_public_key
        },
        "identityKey": {
            "type": identity_key_type,
            "publicKeyBase64": identity_public_key
        }
    }
    device_filename = person_dir + '/devices/' + device_id + '.json'
    return save_json(device_dict, device_filename)


def e2e_edevices_collection(base_dir: str, nickname: str, domain: str,
                            domain_full: str, http_prefix: str) -> {}:
    """Returns a list of registered devices
    """
    person_dir = acct_dir(base_dir, nickname, domain)
    if not os.path.isdir(person_dir):
        return {}
    person_id = local_actor_url(http_prefix, nickname, domain_full)
    if not os.path.isdir(person_dir + '/devices'):
        os.mkdir(person_dir + '/devices')
    device_list = []
    for _, _, files in os.walk(person_dir + '/devices/'):
        for dev in files:
            if not dev.endswith('.json'):
                continue
            device_filename = os.path.join(person_dir + '/devices', dev)
            dev_json = load_json(device_filename)
            if dev_json:
                device_list.append(dev_json)
        break

    devices_dict = {
        'id': person_id + '/collections/devices',
        'type': 'Collection',
        'totalItems': len(device_list),
        'items': device_list
    }
    return devices_dict


def e2e_edecrypt_message_from_device(message_json: {}) -> str:
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
