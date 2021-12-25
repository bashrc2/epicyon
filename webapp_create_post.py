__filename__ = "webapp_create_post.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Web Interface"

import os
from utils import getNewPostEndpoints
from utils import isPublicPostFromUrl
from utils import getNicknameFromActor
from utils import getDomainFromActor
from utils import getMediaFormats
from utils import getConfigParam
from utils import acctDir
from utils import getCurrencies
from utils import getCategoryTypes
from webapp_utils import getBannerFile
from webapp_utils import htmlHeaderWithExternalStyle
from webapp_utils import htmlFooter
from webapp_utils import editTextField
from webapp_utils import editNumberField
from webapp_utils import editCurrencyField
from webapp_post import individualPostAsHtml


def _htmlFollowingDataList(base_dir: str, nickname: str,
                           domain: str, domainFull: str) -> str:
    """Returns a datalist of handles being followed
    """
    listStr = '<datalist id="followingHandles">\n'
    followingFilename = \
        acctDir(base_dir, nickname, domain) + '/following.txt'
    msg = None
    if os.path.isfile(followingFilename):
        with open(followingFilename, 'r') as followingFile:
            msg = followingFile.read()
            # add your own handle, so that you can send DMs
            # to yourself as reminders
            msg += nickname + '@' + domainFull + '\n'
    if msg:
        # include petnames
        petnamesFilename = \
            acctDir(base_dir, nickname, domain) + '/petnames.txt'
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
                    listStr += '<option>@' + followingAddress + '</option>\n'
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
                         dropdownReportSuffix: str,
                         noDropDown: bool,
                         accessKeys: {}) -> str:
    """Returns the html for a drop down list of new post types
    """
    dropDownContent = '<nav><div class="newPostDropdown">\n'
    if not noDropDown:
        dropDownContent += '  <input type="checkbox" ' + \
            'id="my-newPostDropdown" value="" name="my-checkbox">\n'
    dropDownContent += '  <label for="my-newPostDropdown"\n'
    dropDownContent += '     data-toggle="newPostDropdown">\n'
    dropDownContent += '  <img loading="lazy" alt="" title="" src="/' + \
        'icons/' + scopeIcon + '"/><b>' + scopeDescription + '</b></label>\n'

    if noDropDown:
        dropDownContent += '</div></nav>\n'
        return dropDownContent

    dropDownContent += '  <ul>\n'
    if showPublicOnDropdown:
        dropDownContent += \
            '<li><a href="' + pathBase + dropdownNewPostSuffix + \
            '" accesskey="' + accessKeys['Public'] + '">' + \
            '<img loading="lazy" alt="" title="" src="/' + \
            'icons/scope_public.png"/><b>' + \
            translate['Public'] + '</b><br>' + \
            translate['Visible to anyone'] + '</a></li>\n'
        if defaultTimeline == 'tlfeatures':
            dropDownContent += \
                '<li><a href="' + pathBase + dropdownNewBlogSuffix + \
                '" accesskey="' + accessKeys['menuBlogs'] + '">' + \
                '<img loading="lazy" alt="" title="" src="/' + \
                'icons/scope_blog.png"/><b>' + \
                translate['Article'] + '</b><br>' + \
                translate['Create an article'] + '</a></li>\n'
        else:
            dropDownContent += \
                '<li><a href="' + pathBase + dropdownNewBlogSuffix + \
                '" accesskey="' + accessKeys['menuBlogs'] + '">' + \
                '<img loading="lazy" alt="" title="" src="/' + \
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
        '" accesskey="' + accessKeys['menuFollowers'] + '">' + \
        '<img loading="lazy" alt="" title="" src="/' + \
        'icons/scope_followers.png"/><b>' + \
        translate['Followers'] + '</b><br>' + \
        translate['Only to followers'] + '</a></li>\n'
    dropDownContent += \
        '<li><a href="' + pathBase + dropdownDMSuffix + \
        '" accesskey="' + accessKeys['menuDM'] + '">' + \
        '<img loading="lazy" alt="" title="" src="/' + \
        'icons/scope_dm.png"/><b>' + \
        translate['DM'] + '</b><br>' + \
        translate['Only to mentioned people'] + '</a></li>\n'

    dropDownContent += \
        '<li><a href="' + pathBase + dropdownReminderSuffix + \
        '" accesskey="' + accessKeys['Reminder'] + '">' + \
        '<img loading="lazy" alt="" title="" src="/' + \
        'icons/scope_reminder.png"/><b>' + \
        translate['Reminder'] + '</b><br>' + \
        translate['Scheduled note to yourself'] + '</a></li>\n'
    dropDownContent += \
        '<li><a href="' + pathBase + dropdownReportSuffix + \
        '" accesskey="' + accessKeys['reportButton'] + '">' + \
        '<img loading="lazy" alt="" title="" src="/' + \
        'icons/scope_report.png"/><b>' + \
        translate['Report'] + '</b><br>' + \
        translate['Send to moderators'] + '</a></li>\n'

    if not replyStr:
        dropDownContent += \
            '<li><a href="' + pathBase + \
            '/newshare" accesskey="' + accessKeys['menuShares'] + '">' + \
            '<img loading="lazy" alt="" title="" src="/' + \
            'icons/scope_share.png"/><b>' + \
            translate['Shares'] + '</b><br>' + \
            translate['Describe a shared item'] + '</a></li>\n'
        dropDownContent += \
            '<li><a href="' + pathBase + \
            '/newwanted" accesskey="' + accessKeys['menuWanted'] + '">' + \
            '<img loading="lazy" alt="" title="" src="/' + \
            'icons/scope_wanted.png"/><b>' + \
            translate['Wanted'] + '</b><br>' + \
            translate['Describe something wanted'] + '</a></li>\n'
        dropDownContent += \
            '<li><a href="' + pathBase + \
            '/newquestion"><img loading="lazy" alt="" title="" src="/' + \
            'icons/scope_question.png"/><b>' + \
            translate['Question'] + '</b><br>' + \
            translate['Ask a question'] + '</a></li>\n'
    dropDownContent += '  </ul>\n'

    dropDownContent += '</div></nav>\n'
    return dropDownContent


