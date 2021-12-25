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
from utils import localActorUrl
from utils import getActorLanguagesList
from utils import getBaseContentFromPost
from utils import getContentFromPost
from utils import isAccountDir
from utils import removeHtml
from utils import getConfigParam
from utils import getFullDomain
from utils import getMediaFormats
from utils import getNicknameFromActor
from utils import getDomainFromActor
from utils import locatePost
from utils import loadJson
from utils import firstParagraphFromString
from utils import getActorPropertyUrl
from utils import acctDir
from posts import createBlogsTimeline
from newswire import rss2Header
from newswire import rss2Footer
from cache import getPersonFromCache


def _noOfBlogReplies(base_dir: str, httpPrefix: str, translate: {},
                     nickname: str, domain: str, domainFull: str,
                     postId: str, depth=0) -> int:
    """Returns the number of replies on the post
    This is recursive, so can handle replies to replies
    """
    if depth > 4:
        return 0
    if not postId:
        return 0

    tryPostBox = ('tlblogs', 'inbox', 'outbox')
    boxFound = False
    for postBox in tryPostBox:
        postFilename = \
            acctDir(base_dir, nickname, domain) + '/' + postBox + '/' + \
            postId.replace('/', '#') + '.replies'
        if os.path.isfile(postFilename):
            boxFound = True
            break
    if not boxFound:
        # post may exist but has no replies
        for postBox in tryPostBox:
            postFilename = \
                acctDir(base_dir, nickname, domain) + '/' + postBox + '/' + \
                postId.replace('/', '#')
            if os.path.isfile(postFilename):
                return 1
        return 0

    removals = []
    replies = 0
    lines = []
    try:
        with open(postFilename, 'r') as f:
            lines = f.readlines()
    except OSError:
        print('EX: failed to read blog ' + postFilename)

    for replyPostId in lines:
        replyPostId = replyPostId.replace('\n', '').replace('\r', '')
        replyPostId = replyPostId.replace('.json', '')
        if locatePost(base_dir, nickname, domain, replyPostId):
            replyPostId = replyPostId.replace('.replies', '')
            replies += \
                1 + _noOfBlogReplies(base_dir, httpPrefix, translate,
                                     nickname, domain, domainFull,
                                     replyPostId, depth+1)
        else:
            # remove post which no longer exists
            removals.append(replyPostId)

    # remove posts from .replies file if they don't exist
    if lines and removals:
        print('Rewriting ' + postFilename + ' to remove ' +
              str(len(removals)) + ' entries')
        try:
            with open(postFilename, 'w+') as f:
                for replyPostId in lines:
                    replyPostId = \
                        replyPostId.replace('\n', '').replace('\r', '')
                    if replyPostId not in removals:
                        f.write(replyPostId + '\n')
        except OSError as ex:
            print('EX: unable to remove replies from post ' +
                  postFilename + ' ' + str(ex))

    return replies


