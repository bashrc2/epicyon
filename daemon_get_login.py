__filename__ = "daemon_get_login.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.5.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Core"

from utils import get_instance_url
from httpheaders import redirect_headers
from fitnessFunctions import fitness_performance


def redirect_to_login_screen(self, calling_domain: str, path: str,
                             http_prefix: str, domain_full: str,
                             onion_domain: str, i2p_domain: str,
                             getreq_start_time,
                             authorized: bool, debug: bool):
    """Redirects to the login screen if necessary
    """
    divert_to_login_screen = False
    if '/media/' not in path and \
       '/ontologies/' not in path and \
       '/data/' not in path and \
       '/sharefiles/' not in path and \
       '/statuses/' not in path and \
       '/emoji/' not in path and \
       '/tags/' not in path and \
       '/tagmaps/' not in path and \
       '/avatars/' not in path and \
       '/favicons/' not in path and \
       '/headers/' not in path and \
       '/fonts/' not in path and \
       '/icons/' not in path:
        divert_to_login_screen = True
        if path.startswith('/users/'):
            nick_str = path.split('/users/')[1]
            if '/' not in nick_str and '?' not in nick_str:
                divert_to_login_screen = False
            else:
                if path.endswith('/following') or \
                   path.endswith('/followers') or \
                   path.endswith('/skills') or \
                   path.endswith('/roles') or \
                   path.endswith('/wanted') or \
                   path.endswith('/shares'):
                    divert_to_login_screen = False

    if divert_to_login_screen and not authorized:
        divert_path = '/login'
        if self.server.news_instance:
            # for news instances if not logged in then show the
            # front page
            divert_path = '/users/news'
        if debug:
            print('DEBUG: divert_to_login_screen=' +
                  str(divert_to_login_screen))
            print('DEBUG: authorized=' + str(authorized))
            print('DEBUG: path=' + path)
        redirect_url = \
            get_instance_url(calling_domain,
                             http_prefix, domain_full,
                             onion_domain, i2p_domain) + \
            divert_path
        redirect_headers(self, redirect_url, None, calling_domain)
        fitness_performance(getreq_start_time,
                            self.server.fitness,
                            '_GET', '_redirect_to_login_screen',
                            debug)
        return True
    return False
