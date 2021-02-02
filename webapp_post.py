__filename__ = "webapp_post.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import os
import time
from dateutil.parser import parse
from auth import createPassword
from git import isGitPatch
from datetime import datetime
from cache import getPersonFromCache
from bookmarks import bookmarkedByPerson
from like import likedByPerson
from like import noOfLikes
from follow import isFollowingActor
from posts import postIsMuted
from posts import getPersonBox
from posts import isDM
from posts import downloadAnnounce
from posts import populateRepliesJson
from utils import getConfigParam
from utils import getFullDomain
from utils import isEditor
from utils import locatePost
from utils import loadJson
from utils import getCachedPostDirectory
from utils import getCachedPostFilename
from utils import getProtocolPrefixes
from utils import isNewsPost
from utils import isBlogPost
from utils import getDisplayName
from utils import isPublicPost
from utils import updateRecentPostsCache
from utils import removeIdEnding
from utils import getNicknameFromActor
from utils import getDomainFromActor
from utils import isEventPost
from content import replaceEmojiFromTags
from content import htmlReplaceQuoteMarks
from content import htmlReplaceEmailQuote
from content import removeTextFormatting
from content import removeLongWords
from content import getMentionsFromHtml
from content import switchWords
from person import isPersonSnoozed
from announce import announcedByPerson
from webapp_utils import getAvatarImageUrl
from webapp_utils import getPersonAvatarUrl
from webapp_utils import updateAvatarImageCache
from webapp_utils import loadIndividualPostAsHtmlFromCache
from webapp_utils import addEmojiToDisplayName
from webapp_utils import postContainsPublic
from webapp_utils import getContentWarningButton
from webapp_utils import getPostAttachmentsAsHtml
from webapp_utils import htmlHeaderWithExternalStyle
from webapp_utils import htmlFooter
from webapp_utils import getBrokenLinkSubstitute
from webapp_media import addEmbeddedElements
from webapp_question import insertQuestion
from devices import E2EEdecryptMessageFromDevice
from webfinger import webfingerHandle


def _logPostTiming(enableTimingLog: bool, postStartTime, debugId: str) -> None:
    """Create a log of timings for performance tuning
    """
    if not enableTimingLog:
        return
    timeDiff = int((time.time() - postStartTime) * 1000)
    if timeDiff > 100:
        print('TIMING INDIV ' + debugId + ' = ' + str(timeDiff))


def prepareHtmlPostNickname(nickname: str, postHtml: str) -> str:
    """html posts stored in memory are for all accounts on the instance
    and they're indexed by id. However, some incoming posts may be
    destined for multiple accounts (followers). This creates a problem
    where the icon links whose urls begin with href="/users/nickname?
    need to be changed for different nicknames to display correctly
    within their timelines.
    This function changes the nicknames for the icon links.
    """
    # replace the nickname
    usersStr = ' href="/users/'
    if usersStr not in postHtml:
        return postHtml

    userFound = True
    postStr = postHtml
    newPostStr = ''
    while userFound:
        if usersStr not in postStr:
            newPostStr += postStr
            break

        # the next part, after href="/users/nickname?
        nextStr = postStr.split(usersStr, 1)[1]
        if '?' in nextStr:
            nextStr = nextStr.split('?', 1)[1]
        else:
            newPostStr += postStr
            break

        # append the previous text to the result
        newPostStr += postStr.split(usersStr)[0]
        newPostStr += usersStr + nickname + '?'

        # post is now the next part
        postStr = nextStr
    return newPostStr


def preparePostFromHtmlCache(nickname: str, postHtml: str, boxName: str,
                             pageNumber: int) -> str:
    """Sets the page number on a cached html post
    """
    # if on the bookmarks timeline then remain there
    if boxName == 'tlbookmarks' or boxName == 'bookmarks':
        postHtml = postHtml.replace('?tl=inbox', '?tl=tlbookmarks')
        if '?page=' in postHtml:
            pageNumberStr = postHtml.split('?page=')[1]
            if '?' in pageNumberStr:
                pageNumberStr = pageNumberStr.split('?')[0]
            postHtml = postHtml.replace('?page=' + pageNumberStr, '?page=-999')

    withPageNumber = postHtml.replace(';-999;', ';' + str(pageNumber) + ';')
    withPageNumber = withPageNumber.replace('?page=-999',
                                            '?page=' + str(pageNumber))
    return prepareHtmlPostNickname(nickname, withPageNumber)


def _saveIndividualPostAsHtmlToCache(baseDir: str,
                                     nickname: str, domain: str,
                                     postJsonObject: {},
                                     postHtml: str) -> bool:
    """Saves the given html for a post to a cache file
    This is so that it can be quickly reloaded on subsequent
    refresh of the timeline
    """
    htmlPostCacheDir = \
        getCachedPostDirectory(baseDir, nickname, domain)
    cachedPostFilename = \
        getCachedPostFilename(baseDir, nickname, domain, postJsonObject)

    # create the cache directory if needed
    if not os.path.isdir(htmlPostCacheDir):
        os.mkdir(htmlPostCacheDir)

    try:
        with open(cachedPostFilename, 'w+') as fp:
            fp.write(postHtml)
            return True
    except Exception as e:
        print('ERROR: saving post to cache ' + str(e))
    return False


def _getPostFromRecentCache(session,
                            baseDir: str,
                            httpPrefix: str,
                            nickname: str, domain: str,
                            postJsonObject: {},
                            postActor: str,
                            personCache: {},
                            allowDownloads: bool,
                            showPublicOnly: bool,
                            storeToCache: bool,
                            boxName: str,
                            avatarUrl: str,
                            enableTimingLog: bool,
                            postStartTime,
                            pageNumber: int,
                            recentPostsCache: {},
                            maxRecentPosts: int) -> str:
    """Attempts to get the html post from the recent posts cache in memory
    """
    if boxName == 'tlmedia':
        return None

    if showPublicOnly:
        return None

    tryCache = False
    bmTimeline = boxName == 'bookmarks' or boxName == 'tlbookmarks'
    if storeToCache or bmTimeline:
        tryCache = True

    if not tryCache:
        return None

    # update avatar if needed
    if not avatarUrl:
        avatarUrl = \
            getPersonAvatarUrl(baseDir, postActor, personCache,
                               allowDownloads)

        _logPostTiming(enableTimingLog, postStartTime, '2.1')

    updateAvatarImageCache(session, baseDir, httpPrefix,
                           postActor, avatarUrl, personCache,
                           allowDownloads)

    _logPostTiming(enableTimingLog, postStartTime, '2.2')

    postHtml = \
        loadIndividualPostAsHtmlFromCache(baseDir, nickname, domain,
                                          postJsonObject)
    if not postHtml:
        return None

    postHtml = \
        preparePostFromHtmlCache(nickname, postHtml, boxName, pageNumber)
    updateRecentPostsCache(recentPostsCache, maxRecentPosts,
                           postJsonObject, postHtml)
    _logPostTiming(enableTimingLog, postStartTime, '3')
    return postHtml


