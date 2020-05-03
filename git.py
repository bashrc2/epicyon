__filename__ = "git.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.1.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import os
import html


def gitFormatContent(content: str) -> str:
    """ replace html formatting, so that it's more
    like the original patch file
    """
    contentStr = content.replace('<br>', '\n').replace('<br />', '\n')
    contentStr = contentStr.replace('<p>', '').replace('</p>', '\n')
    contentStr = html.unescape(contentStr)
    if 'From ' in contentStr:
        contentStr = 'From ' + contentStr.split('From ', 1)[1]
    return contentStr


def getGitProjectName(baseDir: str, nickname: str, domain: str,
                      subject: str) -> str:
    """Returns the project name for a git patch
    The project name should be contained within the subject line
    and should match against a list of projects which the account
    holder wants to receive
    """
    gitProjectsFilename = \
        baseDir + '/accounts/' + nickname + '@' + domain + '/gitprojects.txt'
    if not os.path.isfile(gitProjectsFilename):
        return None
    subjectLineWords = subject.lower().split(' ')
    for word in subjectLineWords:
        if word in open(gitProjectsFilename).read():
            return word
    return None


def isGitPatch(baseDir: str, nickname: str, domain: str,
               messageType: str,
               subject: str, content: str) -> bool:
    """Is the given post content a git patch?
    """
    if messageType != 'Note' and \
       messageType != 'Commit':
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
    if 'From:' not in content:
        return False
    if 'Date:' not in content:
        return False
    if 'Subject:' not in content:
        return False
    if '<br>' not in content:
        if '<br />' not in content:
            return False
    projectName = \
        getGitProjectName(baseDir, nickname, domain,
                          subject)
    if not projectName:
        return False
    return True


def getGitHash(contentStr: str) -> str:
    """Returns the commit hash from a given patch
    """
    patchLines = contentStr.split('\n')
    for line in patchLines:
        if line.startswith('From '):
            words = line.split(' ')
            if len(words) > 1:
                if len(words[1]) > 20:
                    return words[1]
            break
    return None


def gitAddFromHandle(contentStr: str, handle: str) -> str:
    """Adds the activitypub handle of the sender to the patch
    """
    fromStr = 'AP-signed-off-by: '
    if fromStr in contentStr:
        return contentStr

    prevContentStr = contentStr
    patchLines = prevContentStr.split('\n')
    contentStr = ''
    for line in patchLines:
        contentStr += line + '\n'
        if line.startswith('From:'):
            if fromStr not in contentStr:
                contentStr += fromStr + handle + '\n'
    return contentStr


def receiveGitPatch(baseDir: str, nickname: str, domain: str,
                    subject: str, content: str,
                    fromNickname: str, fromDomain: str) -> bool:
    """Receive a git patch
    """
    if not isGitPatch(baseDir, nickname, domain,
                      subject, content):
        return False

    contentStr = gitFormatContent(content)

    patchLines = contentStr.split('\n')
    patchFilename = None
    projectDir = None
    patchesDir = \
        baseDir + '/accounts/' + nickname + '@' + domain + \
        '/patches'
    # get the subject line and turn it into a filename
    for line in patchLines:
        if line.startswith('Subject:'):
            patchSubject = \
                line.replace('Subject:', '').replace('/', '|')
            patchSubject = patchSubject.replace('[PATCH]', '').strip()
            patchSubject = patchSubject.replace(' ', '_')
            projectName = \
                getGitProjectName(baseDir, nickname, domain, subject)
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
    contentStr = \
        gitAddFromHandle(contentStr, '@' + fromNickname + '@' + fromDomain)
    with open(patchFilename, "w") as patchFile:
        patchFile.write(contentStr)
        patchNotifyFilename = \
            baseDir + '/accounts/' + \
            nickname + '@' + domain + '/.newPatchContent'
        with open(patchNotifyFilename, "w") as patchFile:
            patchFile.write(contentStr)
            return True
    return False
