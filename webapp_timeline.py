__filename__ = "webapp_timeline.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import os
import time
from utils import getConfigParam
from utils import getFullDomain
from utils import isEditor
from utils import removeIdEnding
from follow import followerApprovalActive
from person import isPersonSnoozed
from webapp_utils import htmlPostSeparator
from webapp_utils import getBannerFile
from webapp_utils import htmlHeaderWithExternalStyle
from webapp_utils import htmlFooter
from webapp_utils import sharesTimelineJson
from webapp_utils import htmlHighlightLabel
from webapp_post import preparePostFromHtmlCache
from webapp_post import individualPostAsHtml
from webapp_column_left import getLeftColumnContent
from webapp_column_right import getRightColumnContent
from webapp_headerbuttons import headerButtonsTimeline
from posts import isModerator


def _logTimelineTiming(enableTimingLog: bool, timelineStartTime,
                       boxName: str, debugId: str) -> None:
    """Create a log of timings for performance tuning
    """
    if not enableTimingLog:
        return
    timeDiff = int((time.time() - timelineStartTime) * 1000)
    if timeDiff > 100:
        print('TIMELINE TIMING ' +
              boxName + ' ' + debugId + ' = ' + str(timeDiff))


def htmlTimeline(cssCache: {}, defaultTimeline: str,
                 recentPostsCache: {}, maxRecentPosts: int,
                 translate: {}, pageNumber: int,
                 itemsPerPage: int, session, baseDir: str,
                 cachedWebfingers: {}, personCache: {},
                 nickname: str, domain: str, port: int, timelineJson: {},
                 boxName: str, allowDeletion: bool,
                 httpPrefix: str, projectVersion: str,
                 manuallyApproveFollowers: bool,
                 minimal: bool,
                 YTReplacementDomain: str,
                 showPublishedDateOnly: bool,
                 newswire: {}, moderator: bool,
                 editor: bool,
                 positiveVoting: bool,
                 showPublishAsIcon: bool,
                 fullWidthTimelineButtonHeader: bool,
                 iconsAsButtons: bool,
                 rssIconAtTop: bool,
                 publishButtonAtTop: bool,
                 authorized: bool,
                 moderationActionStr: str,
                 theme: str,
                 peertubeInstances: [],
                 allowLocalNetworkAccess: bool) -> str:
    """Show the timeline as html
    """
    enableTimingLog = False

    timelineStartTime = time.time()

    accountDir = baseDir + '/accounts/' + nickname + '@' + domain

    # should the calendar icon be highlighted?
    newCalendarEvent = False
    calendarImage = 'calendar.png'
    calendarPath = '/calendar'
    calendarFile = accountDir + '/.newCalendar'
    if os.path.isfile(calendarFile):
        newCalendarEvent = True
        calendarImage = 'calendar_notify.png'
        with open(calendarFile, 'r') as calfile:
            calendarPath = calfile.read().replace('##sent##', '')
            calendarPath = calendarPath.replace('\n', '').replace('\r', '')

    # should the DM button be highlighted?
    newDM = False
    dmFile = accountDir + '/.newDM'
    if os.path.isfile(dmFile):
        newDM = True
        if boxName == 'dm':
            os.remove(dmFile)

    # should the Replies button be highlighted?
    newReply = False
    replyFile = accountDir + '/.newReply'
    if os.path.isfile(replyFile):
        newReply = True
        if boxName == 'tlreplies':
            os.remove(replyFile)

    # should the Shares button be highlighted?
    newShare = False
    newShareFile = accountDir + '/.newShare'
    if os.path.isfile(newShareFile):
        newShare = True
        if boxName == 'tlshares':
            os.remove(newShareFile)

    # should the Moderation/reports button be highlighted?
    newReport = False
    newReportFile = accountDir + '/.newReport'
    if os.path.isfile(newReportFile):
        newReport = True
        if boxName == 'moderation':
            os.remove(newReportFile)

    separatorStr = ''
    if boxName != 'tlmedia':
        separatorStr = htmlPostSeparator(baseDir, None)

    # the css filename
    cssFilename = baseDir + '/epicyon-profile.css'
    if os.path.isfile(baseDir + '/epicyon.css'):
        cssFilename = baseDir + '/epicyon.css'

    # filename of the banner shown at the top
    bannerFile, bannerFilename = \
        getBannerFile(baseDir, nickname, domain, theme)

    _logTimelineTiming(enableTimingLog, timelineStartTime, boxName, '1')

    # is the user a moderator?
    if not moderator:
        moderator = isModerator(baseDir, nickname)

    # is the user a site editor?
    if not editor:
        editor = isEditor(baseDir, nickname)

    _logTimelineTiming(enableTimingLog, timelineStartTime, boxName, '2')

    # the appearance of buttons - highlighted or not
    inboxButton = 'button'
    blogsButton = 'button'
    featuresButton = 'button'
    newsButton = 'button'
    dmButton = 'button'
    if newDM:
        dmButton = 'buttonhighlighted'
    repliesButton = 'button'
    if newReply:
        repliesButton = 'buttonhighlighted'
    mediaButton = 'button'
    bookmarksButton = 'button'
    eventsButton = 'button'
    sentButton = 'button'
    sharesButton = 'button'
    if newShare:
        sharesButton = 'buttonhighlighted'
    moderationButton = 'button'
    if newReport:
        moderationButton = 'buttonhighlighted'
    if boxName == 'inbox':
        inboxButton = 'buttonselected'
    elif boxName == 'tlblogs':
        blogsButton = 'buttonselected'
    elif boxName == 'tlfeatures':
        featuresButton = 'buttonselected'
    elif boxName == 'tlnews':
        newsButton = 'buttonselected'
    elif boxName == 'dm':
        dmButton = 'buttonselected'
        if newDM:
            dmButton = 'buttonselectedhighlighted'
    elif boxName == 'tlreplies':
        repliesButton = 'buttonselected'
        if newReply:
            repliesButton = 'buttonselectedhighlighted'
    elif boxName == 'tlmedia':
        mediaButton = 'buttonselected'
    elif boxName == 'outbox':
        sentButton = 'buttonselected'
    elif boxName == 'moderation':
        moderationButton = 'buttonselected'
        if newReport:
            moderationButton = 'buttonselectedhighlighted'
    elif boxName == 'tlshares':
        sharesButton = 'buttonselected'
        if newShare:
            sharesButton = 'buttonselectedhighlighted'
    elif boxName == 'tlbookmarks' or boxName == 'bookmarks':
        bookmarksButton = 'buttonselected'
    elif boxName == 'tlevents':
        eventsButton = 'buttonselected'

    # get the full domain, including any port number
    fullDomain = getFullDomain(domain, port)

    usersPath = '/users/' + nickname
    actor = httpPrefix + '://' + fullDomain + usersPath

    showIndividualPostIcons = True

    # show an icon for new follow approvals
    followApprovals = ''
    followRequestsFilename = \
        baseDir + '/accounts/' + \
        nickname + '@' + domain + '/followrequests.txt'
    if os.path.isfile(followRequestsFilename):
        with open(followRequestsFilename, 'r') as f:
            for line in f:
                if len(line) > 0:
                    # show follow approvals icon
                    followApprovals = \
                        '<a href="' + usersPath + \
                        '/followers#buttonheader">' + \
                        '<img loading="lazy" ' + \
                        'class="timelineicon" alt="' + \
                        translate['Approve follow requests'] + \
                        '" title="' + translate['Approve follow requests'] + \
                        '" src="/icons/person.png"/></a>\n'
                    break

    _logTimelineTiming(enableTimingLog, timelineStartTime, boxName, '3')

    # moderation / reports button
    moderationButtonStr = ''
    if moderator and not minimal:
        moderationButtonStr = \
            '<a href="' + usersPath + \
            '/moderation"><button class="' + \
            moderationButton + '"><span>' + \
            htmlHighlightLabel(translate['Mod'], newReport) + \
            ' </span></button></a>'

    # shares, bookmarks and events buttons
    sharesButtonStr = ''
    bookmarksButtonStr = ''
    eventsButtonStr = ''
    if not minimal:
        sharesButtonStr = \
            '<a href="' + usersPath + '/tlshares"><button class="' + \
            sharesButton + '"><span>' + \
            htmlHighlightLabel(translate['Shares'], newShare) + \
            '</span></button></a>'

        bookmarksButtonStr = \
            '<a href="' + usersPath + '/tlbookmarks"><button class="' + \
            bookmarksButton + '"><span>' + translate['Bookmarks'] + \
            '</span></button></a>'

        eventsButtonStr = \
            '<a href="' + usersPath + '/tlevents"><button class="' + \
            eventsButton + '"><span>' + translate['Events'] + \
            '</span></button></a>'

    instanceTitle = \
        getConfigParam(baseDir, 'instanceTitle')
    tlStr = htmlHeaderWithExternalStyle(cssFilename, instanceTitle)

    _logTimelineTiming(enableTimingLog, timelineStartTime, boxName, '4')

    # if this is a news instance and we are viewing the news timeline
    newsHeader = False
    if defaultTimeline == 'tlfeatures' and boxName == 'tlfeatures':
        newsHeader = True

    newPostButtonStr = ''
    # start of headericons div
    if not newsHeader:
        if not iconsAsButtons:
            newPostButtonStr += '<div class="headericons">'

    # what screen to go to when a new post is created
    if boxName == 'dm':
        if not iconsAsButtons:
            newPostButtonStr += \
                '<a class="imageAnchor" href="' + usersPath + \
                '/newdm"><img loading="lazy" src="/' + \
                'icons/newpost.png" title="' + \
                translate['Create a new DM'] + \
                '" alt="| ' + translate['Create a new DM'] + \
                '" class="timelineicon"/></a>\n'
        else:
            newPostButtonStr += \
                '<a href="' + usersPath + '/newdm">' + \
                '<button class="button"><span>' + \
                translate['Post'] + ' </span></button></a>'
    elif (boxName == 'tlblogs' or
          boxName == 'tlnews' or
          boxName == 'tlfeatures'):
        if not iconsAsButtons:
            newPostButtonStr += \
                '<a class="imageAnchor" href="' + usersPath + \
                '/newblog"><img loading="lazy" src="/' + \
                'icons/newpost.png" title="' + \
                translate['Create a new post'] + '" alt="| ' + \
                translate['Create a new post'] + \
                '" class="timelineicon"/></a>\n'
        else:
            newPostButtonStr += \
                '<a href="' + usersPath + '/newblog">' + \
                '<button class="button"><span>' + \
                translate['Post'] + '</span></button></a>'
    elif boxName == 'tlevents':
        if not iconsAsButtons:
            newPostButtonStr += \
                '<a class="imageAnchor" href="' + usersPath + \
                '/newevent"><img loading="lazy" src="/' + \
                'icons/newpost.png" title="' + \
                translate['Create a new event'] + '" alt="| ' + \
                translate['Create a new event'] + \
                '" class="timelineicon"/></a>\n'
        else:
            newPostButtonStr += \
                '<a href="' + usersPath + '/newevent">' + \
                '<button class="button"><span>' + \
                translate['Post'] + '</span></button></a>'
    elif boxName == 'tlshares':
        if not iconsAsButtons:
            newPostButtonStr += \
                '<a class="imageAnchor" href="' + usersPath + \
                '/newshare"><img loading="lazy" src="/' + \
                'icons/newpost.png" title="' + \
                translate['Create a new shared item'] + '" alt="| ' + \
                translate['Create a new shared item'] + \
                '" class="timelineicon"/></a>\n'
        else:
            newPostButtonStr += \
                '<a href="' + usersPath + '/newshare">' + \
                '<button class="button"><span>' + \
                translate['Post'] + '</span></button></a>'
    else:
        if not manuallyApproveFollowers:
            if not iconsAsButtons:
                newPostButtonStr += \
                    '<a class="imageAnchor" href="' + usersPath + \
                    '/newpost"><img loading="lazy" src="/' + \
                    'icons/newpost.png" title="' + \
                    translate['Create a new post'] + '" alt="| ' + \
                    translate['Create a new post'] + \
                    '" class="timelineicon"/></a>\n'
            else:
                newPostButtonStr += \
                    '<a href="' + usersPath + '/newpost">' + \
                    '<button class="button"><span>' + \
                    translate['Post'] + '</span></button></a>'
        else:
            if not iconsAsButtons:
                newPostButtonStr += \
                    '<a class="imageAnchor" href="' + usersPath + \
                    '/newfollowers"><img loading="lazy" src="/' + \
                    'icons/newpost.png" title="' + \
                    translate['Create a new post'] + \
                    '" alt="| ' + translate['Create a new post'] + \
                    '" class="timelineicon"/></a>\n'
            else:
                newPostButtonStr += \
                    '<a href="' + usersPath + '/newfollowers">' + \
                    '<button class="button"><span>' + \
                    translate['Post'] + '</span></button></a>'

    # This creates a link to skip to the timeline and change to
    # profile view when accessed within lynx, but should be
    # invisible in a graphical web browser
    tlStr += \
        '<div class="transparent">' + \
        '<label class="transparent">' + \
        '<a href="/users/' + nickname + '">' + \
        translate['Switch to profile view'] + '</a></label> | ' + \
        '<label class="transparent">' + \
        '<a class="skip-main" href="' + usersPath + '/' + boxName + \
        '#timeline">' + \
        translate['Skip to timeline'] + '</a></label> | ' + \
        '<label class="transparent">' + \
        '<a class="skip-newswire" href="#newswire">' + \
        translate['Skip to Newswire'] + '</a></label> | ' + \
        '<label class="transparent">' + \
        '<a class="skip-links" href="#links">' + \
        translate['Skip to Links'] + '</a></label>' + \
        '</div>\n'

    # banner and row of buttons
    tlStr += \
        '<header>\n' + \
        '<a href="/users/' + nickname + '" title="' + \
        translate['Switch to profile view'] + '" alt="' + \
        translate['Switch to profile view'] + '">\n'
    tlStr += '<img loading="lazy" class="timeline-banner" ' + \
        'alt="" ' + \
        'src="' + usersPath + '/' + bannerFile + '" /></a>\n' + \
        '</header>\n'

    if fullWidthTimelineButtonHeader:
        tlStr += \
            headerButtonsTimeline(defaultTimeline, boxName, pageNumber,
                                  translate, usersPath, mediaButton,
                                  blogsButton, featuresButton,
                                  newsButton, inboxButton,
                                  dmButton, newDM, repliesButton,
                                  newReply, minimal, sentButton,
                                  sharesButtonStr, bookmarksButtonStr,
                                  eventsButtonStr, moderationButtonStr,
                                  newPostButtonStr, baseDir, nickname,
                                  domain, timelineStartTime,
                                  newCalendarEvent, calendarPath,
                                  calendarImage, followApprovals,
                                  iconsAsButtons)

    # start the timeline
    tlStr += '<table class="timeline">\n'
    tlStr += '  <colgroup>\n'
    tlStr += '    <col span="1" class="column-left">\n'
    tlStr += '    <col span="1" class="column-center">\n'
    tlStr += '    <col span="1" class="column-right">\n'
    tlStr += '  </colgroup>\n'
    tlStr += '  <tbody>\n'
    tlStr += '    <tr>\n'

    domainFull = getFullDomain(domain, port)

    # left column
    leftColumnStr = \
        getLeftColumnContent(baseDir, nickname, domainFull,
                             httpPrefix, translate,
                             editor, False, None, rssIconAtTop,
                             True, False, theme)
    tlStr += '  <td valign="top" class="col-left" ' + \
        'id="links" tabindex="-1">' + \
        leftColumnStr + '  </td>\n'
    # center column containing posts
    tlStr += '  <td valign="top" class="col-center">\n'
    tlStr += '    <main id="timeline" tabindex="-1">\n'

    if not fullWidthTimelineButtonHeader:
        tlStr += \
            headerButtonsTimeline(defaultTimeline, boxName, pageNumber,
                                  translate, usersPath, mediaButton,
                                  blogsButton, featuresButton,
                                  newsButton, inboxButton,
                                  dmButton, newDM, repliesButton,
                                  newReply, minimal, sentButton,
                                  sharesButtonStr, bookmarksButtonStr,
                                  eventsButtonStr, moderationButtonStr,
                                  newPostButtonStr, baseDir, nickname,
                                  domain, timelineStartTime,
                                  newCalendarEvent, calendarPath,
                                  calendarImage, followApprovals,
                                  iconsAsButtons)

    tlStr += '  <div class="timeline-posts">\n'

    # second row of buttons for moderator actions
    if moderator and boxName == 'moderation':
        tlStr += \
            '<form method="POST" action="/users/' + \
            nickname + '/moderationaction">'
        tlStr += '<div class="container">\n'
        idx = 'Nickname or URL. Block using *@domain or nickname@domain'
        tlStr += \
            '    <b>' + translate[idx] + '</b><br>\n'
        if moderationActionStr:
            tlStr += '    <input type="text" ' + \
                'name="moderationAction" value="' + \
                moderationActionStr + '" autofocus><br>\n'
        else:
            tlStr += '    <input type="text" ' + \
                'name="moderationAction" value="" autofocus><br>\n'

        tlStr += \
            '    <input type="submit" title="' + \
            translate['Information about current blocks/suspensions'] + \
            '" name="submitInfo" value="' + translate['Info'] + '">\n'
        tlStr += \
            '    <input type="submit" title="' + \
            translate['Remove the above item'] + \
            '" name="submitRemove" value="' + \
            translate['Remove'] + '">\n'

        tlStr += \
            '    <input type="submit" title="' + \
            translate['Suspend the above account nickname'] + \
            '" name="submitSuspend" value="' + translate['Suspend'] + '">\n'
        tlStr += \
            '    <input type="submit" title="' + \
            translate['Remove a suspension for an account nickname'] + \
            '" name="submitUnsuspend" value="' + \
            translate['Unsuspend'] + '">\n'

        tlStr += \
            '    <input type="submit" title="' + \
            translate['Block an account on another instance'] + \
            '" name="submitBlock" value="' + translate['Block'] + '">\n'
        tlStr += \
            '    <input type="submit" title="' + \
            translate['Unblock an account on another instance'] + \
            '" name="submitUnblock" value="' + translate['Unblock'] + '">\n'

        tlStr += \
            '    <input type="submit" title="' + \
            translate['Filter out words'] + \
            '" name="submitFilter" value="' + translate['Filter'] + '">\n'
        tlStr += \
            '    <input type="submit" title="' + \
            translate['Unfilter words'] + \
            '" name="submitUnfilter" value="' + translate['Unfilter'] + '">\n'

        tlStr += '</div>\n</form>\n'

    _logTimelineTiming(enableTimingLog, timelineStartTime, boxName, '6')

    if boxName == 'tlshares':
        maxSharesPerAccount = itemsPerPage
        return (tlStr +
                _htmlSharesTimeline(translate, pageNumber, itemsPerPage,
                                    baseDir, actor, nickname, domain, port,
                                    maxSharesPerAccount, httpPrefix) +
                htmlFooter())

    _logTimelineTiming(enableTimingLog, timelineStartTime, boxName, '7')

    # page up arrow
    if pageNumber > 1:
        tlStr += \
            '  <center>\n' + \
            '    <a href="' + usersPath + '/' + boxName + \
            '?page=' + str(pageNumber - 1) + \
            '"><img loading="lazy" class="pageicon" src="/' + \
            'icons/pageup.png" title="' + \
            translate['Page up'] + '" alt="' + \
            translate['Page up'] + '"></a>\n' + \
            '  </center>\n'

    # show the posts
    itemCtr = 0
    if timelineJson:
        # if this is the media timeline then add an extra gallery container
        if boxName == 'tlmedia':
            if pageNumber > 1:
                tlStr += '<br>'
            tlStr += '<div class="galleryContainer">\n'

        # show each post in the timeline
        for item in timelineJson['orderedItems']:
            if item['type'] == 'Create' or \
               item['type'] == 'Announce' or \
               item['type'] == 'Update':
                # is the actor who sent this post snoozed?
                if isPersonSnoozed(baseDir, nickname, domain, item['actor']):
                    continue

                # is the post in the memory cache of recent ones?
                currTlStr = None
                if boxName != 'tlmedia' and \
                   recentPostsCache.get('index'):
                    postId = \
                        removeIdEnding(item['id']).replace('/', '#')
                    if postId in recentPostsCache['index']:
                        if not item.get('muted'):
                            if recentPostsCache['html'].get(postId):
                                currTlStr = recentPostsCache['html'][postId]
                                currTlStr = \
                                    preparePostFromHtmlCache(nickname,
                                                             currTlStr,
                                                             boxName,
                                                             pageNumber)
                                _logTimelineTiming(enableTimingLog,
                                                   timelineStartTime,
                                                   boxName, '10')

                if not currTlStr:
                    _logTimelineTiming(enableTimingLog,
                                       timelineStartTime,
                                       boxName, '11')

                    # read the post from disk
                    currTlStr = \
                        individualPostAsHtml(False, recentPostsCache,
                                             maxRecentPosts,
                                             translate, pageNumber,
                                             baseDir, session,
                                             cachedWebfingers,
                                             personCache,
                                             nickname, domain, port,
                                             item, None, True,
                                             allowDeletion,
                                             httpPrefix, projectVersion,
                                             boxName,
                                             YTReplacementDomain,
                                             showPublishedDateOnly,
                                             peertubeInstances,
                                             allowLocalNetworkAccess,
                                             boxName != 'dm',
                                             showIndividualPostIcons,
                                             manuallyApproveFollowers,
                                             False, True)
                    _logTimelineTiming(enableTimingLog,
                                       timelineStartTime, boxName, '12')

                if currTlStr:
                    itemCtr += 1
                    tlStr += currTlStr
                    if separatorStr:
                        tlStr += separatorStr
        if boxName == 'tlmedia':
            tlStr += '</div>\n'

    # page down arrow
    if itemCtr > 2:
        tlStr += \
            '      <center>\n' + \
            '        <a href="' + usersPath + '/' + boxName + '?page=' + \
            str(pageNumber + 1) + \
            '"><img loading="lazy" class="pageicon" src="/' + \
            'icons/pagedown.png" title="' + \
            translate['Page down'] + '" alt="' + \
            translate['Page down'] + '"></a>\n' + \
            '      </center>\n'

    # end of timeline-posts
    tlStr += '  </div>\n'

    # end of column-center
    tlStr += '  </td>\n'

    # right column
    rightColumnStr = getRightColumnContent(baseDir, nickname, domainFull,
                                           httpPrefix, translate,
                                           moderator, editor,
                                           newswire, positiveVoting,
                                           False, None, True,
                                           showPublishAsIcon,
                                           rssIconAtTop, publishButtonAtTop,
                                           authorized, True, theme)
    tlStr += '    </main>\n'
    tlStr += '  <td valign="top" class="col-right" ' + \
        'id="newswire" tabindex="-1">' + \
        rightColumnStr + '  </td>\n'
    tlStr += '  </tr>\n'

    _logTimelineTiming(enableTimingLog, timelineStartTime, boxName, '9')

    tlStr += '  </tbody>\n'
    tlStr += '</table>\n'
    tlStr += htmlFooter()
    return tlStr


