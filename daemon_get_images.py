__filename__ = "daemon_get_images.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.5.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Core"

import os
import datetime
from media import path_is_video
from media import path_is_transcript
from media import path_is_audio
from httpcodes import write2
from httpcodes import http_304
from httpcodes import http_404
from httpheaders import set_headers_etag
from utils import media_file_mime_type
from utils import get_image_mime_type
from utils import get_image_extensions
from utils import acct_dir
from utils import is_image_file
from daemon_utils import etag_exists
from fitnessFunctions import fitness_performance


def show_avatar_or_banner(self, referer_domain: str, path: str,
                          base_dir: str, domain: str,
                          getreq_start_time) -> bool:
    """Shows an avatar or banner or profile background image
    """
    if '/users/' not in path:
        if '/system/accounts/avatars/' not in path and \
           '/system/accounts/headers/' not in path and \
           '/accounts/avatars/' not in path and \
           '/accounts/headers/' not in path:
            return False
    if not is_image_file(path):
        return False
    if '/system/accounts/avatars/' in path:
        avatar_str = path.split('/system/accounts/avatars/')[1]
    elif '/accounts/avatars/' in path:
        avatar_str = path.split('/accounts/avatars/')[1]
    elif '/system/accounts/headers/' in path:
        avatar_str = path.split('/system/accounts/headers/')[1]
    elif '/accounts/headers/' in path:
        avatar_str = path.split('/accounts/headers/')[1]
    else:
        avatar_str = path.split('/users/')[1]
    if not ('/' in avatar_str and '.temp.' not in path):
        return False
    avatar_nickname = avatar_str.split('/')[0]
    avatar_file = avatar_str.split('/')[1]
    avatar_file_ext = avatar_file.split('.')[-1]
    # remove any numbers, eg. avatar123.png becomes avatar.png
    if avatar_file.startswith('avatar'):
        avatar_file = 'avatar.' + avatar_file_ext
    elif avatar_file.startswith('banner'):
        avatar_file = 'banner.' + avatar_file_ext
    elif avatar_file.startswith('search_banner'):
        avatar_file = 'search_banner.' + avatar_file_ext
    elif avatar_file.startswith('image'):
        avatar_file = 'image.' + avatar_file_ext
    elif avatar_file.startswith('left_col_image'):
        avatar_file = 'left_col_image.' + avatar_file_ext
    elif avatar_file.startswith('right_col_image'):
        avatar_file = 'right_col_image.' + avatar_file_ext
    avatar_filename = \
        acct_dir(base_dir, avatar_nickname, domain) + '/' + avatar_file
    if not os.path.isfile(avatar_filename):
        original_ext = avatar_file_ext
        original_avatar_file = avatar_file
        alt_ext = get_image_extensions()
        alt_found = False
        for alt in alt_ext:
            if alt == original_ext:
                continue
            avatar_file = \
                original_avatar_file.replace('.' + original_ext,
                                             '.' + alt)
            avatar_filename = \
                acct_dir(base_dir, avatar_nickname, domain) + \
                '/' + avatar_file
            if os.path.isfile(avatar_filename):
                alt_found = True
                break
        if not alt_found:
            return False
    if etag_exists(self, avatar_filename):
        # The file has not changed
        http_304(self)
        return True

    avatar_tm = os.path.getmtime(avatar_filename)
    last_modified_time = \
        datetime.datetime.fromtimestamp(avatar_tm, datetime.timezone.utc)
    last_modified_time_str = \
        last_modified_time.strftime('%a, %d %b %Y %H:%M:%S GMT')

    media_image_type = get_image_mime_type(avatar_file)
    media_binary = None
    try:
        with open(avatar_filename, 'rb') as av_file:
            media_binary = av_file.read()
    except OSError:
        print('EX: unable to read avatar ' + avatar_filename)
    if media_binary:
        set_headers_etag(self, avatar_filename, media_image_type,
                         media_binary, None,
                         referer_domain, True,
                         last_modified_time_str)
        write2(self, media_binary)
    fitness_performance(getreq_start_time,
                        self.server.fitness,
                        '_GET', '_show_avatar_or_banner',
                        self.server.debug)
    return True


def show_cached_avatar(self, referer_domain: str, path: str,
                       base_dir: str, getreq_start_time) -> None:
    """Shows an avatar image obtained from the cache
    """
    media_filename = base_dir + '/cache' + path
    if os.path.isfile(media_filename):
        if etag_exists(self, media_filename):
            # The file has not changed
            http_304(self)
            return
        media_binary = None
        try:
            with open(media_filename, 'rb') as av_file:
                media_binary = av_file.read()
        except OSError:
            print('EX: unable to read cached avatar ' + media_filename)
        if media_binary:
            mime_type = media_file_mime_type(media_filename)
            set_headers_etag(self, media_filename,
                             mime_type,
                             media_binary, None,
                             referer_domain,
                             False, None)
            write2(self, media_binary)
            fitness_performance(getreq_start_time, self.server.fitness,
                                '_GET', '_show_cached_avatar',
                                self.server.debug)
            return
    http_404(self, 46)


