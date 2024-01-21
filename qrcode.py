__filename__ = "qrcode.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.5.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Core"

import pyqrcode


def save_domain_qrcode(base_dir: str, http_prefix: str,
                       domain_full: str, scale: int = 6) -> None:
    """Saves a qrcode image for the domain name
    This helps to transfer onion or i2p domains to a mobile device
    """
    qrcode_filename = base_dir + '/accounts/qrcode.png'
    url = pyqrcode.create(http_prefix + '://' + domain_full)
    url.png(qrcode_filename, scale)