def _getAvatarImageHtml(showAvatarOptions: bool,
                        nickname: str, domainFull: str,
                        avatarUrl: str, postActor: str,
                        translate: {}, avatarPosition: str,
                        pageNumber: int, messageIdStr: str) -> str:
    """Get html for the avatar image
    """
    avatarLink = ''
    if '/users/news/' not in avatarUrl:
        avatarLink = '        <a class="imageAnchor" href="' + postActor + '">'
        avatarLink += \
            '<img loading="lazy" src="' + avatarUrl + '" title="' + \
            translate['Show profile'] + '" alt=" "' + avatarPosition + \
            getBrokenLinkSubstitute() + '/></a>\n'

    if showAvatarOptions and \
       domainFull + '/users/' + nickname not in postActor:
        if '/users/news/' not in avatarUrl:
            avatarLink = \
                '        <a class="imageAnchor" href="/users/' + \
                nickname + '?options=' + postActor + \
                ';' + str(pageNumber) + ';' + avatarUrl + messageIdStr + '">\n'
            avatarLink += \
                '        <img loading="lazy" title="' + \
                translate['Show options for this person'] + \
                '" src="' + avatarUrl + '" ' + avatarPosition + \
                getBrokenLinkSubstitute() + '/></a>\n'
        else:
            # don't link to the person options for the news account
            avatarLink += \
                '        <img loading="lazy" title="' + \
                translate['Show options for this person'] + \
                '" src="' + avatarUrl + '" ' + avatarPosition + \
                getBrokenLinkSubstitute() + '/>\n'
    return avatarLink.strip()


def _getReplyIconHtml(nickname: str, isPublicRepeat: bool,
                      showIcons: bool, commentsEnabled: bool,
                      postJsonObject: {}, pageNumberParam: str,
                      translate: {}) -> str:
    """Returns html for the reply icon/button
    """
    replyStr = ''
    if not (showIcons and commentsEnabled):
        return replyStr

    # reply is permitted - create reply icon
    replyToLink = postJsonObject['object']['id']
    if postJsonObject['object'].get('attributedTo'):
        if isinstance(postJsonObject['object']['attributedTo'], str):
            replyToLink += \
                '?mention=' + postJsonObject['object']['attributedTo']
    if postJsonObject['object'].get('content'):
        mentionedActors = \
            getMentionsFromHtml(postJsonObject['object']['content'])
        if mentionedActors:
            for actorUrl in mentionedActors:
                if '?mention=' + actorUrl not in replyToLink:
                    replyToLink += '?mention=' + actorUrl
                    if len(replyToLink) > 500:
                        break
    replyToLink += pageNumberParam

    replyStr = ''
    replyToThisPostStr = translate['Reply to this post']
    if isPublicRepeat:
        replyStr += \
            '        <a class="imageAnchor" href="/users/' + \
            nickname + '?replyto=' + replyToLink + \
            '?actor=' + postJsonObject['actor'] + \
            '" title="' + replyToThisPostStr + '">\n'
    else:
        if isDM(postJsonObject):
            replyStr += \
                '        ' + \
                '<a class="imageAnchor" href="/users/' + nickname + \
                '?replydm=' + replyToLink + \
                '?actor=' + postJsonObject['actor'] + \
                '" title="' + replyToThisPostStr + '">\n'
        else:
            replyStr += \
                '        ' + \
                '<a class="imageAnchor" href="/users/' + nickname + \
                '?replyfollowers=' + replyToLink + \
                '?actor=' + postJsonObject['actor'] + \
                '" title="' + replyToThisPostStr + '">\n'

    replyStr += \
        '        ' + \
        '<img loading="lazy" title="' + \
        replyToThisPostStr + '" alt="' + replyToThisPostStr + \
        ' |" src="/icons/reply.png"/></a>\n'
    return replyStr


def _getEditIconHtml(baseDir: str, nickname: str, domainFull: str,
                     postJsonObject: {}, actorNickname: str,
                     translate: {}, isEvent: bool) -> str:
    """Returns html for the edit icon/button
    """
    editStr = ''
    actor = postJsonObject['actor']
    if (actor.endswith(domainFull + '/users/' + nickname) or
        (isEditor(baseDir, nickname) and
         actor.endswith(domainFull + '/users/news'))):

        postId = postJsonObject['object']['id']

        if '/statuses/' not in postId:
            return editStr

        if isBlogPost(postJsonObject):
            editBlogPostStr = translate['Edit blog post']
            if not isNewsPost(postJsonObject):
                editStr += \
                    '        ' + \
                    '<a class="imageAnchor" href="/users/' + \
                    nickname + \
                    '/tlblogs?editblogpost=' + \
                    postId.split('/statuses/')[1] + \
                    '?actor=' + actorNickname + \
                    '" title="' + editBlogPostStr + '">' + \
                    '<img loading="lazy" title="' + \
                    editBlogPostStr + '" alt="' + editBlogPostStr + \
                    ' |" src="/icons/edit.png"/></a>\n'
            else:
                editStr += \
                    '        ' + \
                    '<a class="imageAnchor" href="/users/' + \
                    nickname + '/editnewspost=' + \
                    postId.split('/statuses/')[1] + \
                    '?actor=' + actorNickname + \
                    '" title="' + editBlogPostStr + '">' + \
                    '<img loading="lazy" title="' + \
                    editBlogPostStr + '" alt="' + editBlogPostStr + \
                    ' |" src="/icons/edit.png"/></a>\n'
        elif isEvent:
            editEventStr = translate['Edit event']
            editStr += \
                '        ' + \
                '<a class="imageAnchor" href="/users/' + nickname + \
                '/tlblogs?editeventpost=' + \
                postId.split('/statuses/')[1] + \
                '?actor=' + actorNickname + \
                '" title="' + editEventStr + '">' + \
                '<img loading="lazy" title="' + \
                editEventStr + '" alt="' + editEventStr + \
                ' |" src="/icons/edit.png"/></a>\n'
    return editStr


def _getAnnounceIconHtml(nickname: str, domainFull: str,
                         postJsonObject: {},
                         isPublicRepeat: bool,
                         isModerationPost: bool,
                         showRepeatIcon: bool,
                         translate: {},
                         pageNumberParam: str,
                         timelinePostBookmark: str,
                         boxName: str) -> str:
    """Returns html for announce icon/button
    """
    announceStr = ''
    if not isModerationPost and showRepeatIcon:
        # don't allow announce/repeat of your own posts
        announceIcon = 'repeat_inactive.png'
        announceLink = 'repeat'
        if not isPublicRepeat:
            announceLink = 'repeatprivate'
        announceTitle = translate['Repeat this post']

        if announcedByPerson(postJsonObject, nickname, domainFull):
            announceIcon = 'repeat.png'
            if not isPublicRepeat:
                announceLink = 'unrepeatprivate'
            announceTitle = translate['Undo the repeat']

        announceStr = \
            '        <a class="imageAnchor" href="/users/' + \
            nickname + '?' + announceLink + \
            '=' + postJsonObject['object']['id'] + pageNumberParam + \
            '?actor=' + postJsonObject['actor'] + \
            '?bm=' + timelinePostBookmark + \
            '?tl=' + boxName + '" title="' + announceTitle + '">\n'

        announceStr += \
            '          ' + \
            '<img loading="lazy" title="' + translate['Repeat this post'] + \
            '" alt="' + translate['Repeat this post'] + \
            ' |" src="/icons/' + announceIcon + '"/></a>\n'
    return announceStr


