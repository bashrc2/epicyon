__filename__ = "gemini.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.6.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Timeline"

import os
import shutil
from utils import acct_dir
from utils import has_object_dict
from utils import remove_html
from utils import get_summary_from_post
from utils import get_base_content_from_post
from utils import get_post_attachments
from utils import get_url_from_post


def _get_gemini_blog_title(message_json: dict, system_language: str) -> str:
    """Returns the title for a gemini blog post
    """
    title_text = ''
    title_str = get_summary_from_post(message_json, system_language, [])
    if title_str:
        title_text = remove_html(title_str)
    return title_text


def _get_gemini_blog_published(message_json: dict, debug: bool) -> str:
    """Returns the published date for a gemini blog post
    """
    # get the publication date
    obj = message_json
    if has_object_dict(message_json):
        obj = message_json['object']
    if not obj.get('published'):
        if debug:
            print('WARN: blog_to_gemini Blog post has no publication date ' +
                  str(message_json))
        return ''
    if not isinstance(obj['published'], str):
        if debug:
            print('WARN: blog_to_gemini publication date is not a string ' +
                  str(message_json))
        return ''
    if 'T' not in obj['published']:
        if debug:
            print('WARN: blog_to_gemini ' +
                  'publication date not in expected format ' +
                  obj['published'])
        return ''
    return obj['published'].split('T')[0]


def _get_gemini_blog_filename(base_dir: str, nickname: str, domain: str,
                              message_json: dict, system_language: str,
                              debug: bool, testing: bool) -> str:
    """Returns the filename for a gemini blog post
    """
    title_text = _get_gemini_blog_title(message_json, system_language)
    published = _get_gemini_blog_published(message_json, debug)
    if not published:
        return ''
    title_text2 = title_text.replace('.', ' ')
    title_text2 = title_text2.replace(' ', '_')

    if not testing:
        account_dir = acct_dir(base_dir, nickname, domain)
        gemini_blog_dir = account_dir + '/gemini'
    else:
        account_dir = base_dir
        gemini_blog_dir = account_dir + '/geminitest'

    gemini_blog_filename = \
        gemini_blog_dir + '/' + published + '_' + title_text2.lower() + '.gmi'
    return gemini_blog_filename


def blog_to_gemini(base_dir: str, nickname: str, domain: str,
                   message_json: dict, system_language: str,
                   debug: bool, testing: bool) -> bool:
    """
    Converts a blog post to gemini format
    Returns True on success
    """
    if not testing:
        account_dir = acct_dir(base_dir, nickname, domain)
    else:
        account_dir = base_dir
        if os.path.isdir(account_dir + '/geminitest'):
            shutil.rmtree(account_dir + '/geminitest', ignore_errors=True)

    if not os.path.isdir(account_dir):
        if debug:
            print('WARN: blog_to_gemini account directory not found ' +
                  account_dir)
        return False

    published = _get_gemini_blog_published(message_json, debug)
    if not published:
        return False

    # get the blog content
    content_str = get_base_content_from_post(message_json, system_language)
    if not content_str:
        if debug:
            print('WARN: blog_to_gemini no content ' +
                  str(message_json))
        return False
    content_text = remove_html(content_str)

    # get the blog title
    title_text = _get_gemini_blog_title(message_json, system_language)

    # get web links
    links: list[str] = []
    if '://' in content_text:
        sections = content_text.split('://')
        ctr = 0
        prev_section = ''
        for section in sections:
            if ctr > 0:
                link_str = section
                if '\n' in link_str:
                    link_str = link_str.split('\n')[0]
                if ' ' in link_str:
                    link_str = link_str.split(' ')[0]
                if link_str.endswith('.'):
                    link_length = len(link_str)
                    link_str = link_str[:link_length-1]
                if '.' not in link_str:
                    continue
                prefix = prev_section.rsplit(' ', 1)[-1]
                if prefix in ('http', 'https', 'gemini'):
                    link_str = prefix + '://' + link_str
                    links.append(link_str)
            prev_section = section
            ctr += 1

    # create gemini blog directory
    if not testing:
        gemini_blog_dir = account_dir + '/gemini'
    else:
        gemini_blog_dir = account_dir + '/geminitest'
    if not os.path.isdir(gemini_blog_dir):
        os.mkdir(gemini_blog_dir)

    gemini_blog_filename = \
        _get_gemini_blog_filename(base_dir, nickname, domain,
                                  message_json, system_language,
                                  debug, testing)

    if not title_text.startswith('# '):
        title_text = '# ' + title_text

    # get attachments
    post_attachments = get_post_attachments(message_json)
    if post_attachments:
        descriptions = ''
        for attach in post_attachments:
            if not isinstance(attach, dict):
                continue
            if not attach.get('name'):
                continue
            descriptions += attach['name'] + ' '
            if attach.get('url'):
                links.append(get_url_from_post(attach['url']) + ' ' +
                             attach['name'])

    # add links to the end of the content
    if links:
        content_text += '\n\n'
    for link_str in links:
        content_text += '=> ' + link_str + '\n'

    try:
        with open(gemini_blog_filename, 'w+',
                  encoding='utf-8') as fp_gemini:
            fp_gemini.write(title_text + '\n\n' + published + '\n\n' +
                            content_text)
    except OSError:
        print('EX: blog_to_gemini unable to write ' + gemini_blog_filename)
        return False

    return True
