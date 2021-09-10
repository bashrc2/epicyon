__filename__ = "petnames.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Core"

import os
from utils import acctDir


def setPetName(baseDir: str, nickname: str, domain: str,
               handle: str, petname: str) -> bool:
    """Adds a new petname
    """
    if '@' not in handle:
        return False
    if ' ' in petname:
        petname = petname.replace(' ', '_')
    if handle.startswith('@'):
        handle = handle[1:]
    if petname.startswith('@'):
        petname = petname[1:]
    petnamesFilename = acctDir(baseDir, nickname, domain) + '/petnames.txt'
    entry = petname + ' ' + handle + '\n'

    # does this entry already exist?
    if os.path.isfile(petnamesFilename):
        with open(petnamesFilename, 'r') as petnamesFile:
            petnamesStr = petnamesFile.read()
            if entry in petnamesStr:
                return True
            if ' ' + handle + '\n' in petnamesStr:
                petnamesList = petnamesStr.split('\n')
                newPetnamesStr = ''
                for pet in petnamesList:
                    if not pet.endswith(' ' + handle):
                        newPetnamesStr += pet + '\n'
                    else:
                        newPetnamesStr += entry
                # save the updated petnames file
                with open(petnamesFilename, 'w+') as petnamesFile:
                    petnamesFile.write(newPetnamesStr)
                return True
            # entry does not exist in the petnames file
            with open(petnamesFilename, 'a+') as petnamesFile:
                petnamesFile.write(entry)
            return True

    # first entry
    with open(petnamesFilename, 'w+') as petnamesFile:
        petnamesFile.write(entry)
    return True


def getPetName(baseDir: str, nickname: str, domain: str,
               handle: str) -> str:
    """Given a handle returns the petname
    """
    if '@' not in handle:
        return ''
    if handle.startswith('@'):
        handle = handle[1:]
    petnamesFilename = acctDir(baseDir, nickname, domain) + '/petnames.txt'

    if not os.path.isfile(petnamesFilename):
        return ''
    with open(petnamesFilename, 'r') as petnamesFile:
        petnamesStr = petnamesFile.read()
        if ' ' + handle + '\n' in petnamesStr:
            petnamesList = petnamesStr.split('\n')
            for pet in petnamesList:
                if pet.endswith(' ' + handle):
                    return pet.replace(' ' + handle, '').strip()
        elif ' ' + handle.lower() + '\n' in petnamesStr.lower():
            petnamesList = petnamesStr.split('\n')
            handle = handle.lower()
            for pet in petnamesList:
                if pet.lower().endswith(' ' + handle):
                    handle2 = pet.split(' ')[-1]
                    return pet.replace(' ' + handle2, '').strip()
    return ''


def _getPetNameHandle(baseDir: str, nickname: str, domain: str,
                      petname: str) -> str:
    """Given a petname returns the handle
    """
    if petname.startswith('@'):
        petname = petname[1:]
    petnamesFilename = acctDir(baseDir, nickname, domain) + '/petnames.txt'

    if not os.path.isfile(petnamesFilename):
        return ''
    with open(petnamesFilename, 'r') as petnamesFile:
        petnamesStr = petnamesFile.read()
        if petname + ' ' in petnamesStr:
            petnamesList = petnamesStr.split('\n')
            for pet in petnamesList:
                if pet.startswith(petname + ' '):
                    handle = pet.replace(petname + ' ', '').strip()
                    return handle
    return ''


def resolvePetnames(baseDir: str, nickname: str, domain: str,
                    content: str) -> str:
    """Replaces petnames with their full handles
    """
    if not content:
        return content
    if ' ' not in content:
        return content
    words = content.strip().split(' ')
    for wrd in words:
        # check initial words beginning with @
        if not wrd.startswith('@'):
            break
        # does a petname handle exist for this?
        handle = _getPetNameHandle(baseDir, nickname, domain, wrd)
        if not handle:
            continue
        # replace the petname with the handle
        content = content.replace(wrd + ' ', '@' + handle + ' ')
    return content
