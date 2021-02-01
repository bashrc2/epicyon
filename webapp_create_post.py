__filename__ = "webapp_create_post.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import os
from utils import isPublicPostFromUrl
from utils import getNicknameFromActor
from utils import getDomainFromActor
from utils import getImageFormats
from utils import getMediaFormats
from utils import getConfigParam
from webapp_utils import getBannerFile
from webapp_utils import htmlHeaderWithExternalStyle
from webapp_utils import htmlFooter


def _htmlFollowingDataList(baseDir: str, nickname: str,
                           domain: str, domainFull: str) -> str:
    """Returns a datalist of handles being followed
    """
    listStr = '<datalist id="followingHandles">\n'
    followingFilename = \
        baseDir + '/accounts/' + nickname + '@' + domain + '/following.txt'
    if os.path.isfile(followingFilename):
        with open(followingFilename, 'r') as followingFile:
            msg = followingFile.read()
            # add your own handle, so that you can send DMs
            # to yourself as reminders
            msg += nickname + '@' + domainFull + '\n'
            # include petnames
            petnamesFilename = \
                baseDir + '/accounts/' + \
                nickname + '@' + domain + '/petnames.txt'
            if os.path.isfile(petnamesFilename):
                followingList = []
                with open(petnamesFilename, 'r') as petnamesFile:
                    petStr = petnamesFile.read()
                    # extract each petname and append it
                    petnamesList = petStr.split('\n')
                    for pet in petnamesList:
                        followingList.append(pet.split(' ')[0])
                # add the following.txt entries
                followingList += msg.split('\n')
            else:
                # no petnames list exists - just use following.txt
                followingList = msg.split('\n')
            followingList.sort()
            if followingList:
                for followingAddress in followingList:
                    if followingAddress:
                        listStr += \
                            '<option>@' + followingAddress + '</option>\n'
    listStr += '</datalist>\n'
    return listStr