def htmlNewPost(cssCache: {}, media_instance: bool, translate: {},
                base_dir: str, http_prefix: str,
                path: str, inReplyTo: str,
                mentions: [],
                shareDescription: str,
                reportUrl: str, pageNumber: int,
                category: str,
                nickname: str, domain: str,
                domainFull: str,
                defaultTimeline: str, newswire: {},
                theme: str, noDropDown: bool,
                accessKeys: {}, customSubmitText: str,
                conversationId: str,
                recentPostsCache: {}, max_recent_posts: int,
                session, cached_webfingers: {},
                person_cache: {}, port: int,
                post_json_object: {},
                project_version: str,
                yt_replace_domain: str,
                twitter_replacement_domain: str,
                show_published_date_only: bool,
                peertubeInstances: [],
                allow_local_network_access: bool,
                system_language: str,
                max_like_count: int, signing_priv_key_pem: str,
                CWlists: {}, lists_enabled: str,
                boxName: str) -> str:
    """New post screen
    """
    replyStr = ''

    isNewReminder = False
    if path.endswith('/newreminder'):
        isNewReminder = True

    # the date and time
    dateAndTimeStr = '<p>\n'
    if not isNewReminder:
        dateAndTimeStr += \
            '<img loading="lazy" alt="" title="" ' + \
            'class="emojicalendar" src="/' + \
            'icons/calendar.png"/>\n'
    # select a date and time for this post
    dateAndTimeStr += '<label class="labels">' + \
        translate['Date'] + ': </label>\n'
    dateAndTimeStr += '<input type="date" name="eventDate">\n'
    dateAndTimeStr += '<label class="labelsright">' + \
        translate['Time'] + ': '
    dateAndTimeStr += \
        '<input type="time" name="eventTime"></label>\n</p>\n'

    showPublicOnDropdown = True
    messageBoxHeight = 400

    # filename of the banner shown at the top
    bannerFile, bannerFilename = \
        getBannerFile(base_dir, nickname, domain, theme)

    if not path.endswith('/newshare') and not path.endswith('/newwanted'):
        if not path.endswith('/newreport'):
            if not inReplyTo or isNewReminder:
                newPostText = '<h1>' + \
                    translate['Write your post text below.'] + '</h1>\n'
            else:
                newPostText = ''
                if category != 'accommodation':
                    newPostText = \
                        '<p class="new-post-text">' + \
                        translate['Write your reply to'] + \
                        ' <a href="' + inReplyTo + \
                        '" rel="nofollow noopener noreferrer" ' + \
                        'target="_blank">' + \
                        translate['this post'] + '</a></p>\n'
                    if post_json_object:
                        newPostText += \
                            individualPostAsHtml(signing_priv_key_pem,
                                                 True, recentPostsCache,
                                                 max_recent_posts,
                                                 translate, None,
                                                 base_dir, session,
                                                 cached_webfingers,
                                                 person_cache,
                                                 nickname, domain, port,
                                                 post_json_object,
                                                 None, True, False,
                                                 http_prefix, project_version,
                                                 boxName,
                                                 yt_replace_domain,
                                                 twitter_replacement_domain,
                                                 show_published_date_only,
                                                 peertubeInstances,
                                                 allow_local_network_access,
                                                 theme, system_language,
                                                 max_like_count,
                                                 False, False, False,
                                                 False, False, False,
                                                 CWlists, lists_enabled)

                replyStr = '<input type="hidden" ' + \
                    'name="replyTo" value="' + inReplyTo + '">\n'

                # if replying to a non-public post then also make
                # this post non-public
                if not isPublicPostFromUrl(base_dir, nickname, domain,
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
                '<h1>' + translate['Write your report below.'] + '</h1>\n'

            # custom report header with any additional instructions
            if os.path.isfile(base_dir + '/accounts/report.txt'):
                with open(base_dir + '/accounts/report.txt', 'r') as file:
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
        if path.endswith('/newshare'):
            newPostText = \
                '<h1>' + \
                translate['Enter the details for your shared item below.'] + \
                '</h1>\n'
        else:
            newPostText = \
                '<h1>' + \
                translate['Enter the details for your wanted item below.'] + \
                '</h1>\n'

    if path.endswith('/newquestion'):
        newPostText = \
            '<h1>' + \
            translate['Enter the choices for your question below.'] + \
            '</h1>\n'

    if os.path.isfile(base_dir + '/accounts/newpost.txt'):
        with open(base_dir + '/accounts/newpost.txt', 'r') as file:
            newPostText = \
                '<p>' + file.read() + '</p>\n'

    cssFilename = base_dir + '/epicyon-profile.css'
    if os.path.isfile(base_dir + '/epicyon.css'):
        cssFilename = base_dir + '/epicyon.css'

    if '?' in path:
        path = path.split('?')[0]
    newPostEndpoints = getNewPostEndpoints()
    pathBase = path
    for currPostType in newPostEndpoints:
        pathBase = pathBase.replace('/' + currPostType, '')

    newPostImageSection = '    <div class="container">\n'
    newPostImageSection += \
        editTextField(translate['Image description'], 'imageDescription', '')

    newPostImageSection += \
        '      <input type="file" id="attachpic" name="attachpic"'
    formatsString = getMediaFormats()
    # remove svg as a permitted format
    formatsString = formatsString.replace(', .svg', '').replace('.svg, ', '')
    newPostImageSection += \
        '            accept="' + formatsString + '">\n'
    newPostImageSection += '    </div>\n'

    scopeIcon = 'scope_public.png'
    scopeDescription = translate['Public']
    if shareDescription:
        if category == 'accommodation':
            placeholderSubject = translate['Request to stay']
        else:
            placeholderSubject = translate['Ask about a shared item.'] + '..'
    else:
        placeholderSubject = \
            translate['Subject or Content Warning (optional)'] + '...'
    placeholderMentions = ''
    if inReplyTo:
        placeholderMentions = \
            translate['Replying to'] + '...'
    placeholderMessage = ''
    if category != 'accommodation':
        placeholderMessage = translate['Write something'] + '...'
    else:
        idx = 'Introduce yourself and specify the date ' + \
            'and time when you wish to stay'
        placeholderMessage = translate[idx]
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
    elif isNewReminder:
        scopeIcon = 'scope_reminder.png'
        scopeDescription = translate['Reminder']
        endpoint = 'newreminder'
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
            editNumberField(translate['Quantity'],
                            'itemQty', 1, 1, 999999, 1)
        extraFields += '<br>' + \
            editTextField(translate['Type of shared item. eg. hat'] + ':',
                          'itemType', '', '', True)
        categoryTypes = getCategoryTypes(base_dir)
        catStr = translate['Category of shared item. eg. clothing']
        extraFields += '<label class="labels">' + catStr + '</label><br>\n'

        extraFields += '  <select id="themeDropdown" ' + \
            'name="category" class="theme">\n'
        for category in categoryTypes:
            translatedCategory = "food"
            if translate.get(category):
                translatedCategory = translate[category]
            extraFields += '    <option value="' + \
                translatedCategory + '">' + \
                translatedCategory + '</option>\n'

        extraFields += '  </select><br>\n'
        extraFields += \
            editNumberField(translate['Duration of listing in days'],
                            'duration', 14, 1, 365, 1)
        extraFields += '</div>\n'
        extraFields += '<div class="container">\n'
        cityOrLocStr = translate['City or location of the shared item']
        extraFields += editTextField(cityOrLocStr + ':', 'location', '')
        extraFields += '</div>\n'
        extraFields += '<div class="container">\n'
        extraFields += \
            editCurrencyField(translate['Price'] + ':', 'itemPrice', '0.00',
                              '0.00', True)
        extraFields += '<br>'
        extraFields += \
            '<label class="labels">' + translate['Currency'] + '</label><br>\n'
        currencies = getCurrencies()
        extraFields += '  <select id="themeDropdown" ' + \
            'name="itemCurrency" class="theme">\n'
        currencyList = []
        for symbol, currName in currencies.items():
            currencyList.append(currName + ' ' + symbol)
        currencyList.sort()
        defaultCurrency = getConfigParam(base_dir, 'defaultCurrency')
        if not defaultCurrency:
            defaultCurrency = "EUR"
        for currName in currencyList:
            if defaultCurrency not in currName:
                extraFields += '    <option value="' + \
                    currName + '">' + currName + '</option>\n'
            else:
                extraFields += '    <option value="' + \
                    currName + '" selected="selected">' + \
                    currName + '</option>\n'
        extraFields += '  </select>\n'

        extraFields += '</div>\n'
    elif path.endswith('/newwanted'):
        scopeIcon = 'scope_wanted.png'
        scopeDescription = translate['Wanted']
        placeholderSubject = translate['Name of the wanted item'] + '...'
        placeholderMessage = \
            translate['Description of the item wanted'] + '...'
        endpoint = 'newwanted'
        extraFields = '<div class="container">\n'
        extraFields += \
            editNumberField(translate['Quantity'],
                            'itemQty', 1, 1, 999999, 1)
        extraFields += '<br>' + \
            editTextField(translate['Type of wanted item. eg. hat'] + ':',
                          'itemType', '', '', True)
        categoryTypes = getCategoryTypes(base_dir)
        catStr = translate['Category of wanted item. eg. clothes']
        extraFields += '<label class="labels">' + catStr + '</label><br>\n'

        extraFields += '  <select id="themeDropdown" ' + \
            'name="category" class="theme">\n'
        for category in categoryTypes:
            translatedCategory = "food"
            if translate.get(category):
                translatedCategory = translate[category]
            extraFields += '    <option value="' + \
                translatedCategory + '">' + \
                translatedCategory + '</option>\n'

        extraFields += '  </select><br>\n'
        extraFields += \
            editNumberField(translate['Duration of listing in days'],
                            'duration', 14, 1, 365, 1)
        extraFields += '</div>\n'
        extraFields += '<div class="container">\n'
        cityOrLocStr = translate['City or location of the wanted item']
        extraFields += editTextField(cityOrLocStr + ':', 'location', '')
        extraFields += '</div>\n'
        extraFields += '<div class="container">\n'
        extraFields += \
            editCurrencyField(translate['Maximum Price'] + ':',
                              'itemPrice', '0.00', '0.00', True)
        extraFields += '<br>'
        extraFields += \
            '<label class="labels">' + translate['Currency'] + '</label><br>\n'
        currencies = getCurrencies()
        extraFields += '  <select id="themeDropdown" ' + \
            'name="itemCurrency" class="theme">\n'
        currencyList = []
        for symbol, currName in currencies.items():
            currencyList.append(currName + ' ' + symbol)
        currencyList.sort()
        defaultCurrency = getConfigParam(base_dir, 'defaultCurrency')
        if not defaultCurrency:
            defaultCurrency = "EUR"
        for currName in currencyList:
            if defaultCurrency not in currName:
                extraFields += '    <option value="' + \
                    currName + '">' + currName + '</option>\n'
            else:
                extraFields += '    <option value="' + \
                    currName + '" selected="selected">' + \
                    currName + '</option>\n'
        extraFields += '  </select>\n'

        extraFields += '</div>\n'

    citationsStr = ''
    if endpoint == 'newblog':
        citationsFilename = \
            acctDir(base_dir, nickname, domain) + '/.citations.txt'
        if os.path.isfile(citationsFilename):
            citationsStr = '<div class="container">\n'
            citationsStr += '<p><label class="labels">' + \
                translate['Citations'] + ':</label></p>\n'
            citationsStr += '  <ul>\n'
            citationsSeparator = '#####'
            with open(citationsFilename, 'r') as f:
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
       endpoint != 'newwanted' and \
       endpoint != 'newreport' and \
       endpoint != 'newquestion':

        if not isNewReminder:
            dateAndLocation = \
                '<div class="container">\n'
            if category != 'accommodation':
                dateAndLocation += \
                    '<p><input type="checkbox" class="profilecheckbox" ' + \
                    'name="commentsEnabled" ' + \
                    'checked><label class="labels"> ' + \
                    translate['Allow replies.'] + '</label></p>\n'
            else:
                dateAndLocation += \
                    '<input type="hidden" name="commentsEnabled" ' + \
                    'value="true">\n'

            if endpoint == 'newpost':
                dateAndLocation += \
                    '<p><input type="checkbox" class="profilecheckbox" ' + \
                    'name="pinToProfile"><label class="labels"> ' + \
                    translate['Pin this post to your profile.'] + \
                    '</label></p>\n'

            if not inReplyTo:
                dateAndLocation += \
                    '<p><input type="checkbox" class="profilecheckbox" ' + \
                    'name="schedulePost"><label class="labels"> ' + \
                    translate['This is a scheduled post.'] + '</label></p>\n'

            dateAndLocation += dateAndTimeStr
            dateAndLocation += '</div>\n'

        dateAndLocation += '<div class="container">\n'
        dateAndLocation += \
            editTextField(translate['Location'], 'location', '')
        dateAndLocation += '</div>\n'

    instanceTitle = getConfigParam(base_dir, 'instanceTitle')
    newPostForm = htmlHeaderWithExternalStyle(cssFilename, instanceTitle, None)

    newPostForm += \
        '<header>\n' + \
        '<a href="/users/' + nickname + '/' + defaultTimeline + '" title="' + \
        translate['Switch to timeline view'] + '" alt="' + \
        translate['Switch to timeline view'] + '" ' + \
        'accesskey="' + accessKeys['menuTimeline'] + '">\n'
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
    dropdownReminderSuffix = '/newreminder'
    dropdownReportSuffix = '/newreport'
    if inReplyTo or mentions:
        dropdownNewPostSuffix = ''
        dropdownNewBlogSuffix = ''
        dropdownUnlistedSuffix = ''
        dropdownFollowersSuffix = ''
        dropdownDMSuffix = ''
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
    if conversationId and inReplyTo:
        dropdownNewPostSuffix += '?conversationId=' + conversationId
        dropdownNewBlogSuffix += '?conversationId=' + conversationId
        dropdownUnlistedSuffix += '?conversationId=' + conversationId
        dropdownFollowersSuffix += '?conversationId=' + conversationId
        dropdownDMSuffix += '?conversationId=' + conversationId

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
                                 dropdownReportSuffix,
                                 noDropDown, accessKeys)
    else:
        if not shareDescription:
            # reporting a post to moderator
            mentionsStr = 'Re: ' + reportUrl + '\n\n' + mentionsStr

    newPostForm += \
        '<form enctype="multipart/form-data" method="POST" ' + \
        'accept-charset="UTF-8" action="' + \
        path + '?' + endpoint + '?page=' + str(pageNumber) + '">\n'
    if conversationId:
        newPostForm += \
            '    <input type="hidden" name="conversationId" value="' + \
            conversationId + '">\n'
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

    submitText = translate['Submit']
    if customSubmitText:
        submitText = customSubmitText
    newPostForm += \
        '      <td><input type="submit" name="submitPost" value="' + \
        submitText + '" ' + \
        'accesskey="' + accessKeys['submitButton'] + '"></td>\n'

    newPostForm += '      </tr>\n</table>\n'
    newPostForm += '    </div>\n'

    newPostForm += '    <div class="containerSubmitNewPost"><center>\n'

    newPostForm += '    </center></div>\n'

    newPostForm += replyStr
    if media_instance and not replyStr:
        newPostForm += newPostImageSection

    if not shareDescription:
        shareDescription = ''

    # for reminders show the date and time at the top
    if isNewReminder:
        newPostForm += '<div class="containerNoOverflow">\n'
        newPostForm += dateAndTimeStr
        newPostForm += '</div>\n'

    newPostForm += \
        editTextField(placeholderSubject, 'subject', shareDescription)
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
            _htmlFollowingDataList(base_dir, nickname, domain, domainFull)
        newPostForm += ''
        selectedStr = ''

    newPostForm += \
        '    <br><label class="labels">' + placeholderMessage + '</label>'
    if media_instance:
        messageBoxHeight = 200

    if endpoint == 'newquestion':
        messageBoxHeight = 100
    elif endpoint == 'newblog':
        messageBoxHeight = 800

    newPostForm += \
        '    <textarea id="message" name="message" style="height:' + \
        str(messageBoxHeight) + 'px"' + selectedStr + \
        ' spellcheck="true" autocomplete="on">' + \
        '</textarea>\n'
    newPostForm += extraFields + citationsStr + dateAndLocation
    if not media_instance or replyStr:
        newPostForm += newPostImageSection

    newPostForm += \
        '    <div class="container">\n' + \
        '      <input type="submit" name="submitPost" value="' + \
        submitText + '">\n' + \
        '    </div>\n' + \
        '  </div>\n' + \
        '</form>\n'

    if not reportUrl:
        newPostForm = \
            newPostForm.replace('<body>', '<body onload="focusOnMessage()">')

    newPostForm += htmlFooter()
    return newPostForm
