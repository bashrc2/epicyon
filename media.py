__filename__ = "media.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.3.0"
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
from auth import create_password
from utils import get_base_content_from_post
from utils import get_full_domain
from utils import get_image_extensions
from utils import get_video_extensions
from utils import get_audio_extensions
from utils import get_media_extensions
from utils import has_object_dict
from utils import acct_dir
from shutil import copyfile
from shutil import rmtree
from shutil import move
from city import spoof_geolocation


def _get_blur_hash() -> str:
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


def _replace_silo_domain(post_json_object: {},
                         silo_domain: str, replacement_domain: str,
                         system_language: str) -> None:
    """Replace a silo domain with a replacement domain
    """
    if not replacement_domain:
        return
    if not has_object_dict(post_json_object):
        return
    if not post_json_object['object'].get('content'):
        return
    content_str = get_base_content_from_post(post_json_object, system_language)
    if silo_domain not in content_str:
        return
    content_str = content_str.replace(silo_domain, replacement_domain)
    post_json_object['object']['content'] = content_str
    if post_json_object['object'].get('contentMap'):
        post_json_object['object']['contentMap'][system_language] = content_str


def replace_you_tube(post_json_object: {}, replacement_domain: str,
                     system_language: str) -> None:
    """Replace YouTube with a replacement domain
    This denies Google some, but not all, tracking data
    """
    _replace_silo_domain(post_json_object, 'www.youtube.com',
                         replacement_domain, system_language)


def replace_twitter(post_json_object: {}, replacement_domain: str,
                    system_language: str) -> None:
    """Replace Twitter with a replacement domain
    This allows you to view twitter posts without having a twitter account
    """
    twitter_domains = ('mobile.twitter.com', 'twitter.com')
    for tw_domain in twitter_domains:
        _replace_silo_domain(post_json_object, tw_domain,
                             replacement_domain, system_language)


def _remove_meta_data(image_filename: str, output_filename: str) -> None:
    """Attempts to do this with pure python didn't work well,
    so better to use a dedicated tool if one is installed
    """
    copyfile(image_filename, output_filename)
    if not os.path.isfile(output_filename):
        print('ERROR: unable to remove metadata from ' + image_filename)
        return
    if os.path.isfile('/usr/bin/exiftool'):
        print('Removing metadata from ' + output_filename + ' using exiftool')
        os.system('exiftool -all= ' + output_filename)  # nosec
    elif os.path.isfile('/usr/bin/mogrify'):
        print('Removing metadata from ' + output_filename + ' using mogrify')
        os.system('/usr/bin/mogrify -strip ' + output_filename)  # nosec


def _spoof_meta_data(base_dir: str, nickname: str, domain: str,
                     output_filename: str, spoof_city: str,
                     content_license_url: str) -> None:
    """Spoof image metadata using a decoy model for a given city
    """
    if not os.path.isfile(output_filename):
        print('ERROR: unable to spoof metadata within ' + output_filename)
        return

    # get the random seed used to generate a unique pattern for this account
    decoy_seed_filename = acct_dir(base_dir, nickname, domain) + '/decoyseed'
    decoy_seed = 63725
    if os.path.isfile(decoy_seed_filename):
        with open(decoy_seed_filename, 'r') as fp_seed:
            decoy_seed = int(fp_seed.read())
    else:
        decoy_seed = randint(10000, 10000000000000000)
        try:
            with open(decoy_seed_filename, 'w+') as fp_seed:
                fp_seed.write(str(decoy_seed))
        except OSError:
            print('EX: unable to write ' + decoy_seed_filename)

    if os.path.isfile('/usr/bin/exiftool'):
        print('Spoofing metadata in ' + output_filename + ' using exiftool')
        curr_time_adjusted = \
            datetime.datetime.utcnow() - \
            datetime.timedelta(minutes=randint(2, 120))
        published = curr_time_adjusted.strftime("%Y:%m:%d %H:%M:%S+00:00")
        (latitude, longitude, latitude_ref, longitude_ref,
         cam_make, cam_model, cam_serial_number) = \
            spoof_geolocation(base_dir, spoof_city, curr_time_adjusted,
                              decoy_seed, None, None)
        if os.system('exiftool -artist=@"' + nickname + '@' + domain + '" ' +
                     '-Make="' + cam_make + '" ' +
                     '-Model="' + cam_model + '" ' +
                     '-Comment="' + str(cam_serial_number) + '" ' +
                     '-DateTimeOriginal="' + published + '" ' +
                     '-FileModifyDate="' + published + '" ' +
                     '-CreateDate="' + published + '" ' +
                     '-GPSLongitudeRef=' + longitude_ref + ' ' +
                     '-GPSAltitude=0 ' +
                     '-GPSLongitude=' + str(longitude) + ' ' +
                     '-GPSLatitudeRef=' + latitude_ref + ' ' +
                     '-GPSLatitude=' + str(latitude) + ' ' +
                     '-copyright="' + content_license_url + '" ' +
                     '-Comment="" ' +
                     output_filename) != 0:  # nosec
            print('ERROR: exiftool failed to run')
    else:
        print('ERROR: exiftool is not installed')
        return


