__filename__ = "storage.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"
__module_group__ = "storage"

import os


def storeValue(filename: str, lineStr: str, storeType: str) -> bool:
    """Stores a line to a file
    """
    if not lineStr.endswith('\n'):
        if storeType != 'writeonly':
            lineStr += '\n'

    if storeType[0] == 'a':
        if not os.path.isfile(filename):
            storeType = 'write'

    if storeType[0] == 'a':
        if not os.path.isfile(filename):
            return False
        # append
        try:
            with open(filename, "a+") as fp:
                fp.write(lineStr)
                return True
        except Exception as e:
            print('ERROR: unable to append to ' + filename + ' ' + str(e))
            pass
    elif storeType[0] == 'w':
        # new file
        try:
            with open(filename, "w+") as fp:
                fp.write(lineStr)
                return True
        except Exception as e:
            print('ERROR: unable to write to ' + filename + ' ' + str(e))
            pass
    elif storeType[0] == 'p':
        # prepend
        if lineStr not in open(filename).read():
            try:
                with open(filename, 'r+') as fp:
                    content = fp.read()
                    if lineStr not in content:
                        fp.seek(0, 0)
                        fp.write(lineStr + content)
            except Exception as e:
                print('WARN: Unable to prepend to ' +
                      filename + ' ' + str(e))
    return False
