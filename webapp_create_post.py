__filename__ = "webapp_create_post.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.3.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Web Interface"

import os
from utils import get_new_post_endpoints
from utils import is_public_post_from_url
from utils import get_nickname_from_actor
from utils import get_domain_from_actor
from utils import get_media_formats
from utils import get_config_param
from utils import acct_dir
from utils import get_currencies
from utils import get_category_types
from utils import get_account_timezone
from utils import get_supported_languages
from webapp_utils import html_common_emoji
from webapp_utils import begin_edit_section
from webapp_utils import end_edit_section
from webapp_utils import get_banner_file
from webapp_utils import html_header_with_external_style
from webapp_utils import html_footer
from webapp_utils import edit_text_field
from webapp_utils import edit_number_field
from webapp_utils import edit_currency_field
from webapp_post import individual_post_as_html


def _html_following_data_list(base_dir: str, nickname: str,
                              domain: str, domain_full: str) -> str:
    """Returns a datalist of handles being followed
    """
    list_str = '<datalist id="followingHandles">\n'
    following_filename = \
        acct_dir(base_dir, nickname, domain) + '/following.txt'
    msg = None
    if os.path.isfile(following_filename):
        with open(following_filename, 'r') as following_file:
            msg = following_file.read()
            # add your own handle, so that you can send DMs
            # to yourself as reminders
            msg += nickname + '@' + domain_full + '\n'
    if msg:
        # include petnames
        petnames_filename = \
            acct_dir(base_dir, nickname, domain) + '/petnames.txt'
        if os.path.isfile(petnames_filename):
            following_list = []
            with open(petnames_filename, 'r') as petnames_file:
                pet_str = petnames_file.read()
                # extract each petname and append it
                petnames_list = pet_str.split('\n')
                for pet in petnames_list:
                    following_list.append(pet.split(' ')[0])
            # add the following.txt entries
            following_list += msg.split('\n')
        else:
            # no petnames list exists - just use following.txt
            following_list = msg.split('\n')
        following_list.sort()
        if following_list:
            for following_address in following_list:
                if following_address:
                    list_str += '<option>@' + following_address + '</option>\n'
    list_str += '</datalist>\n'
    return list_str