def convert_image_to_low_bandwidth(image_filename: str) -> None:
    """Converts an image to a low bandwidth version
    """
    low_bandwidth_filename = image_filename + '.low'
    if os.path.isfile(low_bandwidth_filename):
        try:
            os.remove(low_bandwidth_filename)
        except OSError:
            print('EX: convert_image_to_low_bandwidth unable to delete ' +
                  low_bandwidth_filename)

    cmd = \
        '/usr/bin/convert +noise Multiplicative ' + \
        '-evaluate median 10% -dither Floyd-Steinberg ' + \
        '-monochrome  ' + image_filename + ' ' + low_bandwidth_filename
    print('Low bandwidth image conversion: ' + cmd)
    subprocess.call(cmd, shell=True)
    # wait for conversion to happen
    ctr = 0
    while not os.path.isfile(low_bandwidth_filename):
        print('Waiting for low bandwidth image conversion ' + str(ctr))
        time.sleep(0.2)
        ctr += 1
        if ctr > 100:
            print('WARN: timed out waiting for low bandwidth image conversion')
            break
    if os.path.isfile(low_bandwidth_filename):
        try:
            os.remove(image_filename)
        except OSError:
            print('EX: convert_image_to_low_bandwidth unable to delete ' +
                  image_filename)
        os.rename(low_bandwidth_filename, image_filename)
        if os.path.isfile(image_filename):
            print('Image converted to low bandwidth ' + image_filename)
    else:
        print('Low bandwidth converted image not found: ' +
              low_bandwidth_filename)


def process_meta_data(base_dir: str, nickname: str, domain: str,
                      image_filename: str, output_filename: str,
                      city: str, content_license_url: str) -> None:
    """Handles image metadata. This tries to spoof the metadata
    if possible, but otherwise just removes it
    """
    # first remove the metadata
    _remove_meta_data(image_filename, output_filename)

    # now add some spoofed data to misdirect surveillance capitalists
    _spoof_meta_data(base_dir, nickname, domain, output_filename, city,
                     content_license_url)


def _is_media(image_filename: str) -> bool:
    """Is the given file a media file?
    """
    if not os.path.isfile(image_filename):
        print('WARN: Media file does not exist ' + image_filename)
        return False
    permitted_media = get_media_extensions()
    for permit in permitted_media:
        if image_filename.endswith('.' + permit):
            return True
    print('WARN: ' + image_filename + ' is not a permitted media type')
    return False


def create_media_dirs(base_dir: str, media_path: str) -> None:
    """Creates stored media directories
    """
    if not os.path.isdir(base_dir + '/media'):
        os.mkdir(base_dir + '/media')
    if not os.path.isdir(base_dir + '/' + media_path):
        os.mkdir(base_dir + '/' + media_path)


def get_media_path() -> str:
    """Returns the path for stored media
    """
    curr_time = datetime.datetime.utcnow()
    weeks_since_epoch = \
        int((curr_time - datetime.datetime(1970, 1, 1)).days / 7)
    return 'media/' + str(weeks_since_epoch)


def get_attachment_media_type(filename: str) -> str:
    """Returns the type of media for the given file
    image, video or audio
    """
    media_type = None
    image_types = get_image_extensions()
    for mtype in image_types:
        if filename.endswith('.' + mtype):
            return 'image'
    video_types = get_video_extensions()
    for mtype in video_types:
        if filename.endswith('.' + mtype):
            return 'video'
    audio_types = get_audio_extensions()
    for mtype in audio_types:
        if filename.endswith('.' + mtype):
            return 'audio'
    return media_type


def _update_etag(media_filename: str) -> None:
    """ calculate the etag, which is a sha1 of the data
    """
    # only create etags for media
    if '/media/' not in media_filename:
        return

    # check that the media exists
    if not os.path.isfile(media_filename):
        return

    # read the binary data
    data = None
    try:
        with open(media_filename, 'rb') as media_file:
            data = media_file.read()
    except OSError:
        print('EX: _update_etag unable to read ' + str(media_filename))

    if not data:
        return
    # calculate hash
    etag = sha1(data).hexdigest()  # nosec
    # save the hash
    try:
        with open(media_filename + '.etag', 'w+') as efile:
            efile.write(etag)
    except OSError:
        print('EX: _update_etag unable to write ' +
              str(media_filename) + '.etag')


