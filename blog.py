__filename__ = "blog.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "ActivityPub"

import os
from datetime import datetime

from content import replaceEmojiFromTags
from webapp_utils import htmlHeaderWithExternalStyle
from webapp_utils import htmlHeaderWithBlogMarkup
from webapp_utils import htmlFooter
from webapp_utils import getPostAttachmentsAsHtml
from webapp_utils import editTextArea
from webapp_media import addEmbeddedElements
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
from posts import createBlogsTimeline
from newswire import rss2Header
from newswire import rss2Footer
from cache import getPersonFromCache


def _noOfBlogReplies(base_dir: str, http_prefix: str, translate: {},
                     nickname: str, domain: str, domain_full: str,
                     post_id: str, depth=0) -> int:
    """Returns the number of replies on the post
    This is recursive, so can handle replies to replies
    """
    if depth > 4:
        return 0
    if not post_id:
        return 0

    tryPostBox = ('tlblogs', 'inbox', 'outbox')
    boxFound = False
    for postBox in tryPostBox:
        post_filename = \
            acct_dir(base_dir, nickname, domain) + '/' + postBox + '/' + \
            post_id.replace('/', '#') + '.replies'
        if os.path.isfile(post_filename):
            boxFound = True
            break
    if not boxFound:
        # post may exist but has no replies
        for postBox in tryPostBox:
            post_filename = \
                acct_dir(base_dir, nickname, domain) + '/' + postBox + '/' + \
                post_id.replace('/', '#')
            if os.path.isfile(post_filename):
                return 1
        return 0

    removals = []
    replies = 0
    lines = []
    try:
        with open(post_filename, 'r') as f:
            lines = f.readlines()
    except OSError:
        print('EX: failed to read blog ' + post_filename)

    for replyPostId in lines:
        replyPostId = replyPostId.replace('\n', '').replace('\r', '')
        replyPostId = replyPostId.replace('.json', '')
        if locate_post(base_dir, nickname, domain, replyPostId):
            replyPostId = replyPostId.replace('.replies', '')
            replies += \
                1 + _noOfBlogReplies(base_dir, http_prefix, translate,
                                     nickname, domain, domain_full,
                                     replyPostId, depth+1)
        else:
            # remove post which no longer exists
            removals.append(replyPostId)

    # remove posts from .replies file if they don't exist
    if lines and removals:
        print('Rewriting ' + post_filename + ' to remove ' +
              str(len(removals)) + ' entries')
        try:
            with open(post_filename, 'w+') as f:
                for replyPostId in lines:
                    replyPostId = \
                        replyPostId.replace('\n', '').replace('\r', '')
                    if replyPostId not in removals:
                        f.write(replyPostId + '\n')
        except OSError as ex:
            print('EX: unable to remove replies from post ' +
                  post_filename + ' ' + str(ex))

    return replies


def _getBlogReplies(base_dir: str, http_prefix: str, translate: {},
                    nickname: str, domain: str, domain_full: str,
                    post_id: str, depth=0) -> str:
    """Returns a string containing html blog posts
    """
    if depth > 4:
        return ''
    if not post_id:
        return ''

    tryPostBox = ('tlblogs', 'inbox', 'outbox')
    boxFound = False
    for postBox in tryPostBox:
        post_filename = \
            acct_dir(base_dir, nickname, domain) + '/' + postBox + '/' + \
            post_id.replace('/', '#') + '.replies'
        if os.path.isfile(post_filename):
            boxFound = True
            break
    if not boxFound:
        # post may exist but has no replies
        for postBox in tryPostBox:
            post_filename = \
                acct_dir(base_dir, nickname, domain) + '/' + postBox + '/' + \
                post_id.replace('/', '#') + '.json'
            if os.path.isfile(post_filename):
                post_filename = acct_dir(base_dir, nickname, domain) + \
                    '/postcache/' + \
                    post_id.replace('/', '#') + '.html'
                if os.path.isfile(post_filename):
                    try:
                        with open(post_filename, 'r') as postFile:
                            return postFile.read() + '\n'
                    except OSError:
                        print('EX: unable to read blog 3 ' + post_filename)
        return ''

    lines = []
    try:
        with open(post_filename, 'r') as f:
            lines = f.readlines()
    except OSError:
        print('EX: unable to read blog 4 ' + post_filename)

    if lines:
        repliesStr = ''
        for replyPostId in lines:
            replyPostId = replyPostId.replace('\n', '').replace('\r', '')
            replyPostId = replyPostId.replace('.json', '')
            replyPostId = replyPostId.replace('.replies', '')
            post_filename = acct_dir(base_dir, nickname, domain) + \
                '/postcache/' + \
                replyPostId.replace('/', '#') + '.html'
            if not os.path.isfile(post_filename):
                continue
            try:
                with open(post_filename, 'r') as postFile:
                    repliesStr += postFile.read() + '\n'
            except OSError:
                print('EX: unable to read blog replies ' + post_filename)
            rply = _getBlogReplies(base_dir, http_prefix, translate,
                                   nickname, domain, domain_full,
                                   replyPostId, depth+1)
            if rply not in repliesStr:
                repliesStr += rply

        # indicate the reply indentation level
        indentStr = '>'
        for indentLevel in range(depth):
            indentStr += ' >'

        repliesStr = repliesStr.replace(translate['SHOW MORE'], indentStr)
        return repliesStr.replace('?tl=outbox', '?tl=tlblogs')
    return ''