def htmlIndividualShare(actor: str, item: {}, translate: {},
                        showContact: bool, removeButton: bool) -> str:
    """Returns an individual shared item as html
    """
    profileStr = '<div class="container">\n'
    profileStr += '<p class="share-title">' + item['displayName'] + '</p>\n'
    if item.get('imageUrl'):
        profileStr += '<a href="' + item['imageUrl'] + '">\n'
        profileStr += \
            '<img loading="lazy" src="' + item['imageUrl'] + \
            '" alt="' + translate['Item image'] + '">\n</a>\n'
    profileStr += '<p>' + item['summary'] + '</p>\n'
    profileStr += \
        '<p><b>' + translate['Type'] + ':</b> ' + item['itemType'] + ' '
    profileStr += \
        '<b>' + translate['Category'] + ':</b> ' + item['category'] + ' '
    profileStr += \
        '<b>' + translate['Location'] + ':</b> ' + item['location'] + '</p>\n'
    sharedesc = item['displayName']
    if '<' not in sharedesc and '?' not in sharedesc:
        if showContact:
            contactActor = item['actor']
            profileStr += \
                '<p><a href="' + actor + \
                '?replydm=sharedesc:' + sharedesc + \
                '?mention=' + contactActor + '"><button class="button">' + \
                translate['Contact'] + '</button></a>\n'
        if removeButton:
            profileStr += \
                ' <a href="' + actor + '?rmshare=' + sharedesc + \
                '"><button class="button">' + \
                translate['Remove'] + '</button></a>\n'
    profileStr += '</div>\n'
    return profileStr


