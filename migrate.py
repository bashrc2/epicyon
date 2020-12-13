__filename__ = "migrate.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.1.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import os


def migrateFollows(followFilename: str, oldHandle: str,
                   newHandle: str) -> None:
    """Changes a handle within following or followers list
    """
    if not os.path.isfile(followFilename):
        return
    if oldHandle not in open(followFilename).read():
        return
    followData = None
    with open(followFilename, 'r') as followFile:
        followData = followFile.read()
    if not followData:
        return
    newFollowData = followData.replace(oldHandle, newHandle)
    if followData == newFollowData:
        return
    with open(followFilename, 'w+') as followFile:
        followFile.write(newFollowData)


def migrateAccount(baseDir: str, oldHandle: str, newHandle: str) -> None:
    """If a followed account changes then this modifies the
    following and followers lists for each account accordingly
    """
    if oldHandle.startswith('@'):
        oldHandle = oldHandle[1:]
    if '@' not in oldHandle:
        return
    if newHandle.startswith('@'):
        newHandle = newHandle[1:]
    if '@' not in newHandle:
        return

    # update followers and following lists for each account
    for subdir, dirs, files in os.walk(baseDir + '/accounts'):
        for handle in dirs:
            if '@' in handle:
                accountDir = baseDir + '/accounts/' + handle
                followFilename = accountDir + '/following.txt'
                migrateFollows(followFilename, oldHandle, newHandle)
                followFilename = accountDir + '/followers.txt'
                migrateFollows(followFilename, oldHandle, newHandle)
        break