def _htmlBlogPostContent(debug: bool, session, authorized: bool,
                         base_dir: str, http_prefix: str, translate: {},
                         nickname: str, domain: str, domain_full: str,
                         post_json_object: {},
                         handle: str, restrictToDomain: bool,
                         peertube_instances: [],
                         system_language: str,
                         person_cache: {},
                         blogSeparator: str = '<hr>') -> str:
    """Returns the content for a single blog post
    """
    linkedAuthor = False
    actor = ''
    blogStr = ''
    messageLink = ''
    if post_json_object['object'].get('id'):
        messageLink = \
            post_json_object['object']['id'].replace('/statuses/', '/')
    titleStr = ''
    articleAdded = False
    if post_json_object['object'].get('summary'):
        titleStr = post_json_object['object']['summary']
        blogStr += '<article><h1><a href="' + messageLink + '">' + \
            titleStr + '</a></h1>\n'
        articleAdded = True

    # get the handle of the author
    if post_json_object['object'].get('attributedTo'):
        authorNickname = None
        if isinstance(post_json_object['object']['attributedTo'], str):
            actor = post_json_object['object']['attributedTo']
            authorNickname = get_nickname_from_actor(actor)
        if authorNickname:
            authorDomain, authorPort = get_domain_from_actor(actor)
            if authorDomain:
                # author must be from the given domain
                if restrictToDomain and authorDomain != domain:
                    return ''
                handle = authorNickname + '@' + authorDomain
    else:
        # posts from the domain are expected to have an attributedTo field
        if restrictToDomain:
            return ''

    if post_json_object['object'].get('published'):
        if 'T' in post_json_object['object']['published']:
            blogStr += '<h3>' + \
                post_json_object['object']['published'].split('T')[0]
            if handle:
                if handle.startswith(nickname + '@' + domain):
                    blogStr += ' <a href="' + http_prefix + '://' + \
                        domain_full + \
                        '/users/' + nickname + '">' + handle + '</a>'
                    linkedAuthor = True
                else:
                    if actor:
                        blogStr += ' <a href="' + actor + '">' + \
                            handle + '</a>'
                        linkedAuthor = True
                    else:
                        blogStr += ' ' + handle
            blogStr += '</h3>\n'

    avatarLink = ''
    replyStr = ''
    announceStr = ''
    likeStr = ''
    bookmarkStr = ''
    deleteStr = ''
    muteStr = ''
    isMuted = False
    attachmentStr, galleryStr = getPostAttachmentsAsHtml(post_json_object,
                                                         'tlblogs', translate,
                                                         isMuted, avatarLink,
                                                         replyStr, announceStr,
                                                         likeStr, bookmarkStr,
                                                         deleteStr, muteStr)
    if attachmentStr:
        blogStr += '<br><center>' + attachmentStr + '</center>'

    personUrl = local_actor_url(http_prefix, nickname, domain_full)
    actor_json = \
        getPersonFromCache(base_dir, personUrl, person_cache, False)
    languages_understood = []
    if actor_json:
        languages_understood = get_actor_languages_list(actor_json)
    jsonContent = get_content_from_post(post_json_object, system_language,
                                        languages_understood)
    if jsonContent:
        contentStr = addEmbeddedElements(translate, jsonContent,
                                         peertube_instances)
        if post_json_object['object'].get('tag'):
            post_json_object_tags = post_json_object['object']['tag']
            contentStr = replaceEmojiFromTags(session, base_dir, contentStr,
                                              post_json_object_tags,
                                              'content', debug)
        if articleAdded:
            blogStr += '<br>' + contentStr + '</article>\n'
        else:
            blogStr += '<br><article>' + contentStr + '</article>\n'

    citationsStr = ''
    if post_json_object['object'].get('tag'):
        for tagJson in post_json_object['object']['tag']:
            if not isinstance(tagJson, dict):
                continue
            if not tagJson.get('type'):
                continue
            if tagJson['type'] != 'Article':
                continue
            if not tagJson.get('name'):
                continue
            if not tagJson.get('url'):
                continue
            citationsStr += \
                '<li><a href="' + tagJson['url'] + '">' + \
                '<cite>' + tagJson['name'] + '</cite></a></li>\n'
        if citationsStr:
            citationsStr = '<p><b>' + translate['Citations'] + \
                ':</b></p>' + \
                '<ul>\n' + citationsStr + '</ul>\n'

    blogStr += '<br>\n' + citationsStr

    if not linkedAuthor:
        blogStr += '<p class="about"><a class="about" href="' + \
            local_actor_url(http_prefix, nickname, domain_full) + \
            '">' + translate['About the author'] + \
            '</a></p>\n'

    replies = _noOfBlogReplies(base_dir, http_prefix, translate,
                               nickname, domain, domain_full,
                               post_json_object['object']['id'])

    # separator between blogs should be centered
    if '<center>' not in blogSeparator:
        blogSeparator = '<center>' + blogSeparator + '</center>'

    if replies == 0:
        blogStr += blogSeparator + '\n'
        return blogStr

    if not authorized:
        blogStr += '<p class="blogreplies">' + \
            translate['Replies'].lower() + ': ' + str(replies) + '</p>'
        blogStr += '<br><br><br>' + blogSeparator + '\n'
    else:
        blogStr += blogSeparator + '<h1>' + translate['Replies'] + '</h1>\n'
        if not titleStr:
            blogStr += _getBlogReplies(base_dir, http_prefix, translate,
                                       nickname, domain, domain_full,
                                       post_json_object['object']['id'])
        else:
            blogRepliesStr = _getBlogReplies(base_dir, http_prefix, translate,
                                             nickname, domain, domain_full,
                                             post_json_object['object']['id'])
            blogStr += blogRepliesStr.replace('>' + titleStr + '<', '')

    return blogStr


