__filename__ = "webapp_media.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Timeline"

import os
from utils import valid_url_prefix


def load_peertube_instances(base_dir: str, peertube_instances: []) -> None:
    """Loads peertube instances from file into the given list
    """
    peertubeList = None
    peertube_instancesFilename = base_dir + '/accounts/peertube.txt'
    if os.path.isfile(peertube_instancesFilename):
        with open(peertube_instancesFilename, 'r') as fp:
            peertubeStr = fp.read()
            if peertubeStr:
                peertubeStr = peertubeStr.replace('\r', '')
                peertubeList = peertubeStr.split('\n')
    if not peertubeList:
        return
    for url in peertubeList:
        if url in peertube_instances:
            continue
        peertube_instances.append(url)


def _add_embedded_video_from_sites(translate: {}, content: str,
                                   peertube_instances: [],
                                   width: int, height: int) -> str:
    """Adds embedded videos
    """
    if '>vimeo.com/' in content:
        url = content.split('>vimeo.com/')[1]
        if '<' in url:
            url = url.split('<')[0]
            content = \
                content + "<center>\n<iframe loading=\"lazy\" " + \
                "src=\"https://player.vimeo.com/video/" + \
                url + "\" width=\"" + str(width) + \
                "\" height=\"" + str(height) + \
                "\" frameborder=\"0\" allow=\"autoplay; " + \
                "fullscreen\" allowfullscreen></iframe>\n</center>\n"
            return content

    videoSite = 'https://www.youtube.com'
    if '"' + videoSite in content:
        url = content.split('"' + videoSite)[1]
        if '"' in url:
            url = url.split('"')[0].replace('/watch?v=', '/embed/')
            if '&' in url:
                url = url.split('&')[0]
            if '?utm_' in url:
                url = url.split('?utm_')[0]
            content = \
                content + "<center>\n<iframe loading=\"lazy\" src=\"" + \
                videoSite + url + "\" width=\"" + str(width) + \
                "\" height=\"" + str(height) + \
                "\" frameborder=\"0\" allow=\"autoplay; fullscreen\" " + \
                "allowfullscreen></iframe>\n</center>\n"
            return content

    invidiousSites = ('https://invidious.snopyta.org',
                      'https://yewtu.be',
                      'https://tube.connect.cafe',
                      'https://invidious.kavin.rocks',
                      'https://invidiou.site',
                      'https://invidious.tube',
                      'https://invidious.xyz',
                      'https://invidious.zapashcanon.fr',
                      'http://c7hqkpkpemu6e7emz5b4vy' +
                      'z7idjgdvgaaa3dyimmeojqbgpea3xqjoid.onion',
                      'http://axqzx4s6s54s32yentfqojs3x5i7faxza6xo3ehd4' +
                      'bzzsg2ii4fv2iid.onion')
    for videoSite in invidiousSites:
        if '"' + videoSite in content:
            url = content.split('"' + videoSite)[1]
            if '"' in url:
                url = url.split('"')[0].replace('/watch?v=', '/embed/')
                if '&' in url:
                    url = url.split('&')[0]
                if '?utm_' in url:
                    url = url.split('?utm_')[0]
                content = \
                    content + "<center>\n<iframe loading=\"lazy\" src=\"" + \
                    videoSite + url + "\" width=\"" + \
                    str(width) + "\" height=\"" + str(height) + \
                    "\" frameborder=\"0\" allow=\"autoplay; fullscreen\" " + \
                    "allowfullscreen></iframe>\n</center>\n"
                return content

    videoSite = 'https://media.ccc.de'
    if '"' + videoSite in content:
        url = content.split('"' + videoSite)[1]
        if '"' in url:
            url = url.split('"')[0]
            if not url.endswith('/oembed'):
                url = url + '/oembed'
            content = \
                content + "<center>\n<iframe loading=\"lazy\" src=\"" + \
                videoSite + url + "\" width=\"" + \
                str(width) + "\" height=\"" + str(height) + \
                "\" frameborder=\"0\" allow=\"fullscreen\" " + \
                "allowfullscreen></iframe>\n</center>\n"
            return content

    if '"https://' in content:
        if peertube_instances:
            # only create an embedded video for a limited set of
            # peertube sites.
            peerTubeSites = peertube_instances
        else:
            # A default minimal set of peertube instances
            # Also see https://peertube_isolation.frama.io/list/ for
            # adversarial instances. Nothing in that list should be
            # in the defaults below.
            peerTubeSites = (
                'share.tube',
                'visionon.tv',
                'peertube.fr',
                'kolektiva.media',
                'peertube.social',
                'videos.lescommuns.org'
            )
        for site in peerTubeSites:
            site = site.strip()
            if not site:
                continue
            if len(site) < 5:
                continue
            if '.' not in site:
                continue
            siteStr = site
            if site.startswith('http://'):
                site = site.replace('http://', '')
            elif site.startswith('https://'):
                site = site.replace('https://', '')
            if site.endswith('.onion') or site.endswith('.i2p'):
                siteStr = 'http://' + site
            else:
                siteStr = 'https://' + site
            siteStr = '"' + siteStr
            if siteStr not in content:
                continue
            url = content.split(siteStr)[1]
            if '"' not in url:
                continue
            url = url.split('"')[0].replace('/watch/', '/embed/')
            content = \
                content + "<center>\n<iframe loading=\"lazy\" " + \
                "sandbox=\"allow-same-origin " + \
                "allow-scripts\" src=\"https://" + \
                site + url + "\" width=\"" + str(width) + \
                "\" height=\"" + str(height) + \
                "\" frameborder=\"0\" allow=\"autoplay; " + \
                "fullscreen\" allowfullscreen></iframe>\n</center>\n"
            return content
    return content