def _htmlSharesTimeline(translate: {}, pageNumber: int, itemsPerPage: int,
                        baseDir: str, actor: str,
                        nickname: str, domain: str, port: int,
                        maxSharesPerAccount: int, httpPrefix: str) -> str:
    """Show shared items timeline as html
    """
    sharesJson, lastPage = \
        sharesTimelineJson(actor, pageNumber, itemsPerPage,
                           baseDir, maxSharesPerAccount)
    domainFull = getFullDomain(domain, port)
    actor = httpPrefix + '://' + domainFull + '/users/' + nickname
    timelineStr = ''

    if pageNumber > 1:
        timelineStr += \
            '  <center>\n' + \
            '    <a href="' + actor + '/tlshares?page=' + \
            str(pageNumber - 1) + \
            '"><img loading="lazy" class="pageicon" src="/' + \
            'icons/pageup.png" title="' + translate['Page up'] + \
            '" alt="' + translate['Page up'] + '"></a>\n' + \
            '  </center>\n'

    separatorStr = htmlPostSeparator(baseDir, None)
    for published, item in sharesJson.items():
        showContactButton = False
        if item['actor'] != actor:
            showContactButton = True
        showRemoveButton = False
        if item['actor'] == actor:
            showRemoveButton = True
        timelineStr += \
            htmlIndividualShare(actor, item, translate,
                                showContactButton, showRemoveButton)
        timelineStr += separatorStr

    if not lastPage:
        timelineStr += \
            '  <center>\n' + \
            '    <a href="' + actor + '/tlshares?page=' + \
            str(pageNumber + 1) + \
            '"><img loading="lazy" class="pageicon" src="/' + \
            'icons/pagedown.png" title="' + translate['Page down'] + \
            '" alt="' + translate['Page down'] + '"></a>\n' + \
            '  </center>\n'

    return timelineStr


