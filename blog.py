__filename__ = "blog.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.3.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "ActivityPub"

import os
from datetime import datetime

from content import replace_emoji_from_tags
from webapp_utils import html_header_with_external_style
from webapp_utils import html_header_with_blog_markup
from webapp_utils import html_footer
from webapp_utils import get_post_attachments_as_html
from webapp_utils import edit_text_area
from webapp_media import add_embedded_elements
from utils import local_actor_url
from utils import get_actor_languages_list
from utils import get_base_content_from_post
from utils import get_content_from_post
from utils import is_account_dir
from utils import remove_html
from utils import get_config_param
from utils import get_full_domain
from utils import get_media_formats
from utils import get_nickname_from_actor
from utils import get_domain_from_actor
from utils import locate_post
from utils import load_json
from utils import first_paragraph_from_string
from utils import get_actor_property_url
from utils import acct_dir
from posts import create_blogs_timeline
from newswire import rss2header
from newswire import rss2footer
from cache import get_person_from_cache


def _no_of_blog_replies(base_dir: str, http_prefix: str, translate: {},
                        nickname: str, domain: str, domain_full: str,
                        post_id: str, depth=0) -> int:
    """Returns the number of replies on the post
    This is recursive, so can handle replies to replies
    """
    if depth > 4:
        return 0
    if not post_id:
        return 0

    try_post_box = ('tlblogs', 'inbox', 'outbox')
    box_found = False
    for post_box in try_post_box:
        post_filename = \
            acct_dir(base_dir, nickname, domain) + '/' + post_box + '/' + \
            post_id.replace('/', '#') + '.replies'
        if os.path.isfile(post_filename):
            box_found = True
            break
    if not box_found:
        # post may exist but has no replies
        for post_box in try_post_box:
            post_filename = \
                acct_dir(base_dir, nickname, domain) + '/' + post_box + '/' + \
                post_id.replace('/', '#')
            if os.path.isfile(post_filename):
                return 1
        return 0

    removals = []
    replies = 0
    lines = []
    try:
        with open(post_filename, 'r') as post_file:
            lines = post_file.readlines()
    except OSError:
        print('EX: failed to read blog ' + post_filename)

    for reply_post_id in lines:
        reply_post_id = reply_post_id.replace('\n', '').replace('\r', '')
        reply_post_id = reply_post_id.replace('.json', '')
        if locate_post(base_dir, nickname, domain, reply_post_id):
            reply_post_id = reply_post_id.replace('.replies', '')
            replies += \
                1 + _no_of_blog_replies(base_dir, http_prefix, translate,
                                        nickname, domain, domain_full,
                                        reply_post_id, depth+1)
        else:
            # remove post which no longer exists
            removals.append(reply_post_id)

    # remove posts from .replies file if they don't exist
    if lines and removals:
        print('Rewriting ' + post_filename + ' to remove ' +
              str(len(removals)) + ' entries')
        try:
            with open(post_filename, 'w+') as post_file:
                for reply_post_id in lines:
                    reply_post_id = \
                        reply_post_id.replace('\n', '').replace('\r', '')
                    if reply_post_id not in removals:
                        post_file.write(reply_post_id + '\n')
        except OSError as ex:
            print('EX: unable to remove replies from post ' +
                  post_filename + ' ' + str(ex))

    return replies


