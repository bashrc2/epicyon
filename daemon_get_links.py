__filename__ = "daemon_get_links.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.5.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Core GET"

from webapp_column_left import html_edit_links
from httpheaders import set_headers
from httpcodes import write2
from httpcodes import http_404


def edit_links2(self, calling_domain: str, path: str,
                translate: {}, base_dir: str,
                domain: str, cookie: str, theme: str) -> bool:
    """Show the links from the left column
    """
    if '/users/' in path and path.endswith('/editlinks'):
        nickname = path.split('/users/')[1]
        if '/' in nickname:
            nickname = nickname.split('/')[0]

        access_keys = self.server.access_keys
        if self.server.key_shortcuts.get(nickname):
            access_keys = self.server.key_shortcuts[nickname]

        msg = html_edit_links(translate,
                              base_dir,
                              path, domain,
                              self.server.default_timeline,
                              theme, access_keys)
        if msg:
            msg = msg.encode('utf-8')
            msglen = len(msg)
            set_headers(self, 'text/html', msglen,
                        cookie, calling_domain, False)
            write2(self, msg)
        else:
            http_404(self, 106)
        return True
    return False