def show_help_screen_image(self, path: str,
                           base_dir: str, getreq_start_time) -> None:
    """Shows a help screen image
    """
    if not is_image_file(path):
        return
    media_str = path.split('/helpimages/')[1]
    if '/' not in media_str:
        if not self.server.theme_name:
            theme = 'default'
        else:
            theme = self.server.theme_name
        icon_filename = media_str
    else:
        theme = media_str.split('/')[0]
        icon_filename = media_str.split('/')[1]
    media_filename = \
        base_dir + '/theme/' + theme + '/helpimages/' + icon_filename
    # if there is no theme-specific help image then use the default one
    if not os.path.isfile(media_filename):
        media_filename = \
            base_dir + '/theme/default/helpimages/' + icon_filename
    if etag_exists(self, media_filename):
        # The file has not changed
        http_304(self)
        return
    if os.path.isfile(media_filename):
        media_binary = None
        try:
            with open(media_filename, 'rb') as av_file:
                media_binary = av_file.read()
        except OSError:
            print('EX: unable to read help image ' + media_filename)
        if media_binary:
            mime_type = media_file_mime_type(media_filename)
            set_headers_etag(self, media_filename,
                             mime_type,
                             media_binary, None,
                             self.server.domain_full,
                             False, None)
            write2(self, media_binary)
        fitness_performance(getreq_start_time, self.server.fitness,
                            '_GET', '_show_help_screen_image',
                            self.server.debug)
        return
    http_404(self, 43)


def show_manual_image(self, path: str,
                      base_dir: str, getreq_start_time) -> None:
    """Shows an image within the manual
    """
    image_filename = path.split('/', 1)[1]
    if '/' in image_filename:
        http_404(self, 41)
        return
    media_filename = \
        base_dir + '/manual/' + image_filename
    if etag_exists(self, media_filename):
        # The file has not changed
        http_304(self)
        return
    if self.server.iconsCache.get(media_filename):
        media_binary = self.server.iconsCache[media_filename]
        mime_type_str = media_file_mime_type(media_filename)
        set_headers_etag(self, media_filename,
                         mime_type_str,
                         media_binary, None,
                         self.server.domain_full,
                         False, None)
        write2(self, media_binary)
        fitness_performance(getreq_start_time, self.server.fitness,
                            '_GET', '_show_manual_image',
                            self.server.debug)
        return
    if os.path.isfile(media_filename):
        media_binary = None
        try:
            with open(media_filename, 'rb') as av_file:
                media_binary = av_file.read()
        except OSError:
            print('EX: unable to read manual image ' +
                  media_filename)
        if media_binary:
            mime_type = media_file_mime_type(media_filename)
            set_headers_etag(self, media_filename,
                             mime_type,
                             media_binary, None,
                             self.server.domain_full,
                             False, None)
            write2(self, media_binary)
            self.server.iconsCache[media_filename] = media_binary
        fitness_performance(getreq_start_time, self.server.fitness,
                            '_GET', '_show_manual_image',
                            self.server.debug)
        return
    http_404(self, 42)


def show_specification_image(self, path: str,
                             base_dir: str, getreq_start_time) -> None:
    """Shows an image within the ActivityPub specification document
    """
    image_filename = path.split('/', 1)[1]
    if '/' in image_filename:
        http_404(self, 39)
        return
    media_filename = \
        base_dir + '/specification/' + image_filename
    if etag_exists(self, media_filename):
        # The file has not changed
        http_304(self)
        return
    if self.server.iconsCache.get(media_filename):
        media_binary = self.server.iconsCache[media_filename]
        mime_type_str = media_file_mime_type(media_filename)
        set_headers_etag(self, media_filename,
                         mime_type_str,
                         media_binary, None,
                         self.server.domain_full,
                         False, None)
        write2(self, media_binary)
        fitness_performance(getreq_start_time, self.server.fitness,
                            '_GET', '_show_specification_image',
                            self.server.debug)
        return
    if os.path.isfile(media_filename):
        media_binary = None
        try:
            with open(media_filename, 'rb') as av_file:
                media_binary = av_file.read()
        except OSError:
            print('EX: unable to read specification image ' +
                  media_filename)
        if media_binary:
            mime_type = media_file_mime_type(media_filename)
            set_headers_etag(self, media_filename,
                             mime_type,
                             media_binary, None,
                             self.server.domain_full,
                             False, None)
            write2(self, media_binary)
            self.server.iconsCache[media_filename] = media_binary
        fitness_performance(getreq_start_time, self.server.fitness,
                            '_GET', '_show_specification_image',
                            self.server.debug)
        return
    http_404(self, 40)