def _htmlNewPostDropDown(scopeIcon: str, scopeDescription: str,
                         replyStr: str,
                         translate: {},
                         showPublicOnDropdown: bool,
                         defaultTimeline: str,
                         pathBase: str,
                         dropdownNewPostSuffix: str,
                         dropdownNewBlogSuffix: str,
                         dropdownUnlistedSuffix: str,
                         dropdownFollowersSuffix: str,
                         dropdownDMSuffix: str,
                         dropdownReminderSuffix: str,
                         dropdownEventSuffix: str,
                         dropdownReportSuffix: str) -> str:
    """Returns the html for a drop down list of new post types
    """
    dropDownContent = '<nav><div class="newPostDropdown">\n'
    dropDownContent += '  <input type="checkbox" ' + \
        'id="my-newPostDropdown" value="" name="my-checkbox">\n'
    dropDownContent += '  <label for="my-newPostDropdown"\n'
    dropDownContent += '     data-toggle="newPostDropdown">\n'
    dropDownContent += '  <img loading="lazy" alt="" title="" src="/' + \
        'icons/' + scopeIcon + '"/><b>' + \
        scopeDescription + '</b></label>\n'
    dropDownContent += '  <ul>\n'

    if showPublicOnDropdown:
        dropDownContent += \
            '<li><a href="' + pathBase + dropdownNewPostSuffix + \
            '"><img loading="lazy" alt="" title="" src="/' + \
            'icons/scope_public.png"/><b>' + \
            translate['Public'] + '</b><br>' + \
            translate['Visible to anyone'] + '</a></li>\n'
        if defaultTimeline == 'tlfeatures':
            dropDownContent += \
                '<li><a href="' + pathBase + dropdownNewBlogSuffix + \
                '"><img loading="lazy" alt="" title="" src="/' + \
                'icons/scope_blog.png"/><b>' + \
                translate['Article'] + '</b><br>' + \
                translate['Create an article'] + '</a></li>\n'
        else:
            dropDownContent += \
                '<li><a href="' + pathBase + dropdownNewBlogSuffix + \
                '"><img loading="lazy" alt="" title="" src="/' + \
                'icons/scope_blog.png"/><b>' + \
                translate['Blog'] + '</b><br>' + \
                translate['Publicly visible post'] + '</a></li>\n'
        dropDownContent += \
            '<li><a href="' + pathBase + dropdownUnlistedSuffix + \
            '"><img loading="lazy" alt="" title="" src="/' + \
            'icons/scope_unlisted.png"/><b>' + \
            translate['Unlisted'] + '</b><br>' + \
            translate['Not on public timeline'] + '</a></li>\n'
    dropDownContent += \
        '<li><a href="' + pathBase + dropdownFollowersSuffix + \
        '"><img loading="lazy" alt="" title="" src="/' + \
        'icons/scope_followers.png"/><b>' + \
        translate['Followers'] + '</b><br>' + \
        translate['Only to followers'] + '</a></li>\n'
    dropDownContent += \
        '<li><a href="' + pathBase + dropdownDMSuffix + \
        '"><img loading="lazy" alt="" title="" src="/' + \
        'icons/scope_dm.png"/><b>' + \
        translate['DM'] + '</b><br>' + \
        translate['Only to mentioned people'] + '</a></li>\n'

    dropDownContent += \
        '<li><a href="' + pathBase + dropdownReminderSuffix + \
        '"><img loading="lazy" alt="" title="" src="/' + \
        'icons/scope_reminder.png"/><b>' + \
        translate['Reminder'] + '</b><br>' + \
        translate['Scheduled note to yourself'] + '</a></li>\n'
    dropDownContent += \
        '<li><a href="' + pathBase + dropdownEventSuffix + \
        '"><img loading="lazy" alt="" title="" src="/' + \
        'icons/scope_event.png"/><b>' + \
        translate['Event'] + '</b><br>' + \
        translate['Create an event'] + '</a></li>\n'
    dropDownContent += \
        '<li><a href="' + pathBase + dropdownReportSuffix + \
        '"><img loading="lazy" alt="" title="" src="/' + \
        'icons/scope_report.png"/><b>' + \
        translate['Report'] + '</b><br>' + \
        translate['Send to moderators'] + '</a></li>\n'

    if not replyStr:
        dropDownContent += \
            '<li><a href="' + pathBase + \
            '/newshare"><img loading="lazy" alt="" title="" src="/' + \
            'icons/scope_share.png"/><b>' + \
            translate['Shares'] + '</b><br>' + \
            translate['Describe a shared item'] + '</a></li>\n'
        dropDownContent += \
            '<li><a href="' + pathBase + \
            '/newquestion"><img loading="lazy" alt="" title="" src="/' + \
            'icons/scope_question.png"/><b>' + \
            translate['Question'] + '</b><br>' + \
            translate['Ask a question'] + '</a></li>\n'

    dropDownContent += '  </ul>\n'
    dropDownContent += '</div></nav>\n'
    return dropDownContent