def _html_new_post_drop_down(scope_icon: str, scope_description: str,
                             reply_str: str,
                             translate: {},
                             show_public_on_dropdown: bool,
                             default_timeline: str,
                             path_base: str,
                             dropdown_new_post_suffix: str,
                             dropdown_new_blog_suffix: str,
                             dropdown_unlisted_suffix: str,
                             dropdown_followers_suffix: str,
                             dropdown_dm_suffix: str,
                             dropdown_reminder_suffix: str,
                             dropdown_report_suffix: str,
                             no_drop_down: bool,
                             access_keys: {}) -> str:
    """Returns the html for a drop down list of new post types
    """
    drop_down_content = '<nav><div class="newPostDropdown">\n'
    if not no_drop_down:
        drop_down_content += '  <input type="checkbox" ' + \
            'id="my-newPostDropdown" value="" name="my-checkbox">\n'
    drop_down_content += '  <label for="my-newPostDropdown"\n'
    drop_down_content += '     data-toggle="newPostDropdown">\n'
    drop_down_content += '  <img loading="lazy" decoding="async" ' + \
        'alt="" title="" src="/' + \
        'icons/' + scope_icon + '"/><b>' + scope_description + '</b></label>\n'

    if no_drop_down:
        drop_down_content += '</div></nav>\n'
        return drop_down_content

    drop_down_content += '  <ul>\n'
    if show_public_on_dropdown:
        drop_down_content += \
            '<li><a href="' + path_base + dropdown_new_post_suffix + \
            '" accesskey="' + access_keys['Public'] + '">' + \
            '<img loading="lazy" decoding="async" alt="" title="" src="/' + \
            'icons/scope_public.png"/><b>' + \
            translate['Public'] + '</b><br>' + \
            translate['Visible to anyone'] + '</a></li>\n'
        if default_timeline == 'tlfeatures':
            drop_down_content += \
                '<li><a href="' + path_base + dropdown_new_blog_suffix + \
                '" accesskey="' + access_keys['menuBlogs'] + '">' + \
                '<img loading="lazy" decoding="async" ' + \
                'alt="" title="" src="/' + \
                'icons/scope_blog.png"/><b>' + \
                translate['Article'] + '</b><br>' + \
                translate['Create an article'] + '</a></li>\n'
        else:
            drop_down_content += \
                '<li><a href="' + path_base + dropdown_new_blog_suffix + \
                '" accesskey="' + access_keys['menuBlogs'] + '">' + \
                '<img loading="lazy" decoding="async" ' + \
                'alt="" title="" src="/' + \
                'icons/scope_blog.png"/><b>' + \
                translate['Blog'] + '</b><br>' + \
                translate['Publicly visible post'] + '</a></li>\n'
    drop_down_content += \
        '<li><a href="' + path_base + dropdown_unlisted_suffix + \
        '"><img loading="lazy" decoding="async" alt="" title="" src="/' + \
        'icons/scope_unlisted.png"/><b>' + \
        translate['Unlisted'] + '</b><br>' + \
        translate['Not on public timeline'] + '</a></li>\n'
    drop_down_content += \
        '<li><a href="' + path_base + dropdown_followers_suffix + \
        '" accesskey="' + access_keys['menuFollowers'] + '">' + \
        '<img loading="lazy" decoding="async" alt="" title="" src="/' + \
        'icons/scope_followers.png"/><b>' + \
        translate['Followers'] + '</b><br>' + \
        translate['Only to followers'] + '</a></li>\n'
    drop_down_content += \
        '<li><a href="' + path_base + dropdown_dm_suffix + \
        '" accesskey="' + access_keys['menuDM'] + '">' + \
        '<img loading="lazy" decoding="async" alt="" title="" src="/' + \
        'icons/scope_dm.png"/><b>' + \
        translate['DM'] + '</b><br>' + \
        translate['Only to mentioned people'] + '</a></li>\n'

    drop_down_content += \
        '<li><a href="' + path_base + dropdown_reminder_suffix + \
        '" accesskey="' + access_keys['Reminder'] + '">' + \
        '<img loading="lazy" decoding="async" alt="" title="" src="/' + \
        'icons/scope_reminder.png"/><b>' + \
        translate['Reminder'] + '</b><br>' + \
        translate['Scheduled note to yourself'] + '</a></li>\n'
    drop_down_content += \
        '<li><a href="' + path_base + dropdown_report_suffix + \
        '" accesskey="' + access_keys['reportButton'] + '">' + \
        '<img loading="lazy" decoding="async" alt="" title="" src="/' + \
        'icons/scope_report.png"/><b>' + \
        translate['Report'] + '</b><br>' + \
        translate['Send to moderators'] + '</a></li>\n'

    if not reply_str:
        drop_down_content += \
            '<li><a href="' + path_base + \
            '/newshare" accesskey="' + access_keys['menuShares'] + '">' + \
            '<img loading="lazy" decoding="async" alt="" title="" src="/' + \
            'icons/scope_share.png"/><b>' + \
            translate['Shares'] + '</b><br>' + \
            translate['Describe a shared item'] + '</a></li>\n'
        drop_down_content += \
            '<li><a href="' + path_base + \
            '/newwanted" accesskey="' + access_keys['menuWanted'] + '">' + \
            '<img loading="lazy" decoding="async" alt="" title="" src="/' + \
            'icons/scope_wanted.png"/><b>' + \
            translate['Wanted'] + '</b><br>' + \
            translate['Describe something wanted'] + '</a></li>\n'
        drop_down_content += \
            '<li><a href="' + path_base + \
            '/newquestion"><img loading="lazy" decoding="async" ' + \
            'alt="" title="" src="/' + \
            'icons/scope_question.png"/><b>' + \
            translate['Question'] + '</b><br>' + \
            translate['Ask a question'] + '</a></li>\n'
    drop_down_content += '  </ul>\n'

    drop_down_content += '</div></nav>\n'
    return drop_down_content