def _htmlBlogPostRSS2(authorized: bool,
                      base_dir: str, http_prefix: str, translate: {},
                      nickname: str, domain: str, domain_full: str,
                      post_json_object: {},
                      handle: str, restrictToDomain: bool,
                      system_language: str) -> str:
    """Returns the RSS version 2 feed for a single blog post
    """
    rssStr = ''
    messageLink = ''
    if post_json_object['object'].get('id'):
        messageLink = \
            post_json_object['object']['id'].replace('/statuses/', '/')
        if not restrictToDomain or \
           (restrictToDomain and '/' + domain in messageLink):
            if post_json_object['object'].get('summary') and \
               post_json_object['object'].get('published'):
                published = post_json_object['object']['published']
                pubDate = datetime.strptime(published, "%Y-%m-%dT%H:%M:%SZ")
                titleStr = post_json_object['object']['summary']
                rssDateStr = pubDate.strftime("%a, %d %b %Y %H:%M:%S UT")
                content = \
                    get_base_content_from_post(post_json_object,
                                               system_language)
                description = first_paragraph_from_string(content)
                rssStr = '     <item>'
                rssStr += '         <title>' + titleStr + '</title>'
                rssStr += '         <link>' + messageLink + '</link>'
                rssStr += \
                    '         <description>' + description + '</description>'
                rssStr += '         <pubDate>' + rssDateStr + '</pubDate>'
                rssStr += '     </item>'
    return rssStr


