__filename__ = "webapp_person_options.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Web Interface"

import os
from shutil import copyfile
from petnames import get_pet_name
from person import is_person_snoozed
from posts import is_moderator
from utils import get_full_domain
from utils import get_config_param
from utils import is_dormant
from utils import remove_html
from utils import get_domain_from_actor
from utils import get_nickname_from_actor
from utils import is_featured_writer
from utils import acct_dir
from blocking import is_blocked
from follow import is_follower_of_person
from follow import is_following_actor
from followingCalendar import receiving_calendar_events
from notifyOnPost import notify_when_person_posts
from webapp_utils import html_header_with_external_style
from webapp_utils import html_footer
from webapp_utils import get_broken_link_substitute
from webapp_utils import html_keyboard_navigation


def html_person_options(default_timeline: str,
                        css_cache: {}, translate: {}, base_dir: str,
                        domain: str, domain_full: str,
                        origin_path_str: str,
                        options_actor: str,
                        options_profile_url: str,
                        options_link: str,
                        page_number: int,
                        donate_url: str,
                        web_address: str,
                        xmpp_address: str,
                        matrix_address: str,
                        ssb_address: str,
                        blog_address: str,
                        tox_address: str,
                        briar_address: str,
                        jami_address: str,
                        cwtch_address: str,
                        enigma_pub_key: str,
                        pgp_pub_key: str,
                        pgp_fingerprint: str,
                        email_address: str,
                        dormant_months: int,
                        back_to_path: str,
                        locked_account: bool,
                        moved_to: str,
                        also_known_as: [],
                        text_mode_banner: str,
                        news_instance: bool,
                        authorized: bool,
                        access_keys: {},
                        is_group: bool) -> str:
    """Show options for a person: view/follow/block/report
    """
    options_domain, options_port = get_domain_from_actor(options_actor)
    options_domain_full = get_full_domain(options_domain, options_port)

    if os.path.isfile(base_dir + '/accounts/options-background-custom.jpg'):
        if not os.path.isfile(base_dir + '/accounts/options-background.jpg'):
            copyfile(base_dir + '/accounts/options-background.jpg',
                     base_dir + '/accounts/options-background.jpg')

    dormant = False
    follow_str = 'Follow'
    if is_group:
        follow_str = 'Join'
    block_str = 'Block'
    nickname = None
    options_nickname = None
    follows_you = False
    if origin_path_str.startswith('/users/'):
        nickname = origin_path_str.split('/users/')[1]
        if '/' in nickname:
            nickname = nickname.split('/')[0]
        if '?' in nickname:
            nickname = nickname.split('?')[0]