def htmlShares(cssCache: {}, defaultTimeline: str,
               recentPostsCache: {}, maxRecentPosts: int,
               translate: {}, pageNumber: int, itemsPerPage: int,
               session, baseDir: str,
               cachedWebfingers: {}, personCache: {},
               nickname: str, domain: str, port: int,
               allowDeletion: bool,
               httpPrefix: str, projectVersion: str,
               YTReplacementDomain: str,
               showPublishedDateOnly: bool,
               newswire: {}, positiveVoting: bool,
               showPublishAsIcon: bool,
               fullWidthTimelineButtonHeader: bool,
               iconsAsButtons: bool,
               rssIconAtTop: bool,
               publishButtonAtTop: bool,
               authorized: bool, theme: str,
               peertubeInstances: [],
               allowLocalNetworkAccess: bool) -> str:
    """Show the shares timeline as html
    """
    manuallyApproveFollowers = \
        followerApprovalActive(baseDir, nickname, domain)

    return htmlTimeline(cssCache, defaultTimeline,
                        recentPostsCache, maxRecentPosts,
                        translate, pageNumber,
                        itemsPerPage, session, baseDir,
                        cachedWebfingers, personCache,
                        nickname, domain, port, None,
                        'tlshares', allowDeletion,
                        httpPrefix, projectVersion, manuallyApproveFollowers,
                        False, YTReplacementDomain,
                        showPublishedDateOnly,
                        newswire, False, False,
                        positiveVoting, showPublishAsIcon,
                        fullWidthTimelineButtonHeader,
                        iconsAsButtons, rssIconAtTop, publishButtonAtTop,
                        authorized, None, theme, peertubeInstances,
                        allowLocalNetworkAccess)