def _htmlBlogPostRSS3(authorized: bool,
                      base_dir: str, http_prefix: str, translate: {},
                      nickname: str, domain: str, domain_full: str,
                      post_json_object: {},
                      handle: str, restrictToDomain: bool,
                      system_language: str) -> str:
    """Returns the RSS version 3 feed for a single blog post
    """
    rssStr = ''
    messageLink = ''
    if post_json_object['object'].get('id'):
        messageLink = \
            post_json_object['object']['id'].replace('/statuses/', '/')
        if not restrictToDomain or \
           (restrictToDomain and '/' + domain in messageLink):
            if post_json_object['object'].get('summary') and \
               post_json_object['object'].get('published'):
                published = post_json_object['object']['published']
                pubDate = datetime.strptime(published, "%Y-%m-%dT%H:%M:%SZ")
                titleStr = post_json_object['object']['summary']
                rssDateStr = pubDate.strftime("%a, %d %b %Y %H:%M:%S UT")
                content = \
                    get_base_content_from_post(post_json_object,
                                               system_language)
                description = first_paragraph_from_string(content)
                rssStr = 'title: ' + titleStr + '\n'
                rssStr += 'link: ' + messageLink + '\n'
                rssStr += 'description: ' + description + '\n'
                rssStr += 'created: ' + rssDateStr + '\n\n'
    return rssStr


def _htmlBlogRemoveCwButton(blogStr: str, translate: {}) -> str:
    """Removes the CW button from blog posts, where the
    summary field is instead used as the blog title
    """
    blogStr = blogStr.replace('<details>', '<b>')
    blogStr = blogStr.replace('</details>', '</b>')
    blogStr = blogStr.replace('<summary>', '')
    blogStr = blogStr.replace('</summary>', '')
    blogStr = blogStr.replace(translate['SHOW MORE'], '')
    return blogStr


