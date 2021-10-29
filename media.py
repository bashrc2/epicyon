__filename__ = "media.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Timeline"

import os
import time
import datetime
import subprocess
import random
from random import randint
from hashlib import sha1
from auth import createPassword
from utils import getBaseContentFromPost
from utils import getFullDomain
from utils import getImageExtensions
from utils import getVideoExtensions
from utils import getAudioExtensions
from utils import getMediaExtensions
from utils import hasObjectDict
from utils import acctDir
from shutil import copyfile
from shutil import rmtree
from shutil import move
from city import spoofGeolocation


def _getBlurHash() -> str:
    """You may laugh, but this is a lot less computationally intensive,
    especially on large images, while still providing some visual variety
    in the timeline
    """
    hashes = [
        "UfGuaW01%gRi%MM{azofozo0V@xuozn#ofs.",
        "UFD]o8-;9FIU~qD%j[%M-;j[ofWB?bt7IURj",
        "UyO|v_1#im=s%y#U%OxDwRt3W9R-ogjHj[WX",
        "U96vAQt6H;WBt7ofWBa#MbWBo#j[byaze-oe",
        "UJKA.q01M|IV%LM|RjNGIVj[f6oLjrofaeof",
        "U9MPjn]?~Cxut~.PS1%1xXIo0fEer_$*^jxG",
        "UtLENXWCRjju~qayaeaz00j[ofayIVkCkCfQ",
        "UHGbeg-pbzWZ.ANI$wsQ$H-;E9W?0Nx]?FjE",
        "UcHU%#4n_ND%?bxatRWBIU%MazxtNaRjs:of",
        "ULR:TsWr~6xZofWWf6s-~6oK9eR,oes-WXNJ",
        "U77VQB-:MaMx%L%MogRkMwkCxuoIS*WYjEsl",
        "U%Nm{8R+%MxuE1t6WBNG-=RjoIt6~Vj]RkR*",
        "UCM7u;?boft7oft7ayj[~qt7WBoft7oft7Rj"
    ]
    return random.choice(hashes)


def _replaceSiloDomain(postJsonObject: {},
                       siloDomain: str, replacementDomain: str,
                       systemLanguage: str) -> None:
    """Replace a silo domain with a replacement domain
    """
    if not replacementDomain:
        return
    if not hasObjectDict(postJsonObject):
        return
    if not postJsonObject['object'].get('content'):
        return
    contentStr = getBaseContentFromPost(postJsonObject, systemLanguage)
    if siloDomain not in contentStr:
        return
    contentStr = contentStr.replace(siloDomain, replacementDomain)
    postJsonObject['object']['content'] = contentStr
    if postJsonObject['object'].get('contentMap'):
        postJsonObject['object']['contentMap'][systemLanguage] = contentStr


def replaceYouTube(postJsonObject: {}, replacementDomain: str,
                   systemLanguage: str) -> None:
    """Replace YouTube with a replacement domain
    This denies Google some, but not all, tracking data
    """
    _replaceSiloDomain(postJsonObject, 'www.youtube.com',
                       replacementDomain, systemLanguage)


def replaceTwitter(postJsonObject: {}, replacementDomain: str,
                   systemLanguage: str) -> None:
    """Replace Twitter with a replacement domain
    This allows you to view twitter posts without having a twitter account
    """
    _replaceSiloDomain(postJsonObject, 'twitter.com',
                       replacementDomain, systemLanguage)


def _removeMetaData(imageFilename: str, outputFilename: str) -> None:
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


def _spoofMetaData(baseDir: str, nickname: str, domain: str,
                   outputFilename: str, spoofCity: str) -> None:
    """Spoof image metadata using a decoy model for a given city
    """
    if not os.path.isfile(outputFilename):
        print('ERROR: unable to spoof metadata within ' + outputFilename)
        return

    # get the random seed used to generate a unique pattern for this account
    decoySeedFilename = acctDir(baseDir, nickname, domain) + '/decoyseed'
    decoySeed = 63725
    if os.path.isfile(decoySeedFilename):
        with open(decoySeedFilename, 'r') as fp:
            decoySeed = int(fp.read())
    else:
        decoySeed = randint(10000, 10000000000000000)
        try:
            with open(decoySeedFilename, 'w+') as fp:
                fp.write(str(decoySeed))
        except BaseException:
            print('EX: unable to write ' + decoySeedFilename)
            pass

    if os.path.isfile('/usr/bin/exiftool'):
        print('Spoofing metadata in ' + outputFilename + ' using exiftool')
        currTimeAdjusted = \
            datetime.datetime.utcnow() - \
            datetime.timedelta(minutes=randint(2, 120))
        published = currTimeAdjusted.strftime("%Y:%m:%d %H:%M:%S+00:00")
        (latitude, longitude, latitudeRef, longitudeRef,
         camMake, camModel, camSerialNumber) = \
            spoofGeolocation(baseDir, spoofCity, currTimeAdjusted,
                             decoySeed, None, None)
        if os.system('exiftool -artist="' + nickname + '" ' +
                     '-Make="' + camMake + '" ' +
                     '-Model="' + camModel + '" ' +
                     '-Comment="' + str(camSerialNumber) + '" ' +
                     '-DateTimeOriginal="' + published + '" ' +
                     '-FileModifyDate="' + published + '" ' +
                     '-CreateDate="' + published + '" ' +
                     '-GPSLongitudeRef=' + longitudeRef + ' ' +
                     '-GPSAltitude=0 ' +
                     '-GPSLongitude=' + str(longitude) + ' ' +
                     '-GPSLatitudeRef=' + latitudeRef + ' ' +
                     '-GPSLatitude=' + str(latitude) + ' ' +
                     '-Comment="" ' +
                     outputFilename) != 0:  # nosec
            print('ERROR: exiftool failed to run')
    else:
        print('ERROR: exiftool is not installed')
        return


