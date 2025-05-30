__filename__ = "formats.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.6.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Core"


def get_video_extensions() -> []:
    """Returns a list of the possible video file extensions
    """
    return ('mp4', 'webm', 'ogv')


def get_audio_extensions() -> []:
    """Returns a list of the possible audio file extensions
    """
    return ('mp3', 'ogg', 'flac', 'opus', 'spx', 'wav')


def get_image_extensions() -> []:
    """Returns a list of the possible image file extensions
    """
    return ('jpg', 'jpeg', 'gif', 'webp', 'avif', 'heic',
            'svg', 'ico', 'jxl', 'png')


def image_mime_types_dict() -> {}:
    """Returns a dict of image mime types
    """
    return {
        'png': 'png',
        'jpg': 'jpeg',
        'jpeg': 'jpeg',
        'jxl': 'jxl',
        'gif': 'gif',
        'avif': 'avif',
        'heic': 'heic',
        'svg': 'svg+xml',
        'webp': 'webp',
        'ico': 'x-icon'
    }


def get_image_mime_type(image_filename: str) -> str:
    """Returns the mime type for the given image filename
    """
    extensions_to_mime = image_mime_types_dict()
    for ext, mime_ext in extensions_to_mime.items():
        if image_filename.endswith('.' + ext):
            return 'image/' + mime_ext
    return 'image/png'


def get_image_extension_from_mime_type(content_type: str) -> str:
    """Returns the image extension from a mime type, such as image/jpeg
    """
    image_media = {
        'png': 'png',
        'jpeg': 'jpg',
        'jxl': 'jxl',
        'gif': 'gif',
        'svg+xml': 'svg',
        'webp': 'webp',
        'avif': 'avif',
        'heic': 'heic',
        'x-icon': 'ico'
    }
    for mime_ext, ext in image_media.items():
        if content_type.endswith(mime_ext):
            return ext
    return 'png'


def get_media_extensions() -> []:
    """Returns a list of the possible media file extensions
    """
    return get_image_extensions() + \
        get_video_extensions() + get_audio_extensions()


def get_image_formats() -> str:
    """Returns a string of permissable image formats
    used when selecting an image for a new post
    """
    image_ext = get_image_extensions()

    image_formats = ''
    for ext in image_ext:
        if image_formats:
            image_formats += ', '
        image_formats += '.' + ext
    return image_formats


def get_media_formats() -> str:
    """Returns a string of permissable media formats
    used when selecting an attachment for a new post
    """
    media_ext = get_media_extensions()

    media_formats = ''
    for ext in media_ext:
        if media_formats:
            media_formats += ', '
        media_formats += '.' + ext
    return media_formats


def media_file_mime_type(filename: str) -> str:
    """Given a media filename return its mime type
    """
    if '.' not in filename:
        return 'image/png'
    extensions = {
        'json': 'application/json',
        'png': 'image/png',
        'jpg': 'image/jpeg',
        'jxl': 'image/jxl',
        'jpeg': 'image/jpeg',
        'gif': 'image/gif',
        'svg': 'image/svg+xml',
        'webp': 'image/webp',
        'avif': 'image/avif',
        'heic': 'image/heic',
        'ico': 'image/x-icon',
        'mp3': 'audio/mpeg',
        'ogg': 'audio/ogg',
        'audio/wav': 'wav',
        'audio/x-wav': 'wav',
        'audio/x-pn-wave': 'wav',
        'wav': 'audio/vnd.wave',
        'opus': 'audio/opus',
        'spx': 'audio/speex',
        'flac': 'audio/flac',
        'mp4': 'video/mp4',
        'ogv': 'video/ogv'
    }
    file_ext = filename.split('.')[-1]
    if not extensions.get(file_ext):
        return 'image/png'
    return extensions[file_ext]