def htmlInbox(cssCache: {}, defaultTimeline: str,
              recentPostsCache: {}, maxRecentPosts: int,
              translate: {}, pageNumber: int, itemsPerPage: int,
              session, baseDir: str,
              cachedWebfingers: {}, personCache: {},
              nickname: str, domain: str, port: int, inboxJson: {},
              allowDeletion: bool,
              httpPrefix: str, projectVersion: str,
              minimal: bool, YTReplacementDomain: str,
              showPublishedDateOnly: bool,
              newswire: {}, positiveVoting: bool,
              showPublishAsIcon: bool,
              fullWidthTimelineButtonHeader: bool,
              iconsAsButtons: bool,
              rssIconAtTop: bool,
              publishButtonAtTop: bool,
              authorized: bool, theme: str,
              peertubeInstances: [],
              allowLocalNetworkAccess: bool) -> str:
    """Show the inbox as html
    """
    manuallyApproveFollowers = \
        followerApprovalActive(baseDir, nickname, domain)

    return htmlTimeline(cssCache, defaultTimeline,
                        recentPostsCache, maxRecentPosts,
                        translate, pageNumber,
                        itemsPerPage, session, baseDir,
                        cachedWebfingers, personCache,
                        nickname, domain, port, inboxJson,
                        'inbox', allowDeletion,
                        httpPrefix, projectVersion, manuallyApproveFollowers,
                        minimal, YTReplacementDomain,
                        showPublishedDateOnly,
                        newswire, False, False,
                        positiveVoting, showPublishAsIcon,
                        fullWidthTimelineButtonHeader,
                        iconsAsButtons, rssIconAtTop, publishButtonAtTop,
                        authorized, None, theme, peertubeInstances,
                        allowLocalNetworkAccess)


