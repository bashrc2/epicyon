__filename__ = "domainhandler.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"
__module_group__ = "Core"


def removeDomainPort(domain: str) -> str:
    """If the domain has a port appended then remove it
    eg. mydomain.com:80 becomes mydomain.com
    """
    if ':' in domain:
        if domain.startswith('did:'):
            return domain
        domain = domain.split(':')[0]
    return domain


def getPortFromDomain(domain: str) -> int:
    """If the domain has a port number appended then return it
    eg. mydomain.com:80 returns 80
    """
    if ':' in domain:
        if domain.startswith('did:'):
            return None
        portStr = domain.split(':')[1]
        if portStr.isdigit():
            return int(portStr)
    return None