def _get_blog_replies(base_dir: str, http_prefix: str, translate: {},
                      nickname: str, domain: str, domain_full: str,
                      post_id: str, depth=0) -> str:
    """Returns a string containing html blog posts
    """
    if depth > 4:
        return ''
    if not post_id:
        return ''

    try_post_box = ('tlblogs', 'inbox', 'outbox')
    box_found = False
    for post_box in try_post_box:
        post_filename = \
            acct_dir(base_dir, nickname, domain) + '/' + post_box + '/' + \
            post_id.replace('/', '#') + '.replies'
        if os.path.isfile(post_filename):
            box_found = True
            break
    if not box_found:
        # post may exist but has no replies
        for post_box in try_post_box:
            post_filename = \
                acct_dir(base_dir, nickname, domain) + '/' + post_box + '/' + \
                post_id.replace('/', '#') + '.json'
            if os.path.isfile(post_filename):
                post_filename = acct_dir(base_dir, nickname, domain) + \
                    '/postcache/' + \
                    post_id.replace('/', '#') + '.html'
                if os.path.isfile(post_filename):
                    try:
                        with open(post_filename, 'r') as post_file:
                            return post_file.read() + '\n'
                    except OSError:
                        print('EX: unable to read blog 3 ' + post_filename)
        return ''

    lines = []
    try:
        with open(post_filename, 'r') as post_file:
            lines = post_file.readlines()
    except OSError:
        print('EX: unable to read blog 4 ' + post_filename)

    if lines:
        replies_str = ''
        for reply_post_id in lines:
            reply_post_id = reply_post_id.replace('\n', '').replace('\r', '')
            reply_post_id = reply_post_id.replace('.json', '')
            reply_post_id = reply_post_id.replace('.replies', '')
            post_filename = acct_dir(base_dir, nickname, domain) + \
                '/postcache/' + \
                reply_post_id.replace('/', '#') + '.html'
            if not os.path.isfile(post_filename):
                continue
            try:
                with open(post_filename, 'r') as post_file:
                    replies_str += post_file.read() + '\n'
            except OSError:
                print('EX: unable to read blog replies ' + post_filename)
            rply = _get_blog_replies(base_dir, http_prefix, translate,
                                     nickname, domain, domain_full,
                                     reply_post_id, depth+1)
            if rply not in replies_str:
                replies_str += rply

        # indicate the reply indentation level
        indent_str = '>'
        indent_level = 0
        while indent_level < depth:
            indent_str += ' >'
            indent_level += 1

        replies_str = replies_str.replace(translate['SHOW MORE'], indent_str)
        return replies_str.replace('?tl=outbox', '?tl=tlblogs')
    return ''