def htmlBookmarks(cssCache: {}, defaultTimeline: str,
                  recentPostsCache: {}, maxRecentPosts: int,
                  translate: {}, pageNumber: int, itemsPerPage: int,
                  session, baseDir: str,
                  cachedWebfingers: {}, personCache: {},
                  nickname: str, domain: str, port: int, bookmarksJson: {},
                  allowDeletion: bool,
                  httpPrefix: str, projectVersion: str,
                  minimal: bool, YTReplacementDomain: str,
                  showPublishedDateOnly: bool,
                  newswire: {}, positiveVoting: bool,
                  showPublishAsIcon: bool,
                  fullWidthTimelineButtonHeader: bool,
                  iconsAsButtons: bool,
                  rssIconAtTop: bool,
                  publishButtonAtTop: bool,
                  authorized: bool, theme: str,
                  peertubeInstances: [],
                  allowLocalNetworkAccess: bool) -> str:
    """Show the bookmarks as html
    """
    manuallyApproveFollowers = \
        followerApprovalActive(baseDir, nickname, domain)

    return htmlTimeline(cssCache, defaultTimeline,
                        recentPostsCache, maxRecentPosts,
                        translate, pageNumber,
                        itemsPerPage, session, baseDir,
                        cachedWebfingers, personCache,
                        nickname, domain, port, bookmarksJson,
                        'tlbookmarks', allowDeletion,
                        httpPrefix, projectVersion, manuallyApproveFollowers,
                        minimal, YTReplacementDomain,
                        showPublishedDateOnly,
                        newswire, False, False,
                        positiveVoting, showPublishAsIcon,
                        fullWidthTimelineButtonHeader,
                        iconsAsButtons, rssIconAtTop, publishButtonAtTop,
                        authorized, None, theme, peertubeInstances,
                        allowLocalNetworkAccess)


def htmlEvents(cssCache: {}, defaultTimeline: str,
               recentPostsCache: {}, maxRecentPosts: int,
               translate: {}, pageNumber: int, itemsPerPage: int,
               session, baseDir: str,
               cachedWebfingers: {}, personCache: {},
               nickname: str, domain: str, port: int, bookmarksJson: {},
               allowDeletion: bool,
               httpPrefix: str, projectVersion: str,
               minimal: bool, YTReplacementDomain: str,
               showPublishedDateOnly: bool,
               newswire: {}, positiveVoting: bool,
               showPublishAsIcon: bool,
               fullWidthTimelineButtonHeader: bool,
               iconsAsButtons: bool,
               rssIconAtTop: bool,
               publishButtonAtTop: bool,
               authorized: bool, theme: str,
               peertubeInstances: [],
               allowLocalNetworkAccess: bool) -> str:
    """Show the events as html
    """
    manuallyApproveFollowers = \
        followerApprovalActive(baseDir, nickname, domain)

    return htmlTimeline(cssCache, defaultTimeline,
                        recentPostsCache, maxRecentPosts,
                        translate, pageNumber,
                        itemsPerPage, session, baseDir,
                        cachedWebfingers, personCache,
                        nickname, domain, port, bookmarksJson,
                        'tlevents', allowDeletion,
                        httpPrefix, projectVersion, manuallyApproveFollowers,
                        minimal, YTReplacementDomain,
                        showPublishedDateOnly,
                        newswire, False, False,
                        positiveVoting, showPublishAsIcon,
                        fullWidthTimelineButtonHeader,
                        iconsAsButtons, rssIconAtTop, publishButtonAtTop,
                        authorized, None, theme, peertubeInstances,
                        allowLocalNetworkAccess)