def _getSnippetFromBlogContent(post_json_object: {},
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


def htmlBlogPost(session, authorized: bool,
                 base_dir: str, http_prefix: str, translate: {},
                 nickname: str, domain: str, domain_full: str,
                 post_json_object: {},
                 peertube_instances: [],
                 system_language: str, person_cache: {},
                 debug: bool, content_license_url: str) -> str:
    """Returns a html blog post
    """
    blogStr = ''

    cssFilename = base_dir + '/epicyon-blog.css'
    if os.path.isfile(base_dir + '/blog.css'):
        cssFilename = base_dir + '/blog.css'
    instanceTitle = \
        get_config_param(base_dir, 'instanceTitle')
    published = post_json_object['object']['published']
    modified = published
    if post_json_object['object'].get('updated'):
        modified = post_json_object['object']['updated']
    title = post_json_object['object']['summary']
    url = ''
    if post_json_object['object'].get('url'):
        url = post_json_object['object']['url']
    snippet = _getSnippetFromBlogContent(post_json_object, system_language)
    blogStr = htmlHeaderWithBlogMarkup(cssFilename, instanceTitle,
                                       http_prefix, domain_full, nickname,
                                       system_language, published, modified,
                                       title, snippet, translate, url,
                                       content_license_url)
    _htmlBlogRemoveCwButton(blogStr, translate)

    blogStr += _htmlBlogPostContent(debug, session, authorized, base_dir,
                                    http_prefix, translate,
                                    nickname, domain,
                                    domain_full, post_json_object,
                                    None, False,
                                    peertube_instances, system_language,
                                    person_cache)

    # show rss links
    blogStr += '<p class="rssfeed">'

    blogStr += '<a href="' + http_prefix + '://' + \
        domain_full + '/blog/' + nickname + '/rss.xml">'
    blogStr += '<img style="width:3%;min-width:50px" ' + \
        'loading="lazy" alt="RSS 2.0" ' + \
        'title="RSS 2.0" src="/' + \
        'icons/logorss.png" /></a>'

    # blogStr += '<a href="' + http_prefix + '://' + \
    #     domain_full + '/blog/' + nickname + '/rss.txt">'
    # blogStr += '<img style="width:3%;min-width:50px" ' + \
    #     'loading="lazy" alt="RSS 3.0" ' + \
    #     'title="RSS 3.0" src="/' + \
    #     'icons/rss3.png" /></a>'

    blogStr += '</p>'

    return blogStr + htmlFooter()


def htmlBlogPage(authorized: bool, session,
                 base_dir: str, http_prefix: str, translate: {},
                 nickname: str, domain: str, port: int,
                 noOfItems: int, pageNumber: int,
                 peertube_instances: [], system_language: str,
                 person_cache: {}, debug: bool) -> str:
    """Returns a html blog page containing posts
    """
    if ' ' in nickname or '@' in nickname or \
       '\n' in nickname or '\r' in nickname:
        return None
    blogStr = ''

    cssFilename = base_dir + '/epicyon-profile.css'
    if os.path.isfile(base_dir + '/epicyon.css'):
        cssFilename = base_dir + '/epicyon.css'
    instanceTitle = \
        get_config_param(base_dir, 'instanceTitle')
    blogStr = htmlHeaderWithExternalStyle(cssFilename, instanceTitle, None)
    _htmlBlogRemoveCwButton(blogStr, translate)

    blogsIndex = acct_dir(base_dir, nickname, domain) + '/tlblogs.index'
    if not os.path.isfile(blogsIndex):
        return blogStr + htmlFooter()

    timelineJson = createBlogsTimeline(session, base_dir,
                                       nickname, domain, port,
                                       http_prefix,
                                       noOfItems, False,
                                       pageNumber)

    if not timelineJson:
        return blogStr + htmlFooter()

    domain_full = get_full_domain(domain, port)

    # show previous and next buttons
    if pageNumber is not None:
        navigateStr = '<p>'
        if pageNumber > 1:
            # show previous button
            navigateStr += '<a href="' + http_prefix + '://' + \
                domain_full + '/blog/' + \
                nickname + '?page=' + str(pageNumber-1) + '">' + \
                '<img loading="lazy" alt="<" title="<" ' + \
                'src="/icons' + \
                '/prev.png" class="buttonprev"/></a>\n'
        if len(timelineJson['orderedItems']) >= noOfItems:
            # show next button
            navigateStr += '<a href="' + http_prefix + '://' + \
                domain_full + '/blog/' + nickname + \
                '?page=' + str(pageNumber + 1) + '">' + \
                '<img loading="lazy" alt=">" title=">" ' + \
                'src="/icons' + \
                '/prev.png" class="buttonnext"/></a>\n'
        navigateStr += '</p>'
        blogStr += navigateStr

    for item in timelineJson['orderedItems']:
        if item['type'] != 'Create':
            continue

        blogStr += _htmlBlogPostContent(debug, session, authorized, base_dir,
                                        http_prefix, translate,
                                        nickname, domain,
                                        domain_full, item,
                                        None, True,
                                        peertube_instances,
                                        system_language,
                                        person_cache)

    if len(timelineJson['orderedItems']) >= noOfItems:
        blogStr += navigateStr

    # show rss link
    blogStr += '<p class="rssfeed">'

    blogStr += '<a href="' + http_prefix + '://' + \
        domain_full + '/blog/' + nickname + '/rss.xml">'
    blogStr += '<img loading="lazy" alt="RSS 2.0" ' + \
        'title="RSS 2.0" src="/' + \
        'icons/logorss.png" /></a>'

    # blogStr += '<a href="' + http_prefix + '://' + \
    #     domain_full + '/blog/' + nickname + '/rss.txt">'
    # blogStr += '<img loading="lazy" alt="RSS 3.0" ' + \
    #     'title="RSS 3.0" src="/' + \
    #     'icons/rss3.png" /></a>'

    blogStr += '</p>'
    return blogStr + htmlFooter()


def htmlBlogPageRSS2(authorized: bool, session,
                     base_dir: str, http_prefix: str, translate: {},
                     nickname: str, domain: str, port: int,
                     noOfItems: int, pageNumber: int,
                     includeHeader: bool, system_language: str) -> str:
    """Returns an RSS version 2 feed containing posts
    """
    if ' ' in nickname or '@' in nickname or \
       '\n' in nickname or '\r' in nickname:
        return None

    domain_full = get_full_domain(domain, port)

    blogRSS2 = ''
    if includeHeader:
        blogRSS2 = rss2Header(http_prefix, nickname, domain_full,
                              'Blog', translate)

    blogsIndex = acct_dir(base_dir, nickname, domain) + '/tlblogs.index'
    if not os.path.isfile(blogsIndex):
        if includeHeader:
            return blogRSS2 + rss2Footer()
        else:
            return blogRSS2

    timelineJson = createBlogsTimeline(session, base_dir,
                                       nickname, domain, port,
                                       http_prefix,
                                       noOfItems, False,
                                       pageNumber)

    if not timelineJson:
        if includeHeader:
            return blogRSS2 + rss2Footer()
        else:
            return blogRSS2

    if pageNumber is not None:
        for item in timelineJson['orderedItems']:
            if item['type'] != 'Create':
                continue

            blogRSS2 += \
                _htmlBlogPostRSS2(authorized, base_dir,
                                  http_prefix, translate,
                                  nickname, domain,
                                  domain_full, item,
                                  None, True, system_language)

    if includeHeader:
        return blogRSS2 + rss2Footer()
    else:
        return blogRSS2


def htmlBlogPageRSS3(authorized: bool, session,
                     base_dir: str, http_prefix: str, translate: {},
                     nickname: str, domain: str, port: int,
                     noOfItems: int, pageNumber: int,
                     system_language: str) -> str:
    """Returns an RSS version 3 feed containing posts
    """
    if ' ' in nickname or '@' in nickname or \
       '\n' in nickname or '\r' in nickname:
        return None

    domain_full = get_full_domain(domain, port)

    blogRSS3 = ''

    blogsIndex = acct_dir(base_dir, nickname, domain) + '/tlblogs.index'
    if not os.path.isfile(blogsIndex):
        return blogRSS3

    timelineJson = createBlogsTimeline(session, base_dir,
                                       nickname, domain, port,
                                       http_prefix,
                                       noOfItems, False,
                                       pageNumber)

    if not timelineJson:
        return blogRSS3

    if pageNumber is not None:
        for item in timelineJson['orderedItems']:
            if item['type'] != 'Create':
                continue

            blogRSS3 += \
                _htmlBlogPostRSS3(authorized, base_dir,
                                  http_prefix, translate,
                                  nickname, domain,
                                  domain_full, item,
                                  None, True,
                                  system_language)

    return blogRSS3


def _noOfBlogAccounts(base_dir: str) -> int:
    """Returns the number of blog accounts
    """
    ctr = 0
    for subdir, dirs, files in os.walk(base_dir + '/accounts'):
        for acct in dirs:
            if not is_account_dir(acct):
                continue
            accountDir = os.path.join(base_dir + '/accounts', acct)
            blogsIndex = accountDir + '/tlblogs.index'
            if os.path.isfile(blogsIndex):
                ctr += 1
        break
    return ctr


def _singleBlogAccountNickname(base_dir: str) -> str:
    """Returns the nickname of a single blog account
    """
    for subdir, dirs, files in os.walk(base_dir + '/accounts'):
        for acct in dirs:
            if not is_account_dir(acct):
                continue
            accountDir = os.path.join(base_dir + '/accounts', acct)
            blogsIndex = accountDir + '/tlblogs.index'
            if os.path.isfile(blogsIndex):
                return acct.split('@')[0]
        break
    return None


def htmlBlogView(authorized: bool,
                 session, base_dir: str, http_prefix: str,
                 translate: {}, domain: str, port: int,
                 noOfItems: int,
                 peertube_instances: [], system_language: str,
                 person_cache: {}, debug: bool) -> str:
    """Show the blog main page
    """
    blogStr = ''

    cssFilename = base_dir + '/epicyon-profile.css'
    if os.path.isfile(base_dir + '/epicyon.css'):
        cssFilename = base_dir + '/epicyon.css'
    instanceTitle = \
        get_config_param(base_dir, 'instanceTitle')
    blogStr = htmlHeaderWithExternalStyle(cssFilename, instanceTitle, None)

    if _noOfBlogAccounts(base_dir) <= 1:
        nickname = _singleBlogAccountNickname(base_dir)
        if nickname:
            return htmlBlogPage(authorized, session,
                                base_dir, http_prefix, translate,
                                nickname, domain, port,
                                noOfItems, 1, peertube_instances,
                                system_language, person_cache, debug)

    domain_full = get_full_domain(domain, port)

    for subdir, dirs, files in os.walk(base_dir + '/accounts'):
        for acct in dirs:
            if not is_account_dir(acct):
                continue
            accountDir = os.path.join(base_dir + '/accounts', acct)
            blogsIndex = accountDir + '/tlblogs.index'
            if os.path.isfile(blogsIndex):
                blogStr += '<p class="blogaccount">'
                blogStr += '<a href="' + \
                    http_prefix + '://' + domain_full + '/blog/' + \
                    acct.split('@')[0] + '">' + acct + '</a>'
                blogStr += '</p>'
        break

    return blogStr + htmlFooter()


def htmlEditBlog(media_instance: bool, translate: {},
                 base_dir: str, http_prefix: str,
                 path: str,
                 pageNumber: int,
                 nickname: str, domain: str,
                 postUrl: str, system_language: str) -> str:
    """Edit a blog post after it was created
    """
    post_filename = locate_post(base_dir, nickname, domain, postUrl)
    if not post_filename:
        print('Edit blog: Filename not found for ' + postUrl)
        return None

    post_json_object = load_json(post_filename)
    if not post_json_object:
        print('Edit blog: json not loaded for ' + post_filename)
        return None

    editBlogText = '<h1">' + translate['Write your post text below.'] + '</h1>'

    if os.path.isfile(base_dir + '/accounts/newpost.txt'):
        try:
            with open(base_dir + '/accounts/newpost.txt', 'r') as file:
                editBlogText = '<p>' + file.read() + '</p>'
        except OSError:
            print('EX: unable to read ' + base_dir + '/accounts/newpost.txt')

    cssFilename = base_dir + '/epicyon-profile.css'
    if os.path.isfile(base_dir + '/epicyon.css'):
        cssFilename = base_dir + '/epicyon.css'

    if '?' in path:
        path = path.split('?')[0]
    pathBase = path

    editBlogImageSection = '    <div class="container">'
    editBlogImageSection += '      <label class="labels">' + \
        translate['Image description'] + '</label>'
    editBlogImageSection += '      <input type="text" name="imageDescription">'
    editBlogImageSection += \
        '      <input type="file" id="attachpic" name="attachpic"'
    editBlogImageSection += \
        '            accept="' + get_media_formats() + '">'
    editBlogImageSection += '    </div>'

    placeholderMessage = translate['Write something'] + '...'
    endpoint = 'editblogpost'
    placeholderSubject = translate['Title']
    scopeIcon = 'scope_blog.png'
    scopeDescription = translate['Blog']

    dateAndLocation = ''
    dateAndLocation = '<div class="container">'

    dateAndLocation += \
        '<p><input type="checkbox" class="profilecheckbox" ' + \
        'name="schedulePost"><label class="labels">' + \
        translate['This is a scheduled post.'] + '</label></p>'

    dateAndLocation += \
        '<p><img loading="lazy" alt="" title="" ' + \
        'class="emojicalendar" src="/icons/calendar.png"/>'
    dateAndLocation += \
        '<label class="labels">' + translate['Date'] + ': </label>'
    dateAndLocation += '<input type="date" name="eventDate">'
    dateAndLocation += '<label class="labelsright">' + translate['Time'] + ':'
    dateAndLocation += '<input type="time" name="eventTime"></label></p>'
    dateAndLocation += '</div>'
    dateAndLocation += '<div class="container">'
    dateAndLocation += \
        '<br><label class="labels">' + translate['Location'] + ': </label>'
    dateAndLocation += '<input type="text" name="location">'
    dateAndLocation += '</div>'

    instanceTitle = \
        get_config_param(base_dir, 'instanceTitle')
    editBlogForm = \
        htmlHeaderWithExternalStyle(cssFilename, instanceTitle, None)

    editBlogForm += \
        '<form enctype="multipart/form-data" method="POST" ' + \
        'accept-charset="UTF-8" action="' + \
        pathBase + '?' + endpoint + '?page=' + str(pageNumber) + '">'
    editBlogForm += \
        '  <input type="hidden" name="postUrl" value="' + postUrl + '">'
    editBlogForm += \
        '  <input type="hidden" name="pageNumber" value="' + \
        str(pageNumber) + '">'
    editBlogForm += '  <div class="vertical-center">'
    editBlogForm += \
        '    <label for="nickname"><b>' + editBlogText + '</b></label>'
    editBlogForm += '    <div class="container">'

    editBlogForm += '      <div class="dropbtn">'
    editBlogForm += \
        '        <img loading="lazy" alt="" title="" src="/icons' + \
        '/' + scopeIcon + '"/><b class="scope-desc">' + \
        scopeDescription + '</b>'
    editBlogForm += '      </div>'

    editBlogForm += '      <a href="' + pathBase + \
        '/searchemoji"><img loading="lazy" ' + \
        'class="emojisearch" src="/emoji/1F601.png" title="' + \
        translate['Search for emoji'] + '" alt="' + \
        translate['Search for emoji'] + '"/></a>'
    editBlogForm += '    </div>'
    editBlogForm += '    <div class="container"><center>'
    editBlogForm += '      <a href="' + pathBase + \
        '/inbox"><button class="cancelbtn">' + \
        translate['Cancel'] + '</button></a>'
    editBlogForm += '      <input type="submit" name="submitPost" value="' + \
        translate['Submit'] + '">'
    editBlogForm += '    </center></div>'
    if media_instance:
        editBlogForm += editBlogImageSection
    editBlogForm += \
        '    <label class="labels">' + placeholderSubject + '</label><br>'
    titleStr = ''
    if post_json_object['object'].get('summary'):
        titleStr = post_json_object['object']['summary']
    editBlogForm += \
        '    <input type="text" name="subject" value="' + titleStr + '">'
    editBlogForm += ''
    editBlogForm += '    <br>'
    messageBoxHeight = 800

    contentStr = get_base_content_from_post(post_json_object, system_language)
    contentStr = contentStr.replace('<p>', '').replace('</p>', '\n')

    editBlogForm += \
        editTextArea(placeholderMessage, 'message', contentStr,
                     messageBoxHeight, '', True)
    editBlogForm += dateAndLocation
    if not media_instance:
        editBlogForm += editBlogImageSection
    editBlogForm += '  </div>'
    editBlogForm += '</form>'

    editBlogForm = editBlogForm.replace('<body>',
                                        '<body onload="focusOnMessage()">')

    editBlogForm += htmlFooter()
    return editBlogForm


def pathContainsBlogLink(base_dir: str,
                         http_prefix: str, domain: str,
                         domain_full: str, path: str) -> (str, str):
    """If the path contains a blog entry then return its filename
    """
    if '/users/' not in path:
        return None, None
    userEnding = path.split('/users/', 1)[1]
    if '/' not in userEnding:
        return None, None
    userEnding2 = userEnding.split('/')
    nickname = userEnding2[0]
    if len(userEnding2) != 2:
        return None, None
    if len(userEnding2[1]) < 14:
        return None, None
    userEnding2[1] = userEnding2[1].strip()
    if not userEnding2[1].isdigit():
        return None, None
    # check for blog posts
    blogIndexFilename = acct_dir(base_dir, nickname, domain) + '/tlblogs.index'
    if not os.path.isfile(blogIndexFilename):
        return None, None
    if '#' + userEnding2[1] + '.' not in open(blogIndexFilename).read():
        return None, None
    messageId = local_actor_url(http_prefix, nickname, domain_full) + \
        '/statuses/' + userEnding2[1]
    return locate_post(base_dir, nickname, domain, messageId), nickname


def getBlogAddress(actor_json: {}) -> str:
    """Returns blog address for the given actor
    """
    return get_actor_property_url(actor_json, 'Blog')
