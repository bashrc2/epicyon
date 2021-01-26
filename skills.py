__filename__ = "skills.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import os
from webfinger import webfingerHandle
from auth import createBasicAuthHeader
from posts import getPersonBox
from session import postJson
from utils import getFullDomain
from utils import getNicknameFromActor
from utils import getDomainFromActor
from utils import loadJson
from utils import saveJson


def setSkillLevel(baseDir: str, nickname: str, domain: str,
                  skill: str, skillLevelPercent: int) -> bool:
    """Set a skill level for a person
    Setting skill level to zero removes it
    """
    if skillLevelPercent < 0 or skillLevelPercent > 100:
        return False
    actorFilename = baseDir + '/accounts/' + nickname + '@' + domain + '.json'
    if not os.path.isfile(actorFilename):
        return False

    actorJson = loadJson(actorFilename)
    if actorJson:
        if not actorJson.get('skills'):
            actorJson['skills'] = {}
        if skillLevelPercent > 0:
            actorJson['skills'][skill] = skillLevelPercent
        else:
            del actorJson['skills'][skill]
        saveJson(actorJson, actorFilename)
    return True


def getSkills(baseDir: str, nickname: str, domain: str) -> []:
    """Returns the skills for a given person
    """
    actorFilename = baseDir + '/accounts/' + nickname + '@' + domain + '.json'
    if not os.path.isfile(actorFilename):
        return False

    actorJson = loadJson(actorFilename)
    if actorJson:
        if not actorJson.get('skills'):
            return None
        return actorJson['skills']
    return None


def outboxSkills(baseDir: str, nickname: str, messageJson: {},
                 debug: bool) -> bool:
    """Handles receiving a skills update
    """
    if not messageJson.get('type'):
        return False
    if not messageJson['type'] == 'Skill':
        return False
    if not messageJson.get('actor'):
        return False
    if not messageJson.get('object'):
        return False
    if not isinstance(messageJson['object'], str):
        return False

    actorNickname = getNicknameFromActor(messageJson['actor'])
    if actorNickname != nickname:
        return False
    domain, port = getDomainFromActor(messageJson['actor'])
    skill = messageJson['object'].replace('"', '').split(';')[0].strip()
    skillLevelPercentStr = \
        messageJson['object'].replace('"', '').split(';')[1].strip()
    skillLevelPercent = 50
    if skillLevelPercentStr.isdigit():
        skillLevelPercent = int(skillLevelPercentStr)

    return setSkillLevel(baseDir, nickname, domain,
                         skill, skillLevelPercent)


def sendSkillViaServer(baseDir: str, session, nickname: str, password: str,
                       domain: str, port: int,
                       httpPrefix: str,
                       skill: str, skillLevelPercent: int,
                       cachedWebfingers: {}, personCache: {},
                       debug: bool, projectVersion: str) -> {}:
    """Sets a skill for a person via c2s
    """
    if not session:
        print('WARN: No session for sendSkillViaServer')
        return 6

    domainFull = getFullDomain(domain, port)

    actor = httpPrefix + '://' + domainFull + '/users/' + nickname
    toUrl = actor
    ccUrl = actor + '/followers'

    if skillLevelPercent:
        skillStr = skill + ';' + str(skillLevelPercent)
    else:
        skillStr = skill + ';0'

    newSkillJson = {
        'type': 'Skill',
        'actor': actor,
        'object': '"'+skillStr+'"',
        'to': [toUrl],
        'cc': [ccUrl]
    }

    handle = httpPrefix + '://' + domainFull + '/@' + nickname

    # lookup the inbox for the To handle
    wfRequest = \
        webfingerHandle(session, handle, httpPrefix,
                        cachedWebfingers,
                        domain, projectVersion)
    if not wfRequest:
        if debug:
            print('DEBUG: announce webfinger failed for ' + handle)
        return 1
    if not isinstance(wfRequest, dict):
        print('WARN: Webfinger for ' + handle + ' did not return a dict. ' +
              str(wfRequest))
        return 1

    postToBox = 'outbox'

    # get the actor inbox for the To handle
    (inboxUrl, pubKeyId, pubKey,
     fromPersonId, sharedInbox,
     avatarUrl, displayName) = getPersonBox(baseDir, session, wfRequest,
                                            personCache, projectVersion,
                                            httpPrefix, nickname, domain,
                                            postToBox, 86725)

    if not inboxUrl:
        if debug:
            print('DEBUG: No ' + postToBox + ' was found for ' + handle)
        return 3
    if not fromPersonId:
        if debug:
            print('DEBUG: No actor was found for ' + handle)
        return 4

    authHeader = createBasicAuthHeader(nickname, password)

    headers = {
        'host': domain,
        'Content-type': 'application/json',
        'Authorization': authHeader
    }
    postResult = \
        postJson(session, newSkillJson, [], inboxUrl, headers)
    if not postResult:
        if debug:
            print('DEBUG: POST announce failed for c2s to ' + inboxUrl)
#        return 5

    if debug:
        print('DEBUG: c2s POST skill success')

    return newSkillJson
