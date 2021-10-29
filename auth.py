__filename__ = "auth.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Security"

import base64
import hashlib
import binascii
import os
import secrets
import datetime
from utils import isSystemAccount
from utils import hasUsersPath


def _hashPassword(password: str) -> str:
    """Hash a password for storing
    """
    salt = hashlib.sha256(os.urandom(60)).hexdigest().encode('ascii')
    pwdhash = hashlib.pbkdf2_hmac('sha512',
                                  password.encode('utf-8'),
                                  salt, 100000)
    pwdhash = binascii.hexlify(pwdhash)
    return (salt + pwdhash).decode('ascii')


def _getPasswordHash(salt: str, providedPassword: str) -> str:
    """Returns the hash of a password
    """
    pwdhash = hashlib.pbkdf2_hmac('sha512',
                                  providedPassword.encode('utf-8'),
                                  salt.encode('ascii'),
                                  100000)
    return binascii.hexlify(pwdhash).decode('ascii')


def constantTimeStringCheck(string1: str, string2: str) -> bool:
    """Compares two string and returns if they are the same
    using a constant amount of time
    See https://sqreen.github.io/DevelopersSecurityBestPractices/
    timing-attack/python
    """
    # strings must be of equal length
    if len(string1) != len(string2):
        return False
    ctr = 0
    matched = True
    for ch in string1:
        if ch != string2[ctr]:
            matched = False
        else:
            # this is to make the timing more even
            # and not provide clues
            matched = matched
        ctr += 1
    return matched


def _verifyPassword(storedPassword: str, providedPassword: str) -> bool:
    """Verify a stored password against one provided by user
    """
    if not storedPassword:
        return False
    if not providedPassword:
        return False
    salt = storedPassword[:64]
    storedPassword = storedPassword[64:]
    pwHash = _getPasswordHash(salt, providedPassword)
    return constantTimeStringCheck(pwHash, storedPassword)


def createBasicAuthHeader(nickname: str, password: str) -> str:
    """This is only used by tests
    """
    authStr = \
        nickname.replace('\n', '').replace('\r', '') + \
        ':' + \
        password.replace('\n', '').replace('\r', '')
    return 'Basic ' + base64.b64encode(authStr.encode('utf-8')).decode('utf-8')


def authorizeBasic(baseDir: str, path: str, authHeader: str,
                   debug: bool) -> bool:
    """HTTP basic auth
    """
    if ' ' not in authHeader:
        if debug:
            print('DEBUG: basic auth - Authorisation header does not ' +
                  'contain a space character')
        return False
    if not hasUsersPath(path):
        if debug:
            print('DEBUG: basic auth - ' +
                  'path for Authorization does not contain a user')
        return False
    pathUsersSection = path.split('/users/')[1]
    if '/' not in pathUsersSection:
        if debug:
            print('DEBUG: basic auth - this is not a users endpoint')
        return False
    nicknameFromPath = pathUsersSection.split('/')[0]
    if isSystemAccount(nicknameFromPath):
        print('basic auth - attempted login using system account ' +
              nicknameFromPath + ' in path')
        return False
    base64Str = \
        authHeader.split(' ')[1].replace('\n', '').replace('\r', '')
    plain = base64.b64decode(base64Str).decode('utf-8')
    if ':' not in plain:
        if debug:
            print('DEBUG: basic auth header does not contain a ":" ' +
                  'separator for username:password')
        return False
    nickname = plain.split(':')[0]
    if isSystemAccount(nickname):
        print('basic auth - attempted login using system account ' + nickname +
              ' in Auth header')
        return False
    if nickname != nicknameFromPath:
        if debug:
            print('DEBUG: Nickname given in the path (' + nicknameFromPath +
                  ') does not match the one in the Authorization header (' +
                  nickname + ')')
        return False
    passwordFile = baseDir + '/accounts/passwords'
    if not os.path.isfile(passwordFile):
        if debug:
            print('DEBUG: passwords file missing')
        return False
    providedPassword = plain.split(':')[1]
    with open(passwordFile, 'r') as passfile:
        for line in passfile:
            if not line.startswith(nickname + ':'):
                continue
            storedPassword = \
                line.split(':')[1].replace('\n', '').replace('\r', '')
            success = _verifyPassword(storedPassword, providedPassword)
            if not success:
                if debug:
                    print('DEBUG: Password check failed for ' + nickname)
            return success
    print('DEBUG: Did not find credentials for ' + nickname +
          ' in ' + passwordFile)
    return False


