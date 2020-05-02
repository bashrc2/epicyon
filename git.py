__filename__ = "git.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.1.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import os


def extractPatch(baseDir: str, nickname: str, domain: str,
                 subject: str, content: str) -> bool:
    """Is the given post content a git patch?
    """
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
    if '\n' not in content:
        return False
    gitProjectsFilename = \
        baseDir + '/accounts/' + nickname + '@' + domain + '/gitprojects.txt'
    if not os.path.isfile(gitProjectsFilename):
        return False
    projectName = None
    for word in subject.lower().split(' '):
        if word + '\n' in open(gitProjectsFilename).read():
            projectName = word
            break
    if not projectName:
        return False
    patchLines = content.split('\n')
    patchFilename = None
    patchDir = None
    # get the subject line and turn it into a filename
    for line in patchLines:
        if line.startswith('Subject:'):
            patchSubject = \
                line.replace('Subject:', '').replace('/', '|').strip()
            patchDir = \
                baseDir + '/accounts/' + nickname + '@' + domain + \
                '/patches/' + projectName
            patchFilename = \
                patchDir + '/' + patchSubject + '.patch'
            break
    if not patchFilename:
        return False
    patchFile = open(patchFilename, "w")
    if not patchFile:
        return False
    patchFile.write(content)
    patchFile.close()
    return True