def attach_media(base_dir: str, http_prefix: str,
                 nickname: str, domain: str, port: int,
                 post_json: {}, image_filename: str,
                 media_type: str, description: str,
                 city: str, low_bandwidth: bool,
                 content_license_url: str) -> {}:
    """Attaches media to a json object post
    The description can be None
    """
    if not _is_media(image_filename):
        return post_json

    file_extension = None
    accepted_types = get_media_extensions()
    for mtype in accepted_types:
        if image_filename.endswith('.' + mtype):
            if mtype == 'jpg':
                mtype = 'jpeg'
            if mtype == 'mp3':
                mtype = 'mpeg'
            file_extension = mtype
    if not file_extension:
        return post_json
    media_type = media_type + '/' + file_extension
    print('Attached media type: ' + media_type)

    if file_extension == 'jpeg':
        file_extension = 'jpg'
    if media_type == 'audio/mpeg':
        file_extension = 'mp3'

    domain = get_full_domain(domain, port)

    mpath = get_media_path()
    media_path = mpath + '/' + create_password(32) + '.' + file_extension
    if base_dir:
        create_media_dirs(base_dir, mpath)
        media_filename = base_dir + '/' + media_path

    media_path = \
        media_path.replace('media/', 'system/media_attachments/files/', 1)
    attachment_json = {
        'mediaType': media_type,
        'name': description,
        'type': 'Document',
        'url': http_prefix + '://' + domain + '/' + media_path
    }
    if media_type.startswith('image/'):
        attachment_json['blurhash'] = _get_blur_hash()
        # find the dimensions of the image and add them as metadata
        attach_image_width, attach_image_height = \
            get_image_dimensions(image_filename)
        if attach_image_width and attach_image_height:
            attachment_json['width'] = attach_image_width
            attachment_json['height'] = attach_image_height

    post_json['attachment'] = [attachment_json]

    if base_dir:
        if media_type.startswith('image/'):
            if low_bandwidth:
                convert_image_to_low_bandwidth(image_filename)
            process_meta_data(base_dir, nickname, domain,
                              image_filename, media_filename, city,
                              content_license_url)
        else:
            copyfile(image_filename, media_filename)
        _update_etag(media_filename)

    return post_json


def archive_media(base_dir: str, archive_directory: str,
                  max_weeks: int) -> None:
    """Any media older than the given number of weeks gets archived
    """
    if max_weeks == 0:
        return

    curr_time = datetime.datetime.utcnow()
    weeks_since_epoch = int((curr_time - datetime.datetime(1970, 1, 1)).days/7)
    min_week = weeks_since_epoch - max_weeks

    if archive_directory:
        if not os.path.isdir(archive_directory):
            os.mkdir(archive_directory)
        if not os.path.isdir(archive_directory + '/media'):
            os.mkdir(archive_directory + '/media')

    for _, dirs, _ in os.walk(base_dir + '/media'):
        for week_dir in dirs:
            if int(week_dir) < min_week:
                if archive_directory:
                    move(os.path.join(base_dir + '/media', week_dir),
                         archive_directory + '/media')
                else:
                    # archive to /dev/null
                    rmtree(os.path.join(base_dir + '/media', week_dir),
                           ignore_errors=False, onerror=None)
        break


def path_is_video(path: str) -> bool:
    """Is the given path a video file?
    """
    if path.endswith('.ogv') or \
       path.endswith('.mp4'):
        return True
    return False


def path_is_audio(path: str) -> bool:
    """Is the given path an audio file?
    """
    if path.endswith('.ogg') or \
       path.endswith('.opus') or \
       path.endswith('.mp3'):
        return True
    return False


def get_image_dimensions(image_filename: str) -> (int, int):
    """Returns the dimensions of an image file
    """
    try:
        result = subprocess.run(['identify', '-format', '"%wx%h"',
                                 image_filename], stdout=subprocess.PIPE)
    except BaseException:
        print('EX: get_image_dimensions unable to run identify command')
        return None, None
    if not result:
        return None, None
    dimensions_str = result.stdout.decode('utf-8').replace('"', '')
    if 'x' not in dimensions_str:
        return None, None
    width_str = dimensions_str.split('x')[0]
    if not width_str.isdigit():
        return None, None
    height_str = dimensions_str.split('x')[1]
    if not height_str.isdigit():
        return None, None
    return int(width_str), int(height_str)