#        follower_domain, follower_port = get_domain_from_actor(options_actor)
        if is_following_actor(base_dir, nickname, domain, options_actor):
            follow_str = 'Unfollow'
            if is_group:
                follow_str = 'Leave'
            dormant = \
                is_dormant(base_dir, nickname, domain, options_actor,
                           dormant_months)

        options_nickname = get_nickname_from_actor(options_actor)
        options_domain_full = get_full_domain(options_domain, options_port)
        follows_you = \
            is_follower_of_person(base_dir,
                                  nickname, domain,
                                  options_nickname, options_domain_full)
        if is_blocked(base_dir, nickname, domain,
                      options_nickname, options_domain_full):
            block_str = 'Block'

    options_link_str = ''
    if options_link:
        options_link_str = \
            '    <input type="hidden" name="postUrl" value="' + \
            options_link + '">\n'
    css_filename = base_dir + '/epicyon-options.css'
    if os.path.isfile(base_dir + '/options.css'):
        css_filename = base_dir + '/options.css'

    # To snooze, or not to snooze? That is the question
    snooze_button_str = 'Snooze'
    if nickname:
        if is_person_snoozed(base_dir, nickname, domain, options_actor):
            snooze_button_str = 'Unsnooze'

    donate_str = ''
    if donate_url:
        donate_str = \
            '    <a href="' + donate_url + \
            ' tabindex="-1""><button class="button" name="submitDonate">' + \
            translate['Donate'] + '</button></a>\n'

    instance_title = \
        get_config_param(base_dir, 'instanceTitle')
    options_str = \
        html_header_with_external_style(css_filename, instance_title, None)
    options_str += html_keyboard_navigation(text_mode_banner, {}, {})
    options_str += '<br><br>\n'
    options_str += '<div class="options">\n'
    options_str += '  <div class="optionsAvatar">\n'
    options_str += '  <center>\n'
    options_str += '  <a href="' + options_actor + '">\n'
    options_str += '  <img loading="lazy" src="' + options_profile_url + \
        '" alt="" ' + get_broken_link_substitute() + '/></a>\n'
    handle = get_nickname_from_actor(options_actor) + '@' + options_domain
    handle_shown = handle
    if locked_account:
        handle_shown += '🔒'
    if moved_to:
        handle_shown += ' ⌂'
    if dormant:
        handle_shown += ' 💤'
    options_str += \
        '  <p class="optionsText">' + translate['Options for'] + \
        ' @' + handle_shown + '</p>\n'
    if follows_you:
        options_str += \
            '  <p class="optionsText">' + translate['Follows you'] + '</p>\n'
    if moved_to:
        new_nickname = get_nickname_from_actor(moved_to)
        new_domain, _ = get_domain_from_actor(moved_to)
        if new_nickname and new_domain:
            new_handle = new_nickname + '@' + new_domain
            options_str += \
                '  <p class="optionsText">' + \
                translate['New account'] + \
                ': <a href="' + moved_to + '">@' + new_handle + '</a></p>\n'
    elif also_known_as:
        other_accounts_html = \
            '  <p class="optionsText">' + \
            translate['Other accounts'] + ': '

        ctr = 0
        if isinstance(also_known_as, list):
            for alt_actor in also_known_as:
                if alt_actor == options_actor:
                    continue
                if ctr > 0:
                    other_accounts_html += ' '
                ctr += 1
                alt_domain, _ = get_domain_from_actor(alt_actor)
                other_accounts_html += \
                    '<a href="' + alt_actor + '">' + alt_domain + '</a>'
        elif isinstance(also_known_as, str):
            if also_known_as != options_actor:
                ctr += 1
                alt_domain, _ = get_domain_from_actor(also_known_as)
                other_accounts_html += \
                    '<a href="' + also_known_as + '">' + alt_domain + '</a>'
        other_accounts_html += '</p>\n'
        if ctr > 0:
            options_str += other_accounts_html
    if email_address:
        options_str += \
            '<p class="imText">' + translate['Email'] + \
            ': <a href="mailto:' + \
            email_address + '">' + remove_html(email_address) + '</a></p>\n'
    if xmpp_address:
        options_str += \
            '<p class="imText">' + translate['XMPP'] + \
            ': <a href="xmpp:' + remove_html(xmpp_address) + '">' + \
            xmpp_address + '</a></p>\n'
    if matrix_address:
        options_str += \
            '<p class="imText">' + translate['Matrix'] + ': ' + \
            remove_html(matrix_address) + '</p>\n'
    if ssb_address:
        options_str += \
            '<p class="imText">SSB: ' + remove_html(ssb_address) + '</p>\n'
    if blog_address:
        options_str += \
            '<p class="imText">Blog: <a href="' + \
            remove_html(blog_address) + '">' + \
            remove_html(blog_address) + '</a></p>\n'
    if tox_address:
        options_str += \
            '<p class="imText">Tox: ' + remove_html(tox_address) + '</p>\n'
    if briar_address:
        if briar_address.startswith('briar://'):
            options_str += \
                '<p class="imText">' + \
                remove_html(briar_address) + '</p>\n'
        else:
            options_str += \
                '<p class="imText">briar://' + \
                remove_html(briar_address) + '</p>\n'
    if jami_address:
        options_str += \
            '<p class="imText">Jami: ' + remove_html(jami_address) + '</p>\n'
    if cwtch_address:
        options_str += \
            '<p class="imText">Cwtch: ' + remove_html(cwtch_address) + '</p>\n'
    if enigma_pub_key:
        options_str += \
            '<p class="imText">Enigma: ' + \
            remove_html(enigma_pub_key) + '</p>\n'
    if pgp_fingerprint:
        options_str += '<p class="pgp">PGP: ' + \
            remove_html(pgp_fingerprint).replace('\n', '<br>') + '</p>\n'
    if pgp_pub_key:
        options_str += '<p class="pgp">' + \
            remove_html(pgp_pub_key).replace('\n', '<br>') + '</p>\n'
    options_str += '  <form method="POST" action="' + \
        origin_path_str + '/personoptions">\n'
    options_str += '    <input type="hidden" name="pageNumber" value="' + \
        str(page_number) + '">\n'
    options_str += '    <input type="hidden" name="actor" value="' + \
        options_actor + '">\n'
    options_str += '    <input type="hidden" name="avatarUrl" value="' + \
        options_profile_url + '">\n'
    if authorized:
        if origin_path_str == '/users/' + nickname:
            if options_nickname:
                # handle = options_nickname + '@' + options_domain_full
                petname = get_pet_name(base_dir, nickname, domain, handle)
                options_str += \
                    '    ' + translate['Petname'] + ': \n' + \
                    '    <input type="text" name="optionpetname" value="' + \
                    petname + '" ' + \
                    'accesskey="' + access_keys['enterPetname'] + '">\n' \
                    '    <button type="submit" class="buttonsmall" ' + \
                    'name="submitPetname">' + \
                    translate['Submit'] + '</button><br>\n'

            # Notify when a post arrives from this person
            if is_following_actor(base_dir, nickname, domain, options_actor):
                checkbox_str = \
                    '    <input type="checkbox" class="profilecheckbox" ' + \
                    'name="notifyOnPost" checked> 🔔' + \
                    translate['Notify me when this account posts'] + \
                    '\n    <button type="submit" class="buttonsmall" ' + \
                    'name="submitNotifyOnPost">' + \
                    translate['Submit'] + '</button><br>\n'
                if not notify_when_person_posts(base_dir, nickname, domain,
                                                options_nickname,
                                                options_domain_full):
                    checkbox_str = checkbox_str.replace(' checked>', '>')
                options_str += checkbox_str

                checkbox_str = \
                    '    <input type="checkbox" ' + \
                    'class="profilecheckbox" name="onCalendar" checked> ' + \
                    translate['Receive calendar events from this account'] + \
                    '\n    <button type="submit" class="buttonsmall" ' + \
                    'name="submitOnCalendar">' + \
                    translate['Submit'] + '</button><br>\n'
                if not receiving_calendar_events(base_dir, nickname, domain,
                                                 options_nickname,
                                                 options_domain_full):
                    checkbox_str = checkbox_str.replace(' checked>', '>')
                options_str += checkbox_str

            # checkbox for permission to post to newswire
            newswire_posts_permitted = False
            if options_domain_full == domain_full:
                admin_nickname = get_config_param(base_dir, 'admin')
                if (nickname == admin_nickname or
                    (is_moderator(base_dir, nickname) and
                     not is_moderator(base_dir, options_nickname))):
                    newswire_blocked_filename = \
                        base_dir + '/accounts/' + \
                        options_nickname + '@' + options_domain + \
                        '/.nonewswire'
                    checkbox_str = \
                        '    <input type="checkbox" ' + \
                        'class="profilecheckbox" ' + \
                        'name="postsToNews" checked> ' + \
                        translate['Allow news posts'] + \
                        '\n    <button type="submit" class="buttonsmall" ' + \
                        'name="submitPostToNews">' + \
                        translate['Submit'] + '</button><br>\n'
                    if os.path.isfile(newswire_blocked_filename):
                        checkbox_str = checkbox_str.replace(' checked>', '>')
                    else:
                        newswire_posts_permitted = True
                    options_str += checkbox_str

            # whether blogs created by this account are moderated on
            # the newswire
            if newswire_posts_permitted:
                moderated_filename = \
                    base_dir + '/accounts/' + \
                    options_nickname + '@' + \
                    options_domain + '/.newswiremoderated'
                checkbox_str = \
                    '    <input type="checkbox" ' + \
                    'class="profilecheckbox" name="modNewsPosts" checked> ' + \
                    translate['News posts are moderated'] + \
                    '\n    <button type="submit" class="buttonsmall" ' + \
                    'name="submitModNewsPosts">' + \
                    translate['Submit'] + '</button><br>\n'
                if not os.path.isfile(moderated_filename):
                    checkbox_str = checkbox_str.replace(' checked>', '>')
                options_str += checkbox_str

            # checkbox for permission to post to featured articles
            if news_instance and options_domain_full == domain_full:
                admin_nickname = get_config_param(base_dir, 'admin')
                if (nickname == admin_nickname or
                    (is_moderator(base_dir, nickname) and
                     not is_moderator(base_dir, options_nickname))):
                    checkbox_str = \
                        '    <input type="checkbox" ' + \
                        'class="profilecheckbox" ' + \
                        'name="postsToFeatures" checked> ' + \
                        translate['Featured writer'] + \
                        '\n    <button type="submit" class="buttonsmall" ' + \
                        'name="submitPostToFeatures">' + \
                        translate['Submit'] + '</button><br>\n'
                    if not is_featured_writer(base_dir, options_nickname,
                                              options_domain):
                        checkbox_str = checkbox_str.replace(' checked>', '>')
                    options_str += checkbox_str

    options_str += options_link_str
    back_path = '/'
    if nickname:
        back_path = '/users/' + nickname + '/' + default_timeline
        if 'moderation' in back_to_path:
            back_path = '/users/' + nickname + '/moderation'
    if authorized and origin_path_str == '/users/' + nickname:
        options_str += \
            '    <a href="' + back_path + '"><button type="button" ' + \
            'class="buttonIcon" name="submitBack" ' + \
            'accesskey="' + access_keys['menuTimeline'] + '">' + \
            translate['Go Back'] + '</button></a>\n'
    else:
        options_str += \
            '    <a href="' + origin_path_str + '"><button type="button" ' + \
            'class="buttonIcon" name="submitBack" accesskey="' + \
            access_keys['menuTimeline'] + '">' + translate['Go Back'] + \
            '</button></a>\n'
    if authorized:
        options_str += \
            '    <button type="submit" class="button" ' + \
            'name="submitView" accesskey="' + \
            access_keys['viewButton'] + '">' + \
            translate['View'] + '</button>\n'
    options_str += donate_str
    if authorized:
        options_str += \
            '    <button type="submit" class="button" name="submit' + \
            follow_str + \
            '" accesskey="' + access_keys['followButton'] + '">' + \
            translate[follow_str] + '</button>\n'
        options_str += \
            '    <button type="submit" class="button" name="submit' + \
            block_str + '" accesskey="' + access_keys['blockButton'] + '">' + \
            translate[block_str] + '</button>\n'
        options_str += \
            '    <button type="submit" class="button" name="submitDM" ' + \
            'accesskey="' + access_keys['menuDM'] + '">' + \
            translate['DM'] + '</button>\n'
        options_str += \
            '    <button type="submit" class="button" name="submit' + \
            snooze_button_str + '" accesskey="' + \
            access_keys['snoozeButton'] + '">' + \
            translate[snooze_button_str] + '</button>\n'
        options_str += \
            '    <button type="submit" class="button" ' + \
            'name="submitReport" accesskey="' + \
            access_keys['reportButton'] + '">' + \
            translate['Report'] + '</button>\n'

        if is_moderator(base_dir, nickname):
            options_str += \
                '    <button type="submit" class="button" ' + \
                'name="submitPersonInfo" accesskey="' + \
                access_keys['infoButton'] + '">' + \
                translate['Info'] + '</button>\n'

        person_notes = ''
        if origin_path_str == '/users/' + nickname:
            person_notes_filename = \
                acct_dir(base_dir, nickname, domain) + \
                '/notes/' + handle + '.txt'
            if os.path.isfile(person_notes_filename):
                with open(person_notes_filename, 'r') as fp_notes:
                    person_notes = fp_notes.read()

        options_str += \
            '    <br><br>' + translate['Notes'] + ': \n'
        options_str += '    <button type="submit" class="buttonsmall" ' + \
            'name="submitPersonNotes">' + \
            translate['Submit'] + '</button><br>\n'
        options_str += \
            '    <textarea id="message" ' + \
            'name="optionnotes" style="height:400px" spellcheck="true" ' + \
            'accesskey="' + access_keys['enterNotes'] + '">' + \
            person_notes + '</textarea>\n'

    options_str += \
        '  </form>\n' + \
        '</center>\n' + \
        '</div>\n' + \
        '</div>\n'
    options_str += html_footer()
    return options_str
