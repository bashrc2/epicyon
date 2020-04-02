__filename__ = "config.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.1.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import os
from utils import loadJson
from utils import saveJson


def createConfig(baseDir: str) -> None:
    """Creates a configuration file
    """
    configFilename = baseDir + '/config.json'
    if os.path.isfile(configFilename):
        return
    configJson = {
    }
    saveJson(configJson, configFilename)


def setConfigParam(baseDir: str, variableName: str, variableValue) -> None:
    """Sets a configuration value
    """
    createConfig(baseDir)
    configFilename = baseDir + '/config.json'
    configJson = {}
    if os.path.isfile(configFilename):
        configJson = loadJson(configFilename)
    configJson[variableName] = variableValue
    saveJson(configJson, configFilename)


def getConfigParam(baseDir: str, variableName: str):
    """Gets a configuration value
    """
    createConfig(baseDir)
    configFilename = baseDir + '/config.json'
    configJson = loadJson(configFilename)
    if configJson:
        if configJson.get(variableName):
            return configJson[variableName]
    return None
