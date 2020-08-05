__filename__ = "devices.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.1.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import os
from utils import loadJson


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
