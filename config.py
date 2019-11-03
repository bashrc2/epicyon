__filename__ = "config.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.0.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import os
import json
import commentjson

def createConfig(baseDir: str) -> None:
    """Creates a configuration file
    """
    configFilename=baseDir+'/config.json'
    if os.path.isfile(configFilename):
        return
    configJson = {
    }
    with open(configFilename, 'w') as fp:
        commentjson.dump(configJson, fp, indent=4, sort_keys=True)

def setConfigParam(baseDir: str, variableName: str, variableValue) -> None:
    """Sets a configuration value
    """
    createConfig(baseDir)
    configFilename=baseDir+'/config.json'
    with open(configFilename, 'r') as fp:
        configJson=commentjson.load(fp)
    configJson[variableName]=variableValue
    with open(configFilename, 'w') as fp:
        commentjson.dump(configJson, fp, indent=4, sort_keys=True)

def getConfigParam(baseDir: str, variableName: str) -> None:
    """Gets a configuration value
    """
    createConfig(baseDir)
    configFilename=baseDir+'/config.json'
    with open(configFilename, 'r') as fp:
        configJson=commentjson.load(fp)
    if configJson.get(variableName):
        return configJson[variableName]
    return None