def _html_blog_post_content(debug: bool, session, authorized: bool,
                            base_dir: str, http_prefix: str, translate: {},
                            nickname: str, domain: str, domain_full: str,
                            post_json_object: {},
                            handle: str, restrict_to_domain: bool,
                            peertube_instances: [],
                            system_language: str,
                            person_cache: {},
                            blog_separator: str = '<hr>') -> str:
    """Returns the content for a single blog post
    """
    linked_author = False
    actor = ''
    blog_str = ''
    message_link = ''
    if post_json_object['object'].get('id'):
        message_link = \
            post_json_object['object']['id'].replace('/statuses/', '/')
    title_str = ''
    article_added = False
    if post_json_object['object'].get('summary'):
        title_str = post_json_object['object']['summary']
        blog_str += '<article><h1><a href="' + message_link + '">' + \
            title_str + '</a></h1>\n'
        article_added = True

    # get the handle of the author
    if post_json_object['object'].get('attributedTo'):
        author_nickname = None
        if isinstance(post_json_object['object']['attributedTo'], str):
            actor = post_json_object['object']['attributedTo']
            author_nickname = get_nickname_from_actor(actor)
        if author_nickname:
            author_domain, _ = get_domain_from_actor(actor)
            if author_domain:
                # author must be from the given domain
                if restrict_to_domain and author_domain != domain:
                    return ''
                handle = author_nickname + '@' + author_domain
    else:
        # posts from the domain are expected to have an attributedTo field
        if restrict_to_domain:
            return ''

    if post_json_object['object'].get('published'):
        if 'T' in post_json_object['object']['published']:
            blog_str += '<h3>' + \
                post_json_object['object']['published'].split('T')[0]
            if handle:
                if handle.startswith(nickname + '@' + domain):
                    blog_str += ' <a href="' + http_prefix + '://' + \
                        domain_full + \
                        '/users/' + nickname + '">' + handle + '</a>'
                    linked_author = True
                else:
                    if actor:
                        blog_str += ' <a href="' + actor + '">' + \
                            handle + '</a>'
                        linked_author = True
                    else:
                        blog_str += ' ' + handle
            blog_str += '</h3>\n'

    avatar_link = ''
    reply_str = ''
    announce_str = ''
    like_str = ''
    bookmark_str = ''
    delete_str = ''
    mute_str = ''
    is_muted = False
    attachment_str, _ = \
        get_post_attachments_as_html(post_json_object,
                                     'tlblogs', translate,
                                     is_muted, avatar_link,
                                     reply_str, announce_str,
                                     like_str, bookmark_str,
                                     delete_str, mute_str)
    if attachment_str:
        blog_str += '<br><center>' + attachment_str + '</center>'

    person_url = local_actor_url(http_prefix, nickname, domain_full)
    actor_json = \
        get_person_from_cache(base_dir, person_url, person_cache, False)
    languages_understood = []
    if actor_json:
        languages_understood = get_actor_languages_list(actor_json)
    json_content = get_content_from_post(post_json_object, system_language,
                                         languages_understood)
    if json_content:
        content_str = add_embedded_elements(translate, json_content,
                                            peertube_instances)
        if post_json_object['object'].get('tag'):
            post_json_object_tags = post_json_object['object']['tag']
            content_str = replace_emoji_from_tags(session, base_dir,
                                                  content_str,
                                                  post_json_object_tags,
                                                  'content', debug, True)
        if article_added:
            blog_str += '<br>' + content_str + '</article>\n'
        else:
            blog_str += '<br><article>' + content_str + '</article>\n'

    citations_str = ''
    if post_json_object['object'].get('tag'):
        for tag_json in post_json_object['object']['tag']:
            if not isinstance(tag_json, dict):
                continue
            if not tag_json.get('type'):
                continue
            if tag_json['type'] != 'Article':
                continue
            if not tag_json.get('name'):
                continue
            if not tag_json.get('url'):
                continue
            citations_str += \
                '<li><a href="' + tag_json['url'] + '">' + \
                '<cite>' + tag_json['name'] + '</cite></a></li>\n'
        if citations_str:
            citations_str = '<p><b>' + translate['Citations'] + \
                ':</b></p>' + \
                '<ul>\n' + citations_str + '</ul>\n'

    blog_str += '<br>\n' + citations_str

    if not linked_author:
        blog_str += '<p class="about"><a class="about" href="' + \
            local_actor_url(http_prefix, nickname, domain_full) + \
            '">' + translate['About the author'] + \
            '</a></p>\n'

    replies = _no_of_blog_replies(base_dir, http_prefix, translate,
                                  nickname, domain, domain_full,
                                  post_json_object['object']['id'])

    # separator between blogs should be centered
    if '<center>' not in blog_separator:
        blog_separator = '<center>' + blog_separator + '</center>'

    if replies == 0:
        blog_str += blog_separator + '\n'
        return blog_str

    if not authorized:
        blog_str += '<p class="blogreplies">' + \
            translate['Replies'].lower() + ': ' + str(replies) + '</p>'
        blog_str += '<br><br><br>' + blog_separator + '\n'
    else:
        blog_str += blog_separator + '<h1>' + translate['Replies'] + '</h1>\n'
        if not title_str:
            blog_str += \
                _get_blog_replies(base_dir, http_prefix, translate,
                                  nickname, domain, domain_full,
                                  post_json_object['object']['id'])
        else:
            obj_id = post_json_object['object']['id']
            blog_replies_str = \
                _get_blog_replies(base_dir, http_prefix,
                                  translate, nickname,
                                  domain, domain_full, obj_id)
            blog_str += blog_replies_str.replace('>' + title_str + '<', '')

    return blog_str


def _html_blog_post_rss2(authorized: bool,
                         base_dir: str, http_prefix: str, translate: {},
                         nickname: str, domain: str, domain_full: str,
                         post_json_object: {},
                         handle: str, restrict_to_domain: bool,
                         system_language: str) -> str:
    """Returns the RSS version 2 feed for a single blog post
    """
    rss_str = ''
    message_link = ''
    if post_json_object['object'].get('id'):
        message_link = \
            post_json_object['object']['id'].replace('/statuses/', '/')
        if not restrict_to_domain or \
           (restrict_to_domain and '/' + domain in message_link):
            if post_json_object['object'].get('summary') and \
               post_json_object['object'].get('published'):
                published = post_json_object['object']['published']
                pub_date = datetime.strptime(published, "%Y-%m-%dT%H:%M:%SZ")
                title_str = post_json_object['object']['summary']
                rss_date_str = pub_date.strftime("%a, %d %b %Y %H:%M:%S UT")
                content = \
                    get_base_content_from_post(post_json_object,
                                               system_language)
                description = first_paragraph_from_string(content)
                rss_str = '     <item>'
                rss_str += '         <title>' + title_str + '</title>'
                rss_str += '         <link>' + message_link + '</link>'
                rss_str += \
                    '         <description>' + description + '</description>'
                rss_str += '         <pubDate>' + rss_date_str + '</pubDate>'
                rss_str += '     </item>'
    return rss_str


