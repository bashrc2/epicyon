__filename__ = "media.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import os
import datetime
import random
import math
from random import randint
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


def _getCityPulse(currTimeOfDay, doppelgangerSeed: int) -> float:
    """The data doppelganger
    This simulates expected average patterns of movement in a city.
    Jane or Joe average lives and works in the city, commuting in
    and out of the central district for work. They have a unique
    life pattern, which machine learning can latch onto.
    """
    randgen = random.Random(doppelgangerSeed)
    variance = 3
    busyStates = ("work", "shop", "play", "party")
    dataDoppelgangerState = "sleep"
    dataDoppelgangerIndex = 0
    weekday = currTimeOfDay.weekday()
    minHour = 7 + randint(0, variance)
    maxHour = 17 + randint(0, variance)
    if currTimeOfDay.hour > minHour:
        if currTimeOfDay.hour <= maxHour:
            if weekday < 5:
                dataDoppelgangerState = "work"
                dataDoppelgangerIndex = 1
            elif weekday == 5:
                dataDoppelgangerState = "shop"
                dataDoppelgangerIndex = 2
            else:
                dataDoppelgangerState = "play"
                dataDoppelgangerIndex = 3
        else:
            if weekday < 5:
                dataDoppelgangerState = "evening"
                dataDoppelgangerIndex = 4
            else:
                dataDoppelgangerState = "party"
                dataDoppelgangerIndex = 5
    angleRadians = \
        (randgen.randint(0, 100000 - 5 + dataDoppelgangerIndex) / 100000) * \
        2 * math.pi
    # what consitutes the central district is fuzzy
    centralDistrictFuzz = (randgen.randint(0, 100000) / 100000) * 0.1
    busyRadius = 0.3 + centralDistrictFuzz
    if dataDoppelgangerState in busyStates:
        # if we are busy then we're somewhere in the city center
        distanceFromCityCenter = \
            (randgen.randint(0, 100000) / 100000) * busyRadius
    else:
        # otherwise we're in the burbs
        distanceFromCityCenter = busyRadius + \
            ((1.0 - busyRadius) * (randgen.randint(0, 100000) / 100000))
    return distanceFromCityCenter, angleRadians


def spoofGeolocation(baseDir: str,
                     city: str, currTime, doppelgangerSeed: int,
                     citiesList: []) -> (float, float, str, str):
    """Given a city and the current time spoofs the location
    for an image
    returns latitude, longitude, N/S, E/W
    """
    locationsFilename = baseDir + '/custom_locations.txt'
    if not os.path.isfile(locationsFilename):
        locationsFilename = baseDir + '/locations.txt'
    cityRadius = 0.1
    variance = 0.01
    default_latitude = 51.8744
    default_longitude = 0.368333
    default_latdirection = 'N'
    default_longdirection = 'W'

    if citiesList:
        cities = citiesList
    else:
        if not os.path.isfile(locationsFilename):
            return (default_latitude, default_longitude,
                    default_latdirection, default_longdirection)
        cities = []
        with open(locationsFilename, "r") as f:
            cities = f.readlines()

    city = city.lower()
    for cityName in cities:
        if city in cityName.lower():
            latitude = cityName.split(':')[1]
            longitude = cityName.split(':')[2]
            latdirection = 'N'
            longdirection = 'E'
            if 'S' in latitude:
                latdirection = 'S'
                latitude = latitude.replace('S', '')
            if 'W' in longitude:
                longdirection = 'W'
                longitude = longitude.replace('W', '')
            latitude = float(latitude)
            longitude = float(longitude)
            # get the time of day at the city
            approxTimeZone = int(longitude / 15.0)
            if longdirection == 'E':
                approxTimeZone = -approxTimeZone
            currTimeAdjusted = currTime - \
                datetime.timedelta(hours=approxTimeZone)
            # patterns of activity change in the city over time
            (distanceFromCityCenter, angleRadians) = \
                _getCityPulse(currTimeAdjusted, doppelgangerSeed)
            # Get the position within the city, with some randomness added
            fraction = randint(0, 100000) / 100000
            latitude += \
                distanceFromCityCenter * cityRadius * math.cos(angleRadians)
            # add a small amount of variance around the location
            latitude += (fraction * fraction * variance) - (variance / 2.0)
            # gps locations aren't transcendental, so round to a fixed
            # number of decimal places
            latitude = int(latitude * 10000) / 10000.0

            fraction = randint(0, 100000) / 100000
            longitude += \
                distanceFromCityCenter * cityRadius * math.sin(angleRadians)
            # add a small amount of variance around the location
            longitude += (fraction * fraction * variance) - (variance / 2.0)
            # gps locations aren't transcendental, so round to a fixed
            # number of decimal places
            longitude = int(longitude * 10000) / 10000.0
            return latitude, longitude, latdirection, longdirection

    return (default_latitude, default_longitude,
            default_latdirection, default_longdirection)


def _spoofMetaData(baseDir: str, nickname: str, domain: str,
                   outputFilename: str, spoofCity: str) -> None:
    """Use reference images to spoof the metadata
    """
    if not os.path.isfile(outputFilename):
        print('ERROR: unable to spoof metadata within ' + outputFilename)
        return

    # get the random seed used to generate a unique pattern for this account
    doppelgangerSeedFilename = \
        baseDir + '/accounts/' + nickname + '@' + domain + '/doppelgangerseed'
    doppelgangerSeed = 63725
    if os.path.isfile(doppelgangerSeedFilename):
        with open(doppelgangerSeedFilename, 'r') as fp:
            doppelgangerSeed = int(fp.read())
    else:
        doppelgangerSeed = randint(10000, 10000000000000)

    if os.path.isfile('/usr/bin/exiftool'):
        print('Spoofing metadata in ' + outputFilename + ' using exiftool')
        currTimeAdjusted = \
            datetime.datetime.utcnow() - \
            datetime.timedelta(minutes=randint(2, 120))
        published = currTimeAdjusted.strftime("%Y:%m:%d %H:%M:%S+00:00")
        (latitude, longitude, latitudeRef, longitudeRef) = \
            spoofGeolocation(baseDir, spoofCity, currTimeAdjusted,
                             doppelgangerSeed, None)
        os.system('exiftool -artist="' + nickname + '" ' +
                  '-DateTimeOriginal="' + published + '" ' +
                  '-FileModifyDate="' + published + '" ' +
                  '-CreateDate="' + published + '" ' +
                  '-GPSLongitudeRef=' + longitudeRef + ' ' +
                  '-GPSAltitude=0 ' +
                  '-GPSLongitude=' + str(longitude) + ' ' +
                  '-GPSLatitudeRef=' + latitudeRef + ' ' +
                  '-GPSLatitude=' + str(latitude) + ' ' +
                  '-Comment="" ' +
                  outputFilename)  # nosec
    else:
        print('ERROR: exiftool is not installed')
        return


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


def attachMedia(baseDir: str, httpPrefix: str,
                nickname: str, domain: str, port: int,
                postJson: {}, imageFilename: str,
                mediaType: str, description: str,
                city: str) -> {}:
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
            processMetaData(baseDir, nickname, domain,
                            imageFilename, mediaFilename, city)
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