def _getBlogReplies(base_dir: str, httpPrefix: str, translate: {},
                    nickname: str, domain: str, domainFull: str,
                    postId: str, depth=0) -> str:
    """Returns a string containing html blog posts
    """
    if depth > 4:
        return ''
    if not postId:
        return ''

    tryPostBox = ('tlblogs', 'inbox', 'outbox')
    boxFound = False
    for postBox in tryPostBox:
        postFilename = \
            acctDir(base_dir, nickname, domain) + '/' + postBox + '/' + \
            postId.replace('/', '#') + '.replies'
        if os.path.isfile(postFilename):
            boxFound = True
            break
    if not boxFound:
        # post may exist but has no replies
        for postBox in tryPostBox:
            postFilename = \
                acctDir(base_dir, nickname, domain) + '/' + postBox + '/' + \
                postId.replace('/', '#') + '.json'
            if os.path.isfile(postFilename):
                postFilename = acctDir(base_dir, nickname, domain) + \
                    '/postcache/' + \
                    postId.replace('/', '#') + '.html'
                if os.path.isfile(postFilename):
                    try:
                        with open(postFilename, 'r') as postFile:
                            return postFile.read() + '\n'
                    except OSError:
                        print('EX: unable to read blog 3 ' + postFilename)
        return ''

    lines = []
    try:
        with open(postFilename, 'r') as f:
            lines = f.readlines()
    except OSError:
        print('EX: unable to read blog 4 ' + postFilename)

    if lines:
        repliesStr = ''
        for replyPostId in lines:
            replyPostId = replyPostId.replace('\n', '').replace('\r', '')
            replyPostId = replyPostId.replace('.json', '')
            replyPostId = replyPostId.replace('.replies', '')
            postFilename = acctDir(base_dir, nickname, domain) + \
                '/postcache/' + \
                replyPostId.replace('/', '#') + '.html'
            if not os.path.isfile(postFilename):
                continue
            try:
                with open(postFilename, 'r') as postFile:
                    repliesStr += postFile.read() + '\n'
            except OSError:
                print('EX: unable to read blog replies ' + postFilename)
            rply = _getBlogReplies(base_dir, httpPrefix, translate,
                                   nickname, domain, domainFull,
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
                         base_dir: str, httpPrefix: str, translate: {},
                         nickname: str, domain: str, domainFull: str,
                         postJsonObject: {},
                         handle: str, restrictToDomain: bool,
                         peertubeInstances: [],
                         systemLanguage: str,
                         personCache: {},
                         blogSeparator: str = '<hr>') -> str:
    """Returns the content for a single blog post
    """
    linkedAuthor = False
    actor = ''
    blogStr = ''
    messageLink = ''
    if postJsonObject['object'].get('id'):
        messageLink = postJsonObject['object']['id'].replace('/statuses/', '/')
    titleStr = ''
    articleAdded = False
    if postJsonObject['object'].get('summary'):
        titleStr = postJsonObject['object']['summary']
        blogStr += '<article><h1><a href="' + messageLink + '">' + \
            titleStr + '</a></h1>\n'
        articleAdded = True

    # get the handle of the author
    if postJsonObject['object'].get('attributedTo'):
        authorNickname = None
        if isinstance(postJsonObject['object']['attributedTo'], str):
            actor = postJsonObject['object']['attributedTo']
            authorNickname = getNicknameFromActor(actor)
        if authorNickname:
            authorDomain, authorPort = getDomainFromActor(actor)
            if authorDomain:
                # author must be from the given domain
                if restrictToDomain and authorDomain != domain:
                    return ''
                handle = authorNickname + '@' + authorDomain
    else:
        # posts from the domain are expected to have an attributedTo field
        if restrictToDomain:
            return ''

    if postJsonObject['object'].get('published'):
        if 'T' in postJsonObject['object']['published']:
            blogStr += '<h3>' + \
                postJsonObject['object']['published'].split('T')[0]
            if handle:
                if handle.startswith(nickname + '@' + domain):
                    blogStr += ' <a href="' + httpPrefix + '://' + \
                        domainFull + \
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
    attachmentStr, galleryStr = getPostAttachmentsAsHtml(postJsonObject,
                                                         'tlblogs', translate,
                                                         isMuted, avatarLink,
                                                         replyStr, announceStr,
                                                         likeStr, bookmarkStr,
                                                         deleteStr, muteStr)
    if attachmentStr:
        blogStr += '<br><center>' + attachmentStr + '</center>'

    personUrl = localActorUrl(httpPrefix, nickname, domainFull)
    actorJson = \
        getPersonFromCache(base_dir, personUrl, personCache, False)
    languagesUnderstood = []
    if actorJson:
        languagesUnderstood = getActorLanguagesList(actorJson)
    jsonContent = getContentFromPost(postJsonObject, systemLanguage,
                                     languagesUnderstood)
    if jsonContent:
        contentStr = addEmbeddedElements(translate, jsonContent,
                                         peertubeInstances)
        if postJsonObject['object'].get('tag'):
            contentStr = replaceEmojiFromTags(session, base_dir, contentStr,
                                              postJsonObject['object']['tag'],
                                              'content', debug)
        if articleAdded:
            blogStr += '<br>' + contentStr + '</article>\n'
        else:
            blogStr += '<br><article>' + contentStr + '</article>\n'

    citationsStr = ''
    if postJsonObject['object'].get('tag'):
        for tagJson in postJsonObject['object']['tag']:
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
            localActorUrl(httpPrefix, nickname, domainFull) + \
            '">' + translate['About the author'] + \
            '</a></p>\n'

    replies = _noOfBlogReplies(base_dir, httpPrefix, translate,
                               nickname, domain, domainFull,
                               postJsonObject['object']['id'])

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
            blogStr += _getBlogReplies(base_dir, httpPrefix, translate,
                                       nickname, domain, domainFull,
                                       postJsonObject['object']['id'])
        else:
            blogRepliesStr = _getBlogReplies(base_dir, httpPrefix, translate,
                                             nickname, domain, domainFull,
                                             postJsonObject['object']['id'])
            blogStr += blogRepliesStr.replace('>' + titleStr + '<', '')

    return blogStr