def show_share_image(self, path: str,
                     base_dir: str, getreq_start_time) -> bool:
    """Show a shared item image
    """
    if not is_image_file(path):
        http_404(self, 101)
        return True

    media_str = path.split('/sharefiles/')[1]
    media_filename = base_dir + '/sharefiles/' + media_str
    if not os.path.isfile(media_filename):
        http_404(self, 102)
        return True

    if etag_exists(self, media_filename):
        # The file has not changed
        http_304(self)
        return True

    media_file_type = get_image_mime_type(media_filename)
    media_binary = None
    try:
        with open(media_filename, 'rb') as av_file:
            media_binary = av_file.read()
    except OSError:
        print('EX: unable to read binary ' + media_filename)
    if media_binary:
        set_headers_etag(self, media_filename,
                         media_file_type,
                         media_binary, None,
                         self.server.domain_full,
                         False, None)
        write2(self, media_binary)
    fitness_performance(getreq_start_time,
                        self.server.fitness,
                        '_GET', '_show_share_image',
                        self.server.debug)
    return True


def show_icon(self, path: str,
              base_dir: str, getreq_start_time) -> None:
    """Shows an icon
    """
    if not path.endswith('.png'):
        http_404(self, 37)
        return
    media_str = path.split('/icons/')[1]
    if '/' not in media_str:
        if not self.server.theme_name:
            theme = 'default'
        else:
            theme = self.server.theme_name
        icon_filename = media_str
    else:
        theme = media_str.split('/')[0]
        icon_filename = media_str.split('/')[1]
    media_filename = \
        base_dir + '/theme/' + theme + '/icons/' + icon_filename
    if etag_exists(self, media_filename):
        # The file has not changed
        http_304(self)
        return
    if self.server.iconsCache.get(media_str):
        media_binary = self.server.iconsCache[media_str]
        mime_type_str = media_file_mime_type(media_filename)
        set_headers_etag(self, media_filename,
                         mime_type_str,
                         media_binary, None,
                         self.server.domain_full,
                         False, None)
        write2(self, media_binary)
        fitness_performance(getreq_start_time, self.server.fitness,
                            '_GET', '_show_icon', self.server.debug)
        return
    if os.path.isfile(media_filename):
        media_binary = None
        try:
            with open(media_filename, 'rb') as av_file:
                media_binary = av_file.read()
        except OSError:
            print('EX: unable to read icon image ' + media_filename)
        if media_binary:
            mime_type = media_file_mime_type(media_filename)
            set_headers_etag(self, media_filename,
                             mime_type,
                             media_binary, None,
                             self.server.domain_full,
                             False, None)
            write2(self, media_binary)
            self.server.iconsCache[media_str] = media_binary
        fitness_performance(getreq_start_time, self.server.fitness,
                            '_GET', '_show_icon', self.server.debug)
        return
    http_404(self, 38)


def show_media(self, path: str, base_dir: str,
               getreq_start_time) -> None:
    """Returns a media file
    """
    if is_image_file(path) or \
       path_is_video(path) or \
       path_is_transcript(path) or \
       path_is_audio(path):
        media_str = path.split('/media/')[1]
        media_filename = base_dir + '/media/' + media_str
        if os.path.isfile(media_filename):
            if etag_exists(self, media_filename):
                # The file has not changed
                http_304(self)
                return

            media_file_type = media_file_mime_type(media_filename)

            media_tm = os.path.getmtime(media_filename)
            last_modified_time = \
                datetime.datetime.fromtimestamp(media_tm,
                                                datetime.timezone.utc)
            last_modified_time_str = \
                last_modified_time.strftime('%a, %d %b %Y %H:%M:%S GMT')

            if media_filename.endswith('.vtt'):
                media_transcript = None
                try:
                    with open(media_filename, 'r',
                              encoding='utf-8') as fp_vtt:
                        media_transcript = fp_vtt.read()
                        media_file_type = 'text/vtt; charset=utf-8'
                except OSError:
                    print('EX: unable to read media binary ' +
                          media_filename)
                if media_transcript:
                    media_transcript = media_transcript.encode('utf-8')
                    set_headers_etag(self, media_filename, media_file_type,
                                     media_transcript, None,
                                     None, True,
                                     last_modified_time_str)
                    write2(self, media_transcript)
                    fitness_performance(getreq_start_time,
                                        self.server.fitness,
                                        '_GET', '_show_media',
                                        self.server.debug)
                    return
                http_404(self, 32)
                return

            media_binary = None
            try:
                with open(media_filename, 'rb') as av_file:
                    media_binary = av_file.read()
            except OSError:
                print('EX: unable to read media binary ' + media_filename)
            if media_binary:
                set_headers_etag(self, media_filename, media_file_type,
                                 media_binary, None,
                                 None, True,
                                 last_modified_time_str)
                write2(self, media_binary)
            fitness_performance(getreq_start_time, self.server.fitness,
                                '_GET', '_show_media', self.server.debug)
            return
    http_404(self, 33)
