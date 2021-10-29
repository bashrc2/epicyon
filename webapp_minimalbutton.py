__filename__ = "webapp_minimalbutton.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Timeline"

import os
from utils import acctDir


def isMinimal(baseDir: str, domain: str, nickname: str) -> bool:
    """Returns true if minimal buttons should be shown
       for the given account
    """
    accountDir = acctDir(baseDir, nickname, domain)
    if not os.path.isdir(accountDir):
        return True
    minimalFilename = accountDir + '/.notminimal'
    if os.path.isfile(minimalFilename):
        return False
    return True


def setMinimal(baseDir: str, domain: str, nickname: str,
               minimal: bool) -> None:
    """Sets whether an account should display minimal buttons
    """
    accountDir = acctDir(baseDir, nickname, domain)
    if not os.path.isdir(accountDir):
        return
    minimalFilename = accountDir + '/.notminimal'
    minimalFileExists = os.path.isfile(minimalFilename)
    if minimal and minimalFileExists:
        try:
            os.remove(minimalFilename)
        except BaseException:
            print('EX: setMinimal unable to delete ' + minimalFilename)
            pass
    elif not minimal and not minimalFileExists:
        with open(minimalFilename, 'w+') as fp:
            fp.write('\n')