def storeBasicCredentials(baseDir: str, nickname: str, password: str) -> bool:
    """Stores login credentials to a file
    """
    if ':' in nickname or ':' in password:
        return False
    nickname = nickname.replace('\n', '').replace('\r', '').strip()
    password = password.replace('\n', '').replace('\r', '').strip()

    if not os.path.isdir(baseDir + '/accounts'):
        os.mkdir(baseDir + '/accounts')

    passwordFile = baseDir + '/accounts/passwords'
    storeStr = nickname + ':' + _hashPassword(password)
    if os.path.isfile(passwordFile):
        if nickname + ':' in open(passwordFile).read():
            with open(passwordFile, 'r') as fin:
                with open(passwordFile + '.new', 'w+') as fout:
                    for line in fin:
                        if not line.startswith(nickname + ':'):
                            fout.write(line)
                        else:
                            fout.write(storeStr + '\n')
            os.rename(passwordFile + '.new', passwordFile)
        else:
            # append to password file
            with open(passwordFile, 'a+') as passfile:
                passfile.write(storeStr + '\n')
    else:
        with open(passwordFile, 'w+') as passfile:
            passfile.write(storeStr + '\n')
    return True


def removePassword(baseDir: str, nickname: str) -> None:
    """Removes the password entry for the given nickname
    This is called during account removal
    """
    passwordFile = baseDir + '/accounts/passwords'
    if os.path.isfile(passwordFile):
        with open(passwordFile, 'r') as fin:
            with open(passwordFile + '.new', 'w+') as fout:
                for line in fin:
                    if not line.startswith(nickname + ':'):
                        fout.write(line)
        os.rename(passwordFile + '.new', passwordFile)


def authorize(baseDir: str, path: str, authHeader: str, debug: bool) -> bool:
    """Authorize using http header
    """
    if authHeader.lower().startswith('basic '):
        return authorizeBasic(baseDir, path, authHeader, debug)
    return False


def createPassword(length: int = 10):
    validChars = 'abcdefghijklmnopqrstuvwxyz' + \
        'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    return ''.join((secrets.choice(validChars) for i in range(length)))


def recordLoginFailure(baseDir: str, ipAddress: str,
                       countDict: {}, failTime: int,
                       logToFile: bool) -> None:
    """Keeps ip addresses and the number of times login failures
    occured for them in a dict
    """
    if not countDict.get(ipAddress):
        while len(countDict.items()) > 100:
            oldestTime = 0
            oldestIP = None
            for ipAddr, ipItem in countDict.items():
                if oldestTime == 0 or ipItem['time'] < oldestTime:
                    oldestTime = ipItem['time']
                    oldestIP = ipAddr
            if oldestIP:
                del countDict[oldestIP]
        countDict[ipAddress] = {
            "count": 1,
            "time": failTime
        }
    else:
        countDict[ipAddress]['count'] += 1
        countDict[ipAddress]['time'] = failTime
        failCount = countDict[ipAddress]['count']
        if failCount > 4:
            print('WARN: ' + str(ipAddress) + ' failed to log in ' +
                  str(failCount) + ' times')

    if not logToFile:
        return

    failureLog = baseDir + '/accounts/loginfailures.log'
    writeType = 'a+'
    if not os.path.isfile(failureLog):
        writeType = 'w+'
    currTime = datetime.datetime.utcnow()
    try:
        with open(failureLog, writeType) as fp:
            # here we use a similar format to an ssh log, so that
            # systems such as fail2ban can parse it
            fp.write(currTime.strftime("%Y-%m-%d %H:%M:%SZ") + ' ' +
                     'ip-127-0-0-1 sshd[20710]: ' +
                     'Disconnecting invalid user epicyon ' +
                     ipAddress + ' port 443: ' +
                     'Too many authentication failures [preauth]\n')
    except BaseException:
        print('EX: recordLoginFailure failed ' + str(failureLog))
        pass