def _html_blog_post_rss3(authorized: bool,
                         base_dir: str, http_prefix: str, translate: {},
                         nickname: str, domain: str, domain_full: str,
                         post_json_object: {},
                         handle: str, restrict_to_domain: bool,
                         system_language: str) -> str:
    """Returns the RSS version 3 feed for a single blog post
    """
    rss_str = ''
    message_link = ''
    if post_json_object['object'].get('id'):
        message_link = \
            post_json_object['object']['id'].replace('/statuses/', '/')
        if not restrict_to_domain or \
           (restrict_to_domain and '/' + domain in message_link):
            if post_json_object['object'].get('summary') and \
               post_json_object['object'].get('published'):
                published = post_json_object['object']['published']
                pub_date = datetime.strptime(published, "%Y-%m-%dT%H:%M:%SZ")
                title_str = post_json_object['object']['summary']
                rss_date_str = pub_date.strftime("%a, %d %b %Y %H:%M:%S UT")
                content = \
                    get_base_content_from_post(post_json_object,
                                               system_language)
                description = first_paragraph_from_string(content)
                rss_str = 'title: ' + title_str + '\n'
                rss_str += 'link: ' + message_link + '\n'
                rss_str += 'description: ' + description + '\n'
                rss_str += 'created: ' + rss_date_str + '\n\n'
    return rss_str


def _html_blog_remove_cw_button(blog_str: str, translate: {}) -> str:
    """Removes the CW button from blog posts, where the
    summary field is instead used as the blog title
    """
    blog_str = blog_str.replace('<details>', '<b>')
    blog_str = blog_str.replace('</details>', '</b>')
    blog_str = blog_str.replace('<summary>', '')
    blog_str = blog_str.replace('</summary>', '')
    blog_str = blog_str.replace(translate['SHOW MORE'], '')
    return blog_str


def _get_snippet_from_blog_content(post_json_object: {},
                                   system_language: str) -> str:
    """Returns a snippet of text from the blog post as a preview
    """
    content = get_base_content_from_post(post_json_object, system_language)
    if '<p>' in content:
        content = content.split('<p>', 1)[1]
        if '</p>' in content:
            content = content.split('</p>', 1)[0]
    content = remove_html(content)
    if '\n' in content:
        content = content.split('\n')[0]
    if len(content) >= 256:
        content = content[:252] + '...'
    return content


def html_blog_post(session, authorized: bool,
                   base_dir: str, http_prefix: str, translate: {},
                   nickname: str, domain: str, domain_full: str,
                   post_json_object: {},
                   peertube_instances: [],
                   system_language: str, person_cache: {},
                   debug: bool, content_license_url: str) -> str:
    """Returns a html blog post
    """
    blog_str = ''

    css_filename = base_dir + '/epicyon-blog.css'
    if os.path.isfile(base_dir + '/blog.css'):
        css_filename = base_dir + '/blog.css'
    instance_title = \
        get_config_param(base_dir, 'instanceTitle')
    published = post_json_object['object']['published']
    modified = published
    if post_json_object['object'].get('updated'):
        modified = post_json_object['object']['updated']
    title = post_json_object['object']['summary']
    url = ''
    if post_json_object['object'].get('url'):
        url = post_json_object['object']['url']
    snippet = _get_snippet_from_blog_content(post_json_object,
                                             system_language)
    blog_str = html_header_with_blog_markup(css_filename, instance_title,
                                            http_prefix, domain_full, nickname,
                                            system_language, published,
                                            modified,
                                            title, snippet, translate, url,
                                            content_license_url)
    _html_blog_remove_cw_button(blog_str, translate)

    blog_str += _html_blog_post_content(debug, session, authorized, base_dir,
                                        http_prefix, translate,
                                        nickname, domain,
                                        domain_full, post_json_object,
                                        None, False,
                                        peertube_instances, system_language,
                                        person_cache)

    # show rss links
    blog_str += '<p class="rssfeed">'

    blog_str += '<a href="' + http_prefix + '://' + \
        domain_full + '/blog/' + nickname + '/rss.xml">'
    blog_str += '<img style="width:3%;min-width:50px" ' + \
        'loading="lazy" decoding="async" alt="RSS 2.0" ' + \
        'title="RSS 2.0" src="/' + \
        'icons/logorss.png" /></a>'

    # blog_str += '<a href="' + http_prefix + '://' + \
    #     domain_full + '/blog/' + nickname + '/rss.txt">'
    # blog_str += '<img style="width:3%;min-width:50px" ' + \
    #     'loading="lazy" decoding="async" alt="RSS 3.0" ' + \
    #     'title="RSS 3.0" src="/' + \
    #     'icons/rss3.png" /></a>'

    blog_str += '</p>'

    return blog_str + html_footer()


