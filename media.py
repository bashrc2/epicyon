__filename__ = "media.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.1.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

from blurhash import blurhash_encode as blurencode
from PIL import Image
import numpy
import os
import sys
import json
import datetime
from hashlib import sha1
from auth import createPassword
from shutil import copyfile
from shutil import rmtree
from shutil import move

def replaceYouTube(postJsonObject: {}):
    """Replace YouTube with invidio.us
    This denies Google some, but not all, tracking data
    """
    if not isinstance(postJsonObject['object'], dict):
        return
    if not postJsonObject['object'].get('content'):
        return
    if 'www.youtube.com' not in postJsonObject['object']['content']:
        return
    postJsonObject['object']['content']= \
        postJsonObject['object']['content'].replace('www.youtube.com','invidio.us')

def removeMetaData(imageFilename: str,outputFilename: str) -> None:
    """Attempts to do this with pure python didn't work well,
    so better to use a dedicated tool if one is installed
    """
    copyfile(imageFilename,outputFilename)
    if os.path.isfile('/usr/bin/exiftool'):
        print('Removing metadata from '+outputFilename+' using exiftool')
        os.system('exiftool -all= '+outputFilename)
    elif os.path.isfile('/usr/bin/mogrify'):
        print('Removing metadata from '+outputFilename+' using mogrify')
        os.system('/usr/bin/mogrify -strip '+outputFilename)

def getImageHash(imageFilename: str) -> str:
    return blurencode(numpy.array(Image.open(imageFilename).convert("RGB")))

def isMedia(imageFilename: str) -> bool:
    permittedMedia=['png','jpg','gif','webp','mp4','ogv','mp3','ogg']
    for m in permittedMedia:        
        if imageFilename.endswith('.'+m):
            return True
    print('WARN: '+imageFilename+' is not a permitted media type')
    return False

def createMediaDirs(baseDir: str,mediaPath: str) -> None:    
    if not os.path.isdir(baseDir+'/media'):
        os.mkdir(baseDir+'/media')
    if not os.path.isdir(baseDir+'/'+mediaPath):
        os.mkdir(baseDir+'/'+mediaPath)

def getMediaPath() -> str:
    currTime=datetime.datetime.utcnow()
    weeksSinceEpoch=int((currTime - datetime.datetime(1970,1,1)).days/7)
    return 'media/'+str(weeksSinceEpoch)

def getAttachmentMediaType(filename: str) -> str:
    """Returns the type of media for the given file
    image, video or audio
    """
    mediaType=None
    imageTypes=['png','jpg','jpeg','gif','webp']
    for mType in imageTypes:
        if filename.endswith('.'+mType):
            return 'image'
    videoTypes=['mp4','webm','ogv']
    for mType in videoTypes:
        if filename.endswith('.'+mType):
            return 'video'
    audioTypes=['mp3','ogg']
    for mType in audioTypes:
        if filename.endswith('.'+mType):
            return 'audio'
    return mediaType

def updateEtag(mediaFilename: str) -> None:
    """ calculate the etag, which is a sha1 of the data
    """
    # only create etags for media
    if '/media/' not in mediaFilename:
        return

    # check that the media exists
    if not os.path.isfile(mediaFilename):
        return

    # read the binary data
    data=None
    try:
        with open(mediaFilename, 'rb') as mediaFile:
            data=mediaFile.read()                
    except:
        pass

    if not data:
        return
    # calculate hash
    etag=sha1(data).hexdigest()
    # save the hash
    try:
        with open(mediaFilename+'.etag', 'w') as etagFile:
            etagFile.write(etag)
    except:
        pass

def attachMedia(baseDir: str,httpPrefix: str,domain: str,port: int, \
                postJson: {},imageFilename: str, \
                mediaType: str,description: str, \
                useBlurhash: bool) -> {}:
    """Attaches media to a json object post
    The description can be None
    Blurhash is optional, since low power systems may take a long time to calculate it
    """
    if not isMedia(imageFilename):
        return postJson
    
    fileExtension=None
    acceptedTypes=['png','jpg','gif','webp','mp4','webm','ogv','mp3','ogg']
    for mType in acceptedTypes:
        if imageFilename.endswith('.'+mType):
            if mType=='jpg':
                mType='jpeg'
            if mType=='mp3':
                mType='mpeg'
            fileExtension=mType
    if not fileExtension:        
        return postJson
    mediaType=mediaType+'/'+fileExtension
    print('Attached media type: '+mediaType)

    if fileExtension=='jpeg':
        fileExtension='jpg'
    if mediaType=='audio/mpeg':
        fileExtension='mp3'

    if port:
        if port!=80 and port!=443:
            if ':' not in domain:
                domain=domain+':'+str(port)

    mPath=getMediaPath()
    mediaPath=mPath+'/'+createPassword(32)+'.'+fileExtension
    if baseDir:
        createMediaDirs(baseDir,mPath)
        mediaFilename=baseDir+'/'+mediaPath

    attachmentJson={
        'mediaType': mediaType,
        'name': description,
        'type': 'Document',
        'url': httpPrefix+'://'+domain+'/'+mediaPath
    }
    if useBlurhash and mediaType.startswith('image/'):
        attachmentJson['blurhash']=getImageHash(imageFilename)
    postJson['attachment']=[attachmentJson]

    if baseDir:
        if mediaType=='image':
            removeMetaData(imageFilename,mediaFilename)
        else:
            copyfile(imageFilename,mediaFilename)
        updateEtag(mediaFilename)

    return postJson

def archiveMedia(baseDir: str,archiveDirectory: str,maxWeeks=4) -> None:
    """Any media older than the given number of weeks gets archived
    """
    currTime=datetime.datetime.utcnow()
    weeksSinceEpoch=int((currTime - datetime.datetime(1970,1,1)).days/7)
    minWeek=weeksSinceEpoch-maxWeeks

    if archiveDirectory:
        if not os.path.isdir(archiveDirectory):
            os.mkdir(archiveDirectory)
        if not os.path.isdir(archiveDirectory+'/media'):
            os.mkdir(archiveDirectory+'/media')
    
    for subdir, dirs, files in os.walk(baseDir+'/media'):
        for weekDir in dirs:
            if int(weekDir)<minWeek:
                if archiveDirectory:
                    move(os.path.join(baseDir+'/media', weekDir),archiveDirectory+'/media')
                else:
                    # archive to /dev/null
                    rmtree(os.path.join(baseDir+'/media', weekDir))