def _getLikeIconHtml(nickname: str, domainFull: str,
                     isModerationPost: bool,
                     showLikeButton: bool,
                     postJsonObject: {},
                     enableTimingLog: bool,
                     postStartTime,
                     translate: {}, pageNumberParam: str,
                     timelinePostBookmark: str,
                     boxName: str) -> str:
    """Returns html for like icon/button
    """
    likeStr = ''
    if not isModerationPost and showLikeButton:
        likeIcon = 'like_inactive.png'
        likeLink = 'like'
        likeTitle = translate['Like this post']
        likeCount = noOfLikes(postJsonObject)

        _logPostTiming(enableTimingLog, postStartTime, '12.1')

        likeCountStr = ''
        if likeCount > 0:
            if likeCount <= 10:
                likeCountStr = ' (' + str(likeCount) + ')'
            else:
                likeCountStr = ' (10+)'
            if likedByPerson(postJsonObject, nickname, domainFull):
                if likeCount == 1:
                    # liked by the reader only
                    likeCountStr = ''
                likeIcon = 'like.png'
                likeLink = 'unlike'
                likeTitle = translate['Undo the like']

        _logPostTiming(enableTimingLog, postStartTime, '12.2')

        likeStr = ''
        if likeCountStr:
            # show the number of likes next to icon
            likeStr += '<label class="likesCount">'
            likeStr += likeCountStr.replace('(', '').replace(')', '').strip()
            likeStr += '</label>\n'
        likeStr += \
            '        <a class="imageAnchor" href="/users/' + nickname + '?' + \
            likeLink + '=' + postJsonObject['object']['id'] + \
            pageNumberParam + \
            '?actor=' + postJsonObject['actor'] + \
            '?bm=' + timelinePostBookmark + \
            '?tl=' + boxName + '" title="' + \
            likeTitle + likeCountStr + '">\n'
        likeStr += \
            '          ' + \
            '<img loading="lazy" title="' + likeTitle + likeCountStr + \
            '" alt="' + likeTitle + \
            ' |" src="/icons/' + likeIcon + '"/></a>\n'
    return likeStr


def _getBookmarkIconHtml(nickname: str, domainFull: str,
                         postJsonObject: {},
                         isModerationPost: bool,
                         translate: {},
                         enableTimingLog: bool,
                         postStartTime, boxName: str,
                         pageNumberParam: str,
                         timelinePostBookmark: str) -> str:
    """Returns html for bookmark icon/button
    """
    bookmarkStr = ''

    if isModerationPost:
        return bookmarkStr

    bookmarkIcon = 'bookmark_inactive.png'
    bookmarkLink = 'bookmark'
    bookmarkTitle = translate['Bookmark this post']
    if bookmarkedByPerson(postJsonObject, nickname, domainFull):
        bookmarkIcon = 'bookmark.png'
        bookmarkLink = 'unbookmark'
        bookmarkTitle = translate['Undo the bookmark']
    _logPostTiming(enableTimingLog, postStartTime, '12.6')
    bookmarkStr = \
        '        <a class="imageAnchor" href="/users/' + nickname + '?' + \
        bookmarkLink + '=' + postJsonObject['object']['id'] + \
        pageNumberParam + \
        '?actor=' + postJsonObject['actor'] + \
        '?bm=' + timelinePostBookmark + \
        '?tl=' + boxName + '" title="' + bookmarkTitle + '">\n'
    bookmarkStr += \
        '        ' + \
        '<img loading="lazy" title="' + bookmarkTitle + '" alt="' + \
        bookmarkTitle + ' |" src="/icons' + \
        '/' + bookmarkIcon + '"/></a>\n'
    return bookmarkStr


def _getMuteIconHtml(isMuted: bool,
                     postActor: str,
                     messageId: str,
                     nickname: str, domainFull: str,
                     allowDeletion: bool,
                     pageNumberParam: str,
                     boxName: str,
                     timelinePostBookmark: str,
                     translate: {}) -> str:
    """Returns html for mute icon/button
    """
    muteStr = ''
    if (allowDeletion or
        ('/' + domainFull + '/' in postActor and
         messageId.startswith(postActor))):
        return muteStr

    if not isMuted:
        muteStr = \
            '        <a class="imageAnchor" href="/users/' + nickname + \
            '?mute=' + messageId + pageNumberParam + '?tl=' + boxName + \
            '?bm=' + timelinePostBookmark + \
            '" title="' + translate['Mute this post'] + '">\n'
        muteStr += \
            '          ' + \
            '<img loading="lazy" alt="' + \
            translate['Mute this post'] + \
            ' |" title="' + translate['Mute this post'] + \
            '" src="/icons/mute.png"/></a>\n'
    else:
        muteStr = \
            '        <a class="imageAnchor" href="/users/' + \
            nickname + '?unmute=' + messageId + \
            pageNumberParam + '?tl=' + boxName + '?bm=' + \
            timelinePostBookmark + '" title="' + \
            translate['Undo mute'] + '">\n'
        muteStr += \
            '          ' + \
            '<img loading="lazy" alt="' + translate['Undo mute'] + \
            ' |" title="' + translate['Undo mute'] + \
            '" src="/icons/unmute.png"/></a>\n'
    return muteStr


def _getDeleteIconHtml(nickname: str, domainFull: str,
                       allowDeletion: bool,
                       postActor: str,
                       messageId: str,
                       postJsonObject: {},
                       pageNumberParam: str,
                       translate: {}) -> str:
    """Returns html for delete icon/button
    """
    deleteStr = ''
    if (allowDeletion or
        ('/' + domainFull + '/' in postActor and
         messageId.startswith(postActor))):
        if '/users/' + nickname + '/' in messageId:
            if not isNewsPost(postJsonObject):
                deleteStr = \
                    '        <a class="imageAnchor" href="/users/' + \
                    nickname + \
                    '?delete=' + messageId + pageNumberParam + \
                    '" title="' + translate['Delete this post'] + '">\n'
                deleteStr += \
                    '          ' + \
                    '<img loading="lazy" alt="' + \
                    translate['Delete this post'] + \
                    ' |" title="' + translate['Delete this post'] + \
                    '" src="/icons/delete.png"/></a>\n'
    return deleteStr


def _getPublishedDateStr(postJsonObject: {},
                         showPublishedDateOnly: bool) -> str:
    """Return the html for the published date on a post
    """
    publishedStr = ''

    if not postJsonObject['object'].get('published'):
        return publishedStr

    publishedStr = postJsonObject['object']['published']
    if '.' not in publishedStr:
        if '+' not in publishedStr:
            datetimeObject = \
                datetime.strptime(publishedStr, "%Y-%m-%dT%H:%M:%SZ")
        else:
            datetimeObject = \
                datetime.strptime(publishedStr.split('+')[0] + 'Z',
                                  "%Y-%m-%dT%H:%M:%SZ")
    else:
        publishedStr = \
            publishedStr.replace('T', ' ').split('.')[0]
        datetimeObject = parse(publishedStr)
    if not showPublishedDateOnly:
        publishedStr = datetimeObject.strftime("%a %b %d, %H:%M")
    else:
        publishedStr = datetimeObject.strftime("%a %b %d")

    # if the post has replies then append a symbol to indicate this
    if postJsonObject.get('hasReplies'):
        if postJsonObject['hasReplies'] is True:
            publishedStr = '[' + publishedStr + ']'
    return publishedStr


def _getBlogCitationsHtml(boxName: str,
                          postJsonObject: {},
                          translate: {}) -> str:
    """Returns blog citations as html
    """
    # show blog citations
    citationsStr = ''
    if not (boxName == 'tlblogs' or boxName == 'tlfeatures'):
        return citationsStr

    if not postJsonObject['object'].get('tag'):
        return citationsStr

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
        citationsStr = '<p><b>' + translate['Citations'] + ':</b></p>' + \
            '<ul>\n' + citationsStr + '</ul>\n'
    return citationsStr


def _boostOwnTootHtml(translate: {}) -> str:
    """The html title for announcing your own post
    """
    return '        <img loading="lazy" title="' + \
        translate['announces'] + \
        '" alt="' + translate['announces'] + \
        '" src="/icons' + \
        '/repeat_inactive.png" class="announceOrReply"/>\n'


def _announceUnattributedHtml(translate: {},
                              postJsonObject: {}) -> str:
    """Returns the html for an announce title where there
    is no attribution on the announced post
    """
    return '    <img loading="lazy" title="' + \
        translate['announces'] + '" alt="' + \
        translate['announces'] + '" src="/icons' + \
        '/repeat_inactive.png" ' + \
        'class="announceOrReply"/>\n' + \
        '      <a href="' + \
        postJsonObject['object']['id'] + \
        '" class="announceOrReply">@unattributed</a>\n'


