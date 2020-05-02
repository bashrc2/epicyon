__filename__ = "git.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.1.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import os


def gitFormatContent(content: str) -> str:
    """ replace html formatting, so that it's more
    like the original patch file
    """
    contentStr = content.replace('<br>', '\n').replace('<br \\>', '\n')
    contentStr = contentStr.replace('<p>', '').replace('</p>', '\n')
    contentStr = contentStr.replace('&lt;', '<').replace('&gt;', '>')
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
    print('Debug git subject ' + subject)
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
               subject: str, content: str) -> bool:
    """Is the given post content a git patch?
    """
    # must have a subject line
    print('Debug git 11: ' + content)
    if not subject:
        return False
    print('Debug git 12')
    if '[PATCH]' not in content:
        return False
    print('Debug git 13')
    if '---' not in content:
        return False
    print('Debug git 14')
    if 'diff ' not in content:
        return False
    print('Debug git 15')
    if 'From:' not in content:
        return False
    print('Debug git 16')
    if 'Date:' not in content:
        return False
    print('Debug git 17')
    if 'Subject:' not in content:
        return False
    print('Debug git 18')
    if '<br>' not in content:
        if '<br />' not in content:
            return False
    print('Debug git 19')
    projectName = \
        getGitProjectName(baseDir, nickname, domain,
                          subject)
    if not projectName:
        return False
    print('Debug git 20')
    return True


def receiveGitPatch(baseDir: str, nickname: str, domain: str,
                    subject: str, content: str) -> bool:
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
    with open(patchFilename, "w") as patchFile:
        patchFile.write(contentStr)
        patchNotifyFilename = \
            baseDir + '/accounts/' + \
            nickname + '@' + domain + '/.newPatchContent'
        with open(patchNotifyFilename, "w") as patchFile:
            patchFile.write(contentStr)
        return True
    return False
