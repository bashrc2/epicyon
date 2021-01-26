__filename__ = "mastoapiv1.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import os
from utils import loadJson


def getMastApiV1Id(path: str) -> int:
    """Extracts the mastodon Id number from the given path
    """
    mastoId = None
    idPath = '/api/v1/accounts/:'
    if not path.startswith(idPath):
        return None
    mastoIdStr = path.replace(idPath, '')
    if '/' in mastoIdStr:
        mastoIdStr = mastoIdStr.split('/')[0]
    if mastoIdStr.isdigit():
        mastoId = int(mastoIdStr)
        return mastoId
    return None


def getMastoApiV1IdFromNickname(nickname: str) -> int:
    """Given an account nickname return the corresponding mastodon id
    """
    return int.from_bytes(nickname.encode('utf-8'), 'little')


def _intToBytes(num: int) -> str:
    if num == 0:
        return b""
    else:
        return _intToBytes(num // 256) + bytes([num % 256])


def getNicknameFromMastoApiV1Id(mastoId: int) -> str:
    """Given the mastodon Id return the nickname
    """
    nickname = _intToBytes(mastoId).decode()
    return nickname[::-1]


def getMastoApiV1Account(baseDir: str, nickname: str, domain: str) -> {}:
    """See https://github.com/McKael/mastodon-documentation/
    blob/master/Using-the-API/API.md#account
    Authorization has already been performed
    """
    accountFilename = \
        baseDir + '/accounts/' + nickname + '@' + domain + '.json'
    if not os.path.isfile(accountFilename):
        return {}
    accountJson = loadJson(accountFilename)
    if not accountJson:
        return {}
    mastoAccountJson = {
        "id": getMastoApiV1IdFromNickname(nickname),
        "username": nickname,
        "acct": nickname,
        "display_name": accountJson['name'],
        "locked": accountJson['manuallyApprovesFollowers'],
        "created_at": "2016-10-05T10:30:00Z",
        "followers_count": 0,
        "following_count": 0,
        "statuses_count": 0,
        "note": accountJson['summary'],
        "url": accountJson['id'],
        "avatar": accountJson['icon']['url'],
        "avatar_static": accountJson['icon']['url'],
        "header": accountJson['image']['url'],
        "header_static": accountJson['image']['url']
    }
    return mastoAccountJson
