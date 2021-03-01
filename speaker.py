__filename__ = "speaker.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import random
from auth import createBasicAuthHeader
from session import getJson
from utils import getFullDomain


def getSpeakerPitch(displayName: str) -> int:
    """Returns the speech synthesis pitch for the given name
    """
    random.seed(displayName)
    return random.randint(1, 100)


def getSpeakerRate(displayName: str) -> int:
    """Returns the speech synthesis rate for the given name
    """
    random.seed(displayName)
    return random.randint(50, 120)


def getSpeakerRange(displayName: str) -> int:
    """Returns the speech synthesis range for the given name
    """
    random.seed(displayName)
    return random.randint(300, 800)


def getSpeakerFromServer(baseDir: str, session,
                         nickname: str, password: str,
                         domain: str, port: int,
                         httpPrefix: str,
                         debug: bool, projectVersion: str) -> {}:
    """Returns some json which contains the latest inbox
    entry in a minimal format suitable for a text-to-speech reader
    """
    if not session:
        print('WARN: No session for getSpeakerFromServer')
        return 6

    domainFull = getFullDomain(domain, port)

    authHeader = createBasicAuthHeader(nickname, password)

    headers = {
        'host': domain,
        'Content-type': 'application/json',
        'Authorization': authHeader
    }

    url = \
        httpPrefix + '://' + \
        domainFull + '/users/' + nickname + '/speaker'

    speakerJson = \
        getJson(session, url, headers, None,
                __version__, httpPrefix, domain)
    return speakerJson