def _announceWithoutDisplayNameHtml(translate: {},
                                    announceNickname: str,
                                    announceDomain: str,
                                    postJsonObject: {}) -> str:
    """Returns html for an announce title where there is no display name
    only a handle nick@domain
    """
    return '    <img loading="lazy" title="' + \
        translate['announces'] + '" alt="' + translate['announces'] + \
        '" src="/icons/repeat_inactive.png" ' + \
        'class="announceOrReply"/>\n' + \
        '      <a href="' + postJsonObject['object']['id'] + '" ' + \
        'class="announceOrReply">@' + \
        announceNickname + '@' + announceDomain + '</a>\n'


def _announceWithDisplayNameHtml(translate: {},
                                 postJsonObject: {},
                                 announceDisplayName: str) -> str:
    """Returns html for an announce having a display name
    """
    return '          <img loading="lazy" title="' + \
        translate['announces'] + '" alt="' + \
        translate['announces'] + '" src="/' + \
        'icons/repeat_inactive.png" ' + \
        'class="announceOrReply"/>\n' + \
        '        <a href="' + \
        postJsonObject['object']['id'] + '" ' + \
        'class="announceOrReply">' + announceDisplayName + '</a>\n'


def _getPostTitleAnnounceHtml(baseDir: str,
                              httpPrefix: str,
                              nickname: str, domain: str,
                              showRepeatIcon: bool,
                              isAnnounced: bool,
                              postJsonObject: {},
                              postActor: str,
                              translate: {},
                              enableTimingLog: bool,
                              postStartTime,
                              boxName: str,
                              personCache: {},
                              allowDownloads: bool,
                              avatarPosition: str,
                              pageNumber: int,
                              messageIdStr: str,
                              containerClassIcons: str,
                              containerClass: str) -> (str, str, str, str):
    """Returns the announce title of a post containing names of participants
    x announces y
    """
    titleStr = ''
    replyAvatarImageInPost = ''

    if postJsonObject['object'].get('attributedTo'):
        attributedTo = ''
        if isinstance(postJsonObject['object']['attributedTo'], str):
            attributedTo = postJsonObject['object']['attributedTo']

        if attributedTo.startswith(postActor):
            titleStr += _boostOwnTootHtml(translate)
        else:
            # boosting another person's post
            _logPostTiming(enableTimingLog, postStartTime, '13.2')
            announceNickname = None
            if attributedTo:
                announceNickname = getNicknameFromActor(attributedTo)
            if announceNickname:
                announceDomain, announcePort = \
                    getDomainFromActor(attributedTo)
                getPersonFromCache(baseDir, attributedTo,
                                   personCache, allowDownloads)
                announceDisplayName = \
                    getDisplayName(baseDir, attributedTo, personCache)
                if announceDisplayName:
                    _logPostTiming(enableTimingLog, postStartTime, '13.3')

                    # add any emoji to the display name
                    if ':' in announceDisplayName:
                        announceDisplayName = \
                            addEmojiToDisplayName(baseDir, httpPrefix,
                                                  nickname, domain,
                                                  announceDisplayName,
                                                  False)
                    _logPostTiming(enableTimingLog, postStartTime, '13.3.1')
                    titleStr += \
                        _announceWithDisplayNameHtml(translate,
                                                     postJsonObject,
                                                     announceDisplayName)
                    # show avatar of person replied to
                    announceActor = \
                        postJsonObject['object']['attributedTo']
                    announceAvatarUrl = \
                        getPersonAvatarUrl(baseDir, announceActor,
                                           personCache, allowDownloads)

                    _logPostTiming(enableTimingLog, postStartTime, '13.4')

                    if announceAvatarUrl:
                        idx = 'Show options for this person'
                        if '/users/news/' not in announceAvatarUrl:
                            replyAvatarImageInPost = \
                                '        ' \
                                '<div class=' + \
                                '"timeline-avatar-reply">\n' \
                                '            ' + \
                                '<a class="imageAnchor" ' + \
                                'href="/users/' + nickname + \
                                '?options=' + \
                                announceActor + ';' + \
                                str(pageNumber) + \
                                ';' + announceAvatarUrl + \
                                messageIdStr + '">' \
                                '<img loading="lazy" src="' + \
                                announceAvatarUrl + '" ' + \
                                'title="' + translate[idx] + \
                                '" alt=" "' + avatarPosition + \
                                getBrokenLinkSubstitute() + \
                                '/></a>\n    </div>\n'
                else:
                    titleStr += \
                        _announceWithoutDisplayNameHtml(translate,
                                                        announceNickname,
                                                        announceDomain,
                                                        postJsonObject)
            else:
                titleStr += \
                    _announceUnattributedHtml(translate,
                                              postJsonObject)
    else:
        titleStr += \
            _announceUnattributedHtml(translate, postJsonObject)

    return (titleStr, replyAvatarImageInPost,
            containerClassIcons, containerClass)


def _replyToYourselfHtml(translate: {}) -> str:
    """Returns html for a title which is a reply to yourself
    """
    return '    <img loading="lazy" title="' + \
        translate['replying to themselves'] + \
        '" alt="' + translate['replying to themselves'] + \
        '" src="/icons' + \
        '/reply.png" class="announceOrReply"/>\n'


def _replyToUnknownHtml(translate: {},
                        postJsonObject: {}) -> str:
    """Returns the html title for a reply to an unknown handle
    """
    return '        <img loading="lazy" title="' + \
        translate['replying to'] + '" alt="' + \
        translate['replying to'] + '" src="/icons' + \
        '/reply.png" class="announceOrReply"/>\n' + \
        '        <a href="' + \
        postJsonObject['object']['inReplyTo'] + \
        '" class="announceOrReply">@unknown</a>\n'


def _replyWithUnknownPathHtml(translate: {},
                              postJsonObject: {},
                              postDomain: str) -> str:
    """Returns html title for a reply with an unknown path
    eg. does not contain /statuses/
    """
    return '        <img loading="lazy" title="' + \
        translate['replying to'] + \
        '" alt="' + translate['replying to'] + \
        '" src="/icons/reply.png" ' + \
        'class="announceOrReply"/>\n' + \
        '        <a href="' + \
        postJsonObject['object']['inReplyTo'] + \
        '" class="announceOrReply">' + \
        postDomain + '</a>\n'


def _getReplyHtml(translate: {},
                  inReplyTo: str, replyDisplayName: str) -> str:
    """Returns html title for a reply
    """
    return '        ' + \
        '<img loading="lazy" title="' + \
        translate['replying to'] + '" alt="' + \
        translate['replying to'] + '" src="/' + \
        'icons/reply.png" ' + \
        'class="announceOrReply"/>\n' + \
        '        <a href="' + inReplyTo + \
        '" class="announceOrReply">' + \
        replyDisplayName + '</a>\n'


def _getReplyWithoutDisplayName(translate: {},
                                inReplyTo: str,
                                replyNickname: str, replyDomain: str) -> str:
    """Returns html for a reply without a display name,
    only a handle nick@domain
    """
    return '        ' + \
        '<img loading="lazy" title="' + translate['replying to'] + \
        '" alt="' + translate['replying to'] + \
        '" src="/icons/reply.png" ' + \
        'class="announceOrReply"/>\n' + '        <a href="' + \
        inReplyTo + '" class="announceOrReply">@' + \
        replyNickname + '@' + replyDomain + '</a>\n'