def html_blog_page(authorized: bool, session,
                   base_dir: str, http_prefix: str, translate: {},
                   nickname: str, domain: str, port: int,
                   no_of_items: int, page_number: int,
                   peertube_instances: [], system_language: str,
                   person_cache: {}, debug: bool) -> str:
    """Returns a html blog page containing posts
    """
    if ' ' in nickname or '@' in nickname or \
       '\n' in nickname or '\r' in nickname:
        return None
    blog_str = ''

    css_filename = base_dir + '/epicyon-profile.css'
    if os.path.isfile(base_dir + '/epicyon.css'):
        css_filename = base_dir + '/epicyon.css'
    instance_title = \
        get_config_param(base_dir, 'instanceTitle')
    blog_str = \
        html_header_with_external_style(css_filename, instance_title, None)
    _html_blog_remove_cw_button(blog_str, translate)

    blogs_index = acct_dir(base_dir, nickname, domain) + '/tlblogs.index'
    if not os.path.isfile(blogs_index):
        return blog_str + html_footer()

    timeline_json = \
        create_blogs_timeline(session, base_dir,
                              nickname, domain, port, http_prefix,
                              no_of_items, False, page_number)

    if not timeline_json:
        return blog_str + html_footer()

    domain_full = get_full_domain(domain, port)

    # show previous and next buttons
    if page_number is not None:
        navigate_str = '<p>'
        if page_number > 1:
            # show previous button
            navigate_str += '<a href="' + http_prefix + '://' + \
                domain_full + '/blog/' + \
                nickname + '?page=' + str(page_number-1) + '">' + \
                '<img loading="lazy" decoding="async" alt="<" title="<" ' + \
                'src="/icons' + \
                '/prev.png" class="buttonprev"/></a>\n'
        if len(timeline_json['orderedItems']) >= no_of_items:
            # show next button
            navigate_str += '<a href="' + http_prefix + '://' + \
                domain_full + '/blog/' + nickname + \
                '?page=' + str(page_number + 1) + '">' + \
                '<img loading="lazy" decoding="async" alt=">" title=">" ' + \
                'src="/icons' + \
                '/prev.png" class="buttonnext"/></a>\n'
        navigate_str += '</p>'
        blog_str += navigate_str

    for item in timeline_json['orderedItems']:
        if item['type'] != 'Create':
            continue

        blog_str += \
            _html_blog_post_content(debug, session, authorized,
                                    base_dir, http_prefix, translate,
                                    nickname, domain, domain_full, item,
                                    None, True, peertube_instances,
                                    system_language, person_cache)

    if len(timeline_json['orderedItems']) >= no_of_items:
        blog_str += navigate_str

    # show rss link
    blog_str += '<p class="rssfeed">'

    blog_str += '<a href="' + http_prefix + '://' + \
        domain_full + '/blog/' + nickname + '/rss.xml">'
    blog_str += '<img loading="lazy" decoding="async" alt="RSS 2.0" ' + \
        'title="RSS 2.0" src="/' + \
        'icons/logorss.png" /></a>'

    # blog_str += '<a href="' + http_prefix + '://' + \
    #     domain_full + '/blog/' + nickname + '/rss.txt">'
    # blog_str += '<img loading="lazy" decoding="async" alt="RSS 3.0" ' + \
    #     'title="RSS 3.0" src="/' + \
    #     'icons/rss3.png" /></a>'

    blog_str += '</p>'
    return blog_str + html_footer()