def _htmlBlogPostRSS2(authorized: bool,
                      base_dir: str, httpPrefix: str, translate: {},
                      nickname: str, domain: str, domainFull: str,
                      postJsonObject: {},
                      handle: str, restrictToDomain: bool,
                      systemLanguage: str) -> str:
    """Returns the RSS version 2 feed for a single blog post
    """
    rssStr = ''
    messageLink = ''
    if postJsonObject['object'].get('id'):
        messageLink = postJsonObject['object']['id'].replace('/statuses/', '/')
        if not restrictToDomain or \
           (restrictToDomain and '/' + domain in messageLink):
            if postJsonObject['object'].get('summary') and \
               postJsonObject['object'].get('published'):
                published = postJsonObject['object']['published']
                pubDate = datetime.strptime(published, "%Y-%m-%dT%H:%M:%SZ")
                titleStr = postJsonObject['object']['summary']
                rssDateStr = pubDate.strftime("%a, %d %b %Y %H:%M:%S UT")
                content = \
                    getBaseContentFromPost(postJsonObject, systemLanguage)
                description = firstParagraphFromString(content)
                rssStr = '     <item>'
                rssStr += '         <title>' + titleStr + '</title>'
                rssStr += '         <link>' + messageLink + '</link>'
                rssStr += \
                    '         <description>' + description + '</description>'
                rssStr += '         <pubDate>' + rssDateStr + '</pubDate>'
                rssStr += '     </item>'
    return rssStr


def _htmlBlogPostRSS3(authorized: bool,
                      base_dir: str, httpPrefix: str, translate: {},
                      nickname: str, domain: str, domainFull: str,
                      postJsonObject: {},
                      handle: str, restrictToDomain: bool,
                      systemLanguage: str) -> str:
    """Returns the RSS version 3 feed for a single blog post
    """
    rssStr = ''
    messageLink = ''
    if postJsonObject['object'].get('id'):
        messageLink = postJsonObject['object']['id'].replace('/statuses/', '/')
        if not restrictToDomain or \
           (restrictToDomain and '/' + domain in messageLink):
            if postJsonObject['object'].get('summary') and \
               postJsonObject['object'].get('published'):
                published = postJsonObject['object']['published']
                pubDate = datetime.strptime(published, "%Y-%m-%dT%H:%M:%SZ")
                titleStr = postJsonObject['object']['summary']
                rssDateStr = pubDate.strftime("%a, %d %b %Y %H:%M:%S UT")
                content = \
                    getBaseContentFromPost(postJsonObject, systemLanguage)
                description = firstParagraphFromString(content)
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


def _getSnippetFromBlogContent(postJsonObject: {}, systemLanguage: str) -> str:
    """Returns a snippet of text from the blog post as a preview
    """
    content = getBaseContentFromPost(postJsonObject, systemLanguage)
    if '<p>' in content:
        content = content.split('<p>', 1)[1]
        if '</p>' in content:
            content = content.split('</p>', 1)[0]
    content = removeHtml(content)
    if '\n' in content:
        content = content.split('\n')[0]
    if len(content) >= 256:
        content = content[:252] + '...'
    return content


