__filename__ = "mastoapiv1.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.1.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import os
from utils import loadJson


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
        "id": accountJson['id'],
        "username": nickname,
        "acct": nickname,
        "display_name": accountJson['preferredUsername'],
        "locked": accountJson['manuallyApprovesFollowers'],
#        "created_at": "",
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