def _getPostTitleReplyHtml(baseDir: str,
                           httpPrefix: str,
                           nickname: str, domain: str,
                           showRepeatIcon: bool,
                           isAnnounced: bool,
                           postJsonObject: {},
                           postActor: str,
                           translate: {},
                           enableTimingLog: bool,
                           postStartTime,
                           boxName: str,
                           personCache: {},
                           allowDownloads: bool,
                           avatarPosition: str,
                           pageNumber: int,
                           messageIdStr: str,
                           containerClassIcons: str,
                           containerClass: str) -> (str, str, str, str):
    """Returns the reply title of a post containing names of participants
    x replies to y
    """
    titleStr = ''
    replyAvatarImageInPost = ''

    if not postJsonObject['object'].get('inReplyTo'):
        return (titleStr, replyAvatarImageInPost,
                containerClassIcons, containerClass)

    containerClassIcons = 'containericons darker'
    containerClass = 'container darker'
    if postJsonObject['object']['inReplyTo'].startswith(postActor):
        titleStr += _replyToYourselfHtml(translate)
        return (titleStr, replyAvatarImageInPost,
                containerClassIcons, containerClass)

    if '/statuses/' in postJsonObject['object']['inReplyTo']:
        inReplyTo = postJsonObject['object']['inReplyTo']
        replyActor = inReplyTo.split('/statuses/')[0]
        replyNickname = getNicknameFromActor(replyActor)
        if replyNickname:
            replyDomain, replyPort = \
                getDomainFromActor(replyActor)
            if replyNickname and replyDomain:
                getPersonFromCache(baseDir, replyActor,
                                   personCache,
                                   allowDownloads)
                replyDisplayName = \
                    getDisplayName(baseDir, replyActor,
                                   personCache)
                if replyDisplayName:
                    # add emoji to the display name
                    if ':' in replyDisplayName:
                        _logPostTiming(enableTimingLog, postStartTime, '13.5')

                        replyDisplayName = \
                            addEmojiToDisplayName(baseDir,
                                                  httpPrefix,
                                                  nickname,
                                                  domain,
                                                  replyDisplayName,
                                                  False)
                        _logPostTiming(enableTimingLog, postStartTime, '13.6')

                    titleStr += \
                        _getReplyHtml(translate, inReplyTo, replyDisplayName)

                    _logPostTiming(enableTimingLog, postStartTime, '13.7')

                    # show avatar of person replied to
                    replyAvatarUrl = \
                        getPersonAvatarUrl(baseDir,
                                           replyActor,
                                           personCache,
                                           allowDownloads)

                    _logPostTiming(enableTimingLog, postStartTime, '13.8')

                    if replyAvatarUrl:
                        replyAvatarImageInPost = \
                            '        <div class=' + \
                            '"timeline-avatar-reply">\n'
                        replyAvatarImageInPost += \
                            '          ' + \
                            '<a class="imageAnchor" ' + \
                            'href="/users/' + nickname + \
                            '?options=' + replyActor + \
                            ';' + str(pageNumber) + ';' + \
                            replyAvatarUrl + \
                            messageIdStr + '">\n'
                        replyAvatarImageInPost += \
                            '          ' + \
                            '<img loading="lazy" src="' + \
                            replyAvatarUrl + '" '
                        replyAvatarImageInPost += \
                            'title="' + \
                            translate['Show profile']
                        replyAvatarImageInPost += \
                            '" alt=" "' + \
                            avatarPosition + \
                            getBrokenLinkSubstitute() + \
                            '/></a>\n        </div>\n'
                else:
                    inReplyTo = \
                        postJsonObject['object']['inReplyTo']
                    titleStr += \
                        _getReplyWithoutDisplayName(translate,
                                                    inReplyTo,
                                                    replyNickname,
                                                    replyDomain)
        else:
            titleStr += \
                _replyToUnknownHtml(translate, postJsonObject)
    else:
        postDomain = \
            postJsonObject['object']['inReplyTo']
        prefixes = getProtocolPrefixes()
        for prefix in prefixes:
            postDomain = postDomain.replace(prefix, '')
        if '/' in postDomain:
            postDomain = postDomain.split('/', 1)[0]
        if postDomain:
            titleStr += \
                _replyWithUnknownPathHtml(translate,
                                          postJsonObject, postDomain)

    return (titleStr, replyAvatarImageInPost,
            containerClassIcons, containerClass)


def _getPostTitleHtml(baseDir: str,
                      httpPrefix: str,
                      nickname: str, domain: str,
                      showRepeatIcon: bool,
                      isAnnounced: bool,
                      postJsonObject: {},
                      postActor: str,
                      translate: {},
                      enableTimingLog: bool,
                      postStartTime,
                      boxName: str,
                      personCache: {},
                      allowDownloads: bool,
                      avatarPosition: str,
                      pageNumber: int,
                      messageIdStr: str,
                      containerClassIcons: str,
                      containerClass: str) -> (str, str, str, str):
    """Returns the title of a post containing names of participants
    x replies to y, x announces y, etc
    """
    titleStr = ''
    replyAvatarImageInPost = ''
    if not showRepeatIcon:
        return (titleStr, replyAvatarImageInPost,
                containerClassIcons, containerClass)

    if isAnnounced:
        return _getPostTitleAnnounceHtml(baseDir,
                                         httpPrefix,
                                         nickname, domain,
                                         showRepeatIcon,
                                         isAnnounced,
                                         postJsonObject,
                                         postActor,
                                         translate,
                                         enableTimingLog,
                                         postStartTime,
                                         boxName,
                                         personCache,
                                         allowDownloads,
                                         avatarPosition,
                                         pageNumber,
                                         messageIdStr,
                                         containerClassIcons,
                                         containerClass)

    return _getPostTitleReplyHtml(baseDir,
                                  httpPrefix,
                                  nickname, domain,
                                  showRepeatIcon,
                                  isAnnounced,
                                  postJsonObject,
                                  postActor,
                                  translate,
                                  enableTimingLog,
                                  postStartTime,
                                  boxName,
                                  personCache,
                                  allowDownloads,
                                  avatarPosition,
                                  pageNumber,
                                  messageIdStr,
                                  containerClassIcons,
                                  containerClass)


def _getFooterWithIcons(showIcons: bool,
                        containerClassIcons: str,
                        replyStr: str, announceStr: str,
                        likeStr: str, bookmarkStr: str,
                        deleteStr: str, muteStr: str, editStr: str,
                        postJsonObject: {}, publishedLink: str,
                        timeClass: str, publishedStr: str) -> str:
    """Returns the html for a post footer containing icons
    """
    if not showIcons:
        return None

    footerStr = '\n      <nav>\n'
    footerStr += '      <div class="' + containerClassIcons + '">\n'
    footerStr += replyStr + announceStr + likeStr + bookmarkStr
    footerStr += deleteStr + muteStr + editStr
    if not isNewsPost(postJsonObject):
        footerStr += '        <a href="' + publishedLink + '" class="' + \
            timeClass + '">' + publishedStr + '</a>\n'
    else:
        footerStr += '        <a href="' + \
            publishedLink.replace('/news/', '/news/statuses/') + \
            '" class="' + timeClass + '">' + publishedStr + '</a>\n'
    footerStr += '      </div>\n'
    footerStr += '      </nav>\n'
    return footerStr


