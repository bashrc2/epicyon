__filename__ = "mitm.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.7.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Core"

# some posts are proxied through a third party server which removes transport
# layer security, breaking the end-to-end principle. Epicyon warns the
# user when it knows that this is happening.
# The proxy may not be able to alter the post in transit, due to http
# signature, but they can conduct surveillance and gather posts for LLM
# training (or sale for that purpose).

import os
from utils import data_dir
from data import load_string
from data import save_string


def detect_mitm(self) -> bool:
    """Detect if a request contains a MiTM
    """
    mitm_domains = (
        'cloudflare', 'radware', 'imperva', 'akamai', 'azure',
        'fastly', 'google'
    )
    # look for domains within these headers
    check_headers = (
        'Server', 'Report-To', 'Report-to', 'report-to',
        'Expect-CT', 'Expect-Ct', 'expect-ct'
    )
    for interloper in mitm_domains:
        for header_name in check_headers:
            if not self.headers.get(header_name):
                continue
            if interloper in str(self.headers[header_name]).lower():
                return True
    # The presence of these headers on their own indicates a MiTM
    mitm_headers = (
        'CF-Connecting-IP', 'CF-RAY', 'CF-IPCountry', 'CF-Visitor',
        'CDN-Loop', 'CF-Worker', 'CF-Cache-Status'
    )
    for header_name in mitm_headers:
        if self.headers.get(header_name):
            return True
        if self.headers.get(header_name.lower()):
            return True
    return False


def load_mitm_servers(base_dir: str) -> []:
    """Loads a list of servers implementing insecure transport security
    """
    mitm_servers_filename = data_dir(base_dir) + '/mitm_servers.txt'
    mitm_servers: list[str] = []
    if os.path.isfile(mitm_servers_filename):
        mitm_servers_str = \
            load_string(mitm_servers_filename,
                        'EX: error while reading mitm_servers.txt')
        if mitm_servers_str:
            mitm_servers = mitm_servers_str.split('\n')
    if not mitm_servers:
        return []
    return mitm_servers


def save_mitm_servers(base_dir: str, mitm_servers: []) -> None:
    """Saves a list of servers implementing insecure transport security
    """
    mitm_servers_str = ''
    for domain in mitm_servers:
        if domain:
            mitm_servers_str += domain + '\n'

    mitm_servers_filename = data_dir(base_dir) + '/mitm_servers.txt'
    save_string(mitm_servers_str, mitm_servers_filename,
                'EX: error while saving mitm_servers.txt')