def htmlInboxDMs(cssCache: {}, defaultTimeline: str,
                 recentPostsCache: {}, maxRecentPosts: int,
                 translate: {}, pageNumber: int, itemsPerPage: int,
                 session, baseDir: str,
                 cachedWebfingers: {}, personCache: {},
                 nickname: str, domain: str, port: int, inboxJson: {},
                 allowDeletion: bool,
                 httpPrefix: str, projectVersion: str,
                 minimal: bool, YTReplacementDomain: str,
                 showPublishedDateOnly: bool,
                 newswire: {}, positiveVoting: bool,
                 showPublishAsIcon: bool,
                 fullWidthTimelineButtonHeader: bool,
                 iconsAsButtons: bool,
                 rssIconAtTop: bool,
                 publishButtonAtTop: bool,
                 authorized: bool, theme: str,
                 peertubeInstances: [],
                 allowLocalNetworkAccess: bool) -> str:
    """Show the DM timeline as html
    """
    return htmlTimeline(cssCache, defaultTimeline,
                        recentPostsCache, maxRecentPosts,
                        translate, pageNumber,
                        itemsPerPage, session, baseDir,
                        cachedWebfingers, personCache,
                        nickname, domain, port, inboxJson, 'dm', allowDeletion,
                        httpPrefix, projectVersion, False, minimal,
                        YTReplacementDomain, showPublishedDateOnly,
                        newswire, False, False, positiveVoting,
                        showPublishAsIcon,
                        fullWidthTimelineButtonHeader,
                        iconsAsButtons, rssIconAtTop, publishButtonAtTop,
                        authorized, None, theme, peertubeInstances,
                        allowLocalNetworkAccess)


def htmlInboxReplies(cssCache: {}, defaultTimeline: str,
                     recentPostsCache: {}, maxRecentPosts: int,
                     translate: {}, pageNumber: int, itemsPerPage: int,
                     session, baseDir: str,
                     cachedWebfingers: {}, personCache: {},
                     nickname: str, domain: str, port: int, inboxJson: {},
                     allowDeletion: bool,
                     httpPrefix: str, projectVersion: str,
                     minimal: bool, YTReplacementDomain: str,
                     showPublishedDateOnly: bool,
                     newswire: {}, positiveVoting: bool,
                     showPublishAsIcon: bool,
                     fullWidthTimelineButtonHeader: bool,
                     iconsAsButtons: bool,
                     rssIconAtTop: bool,
                     publishButtonAtTop: bool,
                     authorized: bool, theme: str,
                     peertubeInstances: [],
                     allowLocalNetworkAccess: bool) -> str:
    """Show the replies timeline as html
    """
    return htmlTimeline(cssCache, defaultTimeline,
                        recentPostsCache, maxRecentPosts,
                        translate, pageNumber,
                        itemsPerPage, session, baseDir,
                        cachedWebfingers, personCache,
                        nickname, domain, port, inboxJson, 'tlreplies',
                        allowDeletion, httpPrefix, projectVersion, False,
                        minimal, YTReplacementDomain,
                        showPublishedDateOnly,
                        newswire, False, False,
                        positiveVoting, showPublishAsIcon,
                        fullWidthTimelineButtonHeader,
                        iconsAsButtons, rssIconAtTop, publishButtonAtTop,
                        authorized, None, theme, peertubeInstances,
                        allowLocalNetworkAccess)


def htmlInboxMedia(cssCache: {}, defaultTimeline: str,
                   recentPostsCache: {}, maxRecentPosts: int,
                   translate: {}, pageNumber: int, itemsPerPage: int,
                   session, baseDir: str,
                   cachedWebfingers: {}, personCache: {},
                   nickname: str, domain: str, port: int, inboxJson: {},
                   allowDeletion: bool,
                   httpPrefix: str, projectVersion: str,
                   minimal: bool, YTReplacementDomain: str,
                   showPublishedDateOnly: bool,
                   newswire: {}, positiveVoting: bool,
                   showPublishAsIcon: bool,
                   fullWidthTimelineButtonHeader: bool,
                   iconsAsButtons: bool,
                   rssIconAtTop: bool,
                   publishButtonAtTop: bool,
                   authorized: bool, theme: str,
                   peertubeInstances: [],
                   allowLocalNetworkAccess: bool) -> str:
    """Show the media timeline as html
    """
    return htmlTimeline(cssCache, defaultTimeline,
                        recentPostsCache, maxRecentPosts,
                        translate, pageNumber,
                        itemsPerPage, session, baseDir,
                        cachedWebfingers, personCache,
                        nickname, domain, port, inboxJson, 'tlmedia',
                        allowDeletion, httpPrefix, projectVersion, False,
                        minimal, YTReplacementDomain,
                        showPublishedDateOnly,
                        newswire, False, False,
                        positiveVoting, showPublishAsIcon,
                        fullWidthTimelineButtonHeader,
                        iconsAsButtons, rssIconAtTop, publishButtonAtTop,
                        authorized, None, theme, peertubeInstances,
                        allowLocalNetworkAccess)


def htmlInboxBlogs(cssCache: {}, defaultTimeline: str,
                   recentPostsCache: {}, maxRecentPosts: int,
                   translate: {}, pageNumber: int, itemsPerPage: int,
                   session, baseDir: str,
                   cachedWebfingers: {}, personCache: {},
                   nickname: str, domain: str, port: int, inboxJson: {},
                   allowDeletion: bool,
                   httpPrefix: str, projectVersion: str,
                   minimal: bool, YTReplacementDomain: str,
                   showPublishedDateOnly: bool,
                   newswire: {}, positiveVoting: bool,
                   showPublishAsIcon: bool,
                   fullWidthTimelineButtonHeader: bool,
                   iconsAsButtons: bool,
                   rssIconAtTop: bool,
                   publishButtonAtTop: bool,
                   authorized: bool, theme: str,
                   peertubeInstances: [],
                   allowLocalNetworkAccess: bool) -> str:
    """Show the blogs timeline as html
    """
    return htmlTimeline(cssCache, defaultTimeline,
                        recentPostsCache, maxRecentPosts,
                        translate, pageNumber,
                        itemsPerPage, session, baseDir,
                        cachedWebfingers, personCache,
                        nickname, domain, port, inboxJson, 'tlblogs',
                        allowDeletion, httpPrefix, projectVersion, False,
                        minimal, YTReplacementDomain,
                        showPublishedDateOnly,
                        newswire, False, False,
                        positiveVoting, showPublishAsIcon,
                        fullWidthTimelineButtonHeader,
                        iconsAsButtons, rssIconAtTop, publishButtonAtTop,
                        authorized, None, theme, peertubeInstances,
                        allowLocalNetworkAccess)


