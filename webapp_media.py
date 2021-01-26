__filename__ = "webapp_media.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import os


def loadPeertubeInstances(baseDir: str, peertubeInstances: []) -> None:
    """Loads peertube instances from file into the given list
    """
    peertubeList = None
    peertubeInstancesFilename = baseDir + '/accounts/peertube.txt'
    if os.path.isfile(peertubeInstancesFilename):
        with open(peertubeInstancesFilename, 'r') as fp:
            peertubeStr = fp.read()
            if peertubeStr:
                peertubeStr = peertubeStr.replace('\r', '')
                peertubeList = peertubeStr.split('\n')
    if not peertubeList:
        return
    for url in peertubeList:
        if url in peertubeInstances:
            continue
        peertubeInstances.append(url)


def _addEmbeddedVideoFromSites(translate: {}, content: str,
                               peertubeInstances: [],
                               width=400, height=300) -> str:
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
        if peertubeInstances:
            peerTubeSites = peertubeInstances
        else:
            # A default selection of the current larger peertube sites,
            # mostly French and German language.
            # These have only been semi-vetted, and so should be under
            # continuous review.
            # Also see https://peertube_isolation.frama.io/list/ for
            # adversarial instances. Nothing in that list should be
            # in the defaults below.
            peerTubeSites = ('share.tube',
                             'tube.22decembre.eu',
                             'libre.video',
                             'peertube.linuxrocks.online',
                             'spacepub.space',
                             'tube.tchncs.de',
                             'video.irem.univ-paris-diderot.fr',
                             'peertube.openstreetmap.fr',
                             'video.antopie.org',
                             'scitech.video',
                             'video.ploud.fr',
                             'diode.zone',
                             'visionon.tv',
                             'peertube.fr',
                             'peertube.live',
                             'kolektiva.media',
                             'betamax.video',
                             'peertube.social',
                             'videos.lescommuns.org',
                             'video.tedomum.net',
                             'tilvids.com',
                             'exode.me',
                             'peertube.video')
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
            if siteStr in content:
                url = content.split(siteStr)[1]
                if '"' in url:
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


def _addEmbeddedAudio(translate: {}, content: str) -> str:
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

        if not (w.startswith('http') or w.startswith('dat:') or
                w.startswith('hyper:') or w.startswith('i2p:') or
                w.startswith('gnunet:') or
                '/' in w):
            continue
        url = w
        content += '<center>\n<audio controls>\n'
        content += \
            '<source src="' + url + '" type="audio/' + \
            extension.replace('.', '') + '">'
        content += \
            translate['Your browser does not support the audio element.']
        content += '</audio>\n</center>\n'
    return content


def _addEmbeddedVideo(translate: {}, content: str,
                      width=400, height=300) -> str:
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
        if not (w.startswith('http') or w.startswith('dat:') or
                w.startswith('hyper:') or w.startswith('i2p:') or
                w.startswith('gnunet:') or
                '/' in w):
            continue
        url = w
        content += \
            '<center>\n<video width="' + str(width) + '" height="' + \
            str(height) + '" controls>\n'
        content += \
            '<source src="' + url + '" type="video/' + \
            extension.replace('.', '') + '">\n'
        content += \
            translate['Your browser does not support the video element.']
        content += '</video>\n</center>\n'
    return content


def addEmbeddedElements(translate: {}, content: str,
                        peertubeInstances: []) -> str:
    """Adds embedded elements for various media types
    """
    content = _addEmbeddedVideoFromSites(translate, content,
                                         peertubeInstances)
    content = _addEmbeddedAudio(translate, content)
    return _addEmbeddedVideo(translate, content)