def htmlBlogPost(session, authorized: bool,
                 base_dir: str, httpPrefix: str, translate: {},
                 nickname: str, domain: str, domainFull: str,
                 postJsonObject: {},
                 peertubeInstances: [],
                 systemLanguage: str, personCache: {},
                 debug: bool, contentLicenseUrl: str) -> str:
    """Returns a html blog post
    """
    blogStr = ''

    cssFilename = base_dir + '/epicyon-blog.css'
    if os.path.isfile(base_dir + '/blog.css'):
        cssFilename = base_dir + '/blog.css'
    instanceTitle = \
        getConfigParam(base_dir, 'instanceTitle')
    published = postJsonObject['object']['published']
    modified = published
    if postJsonObject['object'].get('updated'):
        modified = postJsonObject['object']['updated']
    title = postJsonObject['object']['summary']
    url = ''
    if postJsonObject['object'].get('url'):
        url = postJsonObject['object']['url']
    snippet = _getSnippetFromBlogContent(postJsonObject, systemLanguage)
    blogStr = htmlHeaderWithBlogMarkup(cssFilename, instanceTitle,
                                       httpPrefix, domainFull, nickname,
                                       systemLanguage, published, modified,
                                       title, snippet, translate, url,
                                       contentLicenseUrl)
    _htmlBlogRemoveCwButton(blogStr, translate)

    blogStr += _htmlBlogPostContent(debug, session, authorized, base_dir,
                                    httpPrefix, translate,
                                    nickname, domain,
                                    domainFull, postJsonObject,
                                    None, False,
                                    peertubeInstances, systemLanguage,
                                    personCache)

    # show rss links
    blogStr += '<p class="rssfeed">'

    blogStr += '<a href="' + httpPrefix + '://' + \
        domainFull + '/blog/' + nickname + '/rss.xml">'
    blogStr += '<img style="width:3%;min-width:50px" ' + \
        'loading="lazy" alt="RSS 2.0" ' + \
        'title="RSS 2.0" src="/' + \
        'icons/logorss.png" /></a>'

    # blogStr += '<a href="' + httpPrefix + '://' + \
    #     domainFull + '/blog/' + nickname + '/rss.txt">'
    # blogStr += '<img style="width:3%;min-width:50px" ' + \
    #     'loading="lazy" alt="RSS 3.0" ' + \
    #     'title="RSS 3.0" src="/' + \
    #     'icons/rss3.png" /></a>'

    blogStr += '</p>'

    return blogStr + htmlFooter()


def htmlBlogPage(authorized: bool, session,
                 base_dir: str, httpPrefix: str, translate: {},
                 nickname: str, domain: str, port: int,
                 noOfItems: int, pageNumber: int,
                 peertubeInstances: [], systemLanguage: str,
                 personCache: {}, debug: bool) -> str:
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
        getConfigParam(base_dir, 'instanceTitle')
    blogStr = htmlHeaderWithExternalStyle(cssFilename, instanceTitle, None)
    _htmlBlogRemoveCwButton(blogStr, translate)

    blogsIndex = acctDir(base_dir, nickname, domain) + '/tlblogs.index'
    if not os.path.isfile(blogsIndex):
        return blogStr + htmlFooter()

    timelineJson = createBlogsTimeline(session, base_dir,
                                       nickname, domain, port,
                                       httpPrefix,
                                       noOfItems, False,
                                       pageNumber)

    if not timelineJson:
        return blogStr + htmlFooter()

    domainFull = getFullDomain(domain, port)

    # show previous and next buttons
    if pageNumber is not None:
        navigateStr = '<p>'
        if pageNumber > 1:
            # show previous button
            navigateStr += '<a href="' + httpPrefix + '://' + \
                domainFull + '/blog/' + \
                nickname + '?page=' + str(pageNumber-1) + '">' + \
                '<img loading="lazy" alt="<" title="<" ' + \
                'src="/icons' + \
                '/prev.png" class="buttonprev"/></a>\n'
        if len(timelineJson['orderedItems']) >= noOfItems:
            # show next button
            navigateStr += '<a href="' + httpPrefix + '://' + \
                domainFull + '/blog/' + nickname + \
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
                                        httpPrefix, translate,
                                        nickname, domain,
                                        domainFull, item,
                                        None, True,
                                        peertubeInstances,
                                        systemLanguage,
                                        personCache)

    if len(timelineJson['orderedItems']) >= noOfItems:
        blogStr += navigateStr

    # show rss link
    blogStr += '<p class="rssfeed">'

    blogStr += '<a href="' + httpPrefix + '://' + \
        domainFull + '/blog/' + nickname + '/rss.xml">'
    blogStr += '<img loading="lazy" alt="RSS 2.0" ' + \
        'title="RSS 2.0" src="/' + \
        'icons/logorss.png" /></a>'

    # blogStr += '<a href="' + httpPrefix + '://' + \
    #     domainFull + '/blog/' + nickname + '/rss.txt">'
    # blogStr += '<img loading="lazy" alt="RSS 3.0" ' + \
    #     'title="RSS 3.0" src="/' + \
    #     'icons/rss3.png" /></a>'

    blogStr += '</p>'
    return blogStr + htmlFooter()