def htmlInboxFeatures(cssCache: {}, defaultTimeline: str,
                      recentPostsCache: {}, maxRecentPosts: int,
                      translate: {}, pageNumber: int, itemsPerPage: int,
                      session, baseDir: str,
                      cachedWebfingers: {}, personCache: {},
                      nickname: str, domain: str, port: int, inboxJson: {},
                      allowDeletion: bool,
                      httpPrefix: str, projectVersion: str,
                      minimal: bool, YTReplacementDomain: str,
                      showPublishedDateOnly: bool,
                      newswire: {}, positiveVoting: bool,
                      showPublishAsIcon: bool,
                      fullWidthTimelineButtonHeader: bool,
                      iconsAsButtons: bool,
                      rssIconAtTop: bool,
                      publishButtonAtTop: bool,
                      authorized: bool,
                      theme: str,
                      peertubeInstances: [],
                      allowLocalNetworkAccess: bool) -> str:
    """Show the features timeline as html
    """
    return htmlTimeline(cssCache, defaultTimeline,
                        recentPostsCache, maxRecentPosts,
                        translate, pageNumber,
                        itemsPerPage, session, baseDir,
                        cachedWebfingers, personCache,
                        nickname, domain, port, inboxJson, 'tlfeatures',
                        allowDeletion, httpPrefix, projectVersion, False,
                        minimal, YTReplacementDomain,
                        showPublishedDateOnly,
                        newswire, False, False,
                        positiveVoting, showPublishAsIcon,
                        fullWidthTimelineButtonHeader,
                        iconsAsButtons, rssIconAtTop, publishButtonAtTop,
                        authorized, None, theme, peertubeInstances,
                        allowLocalNetworkAccess)


def htmlInboxNews(cssCache: {}, defaultTimeline: str,
                  recentPostsCache: {}, maxRecentPosts: int,
                  translate: {}, pageNumber: int, itemsPerPage: int,
                  session, baseDir: str,
                  cachedWebfingers: {}, personCache: {},
                  nickname: str, domain: str, port: int, inboxJson: {},
                  allowDeletion: bool,
                  httpPrefix: str, projectVersion: str,
                  minimal: bool, YTReplacementDomain: str,
                  showPublishedDateOnly: bool,
                  newswire: {}, moderator: bool, editor: bool,
                  positiveVoting: bool, showPublishAsIcon: bool,
                  fullWidthTimelineButtonHeader: bool,
                  iconsAsButtons: bool,
                  rssIconAtTop: bool,
                  publishButtonAtTop: bool,
                  authorized: bool, theme: str,
                  peertubeInstances: [],
                  allowLocalNetworkAccess: bool) -> str:
    """Show the news timeline as html
    """
    return htmlTimeline(cssCache, defaultTimeline,
                        recentPostsCache, maxRecentPosts,
                        translate, pageNumber,
                        itemsPerPage, session, baseDir,
                        cachedWebfingers, personCache,
                        nickname, domain, port, inboxJson, 'tlnews',
                        allowDeletion, httpPrefix, projectVersion, False,
                        minimal, YTReplacementDomain,
                        showPublishedDateOnly,
                        newswire, moderator, editor,
                        positiveVoting, showPublishAsIcon,
                        fullWidthTimelineButtonHeader,
                        iconsAsButtons, rssIconAtTop, publishButtonAtTop,
                        authorized, None, theme, peertubeInstances,
                        allowLocalNetworkAccess)


def htmlOutbox(cssCache: {}, defaultTimeline: str,
               recentPostsCache: {}, maxRecentPosts: int,
               translate: {}, pageNumber: int, itemsPerPage: int,
               session, baseDir: str,
               cachedWebfingers: {}, personCache: {},
               nickname: str, domain: str, port: int, outboxJson: {},
               allowDeletion: bool,
               httpPrefix: str, projectVersion: str,
               minimal: bool, YTReplacementDomain: str,
               showPublishedDateOnly: bool,
               newswire: {}, positiveVoting: bool,
               showPublishAsIcon: bool,
               fullWidthTimelineButtonHeader: bool,
               iconsAsButtons: bool,
               rssIconAtTop: bool,
               publishButtonAtTop: bool,
               authorized: bool, theme: str,
               peertubeInstances: [],
               allowLocalNetworkAccess: bool) -> str:
    """Show the Outbox as html
    """
    manuallyApproveFollowers = \
        followerApprovalActive(baseDir, nickname, domain)
    return htmlTimeline(cssCache, defaultTimeline,
                        recentPostsCache, maxRecentPosts,
                        translate, pageNumber,
                        itemsPerPage, session, baseDir,
                        cachedWebfingers, personCache,
                        nickname, domain, port, outboxJson, 'outbox',
                        allowDeletion, httpPrefix, projectVersion,
                        manuallyApproveFollowers, minimal,
                        YTReplacementDomain, showPublishedDateOnly,
                        newswire, False, False, positiveVoting,
                        showPublishAsIcon, fullWidthTimelineButtonHeader,
                        iconsAsButtons, rssIconAtTop, publishButtonAtTop,
                        authorized, None, theme, peertubeInstances,
                        allowLocalNetworkAccess)
