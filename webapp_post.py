__filename__ = "webapp_post.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.1.0"
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
from posts import isEditor
from posts import postIsMuted
from posts import getPersonBox
from posts import isDM
from posts import downloadAnnounce
from posts import populateRepliesJson
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
from webapp_utils import getPersonAvatarUrl
from webapp_utils import updateAvatarImageCache
from webapp_utils import loadIndividualPostAsHtmlFromCache
from webapp_utils import addEmojiToDisplayName
from webapp_utils import postContainsPublic
from webapp_utils import getContentWarningButton
from webapp_utils import getPostAttachmentsAsHtml
from webapp_utils import getIconsWebPath
from webapp_utils import htmlHeaderWithExternalStyle
from webapp_utils import htmlFooter
from webapp_media import addEmbeddedElements
from webapp_question import insertQuestion
from devices import E2EEdecryptMessageFromDevice


def preparePostFromHtmlCache(postHtml: str, boxName: str,
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
    return withPageNumber


def saveIndividualPostAsHtmlToCache(baseDir: str,
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


def getPostFromRecent(session,
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

        # benchmark 2.1
        if enableTimingLog:
            timeDiff = int((time.time() - postStartTime) * 1000)
            if timeDiff > 100:
                print('TIMING INDIV ' + boxName +
                      ' 2.1 = ' + str(timeDiff))

    updateAvatarImageCache(session, baseDir, httpPrefix,
                           postActor, avatarUrl, personCache,
                           allowDownloads)

    # benchmark 2.2
    if enableTimingLog:
        timeDiff = int((time.time() - postStartTime) * 1000)
        if timeDiff > 100:
            print('TIMING INDIV ' + boxName +
                  ' 2.2 = ' + str(timeDiff))

    postHtml = \
        loadIndividualPostAsHtmlFromCache(baseDir, nickname, domain,
                                          postJsonObject)
    if not postHtml:
        return None

    postHtml = preparePostFromHtmlCache(postHtml, boxName, pageNumber)
    updateRecentPostsCache(recentPostsCache, maxRecentPosts,
                           postJsonObject, postHtml)
    # benchmark 3
    if enableTimingLog:
        timeDiff = int((time.time() - postStartTime) * 1000)
        if timeDiff > 100:
            print('TIMING INDIV ' + boxName +
                  ' 3 = ' + str(timeDiff))
    return postHtml


def getAvatarImageUrl(session,
                      baseDir: str, httpPrefix: str,
                      postActor: str, personCache: {},
                      avatarUrl: str, allowDownloads: bool) -> str:
    """Returns the avatar image url
    """
    # get the avatar image url for the post actor
    if not avatarUrl:
        avatarUrl = \
            getPersonAvatarUrl(baseDir, postActor, personCache,
                               allowDownloads)
        avatarUrl = \
            updateAvatarImageCache(session, baseDir, httpPrefix,
                                   postActor, avatarUrl, personCache,
                                   allowDownloads)
    else:
        updateAvatarImageCache(session, baseDir, httpPrefix,
                               postActor, avatarUrl, personCache,
                               allowDownloads)

    if not avatarUrl:
        avatarUrl = postActor + '/avatar.png'

    return avatarUrl


def individualPostAsHtml(allowDownloads: bool,
                         recentPostsCache: {}, maxRecentPosts: int,
                         iconsPath: str, translate: {},
                         pageNumber: int, baseDir: str,
                         session, wfRequest: {}, personCache: {},
                         nickname: str, domain: str, port: int,
                         postJsonObject: {},
                         avatarUrl: str, showAvatarOptions: bool,
                         allowDeletion: bool,
                         httpPrefix: str, projectVersion: str,
                         boxName: str, YTReplacementDomain: str,
                         showPublishedDateOnly: bool,
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

    # benchmark 1
    timeDiff = int((time.time() - postStartTime) * 1000)
    if timeDiff > 100:
        print('TIMING INDIV ' + boxName + ' 1 = ' + str(timeDiff))

    avatarPosition = ''
    messageId = ''
    if postJsonObject.get('id'):
        messageId = removeIdEnding(postJsonObject['id'])

    # benchmark 2
    timeDiff = int((time.time() - postStartTime) * 1000)
    if timeDiff > 100:
        print('TIMING INDIV ' + boxName + ' 2 = ' + str(timeDiff))

    messageIdStr = ''
    if messageId:
        messageIdStr = ';' + messageId

    fullDomain = domain
    if port:
        if port != 80 and port != 443:
            if ':' not in domain:
                fullDomain = domain + ':' + str(port)

    pageNumberParam = ''
    if pageNumber:
        pageNumberParam = '?page=' + str(pageNumber)

    # get the html post from the recent posts cache if it exists there
    postHtml = \
        getPostFromRecent(session, baseDir,
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

    # benchmark 4
    if enableTimingLog:
        timeDiff = int((time.time() - postStartTime) * 1000)
        if timeDiff > 100:
            print('TIMING INDIV ' + boxName + ' 4 = ' + str(timeDiff))

    avatarUrl = \
        getAvatarImageUrl(session,
                          baseDir, httpPrefix,
                          postActor, personCache,
                          avatarUrl, allowDownloads)

    # benchmark 5
    if enableTimingLog:
        timeDiff = int((time.time() - postStartTime) * 1000)
        if timeDiff > 100:
            print('TIMING INDIV ' + boxName + ' 5 = ' + str(timeDiff))

    if fullDomain not in postActor:
        (inboxUrl, pubKeyId, pubKey,
         fromPersonId, sharedInbox,
         avatarUrl2, displayName) = getPersonBox(baseDir, session, wfRequest,
                                                 personCache,
                                                 projectVersion, httpPrefix,
                                                 nickname, domain, 'outbox')
        # benchmark 6
        if enableTimingLog:
            timeDiff = int((time.time() - postStartTime) * 1000)
            if timeDiff > 100:
                print('TIMING INDIV ' + boxName + ' 6 = ' + str(timeDiff))

        if avatarUrl2:
            avatarUrl = avatarUrl2
        if displayName:
            if ':' in displayName:
                displayName = \
                    addEmojiToDisplayName(baseDir, httpPrefix,
                                          nickname, domain,
                                          displayName, False)

    # benchmark 7
    if enableTimingLog:
        timeDiff = int((time.time() - postStartTime) * 1000)
        if timeDiff > 100:
            print('TIMING INDIV ' + boxName + ' 7 = ' + str(timeDiff))

    avatarLink = ''
    if '/users/news/' not in avatarUrl:
        avatarLink = '        <a class="imageAnchor" href="' + postActor + '">'
        avatarLink += \
            '    <img loading="lazy" src="' + avatarUrl + '" title="' + \
            translate['Show profile'] + '" alt=" "' + avatarPosition + \
            '/></a>\n'

    if showAvatarOptions and \
       fullDomain + '/users/' + nickname not in postActor:
        if '/users/news/' not in avatarUrl:
            avatarLink = \
                '        <a class="imageAnchor" href="/users/' + \
                nickname + '?options=' + postActor + \
                ';' + str(pageNumber) + ';' + avatarUrl + messageIdStr + '">\n'
            avatarLink += \
                '        <img loading="lazy" title="' + \
                translate['Show options for this person'] + \
                '" src="' + avatarUrl + '" ' + avatarPosition + '/></a>\n'
        else:
            # don't link to the person options for the news account
            avatarLink += \
                '        <img loading="lazy" title="' + \
                translate['Show options for this person'] + \
                '" src="' + avatarUrl + '" ' + avatarPosition + '/>\n'
    avatarImageInPost = \
        '      <div class="timeline-avatar">' + avatarLink.strip() + '</div>\n'

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
                             YTReplacementDomain)
        if not postJsonAnnounce:
            return ''
        postJsonObject = postJsonAnnounce
        isAnnounced = True

    # benchmark 8
    if enableTimingLog:
        timeDiff = int((time.time() - postStartTime) * 1000)
        if timeDiff > 100:
            print('TIMING INDIV ' + boxName + ' 8 = ' + str(timeDiff))

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
    if enableTimingLog:
        timeDiff = int((time.time() - postStartTime) * 1000)
        if timeDiff > 100:
            print('TIMING INDIV ' + boxName + ' 9 = ' + str(timeDiff))

    # Show a DM icon for DMs in the inbox timeline
    if showDMicon:
        titleStr = \
            titleStr + ' <img loading="lazy" src="/' + \
            iconsPath + '/dm.png" class="DMicon"/>\n'

    replyStr = ''
    # check if replying is permitted
    commentsEnabled = True
    if 'commentsEnabled' in postJsonObject['object']:
        if postJsonObject['object']['commentsEnabled'] is False:
            commentsEnabled = False
    if showIcons and commentsEnabled:
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
        if isPublicRepeat:
            replyStr += \
                '        <a class="imageAnchor" href="/users/' + \
                nickname + '?replyto=' + replyToLink + \
                '?actor=' + postJsonObject['actor'] + \
                '" title="' + translate['Reply to this post'] + '">\n'
        else:
            if isDM(postJsonObject):
                replyStr += \
                    '        ' + \
                    '<a class="imageAnchor" href="/users/' + nickname + \
                    '?replydm=' + replyToLink + \
                    '?actor=' + postJsonObject['actor'] + \
                    '" title="' + translate['Reply to this post'] + '">\n'
            else:
                replyStr += \
                    '        ' + \
                    '<a class="imageAnchor" href="/users/' + nickname + \
                    '?replyfollowers=' + replyToLink + \
                    '?actor=' + postJsonObject['actor'] + \
                    '" title="' + translate['Reply to this post'] + '">\n'

        replyStr += \
            '        ' + \
            '<img loading="lazy" title="' + \
            translate['Reply to this post'] + '" alt="' + \
            translate['Reply to this post'] + \
            ' |" src="/' + iconsPath + '/reply.png"/></a>\n'

    # benchmark 10
    if enableTimingLog:
        timeDiff = int((time.time() - postStartTime) * 1000)
        if timeDiff > 100:
            print('TIMING INDIV ' + boxName + ' 10 = ' + str(timeDiff))

    isEvent = isEventPost(postJsonObject)

    # benchmark 11
    if enableTimingLog:
        timeDiff = int((time.time() - postStartTime) * 1000)
        if timeDiff > 100:
            print('TIMING INDIV ' + boxName + ' 11 = ' + str(timeDiff))

    editStr = ''
    if (postJsonObject['actor'].endswith(fullDomain + '/users/' + nickname) or
        (isEditor(baseDir, nickname) and
         postJsonObject['actor'].endswith(fullDomain + '/users/news'))):
        if '/statuses/' in postJsonObject['object']['id']:
            if isBlogPost(postJsonObject):
                blogPostId = postJsonObject['object']['id']
                if not isNewsPost(postJsonObject):
                    editStr += \
                        '        ' + \
                        '<a class="imageAnchor" href="/users/' + \
                        nickname + \
                        '/tlblogs?editblogpost=' + \
                        blogPostId.split('/statuses/')[1] + \
                        '?actor=' + actorNickname + \
                        '" title="' + translate['Edit blog post'] + '">' + \
                        '<img loading="lazy" title="' + \
                        translate['Edit blog post'] + '" alt="' + \
                        translate['Edit blog post'] + \
                        ' |" src="/' + iconsPath + '/edit.png"/></a>\n'
                else:
                    editStr += \
                        '        ' + \
                        '<a class="imageAnchor" href="/users/' + \
                        nickname + '/editnewspost=' + \
                        blogPostId.split('/statuses/')[1] + \
                        '?actor=' + actorNickname + \
                        '" title="' + translate['Edit blog post'] + '">' + \
                        '<img loading="lazy" title="' + \
                        translate['Edit blog post'] + '" alt="' + \
                        translate['Edit blog post'] + \
                        ' |" src="/' + iconsPath + '/edit.png"/></a>\n'
            elif isEvent:
                eventPostId = postJsonObject['object']['id']
                editStr += \
                    '        ' + \
                    '<a class="imageAnchor" href="/users/' + nickname + \
                    '/tlblogs?editeventpost=' + \
                    eventPostId.split('/statuses/')[1] + \
                    '?actor=' + actorNickname + \
                    '" title="' + translate['Edit event'] + '">' + \
                    '<img loading="lazy" title="' + \
                    translate['Edit event'] + '" alt="' + \
                    translate['Edit event'] + \
                    ' |" src="/' + iconsPath + '/edit.png"/></a>\n'

    announceStr = ''
    if not isModerationPost and showRepeatIcon:
        # don't allow announce/repeat of your own posts
        announceIcon = 'repeat_inactive.png'
        announceLink = 'repeat'
        if not isPublicRepeat:
            announceLink = 'repeatprivate'
        announceTitle = translate['Repeat this post']
        if announcedByPerson(postJsonObject, nickname, fullDomain):
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
            ' |" src="/' + iconsPath + '/' + announceIcon + '"/></a>\n'

    # benchmark 12
    if enableTimingLog:
        timeDiff = int((time.time() - postStartTime) * 1000)
        if timeDiff > 100:
            print('TIMING INDIV ' + boxName + ' 12 = ' + str(timeDiff))

    # whether to show a like button
    hideLikeButtonFile = \
        baseDir + '/accounts/' + nickname + '@' + domain + '/.hideLikeButton'
    showLikeButton = True
    if os.path.isfile(hideLikeButtonFile):
        showLikeButton = False

    likeStr = ''
    if not isModerationPost and showLikeButton:
        likeIcon = 'like_inactive.png'
        likeLink = 'like'
        likeTitle = translate['Like this post']
        likeCount = noOfLikes(postJsonObject)

        # benchmark 12.1
        if enableTimingLog:
            timeDiff = int((time.time() - postStartTime) * 1000)
            if timeDiff > 100:
                print('TIMING INDIV ' + boxName + ' 12.1 = ' + str(timeDiff))

        likeCountStr = ''
        if likeCount > 0:
            if likeCount <= 10:
                likeCountStr = ' (' + str(likeCount) + ')'
            else:
                likeCountStr = ' (10+)'
            if likedByPerson(postJsonObject, nickname, fullDomain):
                if likeCount == 1:
                    # liked by the reader only
                    likeCountStr = ''
                likeIcon = 'like.png'
                likeLink = 'unlike'
                likeTitle = translate['Undo the like']

        # benchmark 12.2
        if enableTimingLog:
            timeDiff = int((time.time() - postStartTime) * 1000)
            if timeDiff > 100:
                print('TIMING INDIV ' + boxName + ' 12.2 = ' + str(timeDiff))

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
            ' |" src="/' + iconsPath + '/' + likeIcon + '"/></a>\n'

    # benchmark 12.5
    if enableTimingLog:
        timeDiff = int((time.time() - postStartTime) * 1000)
        if timeDiff > 100:
            print('TIMING INDIV ' + boxName + ' 12.5 = ' + str(timeDiff))

    bookmarkStr = ''
    if not isModerationPost:
        bookmarkIcon = 'bookmark_inactive.png'
        bookmarkLink = 'bookmark'
        bookmarkTitle = translate['Bookmark this post']
        if bookmarkedByPerson(postJsonObject, nickname, fullDomain):
            bookmarkIcon = 'bookmark.png'
            bookmarkLink = 'unbookmark'
            bookmarkTitle = translate['Undo the bookmark']
        # benchmark 12.6
        if enableTimingLog:
            timeDiff = int((time.time() - postStartTime) * 1000)
            if timeDiff > 100:
                print('TIMING INDIV ' + boxName + ' 12.6 = ' + str(timeDiff))
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
            bookmarkTitle + ' |" src="/' + iconsPath + \
            '/' + bookmarkIcon + '"/></a>\n'

    # benchmark 12.9
    if enableTimingLog:
        timeDiff = int((time.time() - postStartTime) * 1000)
        if timeDiff > 100:
            print('TIMING INDIV ' + boxName + ' 12.9 = ' + str(timeDiff))

    isMuted = postIsMuted(baseDir, nickname, domain, postJsonObject, messageId)

    # benchmark 13
    if enableTimingLog:
        timeDiff = int((time.time() - postStartTime) * 1000)
        if timeDiff > 100:
            print('TIMING INDIV ' + boxName + ' 13 = ' + str(timeDiff))

    deleteStr = ''
    muteStr = ''
    if (allowDeletion or
        ('/' + fullDomain + '/' in postActor and
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
                    '" src="/' + iconsPath + '/delete.png"/></a>\n'
    else:
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
                '" src="/' + iconsPath + '/mute.png"/></a>\n'
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
                '" src="/' + iconsPath+'/unmute.png"/></a>\n'

    # benchmark 13.1
    if enableTimingLog:
        timeDiff = int((time.time() - postStartTime) * 1000)
        if timeDiff > 100:
            print('TIMING INDIV ' + boxName + ' 13.1 = ' + str(timeDiff))

    replyAvatarImageInPost = ''
    if showRepeatIcon:
        if isAnnounced:
            if postJsonObject['object'].get('attributedTo'):
                attributedTo = ''
                if isinstance(postJsonObject['object']['attributedTo'], str):
                    attributedTo = postJsonObject['object']['attributedTo']
                if attributedTo.startswith(postActor):
                    titleStr += \
                        '        <img loading="lazy" title="' + \
                        translate['announces'] + \
                        '" alt="' + translate['announces'] + \
                        '" src="/' + iconsPath + \
                        '/repeat_inactive.png" class="announceOrReply"/>\n'
                else:
                    # benchmark 13.2
                    if enableTimingLog:
                        timeDiff = int((time.time() - postStartTime) * 1000)
                        if timeDiff > 100:
                            print('TIMING INDIV ' + boxName +
                                  ' 13.2 = ' + str(timeDiff))
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
                            # benchmark 13.3
                            if enableTimingLog:
                                timeDiff = \
                                    int((time.time() - postStartTime) * 1000)
                                if timeDiff > 100:
                                    print('TIMING INDIV ' + boxName +
                                          ' 13.3 = ' + str(timeDiff))

                            if ':' in announceDisplayName:
                                announceDisplayName = \
                                    addEmojiToDisplayName(baseDir, httpPrefix,
                                                          nickname, domain,
                                                          announceDisplayName,
                                                          False)
                            # benchmark 13.3.1
                            if enableTimingLog:
                                timeDiff = \
                                    int((time.time() - postStartTime) * 1000)
                                if timeDiff > 100:
                                    print('TIMING INDIV ' + boxName +
                                          ' 13.3.1 = ' + str(timeDiff))

                            titleStr += \
                                '          ' + \
                                '<img loading="lazy" title="' + \
                                translate['announces'] + '" alt="' + \
                                translate['announces'] + '" src="/' + \
                                iconsPath + '/repeat_inactive.png" ' + \
                                'class="announceOrReply"/>\n' + \
                                '        <a href="' + \
                                postJsonObject['object']['id'] + '" ' + \
                                'class="announceOrReply">' + \
                                announceDisplayName + '</a>\n'
                            # show avatar of person replied to
                            announceActor = \
                                postJsonObject['object']['attributedTo']
                            announceAvatarUrl = \
                                getPersonAvatarUrl(baseDir, announceActor,
                                                   personCache, allowDownloads)

                            # benchmark 13.4
                            if enableTimingLog:
                                timeDiff = \
                                    int((time.time() - postStartTime) * 1000)
                                if timeDiff > 100:
                                    print('TIMING INDIV ' + boxName +
                                          ' 13.4 = ' + str(timeDiff))

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
                                        announceAvatarUrl + '" ' \
                                        'title="' + translate[idx] + \
                                        '" alt=" "' + avatarPosition + \
                                        '/></a>\n    </div>\n'
                        else:
                            titleStr += \
                                '    <img loading="lazy" title="' + \
                                translate['announces'] + \
                                '" alt="' + translate['announces'] + \
                                '" src="/' + iconsPath + \
                                '/repeat_inactive.png" ' + \
                                'class="announceOrReply"/>\n' + \
                                '      <a href="' + \
                                postJsonObject['object']['id'] + '" ' + \
                                'class="announceOrReply">@' + \
                                announceNickname + '@' + \
                                announceDomain + '</a>\n'
                    else:
                        titleStr += \
                            '    <img loading="lazy" title="' + \
                            translate['announces'] + '" alt="' + \
                            translate['announces'] + '" src="/' + iconsPath + \
                            '/repeat_inactive.png" ' + \
                            'class="announceOrReply"/>\n' + \
                            '      <a href="' + \
                            postJsonObject['object']['id'] + \
                            '" class="announceOrReply">@unattributed</a>\n'
            else:
                titleStr += \
                    '    ' + \
                    '<img loading="lazy" title="' + translate['announces'] + \
                    '" alt="' + translate['announces'] + \
                    '" src="/' + iconsPath + \
                    '/repeat_inactive.png" ' + \
                    'class="announceOrReply"/>\n' + \
                    '      <a href="' + \
                    postJsonObject['object']['id'] + '" ' + \
                    'class="announceOrReply">@unattributed</a>\n'
        else:
            if postJsonObject['object'].get('inReplyTo'):
                containerClassIcons = 'containericons darker'
                containerClass = 'container darker'
                if postJsonObject['object']['inReplyTo'].startswith(postActor):
                    titleStr += \
                        '    <img loading="lazy" title="' + \
                        translate['replying to themselves'] + \
                        '" alt="' + translate['replying to themselves'] + \
                        '" src="/' + iconsPath + \
                        '/reply.png" class="announceOrReply"/>\n'
                else:
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
                                    if ':' in replyDisplayName:
                                        # benchmark 13.5
                                        if enableTimingLog:
                                            timeDiff = \
                                                int((time.time() -
                                                     postStartTime) * 1000)
                                            if timeDiff > 100:
                                                print('TIMING INDIV ' +
                                                      boxName + ' 13.5 = ' +
                                                      str(timeDiff))
                                        repDisp = replyDisplayName
                                        replyDisplayName = \
                                            addEmojiToDisplayName(baseDir,
                                                                  httpPrefix,
                                                                  nickname,
                                                                  domain,
                                                                  repDisp,
                                                                  False)
                                        # benchmark 13.6
                                        if enableTimingLog:
                                            timeDiff = \
                                                int((time.time() -
                                                     postStartTime) * 1000)
                                            if timeDiff > 100:
                                                print('TIMING INDIV ' +
                                                      boxName + ' 13.6 = ' +
                                                      str(timeDiff))
                                    titleStr += \
                                        '        ' + \
                                        '<img loading="lazy" title="' + \
                                        translate['replying to'] + \
                                        '" alt="' + \
                                        translate['replying to'] + \
                                        '" src="/' + \
                                        iconsPath + '/reply.png" ' + \
                                        'class="announceOrReply"/>\n' + \
                                        '        ' + \
                                        '<a href="' + inReplyTo + \
                                        '" class="announceOrReply">' + \
                                        replyDisplayName + '</a>\n'

                                    # benchmark 13.7
                                    if enableTimingLog:
                                        timeDiff = int((time.time() -
                                                        postStartTime) * 1000)
                                        if timeDiff > 100:
                                            print('TIMING INDIV ' + boxName +
                                                  ' 13.7 = ' + str(timeDiff))

                                    # show avatar of person replied to
                                    replyAvatarUrl = \
                                        getPersonAvatarUrl(baseDir,
                                                           replyActor,
                                                           personCache,
                                                           allowDownloads)

                                    # benchmark 13.8
                                    if enableTimingLog:
                                        timeDiff = int((time.time() -
                                                        postStartTime) * 1000)
                                        if timeDiff > 100:
                                            print('TIMING INDIV ' + boxName +
                                                  ' 13.8 = ' + str(timeDiff))

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
                                            avatarPosition + '/></a>\n' + \
                                            '        </div>\n'
                                else:
                                    inReplyTo = \
                                        postJsonObject['object']['inReplyTo']
                                    titleStr += \
                                        '        ' + \
                                        '<img loading="lazy" title="' + \
                                        translate['replying to'] + \
                                        '" alt="' + \
                                        translate['replying to'] + \
                                        '" src="/' + \
                                        iconsPath + '/reply.png" ' + \
                                        'class="announceOrReply"/>\n' + \
                                        '        <a href="' + \
                                        inReplyTo + '" ' + \
                                        'class="announceOrReply">@' + \
                                        replyNickname + '@' + \
                                        replyDomain + '</a>\n'
                        else:
                            titleStr += \
                                '        <img loading="lazy" title="' + \
                                translate['replying to'] + \
                                '" alt="' + \
                                translate['replying to'] + \
                                '" src="/' + \
                                iconsPath + \
                                '/reply.png" class="announceOrReply"/>\n' + \
                                '        <a href="' + \
                                postJsonObject['object']['inReplyTo'] + \
                                '" class="announceOrReply">@unknown</a>\n'
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
                                '        <img loading="lazy" title="' + \
                                translate['replying to'] + \
                                '" alt="' + translate['replying to'] + \
                                '" src="/' + \
                                iconsPath + '/reply.png" ' + \
                                'class="announceOrReply"/>\n' + \
                                '        <a href="' + \
                                postJsonObject['object']['inReplyTo'] + \
                                '" class="announceOrReply">' + \
                                postDomain + '</a>\n'

    # benchmark 14
    if enableTimingLog:
        timeDiff = int((time.time() - postStartTime) * 1000)
        if timeDiff > 100:
            print('TIMING INDIV ' + boxName + ' 14 = ' + str(timeDiff))

    attachmentStr, galleryStr = \
        getPostAttachmentsAsHtml(postJsonObject, boxName, translate,
                                 isMuted, avatarLink.strip(),
                                 replyStr, announceStr, likeStr,
                                 bookmarkStr, deleteStr, muteStr)

    publishedStr = ''
    if postJsonObject['object'].get('published'):
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

    # benchmark 15
    if enableTimingLog:
        timeDiff = int((time.time() - postStartTime) * 1000)
        if timeDiff > 100:
            print('TIMING INDIV ' + boxName + ' 15 = ' + str(timeDiff))

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

    if showIcons:
        footerStr = '\n      <div class="' + containerClassIcons + '">\n'
        footerStr += replyStr + announceStr + likeStr + bookmarkStr + \
            deleteStr + muteStr + editStr
        if not isNewsPost(postJsonObject):
            footerStr += '        <a href="' + publishedLink + '" class="' + \
                timeClass + '">' + publishedStr + '</a>\n'
        else:
            footerStr += '        <a href="' + \
                publishedLink.replace('/news/', '/news/statuses/') + \
                '" class="' + \
                timeClass + '">' + publishedStr + '</a>\n'
        footerStr += '      </div>\n'

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

    # benchmark 16
    if enableTimingLog:
        timeDiff = int((time.time() - postStartTime) * 1000)
        if timeDiff > 100:
            print('TIMING INDIV ' + boxName + ' 16 = ' + str(timeDiff))

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

    if not postIsSensitive:
        contentStr = objectContent + attachmentStr
        contentStr = addEmbeddedElements(translate, contentStr)
        contentStr = insertQuestion(baseDir, translate,
                                    nickname, domain, port,
                                    contentStr, postJsonObject,
                                    pageNumber)
    else:
        postID = 'post' + str(createPassword(8))
        contentStr = ''
        if postJsonObject['object'].get('summary'):
            contentStr += \
                '<b>' + str(postJsonObject['object']['summary']) + '</b>\n '
            if isModerationPost:
                containerClass = 'container report'
        # get the content warning text
        cwContentStr = objectContent + attachmentStr
        if not isPatch:
            cwContentStr = addEmbeddedElements(translate, cwContentStr)
            cwContentStr = \
                insertQuestion(baseDir, translate, nickname, domain, port,
                               cwContentStr, postJsonObject, pageNumber)
        if not isBlogPost(postJsonObject):
            # get the content warning button
            contentStr += \
                getContentWarningButton(postID, translate, cwContentStr)
        else:
            contentStr += cwContentStr

    # benchmark 17
    if enableTimingLog:
        timeDiff = int((time.time() - postStartTime) * 1000)
        if timeDiff > 100:
            print('TIMING INDIV ' + boxName + ' 17 = ' + str(timeDiff))

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
    citationsStr = ''
    if boxName == 'tlblogs' or boxName == 'tlfeatures':
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

    # benchmark 18
    if enableTimingLog:
        timeDiff = int((time.time() - postStartTime) * 1000)
        if timeDiff > 100:
            print('TIMING INDIV ' + boxName + ' 18 = ' + str(timeDiff))

    if not showPublicOnly and storeToCache and \
       boxName != 'tlmedia' and boxName != 'tlbookmarks' and \
       boxName != 'bookmarks':
        saveIndividualPostAsHtmlToCache(baseDir, nickname, domain,
                                        postJsonObject, postHtml)
        updateRecentPostsCache(recentPostsCache, maxRecentPosts,
                               postJsonObject, postHtml)

    # benchmark 19
    if enableTimingLog:
        timeDiff = int((time.time() - postStartTime) * 1000)
        if timeDiff > 100:
            print('TIMING INDIV ' + boxName + ' 19 = ' + str(timeDiff))

    return postHtml


def htmlIndividualPost(cssCache: {},
                       recentPostsCache: {}, maxRecentPosts: int,
                       translate: {},
                       baseDir: str, session, wfRequest: {}, personCache: {},
                       nickname: str, domain: str, port: int, authorized: bool,
                       postJsonObject: {}, httpPrefix: str,
                       projectVersion: str, likedBy: str,
                       YTReplacementDomain: str,
                       showPublishedDateOnly: bool) -> str:
    """Show an individual post as html
    """
    iconsPath = getIconsWebPath(baseDir)
    postStr = ''
    if likedBy:
        likedByNickname = getNicknameFromActor(likedBy)
        likedByDomain, likedByPort = getDomainFromActor(likedBy)
        if likedByPort:
            if likedByPort != 80 and likedByPort != 443:
                likedByDomain += ':' + str(likedByPort)
        likedByHandle = likedByNickname + '@' + likedByDomain
        postStr += \
            '<p>' + translate['Liked by'] + \
            ' <a href="' + likedBy + '">@' + \
            likedByHandle + '</a>\n'

        domainFull = domain
        if port:
            if port != 80 and port != 443:
                domainFull = domain + ':' + str(port)
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
                             iconsPath, translate, None,
                             baseDir, session, wfRequest, personCache,
                             nickname, domain, port, postJsonObject,
                             None, True, False,
                             httpPrefix, projectVersion, 'inbox',
                             YTReplacementDomain,
                             showPublishedDateOnly,
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
                                         iconsPath, translate, None,
                                         baseDir, session, wfRequest,
                                         personCache,
                                         nickname, domain, port,
                                         postJsonObject,
                                         None, True, False,
                                         httpPrefix, projectVersion, 'inbox',
                                         YTReplacementDomain,
                                         showPublishedDateOnly,
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
                                         iconsPath, translate, None,
                                         baseDir, session, wfRequest,
                                         personCache,
                                         nickname, domain, port, item,
                                         None, True, False,
                                         httpPrefix, projectVersion, 'inbox',
                                         YTReplacementDomain,
                                         showPublishedDateOnly,
                                         False, authorized,
                                         False, False, False)
    cssFilename = baseDir + '/epicyon-profile.css'
    if os.path.isfile(baseDir + '/epicyon.css'):
        cssFilename = baseDir + '/epicyon.css'

    return htmlHeaderWithExternalStyle(cssFilename) + postStr + htmlFooter()


def htmlPostReplies(cssCache: {},
                    recentPostsCache: {}, maxRecentPosts: int,
                    translate: {}, baseDir: str,
                    session, wfRequest: {}, personCache: {},
                    nickname: str, domain: str, port: int, repliesJson: {},
                    httpPrefix: str, projectVersion: str,
                    YTReplacementDomain: str,
                    showPublishedDateOnly: bool) -> str:
    """Show the replies to an individual post as html
    """
    iconsPath = getIconsWebPath(baseDir)
    repliesStr = ''
    if repliesJson.get('orderedItems'):
        for item in repliesJson['orderedItems']:
            repliesStr += \
                individualPostAsHtml(True, recentPostsCache,
                                     maxRecentPosts,
                                     iconsPath, translate, None,
                                     baseDir, session, wfRequest, personCache,
                                     nickname, domain, port, item,
                                     None, True, False,
                                     httpPrefix, projectVersion, 'inbox',
                                     YTReplacementDomain,
                                     showPublishedDateOnly,
                                     False, False, False, False, False)

    cssFilename = baseDir + '/epicyon-profile.css'
    if os.path.isfile(baseDir + '/epicyon.css'):
        cssFilename = baseDir + '/epicyon.css'

    return htmlHeaderWithExternalStyle(cssFilename) + repliesStr + htmlFooter()
