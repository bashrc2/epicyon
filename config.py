__filename__ = "config.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.0.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import os
import time
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
    tries=0
    while tries<5:
        try:
            with open(configFilename, 'w') as fp:
                commentjson.dump(configJson, fp, indent=2, sort_keys=False)
                break
        except Exception as e:
            print(e)
            time.sleep(1)
            tries+=1

def setConfigParam(baseDir: str, variableName: str, variableValue) -> None:
    """Sets a configuration value
    """
    createConfig(baseDir)
    configFilename=baseDir+'/config.json'
    tries=0
    while tries<5:
        try:
            with open(configFilename, 'r') as fp:
                configJson=commentjson.load(fp)
                break
        except Exception as e:
            print('WARN: commentjson exception setConfigParam - '+str(e))
            time.sleep(1)
            tries+=1
    configJson[variableName]=variableValue
    tries=0
    while tries<5:
        try:
            with open(configFilename, 'w') as fp:
                commentjson.dump(configJson, fp, indent=2, sort_keys=False)
                break
        except Exception as e:
            print(e)
            time.sleep(1)
            tries+=1

def getConfigParam(baseDir: str, variableName: str):
    """Gets a configuration value
    """
    createConfig(baseDir)
    configFilename=baseDir+'/config.json'
    tries=0
    while tries<5:
        try:
            with open(configFilename, 'r') as fp:
                configJson=commentjson.load(fp)
                if configJson.get(variableName):
                    return configJson[variableName]
                break
        except Exception as e:
            print('WARN: commentjson exception getConfigParam - '+str(e))
            time.sleep(1)
            tries+=1
    return None