def htmlNewPost(cssCache: {}, mediaInstance: bool, translate: {},
                baseDir: str, httpPrefix: str,
                path: str, inReplyTo: str,
                mentions: [],
                shareDescription: str,
                reportUrl: str, pageNumber: int,
                nickname: str, domain: str,
                domainFull: str,
                defaultTimeline: str, newswire: {},
                theme: str) -> str:
    """New post screen
    """
    replyStr = ''

    showPublicOnDropdown = True
    messageBoxHeight = 400

    # filename of the banner shown at the top
    bannerFile, bannerFilename = \
        getBannerFile(baseDir, nickname, domain, theme)

    if not path.endswith('/newshare'):
        if not path.endswith('/newreport'):
            if not inReplyTo or path.endswith('/newreminder'):
                newPostText = '<h1>' + \
                    translate['Write your post text below.'] + '</h1>\n'
            else:
                newPostText = \
                    '<p class="new-post-text">' + \
                    translate['Write your reply to'] + \
                    ' <a href="' + inReplyTo + '">' + \
                    translate['this post'] + '</a></p>\n'
                replyStr = '<input type="hidden" ' + \
                    'name="replyTo" value="' + inReplyTo + '">\n'

                # if replying to a non-public post then also make
                # this post non-public
                if not isPublicPostFromUrl(baseDir, nickname, domain,
                                           inReplyTo):
                    newPostPath = path
                    if '?' in newPostPath:
                        newPostPath = newPostPath.split('?')[0]
                    if newPostPath.endswith('/newpost'):
                        path = path.replace('/newpost', '/newfollowers')
                    elif newPostPath.endswith('/newunlisted'):
                        path = path.replace('/newunlisted', '/newfollowers')
                    showPublicOnDropdown = False
        else:
            newPostText = \
                '<h1>' + \
                translate['Write your report below.'] + '</h1>\n'

            # custom report header with any additional instructions
            if os.path.isfile(baseDir + '/accounts/report.txt'):
                with open(baseDir + '/accounts/report.txt', 'r') as file:
                    customReportText = file.read()
                    if '</p>' not in customReportText:
                        customReportText = \
                            '<p class="login-subtext">' + \
                            customReportText + '</p>\n'
                        repStr = '<p class="login-subtext">'
                        customReportText = \
                            customReportText.replace('<p>', repStr)
                        newPostText += customReportText

            idx = 'This message only goes to moderators, even if it ' + \
                'mentions other fediverse addresses.'
            newPostText += \
                '<p class="new-post-subtext">' + translate[idx] + '</p>\n' + \
                '<p class="new-post-subtext">' + translate['Also see'] + \
                ' <a href="/terms">' + \
                translate['Terms of Service'] + '</a></p>\n'
    else:
        newPostText = \
            '<h1>' + \
            translate['Enter the details for your shared item below.'] + \
            '</h1>\n'

    if path.endswith('/newquestion'):
        newPostText = \
            '<h1>' + \
            translate['Enter the choices for your question below.'] + \
            '</h1>\n'

    if os.path.isfile(baseDir + '/accounts/newpost.txt'):
        with open(baseDir + '/accounts/newpost.txt', 'r') as file:
            newPostText = \
                '<p>' + file.read() + '</p>\n'

    cssFilename = baseDir + '/epicyon-profile.css'
    if os.path.isfile(baseDir + '/epicyon.css'):
        cssFilename = baseDir + '/epicyon.css'

    if '?' in path:
        path = path.split('?')[0]
    pathBase = path.replace('/newreport', '').replace('/newpost', '')
    pathBase = pathBase.replace('/newblog', '').replace('/newshare', '')
    pathBase = pathBase.replace('/newunlisted', '')
    pathBase = pathBase.replace('/newevent', '')
    pathBase = pathBase.replace('/newreminder', '')
    pathBase = pathBase.replace('/newfollowers', '').replace('/newdm', '')

    newPostImageSection = '    <div class="container">'
    if not path.endswith('/newevent'):
        newPostImageSection += \
            '      <label class="labels">' + \
            translate['Image description'] + '</label>\n'
    else:
        newPostImageSection += \
            '      <label class="labels">' + \
            translate['Event banner image description'] + '</label>\n'
    newPostImageSection += \
        '      <input type="text" name="imageDescription">\n'

    if path.endswith('/newevent'):
        newPostImageSection += \
            '      <label class="labels">' + \
            translate['Banner image'] + '</label>\n'
        newPostImageSection += \
            '      <input type="file" id="attachpic" name="attachpic"'
        newPostImageSection += \
            '            accept="' + getImageFormats() + '">\n'
    else:
        newPostImageSection += \
            '      <input type="file" id="attachpic" name="attachpic"'
        newPostImageSection += \
            '            accept="' + getMediaFormats() + '">\n'
    newPostImageSection += '    </div>\n'

    scopeIcon = 'scope_public.png'
    scopeDescription = translate['Public']
    if shareDescription:
        placeholderSubject = translate['Ask about a shared item.'] + '..'
    else:
        placeholderSubject = \
            translate['Subject or Content Warning (optional)'] + '...'
    placeholderMentions = ''
    if inReplyTo:
        # mentionsAndContent = getMentionsString(content)
        placeholderMentions = \
            translate['Replying to'] + '...'
    placeholderMessage = translate['Write something'] + '...'
    extraFields = ''
    endpoint = 'newpost'
    if path.endswith('/newblog'):
        placeholderSubject = translate['Title']
        scopeIcon = 'scope_blog.png'
        if defaultTimeline != 'tlfeatures':
            scopeDescription = translate['Blog']
        else:
            scopeDescription = translate['Article']
        endpoint = 'newblog'
    elif path.endswith('/newunlisted'):
        scopeIcon = 'scope_unlisted.png'
        scopeDescription = translate['Unlisted']
        endpoint = 'newunlisted'
    elif path.endswith('/newfollowers'):
        scopeIcon = 'scope_followers.png'
        scopeDescription = translate['Followers']
        endpoint = 'newfollowers'
    elif path.endswith('/newdm'):
        scopeIcon = 'scope_dm.png'
        scopeDescription = translate['DM']
        endpoint = 'newdm'
    elif path.endswith('/newreminder'):
        scopeIcon = 'scope_reminder.png'
        scopeDescription = translate['Reminder']
        endpoint = 'newreminder'
    elif path.endswith('/newevent'):
        scopeIcon = 'scope_event.png'
        scopeDescription = translate['Event']
        endpoint = 'newevent'
        placeholderSubject = translate['Event name']
        placeholderMessage = translate['Describe the event'] + '...'
    elif path.endswith('/newreport'):
        scopeIcon = 'scope_report.png'
        scopeDescription = translate['Report']
        endpoint = 'newreport'
    elif path.endswith('/newquestion'):
        scopeIcon = 'scope_question.png'
        scopeDescription = translate['Question']
        placeholderMessage = translate['Enter your question'] + '...'
        endpoint = 'newquestion'
        extraFields = '<div class="container">\n'
        extraFields += '  <label class="labels">' + \
            translate['Possible answers'] + ':</label><br>\n'
        for questionCtr in range(8):
            extraFields += \
                '  <input type="text" class="questionOption" placeholder="' + \
                str(questionCtr + 1) + \
                '" name="questionOption' + str(questionCtr) + '"><br>\n'
        extraFields += \
            '  <label class="labels">' + \
            translate['Duration of listing in days'] + \
            ':</label> <input type="number" name="duration" ' + \
            'min="1" max="365" step="1" value="14"><br>\n'
        extraFields += '</div>'
    elif path.endswith('/newshare'):
        scopeIcon = 'scope_share.png'
        scopeDescription = translate['Shared Item']
        placeholderSubject = translate['Name of the shared item'] + '...'
        placeholderMessage = \
            translate['Description of the item being shared'] + '...'
        endpoint = 'newshare'
        extraFields = '<div class="container">\n'
        extraFields += \
            '  <label class="labels">' + \
            translate['Type of shared item. eg. hat'] + ':</label>\n'
        extraFields += \
            '  <input type="text" class="itemType" name="itemType">\n'
        extraFields += \
            '  <br><label class="labels">' + \
            translate['Category of shared item. eg. clothing'] + ':</label>\n'
        extraFields += \
            '  <input type="text" class="category" name="category">\n'
        extraFields += \
            '  <br><label class="labels">' + \
            translate['Duration of listing in days'] + ':</label>\n'
        extraFields += '  <input type="number" name="duration" ' + \
            'min="1" max="365" step="1" value="14">\n'
        extraFields += '</div>\n'
        extraFields += '<div class="container">\n'
        extraFields += \
            '<label class="labels">' + \
            translate['City or location of the shared item'] + ':</label>\n'
        extraFields += '<input type="text" name="location">\n'
        extraFields += '</div>\n'

    citationsStr = ''
    if endpoint == 'newblog':
        citationsFilename = \
            baseDir + '/accounts/' + \
            nickname + '@' + domain + '/.citations.txt'
        if os.path.isfile(citationsFilename):
            citationsStr = '<div class="container">\n'
            citationsStr += '<p><label class="labels">' + \
                translate['Citations'] + ':</label></p>\n'
            citationsStr += '  <ul>\n'
            citationsSeparator = '#####'
            with open(citationsFilename, "r") as f:
                citations = f.readlines()
                for line in citations:
                    if citationsSeparator not in line:
                        continue
                    sections = line.strip().split(citationsSeparator)
                    if len(sections) != 3:
                        continue
                    title = sections[1]
                    link = sections[2]
                    citationsStr += \
                        '    <li><a href="' + link + '"><cite>' + \
                        title + '</cite></a></li>'
            citationsStr += '  </ul>\n'
            citationsStr += '</div>\n'

    dateAndLocation = ''
    if endpoint != 'newshare' and \
       endpoint != 'newreport' and \
       endpoint != 'newquestion':
        dateAndLocation = '<div class="container">\n'

        if endpoint == 'newevent':
            # event status
            dateAndLocation += '<label class="labels">' + \
                translate['Status of the event'] + ':</label><br>\n'
            dateAndLocation += '<input type="radio" id="tentative" ' + \
                'name="eventStatus" value="tentative">\n'
            dateAndLocation += '<label class="labels" for="tentative">' + \
                translate['Tentative'] + '</label><br>\n'
            dateAndLocation += '<input type="radio" id="confirmed" ' + \
                'name="eventStatus" value="confirmed" checked>\n'
            dateAndLocation += '<label class="labels" for="confirmed">' + \
                translate['Confirmed'] + '</label><br>\n'
            dateAndLocation += '<input type="radio" id="cancelled" ' + \
                'name="eventStatus" value="cancelled">\n'
            dateAndLocation += '<label class="labels" for="cancelled">' + \
                translate['Cancelled'] + '</label><br>\n'
            dateAndLocation += '</div>\n'
            dateAndLocation += '<div class="container">\n'
            # maximum attendees
            dateAndLocation += '<label class="labels" ' + \
                'for="maximumAttendeeCapacity">' + \
                translate['Maximum attendees'] + ':</label>\n'
            dateAndLocation += '<input type="number" ' + \
                'id="maximumAttendeeCapacity" ' + \
                'name="maximumAttendeeCapacity" min="1" max="999999" ' + \
                'value="100">\n'
            dateAndLocation += '</div>\n'
            dateAndLocation += '<div class="container">\n'
            # event joining options
            dateAndLocation += '<label class="labels">' + \
                translate['Joining'] + ':</label><br>\n'
            dateAndLocation += '<input type="radio" id="free" ' + \
                'name="joinMode" value="free" checked>\n'
            dateAndLocation += '<label class="labels" for="free">' + \
                translate['Anyone can join'] + '</label><br>\n'
            dateAndLocation += '<input type="radio" id="restricted" ' + \
                'name="joinMode" value="restricted">\n'
            dateAndLocation += '<label class="labels" for="female">' + \
                translate['Apply to join'] + '</label><br>\n'
            dateAndLocation += '<input type="radio" id="invite" ' + \
                'name="joinMode" value="invite">\n'
            dateAndLocation += '<label class="labels" for="other">' + \
                translate['Invitation only'] + '</label>\n'
            dateAndLocation += '</div>\n'
            dateAndLocation += '<div class="container">\n'
            # Event posts don't allow replies - they're just an announcement.
            # They also have a few more checkboxes
            dateAndLocation += \
                '<p><input type="checkbox" class="profilecheckbox" ' + \
                'name="privateEvent"><label class="labels"> ' + \
                translate['This is a private event.'] + '</label></p>\n'
            dateAndLocation += \
                '<p><input type="checkbox" class="profilecheckbox" ' + \
                'name="anonymousParticipationEnabled">' + \
                '<label class="labels"> ' + \
                translate['Allow anonymous participation.'] + '</label></p>\n'
        else:
            dateAndLocation += \
                '<p><input type="checkbox" class="profilecheckbox" ' + \
                'name="commentsEnabled" checked><label class="labels"> ' + \
                translate['Allow replies.'] + '</label></p>\n'

        if endpoint == 'newpost':
            dateAndLocation += \
                '<p><input type="checkbox" class="profilecheckbox" ' + \
                'name="pinToProfile"><label class="labels"> ' + \
                translate['Pin this post to your profile.'] + '</label></p>\n'

        if not inReplyTo and endpoint != 'newevent':
            dateAndLocation += \
                '<p><input type="checkbox" class="profilecheckbox" ' + \
                'name="schedulePost"><label class="labels"> ' + \
                translate['This is a scheduled post.'] + '</label></p>\n'

        if endpoint != 'newevent':
            dateAndLocation += \
                '<p><img loading="lazy" alt="" title="" ' + \
                'class="emojicalendar" src="/' + \
                'icons/calendar.png"/>\n'
            # select a date and time for this post
            dateAndLocation += '<label class="labels">' + \
                translate['Date'] + ': </label>\n'
            dateAndLocation += '<input type="date" name="eventDate">\n'
            dateAndLocation += '<label class="labelsright">' + \
                translate['Time'] + ':'
            dateAndLocation += \
                '<input type="time" name="eventTime"></label></p>\n'
        else:
            dateAndLocation += '</div>\n'
            dateAndLocation += '<div class="container">\n'
            dateAndLocation += \
                '<p><img loading="lazy" alt="" title="" ' + \
                'class="emojicalendar" src="/' + \
                'icons/calendar.png"/>\n'
            # select start time for the event
            dateAndLocation += '<label class="labels">' + \
                translate['Start Date'] + ': </label>\n'
            dateAndLocation += '<input type="date" name="eventDate">\n'
            dateAndLocation += '<label class="labelsright">' + \
                translate['Time'] + ':'
            dateAndLocation += \
                '<input type="time" name="eventTime"></label></p>\n'
            # select end time for the event
            dateAndLocation += \
                '<br><img loading="lazy" alt="" title="" ' + \
                'class="emojicalendar" src="/' + \
                'icons/calendar.png"/>\n'
            dateAndLocation += '<label class="labels">' + \
                translate['End Date'] + ': </label>\n'
            dateAndLocation += '<input type="date" name="endDate">\n'
            dateAndLocation += '<label class="labelsright">' + \
                translate['Time'] + ':'
            dateAndLocation += \
                '<input type="time" name="endTime"></label>\n'

        if endpoint == 'newevent':
            dateAndLocation += '</div>\n'
            dateAndLocation += '<div class="container">\n'
            dateAndLocation += '<br><label class="labels">' + \
                translate['Moderation policy or code of conduct'] + \
                ': </label>\n'
            dateAndLocation += \
                '    <textarea id="message" ' + \
                'name="repliesModerationOption" style="height:' + \
                str(messageBoxHeight) + 'px"></textarea>\n'
        dateAndLocation += '</div>\n'
        dateAndLocation += '<div class="container">\n'
        dateAndLocation += '<label class="labels">' + \
            translate['Location'] + ': </label>\n'
        dateAndLocation += '<input type="text" name="location">\n'
        if endpoint == 'newevent':
            dateAndLocation += '<br><label class="labels">' + \
                translate['Ticket URL'] + ': </label>\n'
            dateAndLocation += '<input type="text" name="ticketUrl">\n'
            dateAndLocation += '<br><label class="labels">' + \
                translate['Categories'] + ': </label>\n'
            dateAndLocation += '<input type="text" name="category">\n'
        dateAndLocation += '</div>\n'

    instanceTitle = \
        getConfigParam(baseDir, 'instanceTitle')
    newPostForm = htmlHeaderWithExternalStyle(cssFilename, instanceTitle)

    newPostForm += \
        '<header>\n' + \
        '<a href="/users/' + nickname + '/' + defaultTimeline + '" title="' + \
        translate['Switch to timeline view'] + '" alt="' + \
        translate['Switch to timeline view'] + '">\n'
    newPostForm += '<img loading="lazy" class="timeline-banner" src="' + \
        '/users/' + nickname + '/' + bannerFile + '" alt="" /></a>\n' + \
        '</header>\n'

    mentionsStr = ''
    for m in mentions:
        mentionNickname = getNicknameFromActor(m)
        if not mentionNickname:
            continue
        mentionDomain, mentionPort = getDomainFromActor(m)
        if not mentionDomain:
            continue
        if mentionPort:
            mentionsHandle = \
                '@' + mentionNickname + '@' + \
                mentionDomain + ':' + str(mentionPort)
        else:
            mentionsHandle = '@' + mentionNickname + '@' + mentionDomain
        if mentionsHandle not in mentionsStr:
            mentionsStr += mentionsHandle + ' '

    # build suffixes so that any replies or mentions are
    # preserved when switching between scopes
    dropdownNewPostSuffix = '/newpost'
    dropdownNewBlogSuffix = '/newblog'
    dropdownUnlistedSuffix = '/newunlisted'
    dropdownFollowersSuffix = '/newfollowers'
    dropdownDMSuffix = '/newdm'
    dropdownEventSuffix = '/newevent'
    dropdownReminderSuffix = '/newreminder'
    dropdownReportSuffix = '/newreport'
    if inReplyTo or mentions:
        dropdownNewPostSuffix = ''
        dropdownNewBlogSuffix = ''
        dropdownUnlistedSuffix = ''
        dropdownFollowersSuffix = ''
        dropdownDMSuffix = ''
        dropdownEventSuffix = ''
        dropdownReminderSuffix = ''
        dropdownReportSuffix = ''
    if inReplyTo:
        dropdownNewPostSuffix += '?replyto=' + inReplyTo
        dropdownNewBlogSuffix += '?replyto=' + inReplyTo
        dropdownUnlistedSuffix += '?replyto=' + inReplyTo
        dropdownFollowersSuffix += '?replyfollowers=' + inReplyTo
        dropdownDMSuffix += '?replydm=' + inReplyTo
    for mentionedActor in mentions:
        dropdownNewPostSuffix += '?mention=' + mentionedActor
        dropdownNewBlogSuffix += '?mention=' + mentionedActor
        dropdownUnlistedSuffix += '?mention=' + mentionedActor
        dropdownFollowersSuffix += '?mention=' + mentionedActor
        dropdownDMSuffix += '?mention=' + mentionedActor
        dropdownReportSuffix += '?mention=' + mentionedActor

    dropDownContent = ''
    if not reportUrl and not shareDescription:
        dropDownContent = \
            _htmlNewPostDropDown(scopeIcon, scopeDescription,
                                 replyStr,
                                 translate,
                                 showPublicOnDropdown,
                                 defaultTimeline,
                                 pathBase,
                                 dropdownNewPostSuffix,
                                 dropdownNewBlogSuffix,
                                 dropdownUnlistedSuffix,
                                 dropdownFollowersSuffix,
                                 dropdownDMSuffix,
                                 dropdownReminderSuffix,
                                 dropdownEventSuffix,
                                 dropdownReportSuffix)
    else:
        if not shareDescription:
            # reporting a post to moderator
            mentionsStr = 'Re: ' + reportUrl + '\n\n' + mentionsStr

    newPostForm += \
        '<form enctype="multipart/form-data" method="POST" ' + \
        'accept-charset="UTF-8" action="' + \
        path + '?' + endpoint + '?page=' + str(pageNumber) + '">\n'
    newPostForm += '  <div class="vertical-center">\n'
    newPostForm += \
        '    <label for="nickname"><b>' + newPostText + '</b></label>\n'
    newPostForm += '    <div class="containerNewPost">\n'
    newPostForm += '      <table style="width:100%" border="0">\n'
    newPostForm += '        <colgroup>\n'
    newPostForm += '          <col span="1" style="width:70%">\n'
    newPostForm += '          <col span="1" style="width:10%">\n'
    if newswire and path.endswith('/newblog'):
        newPostForm += '          <col span="1" style="width:10%">\n'
        newPostForm += '          <col span="1" style="width:10%">\n'
    else:
        newPostForm += '          <col span="1" style="width:20%">\n'
    newPostForm += '        </colgroup>\n'
    newPostForm += '<tr>\n'
    newPostForm += '<td>' + dropDownContent + '</td>\n'

    newPostForm += \
        '      <td><a href="' + pathBase + \
        '/searchemoji"><img loading="lazy" class="emojisearch" ' + \
        'src="/emoji/1F601.png" title="' + \
        translate['Search for emoji'] + '" alt="' + \
        translate['Search for emoji'] + '"/></a></td>\n'

    # for a new blog if newswire items exist then add a citations button
    if newswire and path.endswith('/newblog'):
        newPostForm += \
            '      <td><input type="submit" name="submitCitations" value="' + \
            translate['Citations'] + '"></td>\n'

    newPostForm += \
        '      <td><input type="submit" name="submitPost" value="' + \
        translate['Submit'] + '"></td>\n'

    newPostForm += '      </tr>\n'
    newPostForm += '</table>\n'
    newPostForm += '    </div>\n'

    newPostForm += '    <div class="containerSubmitNewPost"><center>\n'

    # newPostForm += \
    #     '      <a href="' + pathBase + \
    #     '/inbox"><button class="cancelbtn">' + \
    #     translate['Go Back'] + '</button></a>\n'

    newPostForm += '    </center></div>\n'

    newPostForm += replyStr
    if mediaInstance and not replyStr:
        newPostForm += newPostImageSection

    newPostForm += \
        '    <label class="labels">' + placeholderSubject + '</label><br>'
    if not shareDescription:
        shareDescription = ''
    newPostForm += \
        '    <input type="text" name="subject" value="' + \
        shareDescription + '">'
    newPostForm += ''

    selectedStr = ' selected'
    if inReplyTo or endpoint == 'newdm':
        if inReplyTo:
            newPostForm += \
                '    <label class="labels">' + placeholderMentions + \
                '</label><br>\n'
        else:
            newPostForm += \
                '    <a href="/users/' + nickname + \
                '/followingaccounts" title="' + \
                translate['Show a list of addresses to send to'] + '">' \
                '<label class="labels">' + \
                translate['Send to'] + ':' + '</label> 📄</a><br>\n'
        newPostForm += \
            '    <input type="text" name="mentions" ' + \
            'list="followingHandles" value="' + mentionsStr + '" selected>\n'
        newPostForm += \
            _htmlFollowingDataList(baseDir, nickname, domain, domainFull)
        newPostForm += ''
        selectedStr = ''

    newPostForm += \
        '    <br><label class="labels">' + placeholderMessage + '</label>'
    if mediaInstance:
        messageBoxHeight = 200

    if endpoint == 'newquestion':
        messageBoxHeight = 100
    elif endpoint == 'newblog':
        messageBoxHeight = 800

    newPostForm += \
        '    <textarea id="message" name="message" style="height:' + \
        str(messageBoxHeight) + 'px"' + selectedStr + '></textarea>\n'
    newPostForm += extraFields + citationsStr + dateAndLocation
    if not mediaInstance or replyStr:
        newPostForm += newPostImageSection
    newPostForm += '  </div>\n'
    newPostForm += '</form>\n'

    if not reportUrl:
        newPostForm = \
            newPostForm.replace('<body>', '<body onload="focusOnMessage()">')

    newPostForm += htmlFooter()
    return newPostForm