def htmlBlogPageRSS2(authorized: bool, session,
                     base_dir: str, httpPrefix: str, translate: {},
                     nickname: str, domain: str, port: int,
                     noOfItems: int, pageNumber: int,
                     includeHeader: bool, systemLanguage: str) -> str:
    """Returns an RSS version 2 feed containing posts
    """
    if ' ' in nickname or '@' in nickname or \
       '\n' in nickname or '\r' in nickname:
        return None

    domainFull = getFullDomain(domain, port)

    blogRSS2 = ''
    if includeHeader:
        blogRSS2 = rss2Header(httpPrefix, nickname, domainFull,
                              'Blog', translate)

    blogsIndex = acctDir(base_dir, nickname, domain) + '/tlblogs.index'
    if not os.path.isfile(blogsIndex):
        if includeHeader:
            return blogRSS2 + rss2Footer()
        else:
            return blogRSS2

    timelineJson = createBlogsTimeline(session, base_dir,
                                       nickname, domain, port,
                                       httpPrefix,
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
                                  httpPrefix, translate,
                                  nickname, domain,
                                  domainFull, item,
                                  None, True, systemLanguage)

    if includeHeader:
        return blogRSS2 + rss2Footer()
    else:
        return blogRSS2


def htmlBlogPageRSS3(authorized: bool, session,
                     base_dir: str, httpPrefix: str, translate: {},
                     nickname: str, domain: str, port: int,
                     noOfItems: int, pageNumber: int,
                     systemLanguage: str) -> str:
    """Returns an RSS version 3 feed containing posts
    """
    if ' ' in nickname or '@' in nickname or \
       '\n' in nickname or '\r' in nickname:
        return None

    domainFull = getFullDomain(domain, port)

    blogRSS3 = ''

    blogsIndex = acctDir(base_dir, nickname, domain) + '/tlblogs.index'
    if not os.path.isfile(blogsIndex):
        return blogRSS3

    timelineJson = createBlogsTimeline(session, base_dir,
                                       nickname, domain, port,
                                       httpPrefix,
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
                                  httpPrefix, translate,
                                  nickname, domain,
                                  domainFull, item,
                                  None, True,
                                  systemLanguage)

    return blogRSS3


def _noOfBlogAccounts(base_dir: str) -> int:
    """Returns the number of blog accounts
    """
    ctr = 0
    for subdir, dirs, files in os.walk(base_dir + '/accounts'):
        for acct in dirs:
            if not isAccountDir(acct):
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
            if not isAccountDir(acct):
                continue
            accountDir = os.path.join(base_dir + '/accounts', acct)
            blogsIndex = accountDir + '/tlblogs.index'
            if os.path.isfile(blogsIndex):
                return acct.split('@')[0]
        break
    return None


