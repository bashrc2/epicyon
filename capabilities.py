__filename__ = "capabilities.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "0.0.1"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

from auth import createPassword

def sendCapabilitiesRequest(baseDir: str,httpPrefix: str,domain: str) -> None:

    capId=createPassword(32)
    capRequest = {
        "id": httpPrefix+"://"+domain+"/caps/request/"+capId,
        "type": "Request",
        "capability": ["inbox:write", "objects:read"],
        "actor": httpPrefix+"://"+domain
    }
        
