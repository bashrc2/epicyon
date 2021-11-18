__filename__ = "git.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Profile Metadata"

import os
import html
from utils import acctDir
from utils import hasObjectStringType


def _gitFormatContent(content: str) -> str:
    """ replace html formatting, so that it's more
    like the original patch file
    """
    patchStr = content.replace('<br>', '\n').replace('<br />', '\n')
    patchStr = patchStr.replace('<p>', '').replace('</p>', '\n')
    patchStr = html.unescape(patchStr)
    if 'From ' in patchStr:
        patchStr = 'From ' + patchStr.split('From ', 1)[1]
    return patchStr


def _getGitProjectName(baseDir: str, nickname: str, domain: str,
                       subject: str) -> str:
    """Returns the project name for a git patch
    The project name should be contained within the subject line
    and should match against a list of projects which the account
    holder wants to receive
    """
    gitProjectsFilename = \
        acctDir(baseDir, nickname, domain) + '/gitprojects.txt'
    if not os.path.isfile(gitProjectsFilename):
        return None
    subjectLineWords = subject.lower().split(' ')
    for word in subjectLineWords:
        if word in open(gitProjectsFilename).read():
            return word
    return None


def isGitPatch(baseDir: str, nickname: str, domain: str,
               messageType: str,
               subject: str, content: str,
               checkProjectName: bool = True) -> bool:
    """Is the given post content a git patch?
    """
    if messageType != 'Note' and \
       messageType != 'Page' and \
       messageType != 'Patch':
        return False
    # must have a subject line
    if not subject:
        return False
    if '[PATCH]' not in content:
        return False
    if '---' not in content:
        return False
    if 'diff ' not in content:
        return False
    if 'From ' not in content:
        return False
    if 'From:' not in content:
        return False
    if 'Date:' not in content:
        return False
    if 'Subject:' not in content:
        return False
    if '<br>' not in content:
        if '<br />' not in content:
            return False
    if checkProjectName:
        projectName = \
            _getGitProjectName(baseDir, nickname, domain, subject)
        if not projectName:
            return False
    return True


def _getGitHash(patchStr: str) -> str:
    """Returns the commit hash from a given patch
    """
    patchLines = patchStr.split('\n')
    for line in patchLines:
        if line.startswith('From '):
            words = line.split(' ')
            if len(words) > 1:
                if len(words[1]) > 20:
                    return words[1]
            break
    return None


def _getPatchDescription(patchStr: str) -> str:
    """Returns the description from a given patch
    """
    patchLines = patchStr.split('\n')
    description = ''
    started = False
    for line in patchLines:
        if started:
            if line.strip() == '---':
                break
            description += line + '\n'
        if line.startswith('Subject:'):
            started = True
    return description


def convertPostToPatch(baseDir: str, nickname: str, domain: str,
                       postJsonObject: {}) -> bool:
    """Detects whether the given post contains a patch
    and if so then converts it to a Patch ActivityPub type
    """
    if not hasObjectStringType(postJsonObject, False):
        return False
    if postJsonObject['object']['type'] == 'Patch':
        return True
    if not postJsonObject['object'].get('summary'):
        return False
    if not postJsonObject['object'].get('content'):
        return False
    if not postJsonObject['object'].get('attributedTo'):
        return False
    if not isinstance(postJsonObject['object']['attributedTo'], str):
        return False
    if not isGitPatch(baseDir, nickname, domain,
                      postJsonObject['object']['type'],
                      postJsonObject['object']['summary'],
                      postJsonObject['object']['content'],
                      False):
        return False
    patchStr = _gitFormatContent(postJsonObject['object']['content'])
    commitHash = _getGitHash(patchStr)
    if not commitHash:
        return False
    postJsonObject['object']['type'] = 'Patch'
    # add a commitedBy parameter
    if not postJsonObject['object'].get('committedBy'):
        postJsonObject['object']['committedBy'] = \
            postJsonObject['object']['attributedTo']
    postJsonObject['object']['hash'] = commitHash
    postJsonObject['object']['description'] = {
        "mediaType": "text/plain",
        "content": _getPatchDescription(patchStr)
    }
    # remove content map
    if postJsonObject['object'].get('contentMap'):
        del postJsonObject['object']['contentMap']
    print('Converted post to Patch ActivityPub type')
    return True


def _gitAddFromHandle(patchStr: str, handle: str) -> str:
    """Adds the activitypub handle of the sender to the patch
    """
    fromStr = 'AP-signed-off-by: '
    if fromStr in patchStr:
        return patchStr

    patchLines = patchStr.split('\n')
    patchStr = ''
    for line in patchLines:
        patchStr += line + '\n'
        if line.startswith('From:'):
            if fromStr not in patchStr:
                patchStr += fromStr + handle + '\n'
    return patchStr


def receiveGitPatch(baseDir: str, nickname: str, domain: str,
                    messageType: str, subject: str, content: str,
                    fromNickname: str, fromDomain: str) -> bool:
    """Receive a git patch
    """
    if not isGitPatch(baseDir, nickname, domain,
                      messageType, subject, content):
        return False

    patchStr = _gitFormatContent(content)

    patchLines = patchStr.split('\n')
    patchFilename = None
    projectDir = None
    patchesDir = acctDir(baseDir, nickname, domain) + '/patches'
    # get the subject line and turn it into a filename
    for line in patchLines:
        if line.startswith('Subject:'):
            patchSubject = \
                line.replace('Subject:', '').replace('/', '|')
            patchSubject = patchSubject.replace('[PATCH]', '').strip()
            patchSubject = patchSubject.replace(' ', '_')
            projectName = \
                _getGitProjectName(baseDir, nickname, domain, subject)
            if not os.path.isdir(patchesDir):
                os.mkdir(patchesDir)
            projectDir = patchesDir + '/' + projectName
            if not os.path.isdir(projectDir):
                os.mkdir(projectDir)
            patchFilename = \
                projectDir + '/' + patchSubject + '.patch'
            break
    if not patchFilename:
        return False
    patchStr = \
        _gitAddFromHandle(patchStr, '@' + fromNickname + '@' + fromDomain)
    with open(patchFilename, 'w+') as patchFile:
        patchFile.write(patchStr)
        patchNotifyFilename = \
            acctDir(baseDir, nickname, domain) + '/.newPatchContent'
        with open(patchNotifyFilename, 'w+') as patchFile:
            patchFile.write(patchStr)
            return True
    return False