def htmlBlogView(authorized: bool,
                 session, base_dir: str, httpPrefix: str,
                 translate: {}, domain: str, port: int,
                 noOfItems: int,
                 peertubeInstances: [], systemLanguage: str,
                 personCache: {}, debug: bool) -> str:
    """Show the blog main page
    """
    blogStr = ''

    cssFilename = base_dir + '/epicyon-profile.css'
    if os.path.isfile(base_dir + '/epicyon.css'):
        cssFilename = base_dir + '/epicyon.css'
    instanceTitle = \
        getConfigParam(base_dir, 'instanceTitle')
    blogStr = htmlHeaderWithExternalStyle(cssFilename, instanceTitle, None)

    if _noOfBlogAccounts(base_dir) <= 1:
        nickname = _singleBlogAccountNickname(base_dir)
        if nickname:
            return htmlBlogPage(authorized, session,
                                base_dir, httpPrefix, translate,
                                nickname, domain, port,
                                noOfItems, 1, peertubeInstances,
                                systemLanguage, personCache, debug)

    domainFull = getFullDomain(domain, port)

    for subdir, dirs, files in os.walk(base_dir + '/accounts'):
        for acct in dirs:
            if not isAccountDir(acct):
                continue
            accountDir = os.path.join(base_dir + '/accounts', acct)
            blogsIndex = accountDir + '/tlblogs.index'
            if os.path.isfile(blogsIndex):
                blogStr += '<p class="blogaccount">'
                blogStr += '<a href="' + \
                    httpPrefix + '://' + domainFull + '/blog/' + \
                    acct.split('@')[0] + '">' + acct + '</a>'
                blogStr += '</p>'
        break

    return blogStr + htmlFooter()


def htmlEditBlog(mediaInstance: bool, translate: {},
                 base_dir: str, httpPrefix: str,
                 path: str,
                 pageNumber: int,
                 nickname: str, domain: str,
                 postUrl: str, systemLanguage: str) -> str:
    """Edit a blog post after it was created
    """
    postFilename = locatePost(base_dir, nickname, domain, postUrl)
    if not postFilename:
        print('Edit blog: Filename not found for ' + postUrl)
        return None

    postJsonObject = loadJson(postFilename)
    if not postJsonObject:
        print('Edit blog: json not loaded for ' + postFilename)
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
        '            accept="' + getMediaFormats() + '">'
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
        getConfigParam(base_dir, 'instanceTitle')
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
    if mediaInstance:
        editBlogForm += editBlogImageSection
    editBlogForm += \
        '    <label class="labels">' + placeholderSubject + '</label><br>'
    titleStr = ''
    if postJsonObject['object'].get('summary'):
        titleStr = postJsonObject['object']['summary']
    editBlogForm += \
        '    <input type="text" name="subject" value="' + titleStr + '">'
    editBlogForm += ''
    editBlogForm += '    <br>'
    messageBoxHeight = 800

    contentStr = getBaseContentFromPost(postJsonObject, systemLanguage)
    contentStr = contentStr.replace('<p>', '').replace('</p>', '\n')

    editBlogForm += \
        editTextArea(placeholderMessage, 'message', contentStr,
                     messageBoxHeight, '', True)
    editBlogForm += dateAndLocation
    if not mediaInstance:
        editBlogForm += editBlogImageSection
    editBlogForm += '  </div>'
    editBlogForm += '</form>'

    editBlogForm = editBlogForm.replace('<body>',
                                        '<body onload="focusOnMessage()">')

    editBlogForm += htmlFooter()
    return editBlogForm


def pathContainsBlogLink(base_dir: str,
                         httpPrefix: str, domain: str,
                         domainFull: str, path: str) -> (str, str):
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
    blogIndexFilename = acctDir(base_dir, nickname, domain) + '/tlblogs.index'
    if not os.path.isfile(blogIndexFilename):
        return None, None
    if '#' + userEnding2[1] + '.' not in open(blogIndexFilename).read():
        return None, None
    messageId = localActorUrl(httpPrefix, nickname, domainFull) + \
        '/statuses/' + userEnding2[1]
    return locatePost(base_dir, nickname, domain, messageId), nickname


def getBlogAddress(actorJson: {}) -> str:
    """Returns blog address for the given actor
    """
    return getActorPropertyUrl(actorJson, 'Blog')