def html_blog_page_rss2(authorized: bool, session,
                        base_dir: str, http_prefix: str, translate: {},
                        nickname: str, domain: str, port: int,
                        no_of_items: int, page_number: int,
                        include_header: bool, system_language: str) -> str:
    """Returns an RSS version 2 feed containing posts
    """
    if ' ' in nickname or '@' in nickname or \
       '\n' in nickname or '\r' in nickname:
        return None

    domain_full = get_full_domain(domain, port)

    blog_rss2 = ''
    if include_header:
        blog_rss2 = rss2header(http_prefix, nickname, domain_full,
                               'Blog', translate)

    blogs_index = acct_dir(base_dir, nickname, domain) + '/tlblogs.index'
    if not os.path.isfile(blogs_index):
        if include_header:
            return blog_rss2 + rss2footer()
        return blog_rss2

    timeline_json = create_blogs_timeline(session, base_dir,
                                          nickname, domain, port,
                                          http_prefix,
                                          no_of_items, False,
                                          page_number)

    if not timeline_json:
        if include_header:
            return blog_rss2 + rss2footer()
        return blog_rss2

    if page_number is not None:
        for item in timeline_json['orderedItems']:
            if item['type'] != 'Create':
                continue

            blog_rss2 += \
                _html_blog_post_rss2(authorized, base_dir,
                                     http_prefix, translate,
                                     nickname, domain,
                                     domain_full, item,
                                     None, True, system_language)

    if include_header:
        return blog_rss2 + rss2footer()
    return blog_rss2


def html_blog_page_rss3(authorized: bool, session,
                        base_dir: str, http_prefix: str, translate: {},
                        nickname: str, domain: str, port: int,
                        no_of_items: int, page_number: int,
                        system_language: str) -> str:
    """Returns an RSS version 3 feed containing posts
    """
    if ' ' in nickname or '@' in nickname or \
       '\n' in nickname or '\r' in nickname:
        return None

    domain_full = get_full_domain(domain, port)

    blog_rss3 = ''

    blogs_index = acct_dir(base_dir, nickname, domain) + '/tlblogs.index'
    if not os.path.isfile(blogs_index):
        return blog_rss3

    timeline_json = \
        create_blogs_timeline(session, base_dir,
                              nickname, domain, port, http_prefix,
                              no_of_items, False, page_number)

    if not timeline_json:
        return blog_rss3

    if page_number is not None:
        for item in timeline_json['orderedItems']:
            if item['type'] != 'Create':
                continue

            blog_rss3 += \
                _html_blog_post_rss3(authorized, base_dir,
                                     http_prefix, translate,
                                     nickname, domain,
                                     domain_full, item,
                                     None, True,
                                     system_language)

    return blog_rss3


def _no_of_blog_accounts(base_dir: str) -> int:
    """Returns the number of blog accounts
    """
    ctr = 0
    for subdir, dirs, files in os.walk(base_dir + '/accounts'):
        for acct in dirs:
            if not is_account_dir(acct):
                continue
            account_dir = os.path.join(base_dir + '/accounts', acct)
            blogs_index = account_dir + '/tlblogs.index'
            if os.path.isfile(blogs_index):
                ctr += 1
        break
    return ctr


def _single_blog_account_nickname(base_dir: str) -> str:
    """Returns the nickname of a single blog account
    """
    for subdir, dirs, files in os.walk(base_dir + '/accounts'):
        for acct in dirs:
            if not is_account_dir(acct):
                continue
            account_dir = os.path.join(base_dir + '/accounts', acct)
            blogs_index = account_dir + '/tlblogs.index'
            if os.path.isfile(blogs_index):
                return acct.split('@')[0]
        break
    return None


