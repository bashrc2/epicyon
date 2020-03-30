__filename__="auth.py"
__author__="Bob Mottram"
__license__="AGPL3+"
__version__="1.1.0"
__maintainer__="Bob Mottram"
__email__="bob@freedombone.net"
__status__="Production"

import base64
import hashlib
import binascii
import os
import shutil
import random

def hashPassword(password: str) -> str:
    """Hash a password for storing
    """
    salt=hashlib.sha256(os.urandom(60)).hexdigest().encode('ascii')
    pwdhash= \
        hashlib.pbkdf2_hmac('sha512', \
                            password.encode('utf-8'), \
                            salt, 100000)
    pwdhash=binascii.hexlify(pwdhash)
    return (salt+pwdhash).decode('ascii')

def verifyPassword(storedPassword: str,providedPassword: str) -> bool:
    """Verify a stored password against one provided by user
    """
    salt=storedPassword[:64]
    storedPassword=storedPassword[64:]
    pwdhash= \
        hashlib.pbkdf2_hmac('sha512', \
                            providedPassword.encode('utf-8'), \
                            salt.encode('ascii'), \
                            100000)
    pwdhash=binascii.hexlify(pwdhash).decode('ascii')
    return pwdhash==storedPassword

def createBasicAuthHeader(nickname: str,password: str) -> str:
    """This is only used by tests
    """
    authStr=nickname.replace('\n','')+':'+password.replace('\n','')
    return 'Basic '+base64.b64encode(authStr.encode('utf-8')).decode('utf-8')

def authorizeBasic(baseDir: str,path: str,authHeader: str,debug: bool) -> bool:
    """HTTP basic auth
    """
    if ' ' not in authHeader:
        if debug:
            print('DEBUG: Authorixation header does not '+ \
                  'contain a space character')
        return False
    if '/users/' not in path and \
       '/channel/' not in path and \
       '/profile/' not in path:
        if debug:
            print('DEBUG: Path for Authorization does not contain a user')
        return False
    pathUsersSection=path.split('/users/')[1]
    if '/' not in pathUsersSection:
        if debug:
            print('DEBUG: This is not a users endpoint')
        return False
    nicknameFromPath=pathUsersSection.split('/')[0]
    base64Str=authHeader.split(' ')[1].replace('\n','')
    plain=base64.b64decode(base64Str).decode('utf-8')
    if ':' not in plain:
        if debug:
            print('DEBUG: Basic Auth header does not contain a ":" '+ \
                  'separator for username:password')
        return False
    nickname=plain.split(':')[0]
    if nickname!=nicknameFromPath:
        if debug:
            print('DEBUG: Nickname given in the path ('+nicknameFromPath+ \
                  ') does not match the one in the Authorization header ('+ \
                  nickname+')')
        return False
    passwordFile=baseDir+'/accounts/passwords'
    if not os.path.isfile(passwordFile):
        if debug:
            print('DEBUG: passwords file missing')
        return False
    providedPassword=plain.split(':')[1]
    passfile=open(passwordFile, "r")
    for line in passfile:
        if line.startswith(nickname+':'):
            storedPassword=line.split(':')[1].replace('\n','')
            success=verifyPassword(storedPassword,providedPassword)
            if not success:
                if debug:
                    print('DEBUG: Password check failed for '+nickname)
            return success
    print('DEBUG: Did not find credentials for '+nickname+' in '+passwordFile)
    return False

def storeBasicCredentials(baseDir: str,nickname: str,password: str) -> bool:
    """Stores login credentials to a file
    """
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

def removePassword(baseDir: str,nickname: str) -> None:
    """Removes the password entry for the given nickname
    This is called during account removal
    """
    passwordFile=baseDir+'/accounts/passwords'
    if os.path.isfile(passwordFile):
        with open(passwordFile, "r") as fin:
            with open(passwordFile+'.new', "w") as fout:
                for line in fin:
                    if not line.startswith(nickname+':'):
                        fout.write(line)
        os.rename(passwordFile+'.new', passwordFile)

def authorize(baseDir: str,path: str,authHeader: str,debug: bool) -> bool:
    """Authorize using http header
    """
    if authHeader.lower().startswith('basic '):
        return authorizeBasic(baseDir,path,authHeader,debug)
    return False

def createPassword(length=10):
    validChars='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    return ''.join((random.choice(validChars) for i in range(length)))
