__filename__ = "daemon_get_exports.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.7.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Daemon GET"

from src.httpcodes import http_404
from src.httpcodes import write2
from src.httpheaders import set_headers
from src.httpheaders import set_headers_etag
from src.utils import get_nickname_from_actor
from src.blocking import export_blocking_file
from src.data import load_binary
from src.data import is_a_file


def get_exported_blocks(self, path: str, base_dir: str,
                        domain: str,
                        calling_domain: str) -> None:
    """Returns an exported blocks csv file
    """
    filename = path.split('/exports/', 1)[1]
    filename = base_dir + '/exports/' + filename
    nickname = get_nickname_from_actor(path)
    if nickname:
        blocks_str = export_blocking_file(base_dir, nickname, domain)
        if blocks_str:
            msg = blocks_str.encode('utf-8')
            msglen = len(msg)
            set_headers(self, 'text/csv',
                        msglen, None, calling_domain, False)
            write2(self, msg)
            return
    http_404(self, 20)


def get_exported_theme(self, path: str, base_dir: str,
                       domain_full: str) -> None:
    """Returns an exported theme zip file
    """
    filename = path.split('/exports/', 1)[1]
    filename = base_dir + '/exports/' + filename
    if is_a_file(filename):
        export_binary = load_binary(filename,
                                    'EX: unable to read theme export ' +
                                    filename)
        if export_binary:
            export_type = 'application/zip'
            set_headers_etag(self, filename, export_type,
                             export_binary, None,
                             domain_full, False, None)
            write2(self, export_binary)
    http_404(self, 19)