def html_blog_view(authorized: bool,
                   session, base_dir: str, http_prefix: str,
                   translate: {}, domain: str, port: int,
                   no_of_items: int,
                   peertube_instances: [], system_language: str,
                   person_cache: {}, debug: bool) -> str:
    """Show the blog main page
    """
    blog_str = ''

    css_filename = base_dir + '/epicyon-profile.css'
    if os.path.isfile(base_dir + '/epicyon.css'):
        css_filename = base_dir + '/epicyon.css'
    instance_title = \
        get_config_param(base_dir, 'instanceTitle')
    blog_str = \
        html_header_with_external_style(css_filename, instance_title, None)

    if _no_of_blog_accounts(base_dir) <= 1:
        nickname = _single_blog_account_nickname(base_dir)
        if nickname:
            return html_blog_page(authorized, session,
                                  base_dir, http_prefix, translate,
                                  nickname, domain, port,
                                  no_of_items, 1, peertube_instances,
                                  system_language, person_cache, debug)

    domain_full = get_full_domain(domain, port)

    for subdir, dirs, files in os.walk(base_dir + '/accounts'):
        for acct in dirs:
            if not is_account_dir(acct):
                continue
            account_dir = os.path.join(base_dir + '/accounts', acct)
            blogs_index = account_dir + '/tlblogs.index'
            if os.path.isfile(blogs_index):
                blog_str += '<p class="blogaccount">'
                blog_str += '<a href="' + \
                    http_prefix + '://' + domain_full + '/blog/' + \
                    acct.split('@')[0] + '">' + acct + '</a>'
                blog_str += '</p>'
        break

    return blog_str + html_footer()


