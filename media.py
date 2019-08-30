__filename__ = "media.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.0.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

from blurhash import blurhash_encode as blurencode
from PIL import Image
import numpy
import os
import sys
import json
import commentjson
import datetime
from auth import createPassword
from shutil import copyfile
from shutil import rmtree
from shutil import move

def removeMetaData(imageFilename: str,outputFilename: str):
    imageFile = open(imageFilename)
    image = Image.open(imageFilename)
    data = list(image.getdata())
    imageWithoutExif = Image.new(image.mode, image.size)
    imageWithoutExif.putdata(data)
    imageWithoutExif.save(outputFilename)

def getImageHash(imageFilename: str) -> str:
    return blurencode(numpy.array(Image.open(imageFilename).convert("RGB")))

def isMedia(imageFilename: str) -> bool:
    permittedMedia=['png','jpg','gif','mp4','ogv','mp3','ogg']
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
    imageTypes=['png','jpg','jpeg','gif']
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

def attachImage(baseDir: str,httpPrefix: str,domain: str,port: int, \
                postJson: {},imageFilename: str, \
                mediaType: str,description: str, \
                useBlurhash: bool) -> {}:
    """Attaches an image to a json object post
    The description can be None
    Blurhash is optional, since low power systems may take a long time to calculate it
    """
    if not isMedia(imageFilename):
        return postJson
    
    fileExtension=None
    acceptedTypes=['png','jpg','gif','mp4','webm','ogv','mp3','ogg']
    for mType in acceptedTypes:
        if imageFilename.endswith('.'+mType):
            fileExtension=mType
            if mType=='jpg':
                mType='jpeg'
    if not fileExtension:        
        return postJson
    mediaType=mediaType+'/'+fileExtension

    if fileExtension=='jpeg':
        fileExtension='jpg'

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
    if useBlurhash and mediaType=='image':
        attachmentJson['blurhash']=getImageHash(imageFilename)
    postJson['attachment']=[attachmentJson]

    if baseDir:
        removeMetaData(imageFilename,mediaFilename)
        #copyfile(imageFilename,mediaFilename)
             
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
