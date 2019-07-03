__filename__ = "auth.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "0.0.1"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import base64
import hashlib
import binascii
import os
import shutil

def hashPassword(password: str) -> str:
    """Hash a password for storing
    """
    salt = hashlib.sha256(os.urandom(60)).hexdigest().encode('ascii')
    pwdhash = hashlib.pbkdf2_hmac('sha512', password.encode('utf-8'), salt, 100000)
    pwdhash = binascii.hexlify(pwdhash)
    return (salt + pwdhash).decode('ascii')
 
def verifyPassword(storedPassword: str,providedPassword: str) -> bool:
    """Verify a stored password against one provided by user
    """
    salt = storedPassword[:64]
    storedPassword = storedPassword[64:]
    pwdhash = hashlib.pbkdf2_hmac('sha512', \
                                  providedPassword.encode('utf-8'), \
                                  salt.encode('ascii'), \
                                  100000)
    pwdhash = binascii.hexlify(pwdhash).decode('ascii')
    return pwdhash == storedPassword

def createBasicAuthHeader(nickname: str,password: str) -> str:
    """This is only used by tests
    """
    authStr=nickname.replace('\n','')+':'+password.replace('\n','')
    return 'Basic '+base64.b64encode(authStr.encode('utf-8')).decode('utf-8')

def authorizeBasic(baseDir: str,authHeader: str) -> bool:
    """HTTP basic auth
    """
    if ' ' not in authHeader:
        return False
    base64Str = authHeader.split(' ')[1].replace('\n','')
    plain = base64.b64decode(base64Str).decode('utf-8')
    if ':' not in plain:
        return False
    nickname = plain.split(':')[0]
    passwordFile=baseDir+'/accounts/passwords'
    if not os.path.isfile(passwordFile):
        return False
    providedPassword = plain.split(':')[1]
    passfile = open(passwordFile, "r")
    for line in passfile:
        if line.startswith(nickname+':'):
            storedPassword=line.split(':')[1].replace('\n','')
            return verifyPassword(storedPassword,providedPassword)
    return False

def storeBasicCredentials(baseDir: str,nickname: str,password: str) -> bool:
    if ':' in nickname or ':' in password:
        return False
    nickname=nickname.replace('\n','').strip()
    password=password.replace('\n','').strip()

    if not os.path.isdir(baseDir+'/accounts'):
        os.mkdir(baseDir+'/accounts')

    passwordFile=baseDir+'/accounts/passwords'
    storeStr=nickname+':'+hashPassword(password)
    if os.path.isfile(passwordFile):
        if nickname+':' in open(passwordFile).read():
            with open(passwordFile, "r") as fin:
                with open(passwordFile+'.new', "w") as fout:
                    for line in fin:
                        if not line.startswith(nickname+':'):
                            fout.write(line)
                        else:
                            fout.write(storeStr+'\n')
            os.rename(passwordFile+'.new', passwordFile)
        else:
            # append to password file
            with open(passwordFile, "a") as passfile:
                passfile.write(storeStr+'\n')
    else:
        with open(passwordFile, "w") as passfile:
            passfile.write(storeStr+'\n')
    return True

def authorize(baseDir: str,authHeader: str) -> bool:
    if authHeader.lower().startswith('basic '):
        return authorizeBasic(baseDir,authHeader)
    return False
