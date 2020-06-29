__filename__ = "petnames.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.1.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import os


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
    petnamesFilename = baseDir + '/accounts/' + \
        nickname + '@' + domain + '/petnames.txt'
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
                with open(petnamesFilename, 'w') as petnamesFile:
                    petnamesFile.write(newPetnamesStr)
                return True
            # entry does not exist in the petnames file
            with open(petnamesFilename, 'a+') as petnamesFile:
                petnamesFile.write(entry)
            return True

    # first entry
    with open(petnamesFilename, 'w') as petnamesFile:
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
    petnamesFilename = baseDir + '/accounts/' + \
        nickname + '@' + domain + '/petnames.txt'

    if not os.path.isfile(petnamesFilename):
        return ''
    with open(petnamesFilename, 'r') as petnamesFile:
        petnamesStr = petnamesFile.read()
        if ' ' + handle + '\n' in petnamesStr:
            petnamesList = petnamesStr.split('\n')
            for pet in petnamesList:
                if pet.endswith(' ' + handle):
                    return pet.replace(' ' + handle, '').strip()
    return ''
