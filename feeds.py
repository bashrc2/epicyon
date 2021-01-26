__filename__ = "feeds.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"


def rss2TagHeader(hashtag: str, httpPrefix: str, domainFull: str) -> str:
    rssStr = "<?xml version=\"1.0\" encoding=\"UTF-8\" ?>"
    rssStr += "<rss version=\"2.0\">"
    rssStr += '<channel>'
    rssStr += '    <title>#' + hashtag + '</title>'
    rssStr += '    <link>' + httpPrefix + '://' + domainFull + \
        '/tags/rss2/' + hashtag + '</link>'
    return rssStr


def rss2TagFooter() -> str:
    rssStr = '</channel>'
    rssStr += '</rss>'
    return rssStr
