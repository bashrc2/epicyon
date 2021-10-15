__filename__ = "skills.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Profile Metadata"

import os
from webfinger import webfingerHandle
from auth import createBasicAuthHeader
from posts import getPersonBox
from session import postJson
from utils import hasObjectString
from utils import getFullDomain
from utils import getNicknameFromActor
from utils import getDomainFromActor
from utils import loadJson
from utils import getOccupationSkills
from utils import setOccupationSkillsList
from utils import acctDir
from utils import localActorUrl
from utils import hasActor


def setSkillsFromDict(actorJson: {}, skillsDict: {}) -> []:
    """Converts a dict containing skills to a list
    Returns the string version of the dictionary
    """
    skillsList = []
    for name, value in skillsDict.items():
        skillsList.append(name + ':' + str(value))
    setOccupationSkillsList(actorJson, skillsList)
    return skillsList


def getSkillsFromList(skillsList: []) -> {}:
    """Returns a dict of skills from a list
    """
    if isinstance(skillsList, list):
        skillsList2 = skillsList
    else:
        skillsList2 = skillsList.split(',')
    skillsDict = {}
    for skill in skillsList2:
        if ':' not in skill:
            continue
        name = skill.split(':')[0].strip().lower()
        valueStr = skill.split(':')[1]
        if not valueStr.isdigit():
            continue
        skillsDict[name] = int(valueStr)
    return skillsDict


def actorSkillValue(actorJson: {}, skillName: str) -> int:
    """Returns The skill level from an actor
    """
    ocSkillsList = getOccupationSkills(actorJson)
    skillsDict = getSkillsFromList(ocSkillsList)
    if not skillsDict:
        return 0
    skillName = skillName.lower()
    if skillsDict.get(skillName):
        return skillsDict[skillName]
    return 0


def noOfActorSkills(actorJson: {}) -> int:
    """Returns the number of skills that an actor has
    """
    if actorJson.get('hasOccupation'):
        skillsList = getOccupationSkills(actorJson)
        return len(skillsList)
    return 0


def setActorSkillLevel(actorJson: {},
                       skill: str, skillLevelPercent: int) -> bool:
    """Set a skill level for a person
    Setting skill level to zero removes it
    """
    if skillLevelPercent < 0 or skillLevelPercent > 100:
        return False

    if not actorJson:
        return True
    if not actorJson.get('hasOccupation'):
        actorJson['hasOccupation'] = [{
            '@type': 'Occupation',
            'name': '',
            "occupationLocation": {
                "@type": "City",
                "name": "Fediverse"
            },
            'skills': []
        }]
    ocSkillsList = getOccupationSkills(actorJson)
    skillsDict = getSkillsFromList(ocSkillsList)
    if not skillsDict.get(skill):
        if len(skillsDict.items()) >= 32:
            print('WARN: Maximum number of skills reached for ' +
                  actorJson['id'])
            return False
    if skillLevelPercent > 0:
        skillsDict[skill] = skillLevelPercent
    else:
        if skillsDict.get(skill):
            del skillsDict[skill]
    setSkillsFromDict(actorJson, skillsDict)
    return True


def setSkillLevel(baseDir: str, nickname: str, domain: str,
                  skill: str, skillLevelPercent: int) -> bool:
    """Set a skill level for a person
    Setting skill level to zero removes it
    """
    if skillLevelPercent < 0 or skillLevelPercent > 100:
        return False
    actorFilename = acctDir(baseDir, nickname, domain) + '.json'
    if not os.path.isfile(actorFilename):
        return False

    actorJson = loadJson(actorFilename)
    return setActorSkillLevel(actorJson,
                              skill, skillLevelPercent)


def getSkills(baseDir: str, nickname: str, domain: str) -> []:
    """Returns the skills for a given person
    """
    actorFilename = acctDir(baseDir, nickname, domain) + '.json'
    if not os.path.isfile(actorFilename):
        return False

    actorJson = loadJson(actorFilename)
    if actorJson:
        if not actorJson.get('hasOccupation'):
            return None
        ocSkillsList = getOccupationSkills(actorJson)
        return getSkillsFromList(ocSkillsList)
    return None


def outboxSkills(baseDir: str, nickname: str, messageJson: {},
                 debug: bool) -> bool:
    """Handles receiving a skills update
    """
    if not messageJson.get('type'):
        return False
    if not messageJson['type'] == 'Skill':
        return False
    if not hasActor(messageJson, debug):
        return False
    if not hasObjectString(messageJson, debug):
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
                       debug: bool, projectVersion: str,
                       signingPrivateKeyPem: str) -> {}:
    """Sets a skill for a person via c2s
    """
    if not session:
        print('WARN: No session for sendSkillViaServer')
        return 6

    domainFull = getFullDomain(domain, port)

    actor = localActorUrl(httpPrefix, nickname, domainFull)
    toUrl = actor
    ccUrl = actor + '/followers'

    if skillLevelPercent:
        skillStr = skill + ';' + str(skillLevelPercent)
    else:
        skillStr = skill + ';0'

    newSkillJson = {
        'type': 'Skill',
        'actor': actor,
        'object': '"' + skillStr + '"',
        'to': [toUrl],
        'cc': [ccUrl]
    }

    handle = httpPrefix + '://' + domainFull + '/@' + nickname

    # lookup the inbox for the To handle
    wfRequest = \
        webfingerHandle(session, handle, httpPrefix,
                        cachedWebfingers,
                        domain, projectVersion, debug, False,
                        signingPrivateKeyPem)
    if not wfRequest:
        if debug:
            print('DEBUG: skill webfinger failed for ' + handle)
        return 1
    if not isinstance(wfRequest, dict):
        print('WARN: skill webfinger for ' + handle +
              ' did not return a dict. ' + str(wfRequest))
        return 1

    postToBox = 'outbox'

    # get the actor inbox for the To handle
    originDomain = domain
    (inboxUrl, pubKeyId, pubKey, fromPersonId, sharedInbox, avatarUrl,
     displayName, _) = getPersonBox(signingPrivateKeyPem,
                                    originDomain,
                                    baseDir, session, wfRequest,
                                    personCache, projectVersion,
                                    httpPrefix, nickname, domain,
                                    postToBox, 76121)

    if not inboxUrl:
        if debug:
            print('DEBUG: skill no ' + postToBox +
                  ' was found for ' + handle)
        return 3
    if not fromPersonId:
        if debug:
            print('DEBUG: skill no actor was found for ' + handle)
        return 4

    authHeader = createBasicAuthHeader(nickname, password)

    headers = {
        'host': domain,
        'Content-type': 'application/json',
        'Authorization': authHeader
    }
    postResult = \
        postJson(httpPrefix, domainFull,
                 session, newSkillJson, [], inboxUrl,
                 headers, 30, True)
    if not postResult:
        if debug:
            print('DEBUG: POST skill failed for c2s to ' + inboxUrl)
#        return 5

    if debug:
        print('DEBUG: c2s POST skill success')

    return newSkillJson


def actorHasSkill(actorJson: {}, skillName: str) -> bool:
    """Returns true if the given actor has the given skill
    """
    ocSkillsList = getOccupationSkills(actorJson)
    for skillStr in ocSkillsList:
        if skillName + ':' in skillStr:
            return True
    return False
