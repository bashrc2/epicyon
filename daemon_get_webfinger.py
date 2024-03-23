__filename__ = "daemon_get_webfinger.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.5.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Core GET"

import json
from httpcodes import write2
from httpcodes import http_404
from httpheaders import redirect_headers
from httpheaders import set_headers
from webfinger import webfinger_lookup
from webfinger import webfinger_node_info
from webfinger import webfinger_meta
from webfinger import wellknown_protocol_handler
from utils import get_json_content_from_accept
from utils import convert_domains
from daemon_utils import has_accept


def get_webfinger(self, calling_domain: str, referer_domain: str,
                  cookie: str) -> bool:
    if not self.path.startswith('/.well-known'):
        return False
    if self.server.debug:
        print('DEBUG: WEBFINGER well-known')

    if self.server.debug:
        print('DEBUG: WEBFINGER host-meta')
    if self.path.startswith('/.well-known/host-meta'):
        if calling_domain.endswith('.onion') and \
           self.server.onion_domain:
            wf_result = \
                webfinger_meta('http', self.server.onion_domain)
        elif (calling_domain.endswith('.i2p') and
              self.server.i2p_domain):
            wf_result = \
                webfinger_meta('http', self.server.i2p_domain)
        else:
            wf_result = \
                webfinger_meta(self.server.http_prefix,
                               self.server.domain_full)
        if wf_result:
            msg = wf_result.encode('utf-8')
            msglen = len(msg)
            set_headers(self, 'application/xrd+xml', msglen,
                        None, calling_domain, True)
            write2(self, msg)
            return True
        http_404(self, 6)
        return True
    if self.path.startswith('/api/statusnet') or \
       self.path.startswith('/api/gnusocial') or \
       self.path.startswith('/siteinfo') or \
       self.path.startswith('/poco') or \
       self.path.startswith('/friendi'):
        http_404(self, 7)
        return True
    # protocol handler. See https://fedi-to.github.io/protocol-handler.html
    if self.path.startswith('/.well-known/protocol-handler'):
        if calling_domain.endswith('.onion'):
            protocol_url, _ = \
                wellknown_protocol_handler(self.path, 'http',
                                           self.server.onion_domain)
        elif calling_domain.endswith('.i2p'):
            protocol_url, _ = \
                wellknown_protocol_handler(self.path,
                                           'http', self.server.i2p_domain)
        else:
            protocol_url, _ = \
                wellknown_protocol_handler(self.path,
                                           self.server.http_prefix,
                                           self.server.domain_full)
        if protocol_url:
            redirect_headers(self, protocol_url, cookie,
                             calling_domain, 308)
        else:
            http_404(self, 8)
        return True
    # nodeinfo
    if self.path.startswith('/.well-known/nodeinfo') or \
       self.path.startswith('/.well-known/x-nodeinfo'):
        if calling_domain.endswith('.onion') and \
           self.server.onion_domain:
            wf_result = \
                webfinger_node_info('http', self.server.onion_domain)
        elif (calling_domain.endswith('.i2p') and
              self.server.i2p_domain):
            wf_result = \
                webfinger_node_info('http', self.server.i2p_domain)
        else:
            wf_result = \
                webfinger_node_info(self.server.http_prefix,
                                    self.server.domain_full)
        if wf_result:
            msg_str = json.dumps(wf_result)
            msg_str = convert_domains(calling_domain,
                                      referer_domain,
                                      msg_str,
                                      self.server.http_prefix,
                                      self.server.domain,
                                      self.server.onion_domain,
                                      self.server.i2p_domain)
            msg = msg_str.encode('utf-8')
            msglen = len(msg)
            if has_accept(self, calling_domain):
                accept_str = self.headers.get('Accept')
                protocol_str = \
                    get_json_content_from_accept(accept_str)
                set_headers(self, protocol_str, msglen,
                            None, calling_domain, True)
            else:
                set_headers(self, 'application/ld+json', msglen,
                            None, calling_domain, True)
            write2(self, msg)
            return True
        http_404(self, 9)
        return True

    if self.server.debug:
        print('DEBUG: WEBFINGER lookup ' + self.path + ' ' +
              str(self.server.base_dir))
    wf_result = \
        webfinger_lookup(self.path, self.server.base_dir,
                         self.server.domain,
                         self.server.onion_domain,
                         self.server.i2p_domain,
                         self.server.port, self.server.debug)
    if wf_result:
        msg_str = json.dumps(wf_result)
        msg_str = convert_domains(calling_domain,
                                  referer_domain,
                                  msg_str,
                                  self.server.http_prefix,
                                  self.server.domain,
                                  self.server.onion_domain,
                                  self.server.i2p_domain)
        msg = msg_str.encode('utf-8')
        msglen = len(msg)
        set_headers(self, 'application/jrd+json', msglen,
                    None, calling_domain, True)
        write2(self, msg)
    else:
        if self.server.debug:
            print('DEBUG: WEBFINGER lookup 404 ' + self.path)
        http_404(self, 10)
    return True