def individualPostAsHtml(allowDownloads: bool,
                         recentPostsCache: {}, maxRecentPosts: int,
                         translate: {},
                         pageNumber: int, baseDir: str,
                         session, cachedWebfingers: {}, personCache: {},
                         nickname: str, domain: str, port: int,
                         postJsonObject: {},
                         avatarUrl: str, showAvatarOptions: bool,
                         allowDeletion: bool,
                         httpPrefix: str, projectVersion: str,
                         boxName: str, YTReplacementDomain: str,
                         showPublishedDateOnly: bool,
                         peertubeInstances: [],
                         allowLocalNetworkAccess: bool,
                         showRepeats=True,
                         showIcons=False,
                         manuallyApprovesFollowers=False,
                         showPublicOnly=False,
                         storeToCache=True) -> str:
    """ Shows a single post as html
    """
    if not postJsonObject:
        return ''

    # benchmark
    postStartTime = time.time()

    postActor = postJsonObject['actor']

    # ZZZzzz
    if isPersonSnoozed(baseDir, nickname, domain, postActor):
        return ''

    # if downloads of avatar images aren't enabled then we can do more
    # accurate timing of different parts of the code
    enableTimingLog = not allowDownloads

    _logPostTiming(enableTimingLog, postStartTime, '1')

    avatarPosition = ''
    messageId = ''
    if postJsonObject.get('id'):
        messageId = removeIdEnding(postJsonObject['id'])

    _logPostTiming(enableTimingLog, postStartTime, '2')

    messageIdStr = ''
    if messageId:
        messageIdStr = ';' + messageId

    domainFull = getFullDomain(domain, port)

    pageNumberParam = ''
    if pageNumber:
        pageNumberParam = '?page=' + str(pageNumber)

    # get the html post from the recent posts cache if it exists there
    postHtml = \
        _getPostFromRecentCache(session, baseDir,
                                httpPrefix, nickname, domain,
                                postJsonObject,
                                postActor,
                                personCache,
                                allowDownloads,
                                showPublicOnly,
                                storeToCache,
                                boxName,
                                avatarUrl,
                                enableTimingLog,
                                postStartTime,
                                pageNumber,
                                recentPostsCache,
                                maxRecentPosts)
    if postHtml:
        return postHtml

    _logPostTiming(enableTimingLog, postStartTime, '4')

    avatarUrl = \
        getAvatarImageUrl(session,
                          baseDir, httpPrefix,
                          postActor, personCache,
                          avatarUrl, allowDownloads)

    _logPostTiming(enableTimingLog, postStartTime, '5')

    # get the display name
    if domainFull not in postActor:
        # lookup the correct webfinger for the postActor
        postActorNickname = getNicknameFromActor(postActor)
        postActorDomain, postActorPort = getDomainFromActor(postActor)
        postActorDomainFull = getFullDomain(postActorDomain, postActorPort)
        postActorHandle = postActorNickname + '@' + postActorDomainFull
        postActorWf = \
            webfingerHandle(session, postActorHandle, httpPrefix,
                            cachedWebfingers,
                            domain, __version__)

        avatarUrl2 = None
        displayName = None
        if postActorWf:
            (inboxUrl, pubKeyId, pubKey,
             fromPersonId, sharedInbox,
             avatarUrl2, displayName) = getPersonBox(baseDir, session,
                                                     postActorWf,
                                                     personCache,
                                                     projectVersion,
                                                     httpPrefix,
                                                     nickname, domain,
                                                     'outbox', 72367)

        _logPostTiming(enableTimingLog, postStartTime, '6')

        if avatarUrl2:
            avatarUrl = avatarUrl2
        if displayName:
            # add any emoji to the display name
            if ':' in displayName:
                displayName = \
                    addEmojiToDisplayName(baseDir, httpPrefix,
                                          nickname, domain,
                                          displayName, False)

    _logPostTiming(enableTimingLog, postStartTime, '7')

    avatarLink = \
        _getAvatarImageHtml(showAvatarOptions,
                            nickname, domainFull,
                            avatarUrl, postActor,
                            translate, avatarPosition,
                            pageNumber, messageIdStr)

    avatarImageInPost = \
        '      <div class="timeline-avatar">' + avatarLink + '</div>\n'

    # don't create new html within the bookmarks timeline
    # it should already have been created for the inbox
    if boxName == 'tlbookmarks' or boxName == 'bookmarks':
        return ''

    timelinePostBookmark = removeIdEnding(postJsonObject['id'])
    timelinePostBookmark = timelinePostBookmark.replace('://', '-')
    timelinePostBookmark = timelinePostBookmark.replace('/', '-')

    # If this is the inbox timeline then don't show the repeat icon on any DMs
    showRepeatIcon = showRepeats
    isPublicRepeat = False
    showDMicon = False
    if showRepeats:
        if isDM(postJsonObject):
            showDMicon = True
            showRepeatIcon = False
        else:
            if not isPublicPost(postJsonObject):
                isPublicRepeat = True

    titleStr = ''
    galleryStr = ''
    isAnnounced = False
    if postJsonObject['type'] == 'Announce':
        postJsonAnnounce = \
            downloadAnnounce(session, baseDir, httpPrefix,
                             nickname, domain, postJsonObject,
                             projectVersion, translate,
                             YTReplacementDomain,
                             allowLocalNetworkAccess)
        if not postJsonAnnounce:
            return ''
        postJsonObject = postJsonAnnounce
        isAnnounced = True

    _logPostTiming(enableTimingLog, postStartTime, '8')

    if not isinstance(postJsonObject['object'], dict):
        return ''

    # if this post should be public then check its recipients
    if showPublicOnly:
        if not postContainsPublic(postJsonObject):
            return ''

    isModerationPost = False
    if postJsonObject['object'].get('moderationStatus'):
        isModerationPost = True
    containerClass = 'container'
    containerClassIcons = 'containericons'
    timeClass = 'time-right'
    actorNickname = getNicknameFromActor(postActor)
    if not actorNickname:
        # single user instance
        actorNickname = 'dev'
    actorDomain, actorPort = getDomainFromActor(postActor)

    displayName = getDisplayName(baseDir, postActor, personCache)
    if displayName:
        if ':' in displayName:
            displayName = \
                addEmojiToDisplayName(baseDir, httpPrefix,
                                      nickname, domain,
                                      displayName, False)
        titleStr += \
            '        <a class="imageAnchor" href="/users/' + \
            nickname + '?options=' + postActor + \
            ';' + str(pageNumber) + ';' + avatarUrl + messageIdStr + \
            '">' + displayName + '</a>\n'
    else:
        if not messageId:
            # pprint(postJsonObject)
            print('ERROR: no messageId')
        if not actorNickname:
            # pprint(postJsonObject)
            print('ERROR: no actorNickname')
        if not actorDomain:
            # pprint(postJsonObject)
            print('ERROR: no actorDomain')
        titleStr += \
            '        <a class="imageAnchor" href="/users/' + \
            nickname + '?options=' + postActor + \
            ';' + str(pageNumber) + ';' + avatarUrl + messageIdStr + \
            '">@' + actorNickname + '@' + actorDomain + '</a>\n'

    # benchmark 9
    _logPostTiming(enableTimingLog, postStartTime, '9')

    # Show a DM icon for DMs in the inbox timeline
    if showDMicon:
        titleStr = \
            titleStr + ' <img loading="lazy" src="/' + \
            'icons/dm.png" class="DMicon"/>\n'

    # check if replying is permitted
    commentsEnabled = True
    if 'commentsEnabled' in postJsonObject['object']:
        if postJsonObject['object']['commentsEnabled'] is False:
            commentsEnabled = False

    replyStr = _getReplyIconHtml(nickname, isPublicRepeat,
                                 showIcons, commentsEnabled,
                                 postJsonObject, pageNumberParam,
                                 translate)

    _logPostTiming(enableTimingLog, postStartTime, '10')

    isEvent = isEventPost(postJsonObject)

    _logPostTiming(enableTimingLog, postStartTime, '11')

    editStr = _getEditIconHtml(baseDir, nickname, domainFull,
                               postJsonObject, actorNickname,
                               translate, isEvent)

    announceStr = \
        _getAnnounceIconHtml(nickname, domainFull,
                             postJsonObject,
                             isPublicRepeat,
                             isModerationPost,
                             showRepeatIcon,
                             translate,
                             pageNumberParam,
                             timelinePostBookmark,
                             boxName)

    _logPostTiming(enableTimingLog, postStartTime, '12')

    # whether to show a like button
    hideLikeButtonFile = \
        baseDir + '/accounts/' + nickname + '@' + domain + '/.hideLikeButton'
    showLikeButton = True
    if os.path.isfile(hideLikeButtonFile):
        showLikeButton = False

    likeStr = _getLikeIconHtml(nickname, domainFull,
                               isModerationPost,
                               showLikeButton,
                               postJsonObject,
                               enableTimingLog,
                               postStartTime,
                               translate, pageNumberParam,
                               timelinePostBookmark,
                               boxName)

    _logPostTiming(enableTimingLog, postStartTime, '12.5')

    bookmarkStr = \
        _getBookmarkIconHtml(nickname, domainFull,
                             postJsonObject,
                             isModerationPost,
                             translate,
                             enableTimingLog,
                             postStartTime, boxName,
                             pageNumberParam,
                             timelinePostBookmark)

    _logPostTiming(enableTimingLog, postStartTime, '12.9')

    isMuted = postIsMuted(baseDir, nickname, domain, postJsonObject, messageId)

    _logPostTiming(enableTimingLog, postStartTime, '13')

    muteStr = \
        _getMuteIconHtml(isMuted,
                         postActor,
                         messageId,
                         nickname, domainFull,
                         allowDeletion,
                         pageNumberParam,
                         boxName,
                         timelinePostBookmark,
                         translate)

    deleteStr = \
        _getDeleteIconHtml(nickname, domainFull,
                           allowDeletion,
                           postActor,
                           messageId,
                           postJsonObject,
                           pageNumberParam,
                           translate)

    _logPostTiming(enableTimingLog, postStartTime, '13.1')

    # get the title: x replies to y, x announces y, etc
    (titleStr2,
     replyAvatarImageInPost,
     containerClassIcons,
     containerClass) = _getPostTitleHtml(baseDir,
                                         httpPrefix,
                                         nickname, domain,
                                         showRepeatIcon,
                                         isAnnounced,
                                         postJsonObject,
                                         postActor,
                                         translate,
                                         enableTimingLog,
                                         postStartTime,
                                         boxName,
                                         personCache,
                                         allowDownloads,
                                         avatarPosition,
                                         pageNumber,
                                         messageIdStr,
                                         containerClassIcons,
                                         containerClass)
    titleStr += titleStr2

    _logPostTiming(enableTimingLog, postStartTime, '14')

    attachmentStr, galleryStr = \
        getPostAttachmentsAsHtml(postJsonObject, boxName, translate,
                                 isMuted, avatarLink,
                                 replyStr, announceStr, likeStr,
                                 bookmarkStr, deleteStr, muteStr)

    publishedStr = \
        _getPublishedDateStr(postJsonObject, showPublishedDateOnly)

    _logPostTiming(enableTimingLog, postStartTime, '15')

    publishedLink = messageId
    # blog posts should have no /statuses/ in their link
    if isBlogPost(postJsonObject):
        # is this a post to the local domain?
        if '://' + domain in messageId:
            publishedLink = messageId.replace('/statuses/', '/')
    # if this is a local link then make it relative so that it works
    # on clearnet or onion address
    if domain + '/users/' in publishedLink or \
       domain + ':' + str(port) + '/users/' in publishedLink:
        publishedLink = '/users/' + publishedLink.split('/users/')[1]

    if not isNewsPost(postJsonObject):
        footerStr = '<a href="' + publishedLink + \
            '" class="' + timeClass + '">' + publishedStr + '</a>\n'
    else:
        footerStr = '<a href="' + \
            publishedLink.replace('/news/', '/news/statuses/') + \
            '" class="' + timeClass + '">' + publishedStr + '</a>\n'

    # change the background color for DMs in inbox timeline
    if showDMicon:
        containerClassIcons = 'containericons dm'
        containerClass = 'container dm'

    newFooterStr = _getFooterWithIcons(showIcons,
                                       containerClassIcons,
                                       replyStr, announceStr,
                                       likeStr, bookmarkStr,
                                       deleteStr, muteStr, editStr,
                                       postJsonObject, publishedLink,
                                       timeClass, publishedStr)
    if newFooterStr:
        footerStr = newFooterStr

    postIsSensitive = False
    if postJsonObject['object'].get('sensitive'):
        # sensitive posts should have a summary
        if postJsonObject['object'].get('summary'):
            postIsSensitive = postJsonObject['object']['sensitive']
        else:
            # add a generic summary if none is provided
            postJsonObject['object']['summary'] = translate['Sensitive']

    # add an extra line if there is a content warning,
    # for better vertical spacing on mobile
    if postIsSensitive:
        footerStr = '<br>' + footerStr

    if not postJsonObject['object'].get('summary'):
        postJsonObject['object']['summary'] = ''

    if postJsonObject['object'].get('cipherText'):
        postJsonObject['object']['content'] = \
            E2EEdecryptMessageFromDevice(postJsonObject['object'])

    if not postJsonObject['object'].get('content'):
        return ''

    isPatch = isGitPatch(baseDir, nickname, domain,
                         postJsonObject['object']['type'],
                         postJsonObject['object']['summary'],
                         postJsonObject['object']['content'])

    _logPostTiming(enableTimingLog, postStartTime, '16')

    if not isPatch:
        objectContent = \
            removeLongWords(postJsonObject['object']['content'], 40, [])
        objectContent = removeTextFormatting(objectContent)
        objectContent = \
            switchWords(baseDir, nickname, domain, objectContent)
        objectContent = htmlReplaceEmailQuote(objectContent)
        objectContent = htmlReplaceQuoteMarks(objectContent)
    else:
        objectContent = \
            postJsonObject['object']['content']

    objectContent = '<article>' + objectContent + '</article>'

    if not postIsSensitive:
        contentStr = objectContent + attachmentStr
        contentStr = addEmbeddedElements(translate, contentStr,
                                         peertubeInstances)
        contentStr = insertQuestion(baseDir, translate,
                                    nickname, domain, port,
                                    contentStr, postJsonObject,
                                    pageNumber)
    else:
        postID = 'post' + str(createPassword(8))
        contentStr = ''
        if postJsonObject['object'].get('summary'):
            cwStr = str(postJsonObject['object']['summary'])
            cwStr = \
                addEmojiToDisplayName(baseDir, httpPrefix,
                                      nickname, domain,
                                      cwStr, False)
            contentStr += \
                '<label class="cw">' + cwStr + '</label>\n '
            if isModerationPost:
                containerClass = 'container report'
        # get the content warning text
        cwContentStr = objectContent + attachmentStr
        if not isPatch:
            cwContentStr = addEmbeddedElements(translate, cwContentStr,
                                               peertubeInstances)
            cwContentStr = \
                insertQuestion(baseDir, translate, nickname, domain, port,
                               cwContentStr, postJsonObject, pageNumber)
            cwContentStr = \
                switchWords(baseDir, nickname, domain, cwContentStr)
        if not isBlogPost(postJsonObject):
            # get the content warning button
            contentStr += \
                getContentWarningButton(postID, translate, cwContentStr)
        else:
            contentStr += cwContentStr

    _logPostTiming(enableTimingLog, postStartTime, '17')

    if postJsonObject['object'].get('tag') and not isPatch:
        contentStr = \
            replaceEmojiFromTags(contentStr,
                                 postJsonObject['object']['tag'],
                                 'content')

    if isMuted:
        contentStr = ''
    else:
        if not isPatch:
            contentStr = '      <div class="message">' + \
                contentStr + \
                '      </div>\n'
        else:
            contentStr = \
                '<div class="gitpatch"><pre><code>' + contentStr + \
                '</code></pre></div>\n'

    # show blog citations
    citationsStr = \
        _getBlogCitationsHtml(boxName, postJsonObject, translate)

    postHtml = ''
    if boxName != 'tlmedia':
        postHtml = '    <div id="' + timelinePostBookmark + \
            '" class="' + containerClass + '">\n'
        postHtml += avatarImageInPost
        postHtml += '      <div class="post-title">\n' + \
            '        ' + titleStr + \
            replyAvatarImageInPost + '      </div>\n'
        postHtml += contentStr + citationsStr + footerStr + '\n'
        postHtml += '    </div>\n'
    else:
        postHtml = galleryStr

    _logPostTiming(enableTimingLog, postStartTime, '18')

    # save the created html to the recent posts cache
    if not showPublicOnly and storeToCache and \
       boxName != 'tlmedia' and boxName != 'tlbookmarks' and \
       boxName != 'bookmarks':
        _saveIndividualPostAsHtmlToCache(baseDir, nickname, domain,
                                         postJsonObject, postHtml)
        updateRecentPostsCache(recentPostsCache, maxRecentPosts,
                               postJsonObject, postHtml)

    _logPostTiming(enableTimingLog, postStartTime, '19')

    return postHtml