def html_edit_blog(media_instance: bool, translate: {},
                   base_dir: str, http_prefix: str,
                   path: str,
                   page_number: int,
                   nickname: str, domain: str,
                   post_url: str, system_language: str) -> str:
    """Edit a blog post after it was created
    """
    post_filename = locate_post(base_dir, nickname, domain, post_url)
    if not post_filename:
        print('Edit blog: filename not found for ' + post_url)
        return None

    post_json_object = load_json(post_filename)
    if not post_json_object:
        print('Edit blog: json not loaded for ' + post_filename)
        return None

    edit_blog_text = \
        '<h1">' + translate['Write your post text below.'] + '</h1>'

    if os.path.isfile(base_dir + '/accounts/newpost.txt'):
        try:
            with open(base_dir + '/accounts/newpost.txt', 'r') as file:
                edit_blog_text = '<p>' + file.read() + '</p>'
        except OSError:
            print('EX: unable to read ' + base_dir + '/accounts/newpost.txt')

    css_filename = base_dir + '/epicyon-profile.css'
    if os.path.isfile(base_dir + '/epicyon.css'):
        css_filename = base_dir + '/epicyon.css'

    if '?' in path:
        path = path.split('?')[0]
    path_base = path

    edit_blog_image_section = '    <div class="container">'
    edit_blog_image_section += '      <label class="labels">' + \
        translate['Image description'] + '</label>'
    edit_blog_image_section += \
        '      <input type="text" name="imageDescription">'
    edit_blog_image_section += \
        '      <input type="file" id="attachpic" name="attachpic"'
    edit_blog_image_section += \
        '            accept="' + get_media_formats() + '">'
    edit_blog_image_section += '    </div>'

    placeholder_message = translate['Write something'] + '...'
    endpoint = 'editblogpost'
    placeholder_subject = translate['Title']
    scope_icon = 'scope_blog.png'
    scope_description = translate['Blog']

    date_and_location = ''
    date_and_location = '<div class="container">'

    date_and_location += \
        '<p><input type="checkbox" class="profilecheckbox" ' + \
        'name="schedulePost"><label class="labels">' + \
        translate['This is a scheduled post.'] + '</label></p>'

    date_and_location += \
        '<p><img loading="lazy" decoding="async" alt="" title="" ' + \
        'class="emojicalendar" src="/icons/calendar.png"/>'
    date_and_location += \
        '<label class="labels">' + translate['Date'] + ': </label>'
    date_and_location += '<input type="date" name="eventDate">'
    date_and_location += \
        '<label class="labelsright">' + translate['Time'] + ':'
    date_and_location += '<input type="time" name="eventTime"></label></p>'
    date_and_location += '</div>'
    date_and_location += '<div class="container">'
    date_and_location += \
        '<br><label class="labels">' + translate['Location'] + ': </label>'
    date_and_location += '<input type="text" name="location">'
    date_and_location += '</div>'

    instance_title = \
        get_config_param(base_dir, 'instanceTitle')
    edit_blog_form = \
        html_header_with_external_style(css_filename, instance_title, None)

    edit_blog_form += \
        '<form enctype="multipart/form-data" method="POST" ' + \
        'accept-charset="UTF-8" action="' + \
        path_base + '?' + endpoint + '?page=' + str(page_number) + '">'
    edit_blog_form += \
        '  <input type="hidden" name="postUrl" value="' + post_url + '">'
    edit_blog_form += \
        '  <input type="hidden" name="pageNumber" value="' + \
        str(page_number) + '">'
    edit_blog_form += '  <div class="vertical-center">'
    edit_blog_form += \
        '    <label for="nickname"><b>' + edit_blog_text + '</b></label>'
    edit_blog_form += '    <div class="container">'

    edit_blog_form += '      <div class="dropbtn">'
    edit_blog_form += \
        '        <img loading="lazy" decoding="async" ' + \
        'alt="" title="" src="/icons' + \
        '/' + scope_icon + '"/><b class="scope-desc">' + \
        scope_description + '</b>'
    edit_blog_form += '      </div>'

    edit_blog_form += '      <a href="' + path_base + \
        '/searchemoji"><img loading="lazy" decoding="async" ' + \
        'class="emojisearch" src="/emoji/1F601.png" title="' + \
        translate['Search for emoji'] + '" alt="' + \
        translate['Search for emoji'] + '"/></a>'
    edit_blog_form += '    </div>'
    edit_blog_form += '    <div class="container"><center>'
    edit_blog_form += '      <a href="' + path_base + \
        '/inbox"><button class="cancelbtn">' + \
        translate['Cancel'] + '</button></a>'
    edit_blog_form += \
        '      <input type="submit" name="submitPost" value="' + \
        translate['Publish'] + '">'
    edit_blog_form += '    </center></div>'
    if media_instance:
        edit_blog_form += edit_blog_image_section
    edit_blog_form += \
        '    <label class="labels">' + placeholder_subject + '</label><br>'
    title_str = ''
    if post_json_object['object'].get('summary'):
        title_str = post_json_object['object']['summary']
    edit_blog_form += \
        '    <input type="text" name="subject" value="' + title_str + '">'
    edit_blog_form += ''
    edit_blog_form += '    <br>'
    message_box_height = 800

    content_str = get_base_content_from_post(post_json_object, system_language)
    content_str = content_str.replace('<p>', '').replace('</p>', '\n')

    edit_blog_form += \
        edit_text_area(placeholder_message, 'message', content_str,
                       message_box_height, '', True)
    edit_blog_form += date_and_location
    if not media_instance:
        edit_blog_form += edit_blog_image_section
    edit_blog_form += '  </div>'
    edit_blog_form += '</form>'

    edit_blog_form = \
        edit_blog_form.replace('<body>',
                               '<body onload="focusOnMessage()">')

    edit_blog_form += html_footer()
    return edit_blog_form


def path_contains_blog_link(base_dir: str,
                            http_prefix: str, domain: str,
                            domain_full: str, path: str) -> (str, str):
    """If the path contains a blog entry then return its filename
    """
    if '/users/' not in path:
        return None, None
    user_ending = path.split('/users/', 1)[1]
    if '/' not in user_ending:
        return None, None
    user_ending2 = user_ending.split('/')
    nickname = user_ending2[0]
    if len(user_ending2) != 2:
        return None, None
    if len(user_ending2[1]) < 14:
        return None, None
    user_ending2[1] = user_ending2[1].strip()
    if not user_ending2[1].isdigit():
        return None, None
    # check for blog posts
    blog_index_filename = \
        acct_dir(base_dir, nickname, domain) + '/tlblogs.index'
    if not os.path.isfile(blog_index_filename):
        return None, None
    if '#' + user_ending2[1] + '.' not in open(blog_index_filename).read():
        return None, None
    message_id = local_actor_url(http_prefix, nickname, domain_full) + \
        '/statuses/' + user_ending2[1]
    return locate_post(base_dir, nickname, domain, message_id), nickname


def get_blog_address(actor_json: {}) -> str:
    """Returns blog address for the given actor
    """
    return get_actor_property_url(actor_json, 'Blog')