def convertImageToLowBandwidth(imageFilename: str) -> None:
    """Converts an image to a low bandwidth version
    """
    lowBandwidthFilename = imageFilename + '.low'
    if os.path.isfile(lowBandwidthFilename):
        try:
            os.remove(lowBandwidthFilename)
        except BaseException:
            print('EX: convertImageToLowBandwidth unable to delete ' +
                  lowBandwidthFilename)
            pass

    cmd = \
        '/usr/bin/convert +noise Multiplicative ' + \
        '-evaluate median 10% -dither Floyd-Steinberg ' + \
        '-monochrome  ' + imageFilename + ' ' + lowBandwidthFilename
    print('Low bandwidth image conversion: ' + cmd)
    subprocess.call(cmd, shell=True)
    # wait for conversion to happen
    ctr = 0
    while not os.path.isfile(lowBandwidthFilename):
        print('Waiting for low bandwidth image conversion ' + str(ctr))
        time.sleep(0.2)
        ctr += 1
        if ctr > 100:
            print('WARN: timed out waiting for low bandwidth image conversion')
            break
    if os.path.isfile(lowBandwidthFilename):
        try:
            os.remove(imageFilename)
        except BaseException:
            print('EX: convertImageToLowBandwidth unable to delete ' +
                  imageFilename)
            pass
        os.rename(lowBandwidthFilename, imageFilename)
        if os.path.isfile(imageFilename):
            print('Image converted to low bandwidth ' + imageFilename)
    else:
        print('Low bandwidth converted image not found: ' +
              lowBandwidthFilename)


def processMetaData(baseDir: str, nickname: str, domain: str,
                    imageFilename: str, outputFilename: str,
                    city: str) -> None:
    """Handles image metadata. This tries to spoof the metadata
    if possible, but otherwise just removes it
    """
    # first remove the metadata
    _removeMetaData(imageFilename, outputFilename)

    # now add some spoofed data to misdirect surveillance capitalists
    _spoofMetaData(baseDir, nickname, domain, outputFilename, city)


def _isMedia(imageFilename: str) -> bool:
    """Is the given file a media file?
    """
    if not os.path.isfile(imageFilename):
        print('WARN: Media file does not exist ' + imageFilename)
        return False
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
        print('EX: _updateEtag unable to read ' + str(mediaFilename))
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
        print('EX: _updateEtag unable to write ' +
              str(mediaFilename) + '.etag')
        pass


def attachMedia(baseDir: str, httpPrefix: str,
                nickname: str, domain: str, port: int,
                postJson: {}, imageFilename: str,
                mediaType: str, description: str,
                city: str, lowBandwidth: bool) -> {}:
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

    mediaPath = \
        mediaPath.replace('media/', 'system/media_attachments/files/', 1)
    attachmentJson = {
        'mediaType': mediaType,
        'name': description,
        'type': 'Document',
        'url': httpPrefix + '://' + domain + '/' + mediaPath
    }
    if mediaType.startswith('image/'):
        attachmentJson['blurhash'] = _getBlurHash()
        # find the dimensions of the image and add them as metadata
        attachImageWidth, attachImageHeight = \
            getImageDimensions(imageFilename)
        if attachImageWidth and attachImageHeight:
            attachmentJson['width'] = attachImageWidth
            attachmentJson['height'] = attachImageHeight

    postJson['attachment'] = [attachmentJson]

    if baseDir:
        if mediaType.startswith('image/'):
            if lowBandwidth:
                convertImageToLowBandwidth(imageFilename)
            processMetaData(baseDir, nickname, domain,
                            imageFilename, mediaFilename, city)
        else:
            copyfile(imageFilename, mediaFilename)
        _updateEtag(mediaFilename)

    return postJson


def archiveMedia(baseDir: str, archiveDirectory: str, maxWeeks: int) -> None:
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
                    rmtree(os.path.join(baseDir + '/media', weekDir),
                           ignore_errors=False, onerror=None)
        break


def pathIsVideo(path: str) -> bool:
    if path.endswith('.ogv') or \
       path.endswith('.mp4'):
        return True
    return False


def pathIsAudio(path: str) -> bool:
    if path.endswith('.ogg') or \
       path.endswith('.mp3'):
        return True
    return False


def getImageDimensions(imageFilename: str) -> (int, int):
    """Returns the dimensions of an image file
    """
    try:
        result = subprocess.run(['identify', '-format', '"%wx%h"',
                                 imageFilename], stdout=subprocess.PIPE)
    except BaseException:
        print('EX: getImageDimensions unable to run identify command')
        return None, None
    if not result:
        return None, None
    dimensionsStr = result.stdout.decode('utf-8').replace('"', '')
    if 'x' not in dimensionsStr:
        return None, None
    widthStr = dimensionsStr.split('x')[0]
    if not widthStr.isdigit():
        return None, None
    heightStr = dimensionsStr.split('x')[1]
    if not heightStr.isdigit():
        return None, None
    return int(widthStr), int(heightStr)
