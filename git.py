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
from utils import acct_dir
from utils import has_object_stringType


def _git_format_content(content: str) -> str:
    """ replace html formatting, so that it's more
    like the original patch file
    """
    patchStr = content.replace('<br>', '\n').replace('<br />', '\n')
    patchStr = patchStr.replace('<p>', '').replace('</p>', '\n')
    patchStr = html.unescape(patchStr)
    if 'From ' in patchStr:
        patchStr = 'From ' + patchStr.split('From ', 1)[1]
    return patchStr


def _get_git_project_name(base_dir: str, nickname: str, domain: str,
                          subject: str) -> str:
    """Returns the project name for a git patch
    The project name should be contained within the subject line
    and should match against a list of projects which the account
    holder wants to receive
    """
    gitProjectsFilename = \
        acct_dir(base_dir, nickname, domain) + '/gitprojects.txt'
    if not os.path.isfile(gitProjectsFilename):
        return None
    subjectLineWords = subject.lower().split(' ')
    for word in subjectLineWords:
        if word in open(gitProjectsFilename).read():
            return word
    return None


def is_git_patch(base_dir: str, nickname: str, domain: str,
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
            _get_git_project_name(base_dir, nickname, domain, subject)
        if not projectName:
            return False
    return True


def _get_git_hash(patchStr: str) -> str:
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


def _get_patch_description(patchStr: str) -> str:
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


def convert_post_to_patch(base_dir: str, nickname: str, domain: str,
                          post_json_object: {}) -> bool:
    """Detects whether the given post contains a patch
    and if so then converts it to a Patch ActivityPub type
    """
    if not has_object_stringType(post_json_object, False):
        return False
    if post_json_object['object']['type'] == 'Patch':
        return True
    if not post_json_object['object'].get('summary'):
        return False
    if not post_json_object['object'].get('content'):
        return False
    if not post_json_object['object'].get('attributedTo'):
        return False
    if not isinstance(post_json_object['object']['attributedTo'], str):
        return False
    if not is_git_patch(base_dir, nickname, domain,
                        post_json_object['object']['type'],
                        post_json_object['object']['summary'],
                        post_json_object['object']['content'],
                        False):
        return False
    patchStr = _git_format_content(post_json_object['object']['content'])
    commitHash = _get_git_hash(patchStr)
    if not commitHash:
        return False
    post_json_object['object']['type'] = 'Patch'
    # add a commitedBy parameter
    if not post_json_object['object'].get('committedBy'):
        post_json_object['object']['committedBy'] = \
            post_json_object['object']['attributedTo']
    post_json_object['object']['hash'] = commitHash
    post_json_object['object']['description'] = {
        "mediaType": "text/plain",
        "content": _get_patch_description(patchStr)
    }
    # remove content map
    if post_json_object['object'].get('contentMap'):
        del post_json_object['object']['contentMap']
    print('Converted post to Patch ActivityPub type')
    return True


def _git_add_from_handle(patchStr: str, handle: str) -> str:
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


def receive_git_patch(base_dir: str, nickname: str, domain: str,
                      messageType: str, subject: str, content: str,
                      fromNickname: str, fromDomain: str) -> bool:
    """Receive a git patch
    """
    if not is_git_patch(base_dir, nickname, domain,
                        messageType, subject, content):
        return False

    patchStr = _git_format_content(content)

    patchLines = patchStr.split('\n')
    patchFilename = None
    projectDir = None
    patchesDir = acct_dir(base_dir, nickname, domain) + '/patches'
    # get the subject line and turn it into a filename
    for line in patchLines:
        if line.startswith('Subject:'):
            patchSubject = \
                line.replace('Subject:', '').replace('/', '|')
            patchSubject = patchSubject.replace('[PATCH]', '').strip()
            patchSubject = patchSubject.replace(' ', '_')
            projectName = \
                _get_git_project_name(base_dir, nickname, domain, subject)
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
        _git_add_from_handle(patchStr, '@' + fromNickname + '@' + fromDomain)
    try:
        with open(patchFilename, 'w+') as patchFile:
            patchFile.write(patchStr)
            patchNotifyFilename = \
                acct_dir(base_dir, nickname, domain) + '/.newPatchContent'
            with open(patchNotifyFilename, 'w+') as patchFile:
                patchFile.write(patchStr)
                return True
    except OSError as ex:
        print('EX: receive_git_patch ' + patchFilename + ' ' + str(ex))
    return False
