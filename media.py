__filename__ = "media.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import os
import datetime
from hashlib import sha1
from auth import createPassword
from utils import getFullDomain
from utils import getImageExtensions
from utils import getVideoExtensions
from utils import getAudioExtensions
from utils import getMediaExtensions
from shutil import copyfile
from shutil import rmtree
from shutil import move


def replaceYouTube(postJsonObject: {}, replacementDomain: str) -> None:
    """Replace YouTube with a replacement domain
    This denies Google some, but not all, tracking data
    """
    if not replacementDomain:
        return
    if not isinstance(postJsonObject['object'], dict):
        return
    if not postJsonObject['object'].get('content'):
        return
    if 'www.youtube.com' not in postJsonObject['object']['content']:
        return
    postJsonObject['object']['content'] = \
        postJsonObject['object']['content'].replace('www.youtube.com',
                                                    replacementDomain)


def removeMetaData(imageFilename: str, outputFilename: str) -> None:
    """Attempts to do this with pure python didn't work well,
    so better to use a dedicated tool if one is installed
    """
    copyfile(imageFilename, outputFilename)
    if not os.path.isfile(outputFilename):
        print('ERROR: unable to remove metadata from ' + imageFilename)
        return
    if os.path.isfile('/usr/bin/exiftool'):
        print('Removing metadata from ' + outputFilename + ' using exiftool')
        os.system('exiftool -all= ' + outputFilename)  # nosec
    elif os.path.isfile('/usr/bin/mogrify'):
        print('Removing metadata from ' + outputFilename + ' using mogrify')
        os.system('/usr/bin/mogrify -strip ' + outputFilename)  # nosec


def _isMedia(imageFilename: str) -> bool:
    permittedMedia = getMediaExtensions()
    for m in permittedMedia:
        if imageFilename.endswith('.' + m):
            return True
    print('WARN: ' + imageFilename + ' is not a permitted media type')
    return False


def createMediaDirs(baseDir: str, mediaPath: str) -> None:
    if not os.path.isdir(baseDir + '/media'):
        os.mkdir(baseDir + '/media')
    if not os.path.isdir(baseDir + '/' + mediaPath):
        os.mkdir(baseDir + '/' + mediaPath)


def getMediaPath() -> str:
    currTime = datetime.datetime.utcnow()
    weeksSinceEpoch = int((currTime - datetime.datetime(1970, 1, 1)).days / 7)
    return 'media/' + str(weeksSinceEpoch)


def getAttachmentMediaType(filename: str) -> str:
    """Returns the type of media for the given file
    image, video or audio
    """
    mediaType = None
    imageTypes = getImageExtensions()
    for mType in imageTypes:
        if filename.endswith('.' + mType):
            return 'image'
    videoTypes = getVideoExtensions()
    for mType in videoTypes:
        if filename.endswith('.' + mType):
            return 'video'
    audioTypes = getAudioExtensions()
    for mType in audioTypes:
        if filename.endswith('.' + mType):
            return 'audio'
    return mediaType


def _updateEtag(mediaFilename: str) -> None:
    """ calculate the etag, which is a sha1 of the data
    """
    # only create etags for media
    if '/media/' not in mediaFilename:
        return

    # check that the media exists
    if not os.path.isfile(mediaFilename):
        return

    # read the binary data
    data = None
    try:
        with open(mediaFilename, 'rb') as mediaFile:
            data = mediaFile.read()
    except BaseException:
        pass

    if not data:
        return
    # calculate hash
    etag = sha1(data).hexdigest()  # nosec
    # save the hash
    try:
        with open(mediaFilename + '.etag', 'w+') as etagFile:
            etagFile.write(etag)
    except BaseException:
        pass


def attachMedia(baseDir: str, httpPrefix: str, domain: str, port: int,
                postJson: {}, imageFilename: str,
                mediaType: str, description: str) -> {}:
    """Attaches media to a json object post
    The description can be None
    """
    if not _isMedia(imageFilename):
        return postJson

    fileExtension = None
    acceptedTypes = getMediaExtensions()
    for mType in acceptedTypes:
        if imageFilename.endswith('.' + mType):
            if mType == 'jpg':
                mType = 'jpeg'
            if mType == 'mp3':
                mType = 'mpeg'
            fileExtension = mType
    if not fileExtension:
        return postJson
    mediaType = mediaType + '/' + fileExtension
    print('Attached media type: ' + mediaType)

    if fileExtension == 'jpeg':
        fileExtension = 'jpg'
    if mediaType == 'audio/mpeg':
        fileExtension = 'mp3'

    domain = getFullDomain(domain, port)

    mPath = getMediaPath()
    mediaPath = mPath + '/' + createPassword(32) + '.' + fileExtension
    if baseDir:
        createMediaDirs(baseDir, mPath)
        mediaFilename = baseDir + '/' + mediaPath

    attachmentJson = {
        'mediaType': mediaType,
        'name': description,
        'type': 'Document',
        'url': httpPrefix + '://' + domain + '/' + mediaPath
    }
    if mediaType.startswith('image/'):
        attachmentJson['focialPoint'] = [0.0, 0.0]
    postJson['attachment'] = [attachmentJson]

    if baseDir:
        if mediaType.startswith('image/'):
            removeMetaData(imageFilename, mediaFilename)
        else:
            copyfile(imageFilename, mediaFilename)
        _updateEtag(mediaFilename)

    return postJson


def archiveMedia(baseDir: str, archiveDirectory: str, maxWeeks=4) -> None:
    """Any media older than the given number of weeks gets archived
    """
    if maxWeeks == 0:
        return

    currTime = datetime.datetime.utcnow()
    weeksSinceEpoch = int((currTime - datetime.datetime(1970, 1, 1)).days/7)
    minWeek = weeksSinceEpoch - maxWeeks

    if archiveDirectory:
        if not os.path.isdir(archiveDirectory):
            os.mkdir(archiveDirectory)
        if not os.path.isdir(archiveDirectory + '/media'):
            os.mkdir(archiveDirectory + '/media')

    for subdir, dirs, files in os.walk(baseDir + '/media'):
        for weekDir in dirs:
            if int(weekDir) < minWeek:
                if archiveDirectory:
                    move(os.path.join(baseDir + '/media', weekDir),
                         archiveDirectory + '/media')
                else:
                    # archive to /dev/null
                    rmtree(os.path.join(baseDir + '/media', weekDir))
        break