def htmlIndividualPost(cssCache: {},
                       recentPostsCache: {}, maxRecentPosts: int,
                       translate: {},
                       baseDir: str, session, cachedWebfingers: {},
                       personCache: {},
                       nickname: str, domain: str, port: int, authorized: bool,
                       postJsonObject: {}, httpPrefix: str,
                       projectVersion: str, likedBy: str,
                       YTReplacementDomain: str,
                       showPublishedDateOnly: bool,
                       peertubeInstances: [],
                       allowLocalNetworkAccess: bool) -> str:
    """Show an individual post as html
    """
    postStr = ''
    if likedBy:
        likedByNickname = getNicknameFromActor(likedBy)
        likedByDomain, likedByPort = getDomainFromActor(likedBy)
        likedByDomain = getFullDomain(likedByDomain, likedByPort)
        likedByHandle = likedByNickname + '@' + likedByDomain
        postStr += \
            '<p>' + translate['Liked by'] + \
            ' <a href="' + likedBy + '">@' + \
            likedByHandle + '</a>\n'

        domainFull = getFullDomain(domain, port)
        actor = '/users/' + nickname
        followStr = '  <form method="POST" ' + \
            'accept-charset="UTF-8" action="' + actor + '/searchhandle">\n'
        followStr += \
            '    <input type="hidden" name="actor" value="' + actor + '">\n'
        followStr += \
            '    <input type="hidden" name="searchtext" value="' + \
            likedByHandle + '">\n'
        if not isFollowingActor(baseDir, nickname, domainFull, likedBy):
            followStr += '    <button type="submit" class="button" ' + \
                'name="submitSearch">' + translate['Follow'] + '</button>\n'
        followStr += '    <button type="submit" class="button" ' + \
            'name="submitBack">' + translate['Go Back'] + '</button>\n'
        followStr += '  </form>\n'
        postStr += followStr + '</p>\n'

    postStr += \
        individualPostAsHtml(True, recentPostsCache, maxRecentPosts,
                             translate, None,
                             baseDir, session, cachedWebfingers, personCache,
                             nickname, domain, port, postJsonObject,
                             None, True, False,
                             httpPrefix, projectVersion, 'inbox',
                             YTReplacementDomain,
                             showPublishedDateOnly,
                             peertubeInstances,
                             allowLocalNetworkAccess,
                             False, authorized, False, False, False)
    messageId = removeIdEnding(postJsonObject['id'])

    # show the previous posts
    if isinstance(postJsonObject['object'], dict):
        while postJsonObject['object'].get('inReplyTo'):
            postFilename = \
                locatePost(baseDir, nickname, domain,
                           postJsonObject['object']['inReplyTo'])
            if not postFilename:
                break
            postJsonObject = loadJson(postFilename)
            if postJsonObject:
                postStr = \
                    individualPostAsHtml(True, recentPostsCache,
                                         maxRecentPosts,
                                         translate, None,
                                         baseDir, session, cachedWebfingers,
                                         personCache,
                                         nickname, domain, port,
                                         postJsonObject,
                                         None, True, False,
                                         httpPrefix, projectVersion, 'inbox',
                                         YTReplacementDomain,
                                         showPublishedDateOnly,
                                         peertubeInstances,
                                         allowLocalNetworkAccess,
                                         False, authorized,
                                         False, False, False) + postStr

    # show the following posts
    postFilename = locatePost(baseDir, nickname, domain, messageId)
    if postFilename:
        # is there a replies file for this post?
        repliesFilename = postFilename.replace('.json', '.replies')
        if os.path.isfile(repliesFilename):
            # get items from the replies file
            repliesJson = {
                'orderedItems': []
            }
            populateRepliesJson(baseDir, nickname, domain,
                                repliesFilename, authorized, repliesJson)
            # add items to the html output
            for item in repliesJson['orderedItems']:
                postStr += \
                    individualPostAsHtml(True, recentPostsCache,
                                         maxRecentPosts,
                                         translate, None,
                                         baseDir, session, cachedWebfingers,
                                         personCache,
                                         nickname, domain, port, item,
                                         None, True, False,
                                         httpPrefix, projectVersion, 'inbox',
                                         YTReplacementDomain,
                                         showPublishedDateOnly,
                                         peertubeInstances,
                                         allowLocalNetworkAccess,
                                         False, authorized,
                                         False, False, False)
    cssFilename = baseDir + '/epicyon-profile.css'
    if os.path.isfile(baseDir + '/epicyon.css'):
        cssFilename = baseDir + '/epicyon.css'

    instanceTitle = \
        getConfigParam(baseDir, 'instanceTitle')
    return htmlHeaderWithExternalStyle(cssFilename, instanceTitle) + \
        postStr + htmlFooter()