def html_new_post(css_cache: {}, media_instance: bool, translate: {},
                  base_dir: str, http_prefix: str,
                  path: str, inReplyTo: str,
                  mentions: [],
                  share_description: str,
                  report_url: str, page_number: int,
                  category: str,
                  nickname: str, domain: str,
                  domain_full: str,
                  default_timeline: str, newswire: {},
                  theme: str, no_drop_down: bool,
                  access_keys: {}, custom_submit_text: str,
                  conversationId: str,
                  recent_posts_cache: {}, max_recent_posts: int,
                  session, cached_webfingers: {},
                  person_cache: {}, port: int,
                  post_json_object: {},
                  project_version: str,
                  yt_replace_domain: str,
                  twitter_replacement_domain: str,
                  show_published_date_only: bool,
                  peertube_instances: [],
                  allow_local_network_access: bool,
                  system_language: str,
                  max_like_count: int, signing_priv_key_pem: str,
                  cw_lists: {}, lists_enabled: str,
                  boxName: str,
                  reply_is_chat: bool, bold_reading: bool) -> str:
    """New post screen
    """
    reply_str = ''

    is_new_reminder = False
    if path.endswith('/newreminder'):
        is_new_reminder = True

    # the date and time
    date_and_time_str = '<p>\n'
    if not is_new_reminder:
        date_and_time_str += \
            '<img loading="lazy" decoding="async" alt="" title="" ' + \
            'class="emojicalendar" src="/' + \
            'icons/calendar.png"/>\n'
    # select a date and time for this post
    date_and_time_str += '<label class="labels">' + \
        translate['Date'] + ': </label>\n'
    date_and_time_str += '<input type="date" name="eventDate">\n'
    date_and_time_str += '<label class="labelsright">' + \
        translate['Time'] + ': '
    date_and_time_str += \
        '<input type="time" name="eventTime"></label>\n</p>\n'

    show_public_on_dropdown = True
    message_box_height = 400

    # filename of the banner shown at the top
    banner_file, _ = \
        get_banner_file(base_dir, nickname, domain, theme)

    if not path.endswith('/newshare') and not path.endswith('/newwanted'):
        if not path.endswith('/newreport'):
            if not inReplyTo or is_new_reminder:
                new_post_text = '<h1>' + \
                    translate['Write your post text below.'] + '</h1>\n'
            else:
                new_post_text = ''
                if category != 'accommodation':
                    new_post_text = \
                        '<p class="new-post-text">' + \
                        translate['Write your reply to'] + \
                        ' <a href="' + inReplyTo + \
                        '" rel="nofollow noopener noreferrer" ' + \
                        'target="_blank">' + \
                        translate['this post'] + '</a></p>\n'
                    if post_json_object:
                        timezone = \
                            get_account_timezone(base_dir, nickname, domain)
                        new_post_text += \
                            individual_post_as_html(signing_priv_key_pem,
                                                    True, recent_posts_cache,
                                                    max_recent_posts,
                                                    translate, None,
                                                    base_dir, session,
                                                    cached_webfingers,
                                                    person_cache,
                                                    nickname, domain, port,
                                                    post_json_object,
                                                    None, True, False,
                                                    http_prefix,
                                                    project_version,
                                                    boxName,
                                                    yt_replace_domain,
                                                    twitter_replacement_domain,
                                                    show_published_date_only,
                                                    peertube_instances,
                                                    allow_local_network_access,
                                                    theme, system_language,
                                                    max_like_count,
                                                    False, False, False,
                                                    False, False, False,
                                                    cw_lists, lists_enabled,
                                                    timezone, False,
                                                    bold_reading)

                reply_str = '<input type="hidden" ' + \
                    'name="replyTo" value="' + inReplyTo + '">\n'

                # if replying to a non-public post then also make
                # this post non-public
                if not is_public_post_from_url(base_dir, nickname, domain,
                                               inReplyTo):
                    new_post_path = path
                    if '?' in new_post_path:
                        new_post_path = new_post_path.split('?')[0]
                    if new_post_path.endswith('/newpost'):
                        path = path.replace('/newpost', '/newfollowers')
                    show_public_on_dropdown = False
        else:
            new_post_text = \
                '<h1>' + translate['Write your report below.'] + '</h1>\n'

            # custom report header with any additional instructions
            if os.path.isfile(base_dir + '/accounts/report.txt'):
                with open(base_dir + '/accounts/report.txt', 'r') as file:
                    custom_report_text = file.read()
                    if '</p>' not in custom_report_text:
                        custom_report_text = \
                            '<p class="login-subtext">' + \
                            custom_report_text + '</p>\n'
                        rep_str = '<p class="login-subtext">'
                        custom_report_text = \
                            custom_report_text.replace('<p>', rep_str)
                        new_post_text += custom_report_text

            idx = 'This message only goes to moderators, even if it ' + \
                'mentions other fediverse addresses.'
            new_post_text += \
                '<p class="new-post-subtext">' + translate[idx] + '</p>\n' + \
                '<p class="new-post-subtext">' + translate['Also see'] + \
                ' <a href="/terms">' + \
                translate['Terms of Service'] + '</a></p>\n'
    else:
        if path.endswith('/newshare'):
            new_post_text = \
                '<h1>' + \
                translate['Enter the details for your shared item below.'] + \
                '</h1>\n'
        else:
            new_post_text = \
                '<h1>' + \
                translate['Enter the details for your wanted item below.'] + \
                '</h1>\n'

    if path.endswith('/newquestion'):
        new_post_text = \
            '<h1>' + \
            translate['Enter the choices for your question below.'] + \
            '</h1>\n'

    if os.path.isfile(base_dir + '/accounts/newpost.txt'):
        with open(base_dir + '/accounts/newpost.txt', 'r') as file:
            new_post_text = \
                '<p>' + file.read() + '</p>\n'

    css_filename = base_dir + '/epicyon-profile.css'
    if os.path.isfile(base_dir + '/epicyon.css'):
        css_filename = base_dir + '/epicyon.css'

    if '?' in path:
        path = path.split('?')[0]
    new_post_endpoints = get_new_post_endpoints()
    path_base = path
    for curr_post_type in new_post_endpoints:
        path_base = path_base.replace('/' + curr_post_type, '')

    attach_str = 'Attach an image, video or audio file'
    new_post_image_section = begin_edit_section('📷 ' + translate[attach_str])
    new_post_image_section += \
        '      <input type="file" id="attachpic" name="attachpic"'
    formats_string = get_media_formats()
    # remove svg as a permitted format
    formats_string = formats_string.replace(', .svg', '').replace('.svg, ', '')
    new_post_image_section += \
        '            accept="' + formats_string + '">\n'
    new_post_image_section += \
        edit_text_field(translate['Describe your attachment'],
                        'imageDescription', '')
    new_post_image_section += end_edit_section()

    new_post_emoji_section = ''
    common_emoji_str = html_common_emoji(base_dir, 16)
    if common_emoji_str:
        new_post_emoji_section = \
            begin_edit_section('😀 ' + translate['Common emoji'])
        new_post_emoji_section += \
            '<label class="labels">' + \
            translate['Copy and paste into your text'] + '</label><br>\n'
        new_post_emoji_section += common_emoji_str
        new_post_emoji_section += end_edit_section()

    scope_icon = 'scope_public.png'
    scope_description = translate['Public']
    if share_description:
        if category == 'accommodation':
            placeholder_subject = translate['Request to stay']
        else:
            placeholder_subject = translate['Ask about a shared item.'] + '..'
    else:
        placeholder_subject = \
            translate['Subject or Content Warning (optional)'] + '...'
    placeholder_mentions = ''
    if inReplyTo:
        placeholder_mentions = \
            translate['Replying to'] + '...'
    placeholder_message = ''
    if category != 'accommodation':
        if default_timeline == 'tlfeatures':
            placeholder_message = translate['Write your news report'] + '...'
        else:
            placeholder_message = translate['Write something'] + '...'
    else:
        idx = 'Introduce yourself and specify the date ' + \
            'and time when you wish to stay'
        placeholder_message = translate[idx]
    extra_fields = ''
    endpoint = 'newpost'
    if path.endswith('/newblog'):
        placeholder_subject = translate['Title']
        scope_icon = 'scope_blog.png'
        if default_timeline != 'tlfeatures':
            scope_description = translate['Blog']
        else:
            scope_description = translate['Article']
        endpoint = 'newblog'
    elif path.endswith('/newunlisted'):
        scope_icon = 'scope_unlisted.png'
        scope_description = translate['Unlisted']
        endpoint = 'newunlisted'
    elif path.endswith('/newfollowers'):
        scope_icon = 'scope_followers.png'
        scope_description = translate['Followers']
        endpoint = 'newfollowers'
    elif path.endswith('/newdm'):
        scope_icon = 'scope_dm.png'
        scope_description = translate['DM']
        endpoint = 'newdm'
        placeholder_message = '⚠️ ' + translate['DM warning']
    elif is_new_reminder:
        scope_icon = 'scope_reminder.png'
        scope_description = translate['Reminder']
        endpoint = 'newreminder'
    elif path.endswith('/newreport'):
        scope_icon = 'scope_report.png'
        scope_description = translate['Report']
        endpoint = 'newreport'
    elif path.endswith('/newquestion'):
        scope_icon = 'scope_question.png'
        scope_description = translate['Question']
        placeholder_message = translate['Enter your question'] + '...'
        endpoint = 'newquestion'
        extra_fields = '<div class="container">\n'
        extra_fields += '  <label class="labels">' + \
            translate['Possible answers'] + ':</label><br>\n'
        for question_ctr in range(8):
            extra_fields += \
                '  <input type="text" class="questionOption" placeholder="' + \
                str(question_ctr + 1) + \
                '" name="questionOption' + str(question_ctr) + '"><br>\n'
        extra_fields += \
            '  <label class="labels">' + \
            translate['Duration of listing in days'] + \
            ':</label> <input type="number" name="duration" ' + \
            'min="1" max="365" step="1" value="14"><br>\n'
        extra_fields += '</div>'
    elif path.endswith('/newshare'):
        scope_icon = 'scope_share.png'
        scope_description = translate['Shared Item']
        placeholder_subject = translate['Name of the shared item'] + '...'
        placeholder_message = \
            translate['Description of the item being shared'] + '...'
        endpoint = 'newshare'
        extra_fields = '<div class="container">\n'
        extra_fields += \
            edit_number_field(translate['Quantity'],
                              'itemQty', 1, 1, 999999, 1)
        extra_fields += '<br>' + \
            edit_text_field(translate['Type of shared item. eg. hat'] + ':',
                            'itemType', '', '', True)
        category_types = get_category_types(base_dir)
        cat_str = translate['Category of shared item. eg. clothing']
        extra_fields += '<label class="labels">' + cat_str + '</label><br>\n'

        extra_fields += '  <select id="themeDropdown" ' + \
            'name="category" class="theme">\n'
        for cat in category_types:
            translated_category = "food"
            if translate.get(cat):
                translated_category = translate[cat]
            extra_fields += '    <option value="' + \
                translated_category + '">' + \
                translated_category + '</option>\n'

        extra_fields += '  </select><br>\n'
        extra_fields += \
            edit_number_field(translate['Duration of listing in days'],
                              'duration', 14, 1, 365, 1)
        extra_fields += '</div>\n'
        extra_fields += '<div class="container">\n'
        city_or_loc_str = translate['City or location of the shared item']
        extra_fields += edit_text_field(city_or_loc_str + ':', 'location', '')
        extra_fields += '</div>\n'
        extra_fields += '<div class="container">\n'
        extra_fields += \
            edit_currency_field(translate['Price'] + ':', 'itemPrice', '0.00',
                                '0.00', True)
        extra_fields += '<br>'
        extra_fields += \
            '<label class="labels">' + translate['Currency'] + '</label><br>\n'
        currencies = get_currencies()
        extra_fields += '  <select id="themeDropdown" ' + \
            'name="itemCurrency" class="theme">\n'
        currency_list = []
        for symbol, curr_name in currencies.items():
            currency_list.append(curr_name + ' ' + symbol)
        currency_list.sort()
        default_currency = get_config_param(base_dir, 'defaultCurrency')
        if not default_currency:
            default_currency = "EUR"
        for curr_name in currency_list:
            if default_currency not in curr_name:
                extra_fields += '    <option value="' + \
                    curr_name + '">' + curr_name + '</option>\n'
            else:
                extra_fields += '    <option value="' + \
                    curr_name + '" selected="selected">' + \
                    curr_name + '</option>\n'
        extra_fields += '  </select>\n'

        extra_fields += '</div>\n'
    elif path.endswith('/newwanted'):
        scope_icon = 'scope_wanted.png'
        scope_description = translate['Wanted']
        placeholder_subject = translate['Name of the wanted item'] + '...'
        placeholder_message = \
            translate['Description of the item wanted'] + '...'
        endpoint = 'newwanted'
        extra_fields = '<div class="container">\n'
        extra_fields += \
            edit_number_field(translate['Quantity'],
                              'itemQty', 1, 1, 999999, 1)
        extra_fields += '<br>' + \
            edit_text_field(translate['Type of wanted item. eg. hat'] + ':',
                            'itemType', '', '', True)
        category_types = get_category_types(base_dir)
        cat_str = translate['Category of wanted item. eg. clothes']
        extra_fields += '<label class="labels">' + cat_str + '</label><br>\n'

        extra_fields += '  <select id="themeDropdown" ' + \
            'name="category" class="theme">\n'
        for cat in category_types:
            translated_category = "food"
            if translate.get(cat):
                translated_category = translate[cat]
            extra_fields += '    <option value="' + \
                translated_category + '">' + \
                translated_category + '</option>\n'

        extra_fields += '  </select><br>\n'
        extra_fields += \
            edit_number_field(translate['Duration of listing in days'],
                              'duration', 14, 1, 365, 1)
        extra_fields += '</div>\n'
        extra_fields += '<div class="container">\n'
        city_or_loc_str = translate['City or location of the wanted item']
        extra_fields += edit_text_field(city_or_loc_str + ':', 'location', '')
        extra_fields += '</div>\n'
        extra_fields += '<div class="container">\n'
        extra_fields += \
            edit_currency_field(translate['Maximum Price'] + ':',
                                'itemPrice', '0.00', '0.00', True)
        extra_fields += '<br>'
        extra_fields += \
            '<label class="labels">' + translate['Currency'] + '</label><br>\n'
        currencies = get_currencies()
        extra_fields += '  <select id="themeDropdown" ' + \
            'name="itemCurrency" class="theme">\n'
        currency_list = []
        for symbol, curr_name in currencies.items():
            currency_list.append(curr_name + ' ' + symbol)
        currency_list.sort()
        default_currency = get_config_param(base_dir, 'defaultCurrency')
        if not default_currency:
            default_currency = "EUR"
        for curr_name in currency_list:
            if default_currency not in curr_name:
                extra_fields += '    <option value="' + \
                    curr_name + '">' + curr_name + '</option>\n'
            else:
                extra_fields += '    <option value="' + \
                    curr_name + '" selected="selected">' + \
                    curr_name + '</option>\n'
        extra_fields += '  </select>\n'

        extra_fields += '</div>\n'

    citations_str = ''
    if endpoint == 'newblog':
        citations_filename = \
            acct_dir(base_dir, nickname, domain) + '/.citations.txt'
        if os.path.isfile(citations_filename):
            citations_str = '<div class="container">\n'
            citations_str += '<p><label class="labels">' + \
                translate['Citations'] + ':</label></p>\n'
            citations_str += '  <ul>\n'
            citations_separator = '#####'
            with open(citations_filename, 'r') as cit_file:
                citations = cit_file.readlines()
                for line in citations:
                    if citations_separator not in line:
                        continue
                    sections = line.strip().split(citations_separator)
                    if len(sections) != 3:
                        continue
                    title = sections[1]
                    link = sections[2]
                    citations_str += \
                        '    <li><a href="' + link + '"><cite>' + \
                        title + '</cite></a></li>'
            citations_str += '  </ul>\n'
            citations_str += '</div>\n'

    replies_section = ''
    date_and_location = ''
    if endpoint not in ('newshare', 'newwanted', 'newreport', 'newquestion'):

        if not is_new_reminder:
            replies_section = \
                '<div class="container">\n'
            if category != 'accommodation':
                replies_section += \
                    '<p><input type="checkbox" class="profilecheckbox" ' + \
                    'name="commentsEnabled" ' + \
                    'checked><label class="labels"> ' + \
                    translate['Allow replies.'] + '</label></p>\n'
            else:
                replies_section += \
                    '<input type="hidden" name="commentsEnabled" ' + \
                    'value="true">\n'
            supported_languages = get_supported_languages(base_dir)
            languages_dropdown = '<select id="themeDropdown" ' + \
                'name="languagesDropdown" class="theme">'
            for lang_name in supported_languages:
                translated_lang_name = lang_name
                if translate.get('lang_' + lang_name):
                    translated_lang_name = translate['lang_' + lang_name]
                languages_dropdown += '    <option value="' + \
                    lang_name.lower() + '">' + \
                    translated_lang_name + '</option>'
            languages_dropdown += '  </select><br>'
            languages_dropdown = \
                languages_dropdown.replace('<option value="' +
                                           system_language + '">',
                                           '<option value="' +
                                           system_language +
                                           '" selected>')
            replies_section += \
                '      <label class="labels">' + \
                translate['Language used'] + '</label>\n'
            replies_section += languages_dropdown
            replies_section += '</div>\n'

            date_and_location = \
                begin_edit_section('🗓️ ' + translate['Set a place and time'])
            if endpoint == 'newpost':
                date_and_location += \
                    '<p><input type="checkbox" class="profilecheckbox" ' + \
                    'name="pinToProfile"><label class="labels"> ' + \
                    translate['Pin this post to your profile.'] + \
                    '</label></p>\n'

            if not inReplyTo:
                date_and_location += \
                    '<p><input type="checkbox" class="profilecheckbox" ' + \
                    'name="schedulePost"><label class="labels"> ' + \
                    translate['This is a scheduled post.'] + '</label></p>\n'

            date_and_location += date_and_time_str

        maps_url = get_config_param(base_dir, 'mapsUrl')
        if not maps_url:
            maps_url = 'https://www.openstreetmap.org'
        if '://' not in maps_url:
            maps_url = 'https://' + maps_url
        location_label_with_link = \
            '<a href="' + maps_url + '" ' + \
            'rel="nofollow noopener noreferrer" target="_blank">' + \
            translate['Location'] + '</a>'
        date_and_location += \
            edit_text_field(location_label_with_link, 'location', '',
                            'https://www.openstreetmap.org/#map=')
        date_and_location += end_edit_section()

    instance_title = get_config_param(base_dir, 'instanceTitle')
    new_post_form = html_header_with_external_style(css_filename,
                                                    instance_title, None)

    new_post_form += \
        '<header>\n' + \
        '<a href="/users/' + nickname + '/' + default_timeline + \
        '" title="' + \
        translate['Switch to timeline view'] + '" alt="' + \
        translate['Switch to timeline view'] + '" ' + \
        'accesskey="' + access_keys['menuTimeline'] + '">\n'
    new_post_form += '<img loading="lazy" decoding="async" ' + \
        'class="timeline-banner" src="' + \
        '/users/' + nickname + '/' + banner_file + '" alt="" /></a>\n' + \
        '</header>\n'

    mentions_str = ''
    for ment in mentions:
        mention_nickname = get_nickname_from_actor(ment)
        if not mention_nickname:
            continue
        mention_domain, mention_port = get_domain_from_actor(ment)
        if not mention_domain:
            continue
        if mention_port:
            mentions_handle = \
                '@' + mention_nickname + '@' + \
                mention_domain + ':' + str(mention_port)
        else:
            mentions_handle = '@' + mention_nickname + '@' + mention_domain
        if mentions_handle not in mentions_str:
            mentions_str += mentions_handle + ' '

    # build suffixes so that any replies or mentions are
    # preserved when switching between scopes
    dropdown_new_post_suffix = '/newpost'
    dropdown_new_blog_suffix = '/newblog'
    dropdown_unlisted_suffix = '/newunlisted'
    dropdown_followers_suffix = '/newfollowers'
    dropdown_dm_suffix = '/newdm'
    dropdown_reminder_suffix = '/newreminder'
    dropdown_report_suffix = '/newreport'
    if inReplyTo or mentions:
        dropdown_new_post_suffix = ''
        dropdown_new_blog_suffix = ''
        dropdown_unlisted_suffix = ''
        dropdown_followers_suffix = ''
        dropdown_dm_suffix = ''
        dropdown_reminder_suffix = ''
        dropdown_report_suffix = ''
    if inReplyTo:
        dropdown_new_post_suffix += '?replyto=' + inReplyTo
        dropdown_new_blog_suffix += '?replyto=' + inReplyTo
        dropdown_unlisted_suffix += '?replyunlisted=' + inReplyTo
        dropdown_followers_suffix += '?replyfollowers=' + inReplyTo
        if reply_is_chat:
            dropdown_dm_suffix += '?replychat=' + inReplyTo
        else:
            dropdown_dm_suffix += '?replydm=' + inReplyTo
    for mentioned_actor in mentions:
        dropdown_new_post_suffix += '?mention=' + mentioned_actor
        dropdown_new_blog_suffix += '?mention=' + mentioned_actor
        dropdown_unlisted_suffix += '?mention=' + mentioned_actor
        dropdown_followers_suffix += '?mention=' + mentioned_actor
        dropdown_dm_suffix += '?mention=' + mentioned_actor
        dropdown_report_suffix += '?mention=' + mentioned_actor
    if conversationId and inReplyTo:
        dropdown_new_post_suffix += '?conversationId=' + conversationId
        dropdown_new_blog_suffix += '?conversationId=' + conversationId
        dropdown_unlisted_suffix += '?conversationId=' + conversationId
        dropdown_followers_suffix += '?conversationId=' + conversationId
        dropdown_dm_suffix += '?conversationId=' + conversationId

    drop_down_content = ''
    if not report_url and not share_description:
        drop_down_content = \
            _html_new_post_drop_down(scope_icon, scope_description,
                                     reply_str,
                                     translate,
                                     show_public_on_dropdown,
                                     default_timeline,
                                     path_base,
                                     dropdown_new_post_suffix,
                                     dropdown_new_blog_suffix,
                                     dropdown_unlisted_suffix,
                                     dropdown_followers_suffix,
                                     dropdown_dm_suffix,
                                     dropdown_reminder_suffix,
                                     dropdown_report_suffix,
                                     no_drop_down, access_keys)
    else:
        if not share_description:
            # reporting a post to moderator
            mentions_str = 'Re: ' + report_url + '\n\n' + mentions_str

    new_post_form += \
        '<form enctype="multipart/form-data" method="POST" ' + \
        'accept-charset="UTF-8" action="' + \
        path + '?' + endpoint + '?page=' + str(page_number) + '">\n'
    if reply_is_chat:
        new_post_form += \
            '    <input type="hidden" name="replychatmsg" value="yes">\n'
    if conversationId:
        new_post_form += \
            '    <input type="hidden" name="conversationId" value="' + \
            conversationId + '">\n'
    new_post_form += '  <div class="vertical-center">\n'
    new_post_form += \
        '    <label for="nickname"><b>' + new_post_text + '</b></label>\n'
    new_post_form += '    <div class="containerNewPost">\n'
    new_post_form += '      <table style="width:100%" border="0">\n'
    new_post_form += '        <colgroup>\n'
    new_post_form += '          <col span="1" style="width:70%">\n'
    new_post_form += '          <col span="1" style="width:10%">\n'
    if newswire and path.endswith('/newblog'):
        new_post_form += '          <col span="1" style="width:10%">\n'
        new_post_form += '          <col span="1" style="width:10%">\n'
    else:
        new_post_form += '          <col span="1" style="width:20%">\n'
    new_post_form += '        </colgroup>\n'
    new_post_form += '<tr>\n'
    new_post_form += '<td>' + drop_down_content + '</td>\n'

    new_post_form += \
        '      <td><a href="' + path_base + \
        '/searchemoji"><img loading="lazy" decoding="async" ' + \
        'class="emojisearch" src="/emoji/1F601.png" title="' + \
        translate['Search for emoji'] + '" alt="' + \
        translate['Search for emoji'] + '"/></a></td>\n'

    # for a new blog if newswire items exist then add a citations button
    if newswire and path.endswith('/newblog'):
        new_post_form += \
            '      <td><input type="submit" name="submitCitations" value="' + \
            translate['Citations'] + '"></td>\n'

    submit_text = translate['Submit']
    if custom_submit_text:
        submit_text = custom_submit_text
    new_post_form += \
        '      <td><input type="submit" name="submitPost" value="' + \
        submit_text + '" ' + \
        'accesskey="' + access_keys['submitButton'] + '"></td>\n'

    new_post_form += '      </tr>\n</table>\n'
    new_post_form += '    </div>\n'

    new_post_form += '    <div class="containerSubmitNewPost"><center>\n'

    new_post_form += '    </center></div>\n'

    new_post_form += reply_str
    if media_instance and not reply_str:
        new_post_form += new_post_image_section

    if not share_description:
        share_description = ''

    # for reminders show the date and time at the top
    if is_new_reminder:
        new_post_form += '<div class="containerNoOverflow">\n'
        new_post_form += date_and_time_str
        new_post_form += '</div>\n'

    new_post_form += \
        edit_text_field(placeholder_subject, 'subject', share_description)
    new_post_form += ''

    selected_str = ' selected'
    if inReplyTo or endpoint == 'newdm':
        if inReplyTo:
            new_post_form += \
                '    <label class="labels">' + placeholder_mentions + \
                '</label><br>\n'
        else:
            new_post_form += \
                '    <a href="/users/' + nickname + \
                '/followingaccounts" title="' + \
                translate['Show a list of addresses to send to'] + '">' \
                '<label class="labels">' + \
                translate['Send to'] + ':' + '</label> 📄</a><br>\n'
        new_post_form += \
            '    <input type="text" name="mentions" ' + \
            'list="followingHandles" value="' + mentions_str + '" selected>\n'
        new_post_form += \
            _html_following_data_list(base_dir, nickname, domain, domain_full)
        new_post_form += ''
        selected_str = ''

    new_post_form += \
        '    <br><label class="labels">' + placeholder_message + '</label>'
    if media_instance:
        message_box_height = 200

    if endpoint == 'newquestion':
        message_box_height = 100
    elif endpoint == 'newblog':
        message_box_height = 800

    new_post_form += \
        '    <textarea id="message" name="message" style="height:' + \
        str(message_box_height) + 'px"' + selected_str + \
        ' spellcheck="true" autocomplete="on">' + \
        '</textarea>\n'
    new_post_form += \
        extra_fields + citations_str + replies_section + date_and_location
    if not media_instance or reply_str:
        new_post_form += new_post_image_section
    new_post_form += new_post_emoji_section

    new_post_form += \
        '    <div class="container">\n' + \
        '      <input type="submit" name="submitPost" value="' + \
        submit_text + '">\n' + \
        '    </div>\n' + \
        '  </div>\n' + \
        '</form>\n'

    if not report_url:
        new_post_form = \
            new_post_form.replace('<body>', '<body onload="focusOnMessage()">')

    new_post_form += html_footer()
    return new_post_form
