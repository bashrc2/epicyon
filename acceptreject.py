__filename__ = "acceptreject.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import os
from utils import hasUsersPath
from utils import getFullDomain
from utils import urlPermitted
from utils import getDomainFromActor
from utils import getNicknameFromActor
from utils import domainPermitted
from utils import followPerson


def _createAcceptReject(baseDir: str, federationList: [],
                        nickname: str, domain: str, port: int,
                        toUrl: str, ccUrl: str, httpPrefix: str,
                        objectJson: {}, acceptType: str) -> {}:
    """Accepts or rejects something (eg. a follow request or offer)
    Typically toUrl will be https://www.w3.org/ns/activitystreams#Public
    and ccUrl might be a specific person favorited or repeated and
    the followers url objectUrl is typically the url of the message,
    corresponding to url or atomUri in createPostBase
    """
    if not objectJson.get('actor'):
        return None

    if not urlPermitted(objectJson['actor'], federationList):
        return None

    domain = getFullDomain(domain, port)

    newAccept = {
        "@context": "https://www.w3.org/ns/activitystreams",
        'type': acceptType,
        'actor': httpPrefix+'://' + domain + '/users/' + nickname,
        'to': [toUrl],
        'cc': [],
        'object': objectJson
    }
    if ccUrl:
        if len(ccUrl) > 0:
            newAccept['cc'] = [ccUrl]
    return newAccept


def createAccept(baseDir: str, federationList: [],
                 nickname: str, domain: str, port: int,
                 toUrl: str, ccUrl: str, httpPrefix: str,
                 objectJson: {}) -> {}:
    return _createAcceptReject(baseDir, federationList,
                               nickname, domain, port,
                               toUrl, ccUrl, httpPrefix,
                               objectJson, 'Accept')


def createReject(baseDir: str, federationList: [],
                 nickname: str, domain: str, port: int,
                 toUrl: str, ccUrl: str, httpPrefix: str,
                 objectJson: {}) -> {}:
    return _createAcceptReject(baseDir, federationList,
                               nickname, domain, port,
                               toUrl, ccUrl,
                               httpPrefix, objectJson, 'Reject')


def _acceptFollow(baseDir: str, domain: str, messageJson: {},
                  federationList: [], debug: bool) -> None:
    """Receiving a follow Accept activity
    """
    if not messageJson.get('object'):
        return
    if not messageJson['object'].get('type'):
        return
    if not messageJson['object']['type'] == 'Follow':
        return
    if debug:
        print('DEBUG: receiving Follow activity')
    if not messageJson['object'].get('actor'):
        print('DEBUG: no actor in Follow activity')
        return
    # no, this isn't a mistake
    if not messageJson['object'].get('object'):
        print('DEBUG: no object within Follow activity')
        return
    if not messageJson.get('to'):
        if debug:
            print('DEBUG: No "to" parameter in follow Accept')
        return
    if debug:
        print('DEBUG: follow Accept received')
    thisActor = messageJson['object']['actor']
    nickname = getNicknameFromActor(thisActor)
    if not nickname:
        print('WARN: no nickname found in ' + thisActor)
        return
    acceptedDomain, acceptedPort = getDomainFromActor(thisActor)
    if not acceptedDomain:
        if debug:
            print('DEBUG: domain not found in ' + thisActor)
        return
    if not nickname:
        if debug:
            print('DEBUG: nickname not found in ' + thisActor)
        return
    if acceptedPort:
        if '/' + acceptedDomain + ':' + str(acceptedPort) + \
           '/users/' + nickname not in thisActor:
            if debug:
                print('Port: ' + str(acceptedPort))
                print('Expected: /' + acceptedDomain + ':' +
                      str(acceptedPort) + '/users/' + nickname)
                print('Actual:   ' + thisActor)
                print('DEBUG: unrecognized actor ' + thisActor)
            return
    else:
        if not '/' + acceptedDomain+'/users/' + nickname in thisActor:
            if debug:
                print('Expected: /' + acceptedDomain+'/users/' + nickname)
                print('Actual:   ' + thisActor)
                print('DEBUG: unrecognized actor ' + thisActor)
            return
    followedActor = messageJson['object']['object']
    followedDomain, port = getDomainFromActor(followedActor)
    if not followedDomain:
        print('DEBUG: no domain found within Follow activity object ' +
              followedActor)
        return
    followedDomainFull = followedDomain
    if port:
        followedDomainFull = followedDomain+':' + str(port)
    followedNickname = getNicknameFromActor(followedActor)
    if not followedNickname:
        print('DEBUG: no nickname found within Follow activity object ' +
              followedActor)
        return

    acceptedDomainFull = acceptedDomain
    if acceptedPort:
        acceptedDomainFull = acceptedDomain + ':' + str(acceptedPort)

    # has this person already been unfollowed?
    unfollowedFilename = baseDir + '/accounts/' + \
        nickname + '@' + acceptedDomainFull + '/unfollowed.txt'
    if os.path.isfile(unfollowedFilename):
        if followedNickname + '@' + followedDomainFull in \
           open(unfollowedFilename).read():
            if debug:
                print('DEBUG: follow accept arrived for ' +
                      nickname + '@' + acceptedDomainFull +
                      ' from ' + followedNickname + '@' + followedDomainFull +
                      ' but they have been unfollowed')
            return

    if followPerson(baseDir,
                    nickname, acceptedDomainFull,
                    followedNickname, followedDomainFull,
                    federationList, debug):
        if debug:
            print('DEBUG: ' + nickname + '@' + acceptedDomainFull +
                  ' followed ' + followedNickname + '@' + followedDomainFull)
    else:
        if debug:
            print('DEBUG: Unable to create follow - ' +
                  nickname + '@' + acceptedDomain+' -> ' +
                  followedNickname + '@' + followedDomain)


def receiveAcceptReject(session, baseDir: str,
                        httpPrefix: str, domain: str, port: int,
                        sendThreads: [], postLog: [], cachedWebfingers: {},
                        personCache: {}, messageJson: {}, federationList: [],
                        debug: bool) -> bool:
    """Receives an Accept or Reject within the POST section of HTTPServer
    """
    if messageJson['type'] != 'Accept' and messageJson['type'] != 'Reject':
        return False
    if not messageJson.get('actor'):
        if debug:
            print('DEBUG: ' + messageJson['type'] + ' has no actor')
        return False
    if not hasUsersPath(messageJson['actor']):
        if debug:
            print('DEBUG: "users" or "profile" missing from actor in ' +
                  messageJson['type'] + '. Assuming single user instance.')
    domain, tempPort = getDomainFromActor(messageJson['actor'])
    if not domainPermitted(domain, federationList):
        if debug:
            print('DEBUG: ' + messageJson['type'] +
                  ' from domain not permitted - ' + domain)
        return False
    nickname = getNicknameFromActor(messageJson['actor'])
    if not nickname:
        # single user instance
        nickname = 'dev'
        if debug:
            print('DEBUG: ' + messageJson['type'] +
                  ' does not contain a nickname. ' +
                  'Assuming single user instance.')
    # receive follow accept
    _acceptFollow(baseDir, domain, messageJson, federationList, debug)
    if debug:
        print('DEBUG: Uh, ' + messageJson['type'] + ', I guess')
    return True