def htmlPostReplies(cssCache: {},
                    recentPostsCache: {}, maxRecentPosts: int,
                    translate: {}, baseDir: str,
                    session, cachedWebfingers: {}, personCache: {},
                    nickname: str, domain: str, port: int, repliesJson: {},
                    httpPrefix: str, projectVersion: str,
                    YTReplacementDomain: str,
                    showPublishedDateOnly: bool,
                    peertubeInstances: [],
                    allowLocalNetworkAccess: bool) -> str:
    """Show the replies to an individual post as html
    """
    repliesStr = ''
    if repliesJson.get('orderedItems'):
        for item in repliesJson['orderedItems']:
            repliesStr += \
                individualPostAsHtml(True, recentPostsCache,
                                     maxRecentPosts,
                                     translate, None,
                                     baseDir, session, cachedWebfingers,
                                     personCache,
                                     nickname, domain, port, item,
                                     None, True, False,
                                     httpPrefix, projectVersion, 'inbox',
                                     YTReplacementDomain,
                                     showPublishedDateOnly,
                                     peertubeInstances,
                                     allowLocalNetworkAccess,
                                     False, False, False, False, False)

    cssFilename = baseDir + '/epicyon-profile.css'
    if os.path.isfile(baseDir + '/epicyon.css'):
        cssFilename = baseDir + '/epicyon.css'

    instanceTitle = \
        getConfigParam(baseDir, 'instanceTitle')
    return htmlHeaderWithExternalStyle(cssFilename, instanceTitle) + \
        repliesStr + htmlFooter()