def _add_embedded_audio(translate: {}, content: str) -> str:
    """Adds embedded audio for mp3/ogg
    """
    if not ('.mp3' in content or '.ogg' in content):
        return content

    if '<audio ' in content:
        return content

    extension = '.mp3'
    if '.ogg' in content:
        extension = '.ogg'

    words = content.strip('\n').split(' ')
    for w in words:
        if extension not in w:
            continue
        w = w.replace('href="', '').replace('">', '')
        if w.endswith('.'):
            w = w[:-1]
        if w.endswith('"'):
            w = w[:-1]
        if w.endswith(';'):
            w = w[:-1]
        if w.endswith(':'):
            w = w[:-1]
        if not w.endswith(extension):
            continue

        if not valid_url_prefix(w):
            continue
        content += \
            '<center>\n<audio controls>\n' + \
            '<source src="' + w + '" type="audio/' + \
            extension.replace('.', '') + '">' + \
            translate['Your browser does not support the audio element.'] + \
            '</audio>\n</center>\n'
    return content


def _add_embedded_video(translate: {}, content: str) -> str:
    """Adds embedded video for mp4/webm/ogv
    """
    if not ('.mp4' in content or '.webm' in content or '.ogv' in content):
        return content

    if '<video ' in content:
        return content

    extension = '.mp4'
    if '.webm' in content:
        extension = '.webm'
    elif '.ogv' in content:
        extension = '.ogv'

    words = content.strip('\n').split(' ')
    for w in words:
        if extension not in w:
            continue
        w = w.replace('href="', '').replace('">', '')
        if w.endswith('.'):
            w = w[:-1]
        if w.endswith('"'):
            w = w[:-1]
        if w.endswith(';'):
            w = w[:-1]
        if w.endswith(':'):
            w = w[:-1]
        if not w.endswith(extension):
            continue
        if not valid_url_prefix(w):
            continue
        content += \
            '<center><figure id="videoContainer" ' + \
            'data-fullscreen="false">\n' + \
            '    <video id="video" controls ' + \
            'preload="metadata">\n' + \
            '<source src="' + w + '" type="video/' + \
            extension.replace('.', '') + '">\n' + \
            translate['Your browser does not support the video element.'] + \
            '</video>\n</figure>\n</center>\n'
    return content


def add_embedded_elements(translate: {}, content: str,
                          peertube_instances: []) -> str:
    """Adds embedded elements for various media types
    """
    content = _add_embedded_video_from_sites(translate, content,
                                             peertube_instances, 400, 300)
    content = _add_embedded_audio(translate, content)
    return _add_embedded_video(translate, content)
