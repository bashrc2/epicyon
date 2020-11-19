__filename__ = "webapp_hashtagswarm.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.1.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import os
from blocking import isBlockedHashtag
from datetime import datetime


def htmlHashTagSwarm(baseDir: str, actor: str) -> str:
    """Returns a tag swarm of today's hashtags
    """
    currTime = datetime.utcnow()
    daysSinceEpoch = (currTime - datetime(1970, 1, 1)).days
    daysSinceEpochStr = str(daysSinceEpoch) + ' '
    tagSwarm = []

    for subdir, dirs, files in os.walk(baseDir + '/tags'):
        for f in files:
            tagsFilename = os.path.join(baseDir + '/tags', f)
            if not os.path.isfile(tagsFilename):
                continue
            # get last modified datetime
            modTimesinceEpoc = os.path.getmtime(tagsFilename)
            lastModifiedDate = datetime.fromtimestamp(modTimesinceEpoc)
            fileDaysSinceEpoch = (lastModifiedDate - datetime(1970, 1, 1)).days
            # check if the file was last modified today
            if fileDaysSinceEpoch != daysSinceEpoch:
                continue

            hashTagName = f.split('.')[0]
            if isBlockedHashtag(baseDir, hashTagName):
                continue
            if daysSinceEpochStr not in open(tagsFilename).read():
                continue
            with open(tagsFilename, 'r') as tagsFile:
                line = tagsFile.readline()
                tagCtr = 0
                while line:
                    if '  ' not in line:
                        line = tagsFile.readline()
                        break
                    postDaysSinceEpochStr = line.split('  ')[0]
                    if not postDaysSinceEpochStr.isdigit():
                        line = tagsFile.readline()
                        break
                    postDaysSinceEpoch = int(postDaysSinceEpochStr)
                    if postDaysSinceEpoch < daysSinceEpoch:
                        break
                    if postDaysSinceEpoch == daysSinceEpoch:
                        if tagCtr == 0:
                            tagSwarm.append(hashTagName)
                        tagCtr += 1

                    line = tagsFile.readline()
                    break

    if not tagSwarm:
        return ''
    tagSwarm.sort()
    tagSwarmStr = ''
    ctr = 0
    for tagName in tagSwarm:
        tagSwarmStr += \
            '<a href="' + actor + '/tags/' + tagName + \
            '" class="hashtagswarm">' + tagName + '</a>\n'
        ctr += 1
    tagSwarmHtml = tagSwarmStr.strip() + '\n'
    return tagSwarmHtml
