__filename__ = "inbox.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "0.0.1"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import json
import os

def inboxPermittedMessage(messageJson,federationList) -> bool:
    """ check that we are receiving from a permitted domain
    """
    testParam='actor'
    if not messageJson.get(testParam):
        return False
    actor=messageJson[testParam]
    # always allow the local domain
    if thisDomain in actor:
        return True

    permittedDomain=False
    for domain in federationList:
        if domain in actor:
            permittedDomain=True
            break
    if not permittedDomain:
        return False

    if messageJson.get('object'):
        if messageJson['object'].get('inReplyTo'):
            inReplyTo=messageJson['object']['inReplyTo']
            permittedReplyDomain=False
            for domain in federationList:
                if domain in inReplyTo:
                    permittedReplyDomain=True
                    break
            if not permittedReplyDomain:
                return False

    return True
