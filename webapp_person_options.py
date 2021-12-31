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
                        originPathStr: str,
                        optionsActor: str,
                        optionsProfileUrl: str,
                        optionsLink: str,
                        pageNumber: int,
                        donate_url: str,
                        webAddress: str,
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
                        backToPath: str,
                        lockedAccount: bool,
                        movedTo: str,
                        alsoKnownAs: [],
                        text_mode_banner: str,
                        news_instance: bool,
                        authorized: bool,
                        access_keys: {},
                        isGroup: bool) -> str:
    """Show options for a person: view/follow/block/report
    """
    optionsDomain, optionsPort = get_domain_from_actor(optionsActor)
    optionsDomainFull = get_full_domain(optionsDomain, optionsPort)

    if os.path.isfile(base_dir + '/accounts/options-background-custom.jpg'):
        if not os.path.isfile(base_dir + '/accounts/options-background.jpg'):
            copyfile(base_dir + '/accounts/options-background.jpg',
                     base_dir + '/accounts/options-background.jpg')

    dormant = False
    followStr = 'Follow'
    if isGroup:
        followStr = 'Join'
    blockStr = 'Block'
    nickname = None
    optionsNickname = None
    followsYou = False
    if originPathStr.startswith('/users/'):
        nickname = originPathStr.split('/users/')[1]
        if '/' in nickname:
            nickname = nickname.split('/')[0]
        if '?' in nickname:
            nickname = nickname.split('?')[0]
        followerDomain, followerPort = get_domain_from_actor(optionsActor)
        if is_following_actor(base_dir, nickname, domain, optionsActor):
            followStr = 'Unfollow'
            if isGroup:
                followStr = 'Leave'
            dormant = \
                is_dormant(base_dir, nickname, domain, optionsActor,
                           dormant_months)

        optionsNickname = get_nickname_from_actor(optionsActor)
        optionsDomainFull = get_full_domain(optionsDomain, optionsPort)
        followsYou = \
            is_follower_of_person(base_dir,
                                  nickname, domain,
                                  optionsNickname, optionsDomainFull)
        if is_blocked(base_dir, nickname, domain,
                      optionsNickname, optionsDomainFull):
            blockStr = 'Block'

    optionsLinkStr = ''
    if optionsLink:
        optionsLinkStr = \
            '    <input type="hidden" name="postUrl" value="' + \
            optionsLink + '">\n'
    css_filename = base_dir + '/epicyon-options.css'
    if os.path.isfile(base_dir + '/options.css'):
        css_filename = base_dir + '/options.css'

    # To snooze, or not to snooze? That is the question
    snoozeButtonStr = 'Snooze'
    if nickname:
        if is_person_snoozed(base_dir, nickname, domain, optionsActor):
            snoozeButtonStr = 'Unsnooze'

    donateStr = ''
    if donate_url:
        donateStr = \
            '    <a href="' + donate_url + \
            ' tabindex="-1""><button class="button" name="submitDonate">' + \
            translate['Donate'] + '</button></a>\n'

    instanceTitle = \
        get_config_param(base_dir, 'instanceTitle')
    optionsStr = \
        html_header_with_external_style(css_filename, instanceTitle, None)
    optionsStr += html_keyboard_navigation(text_mode_banner, {}, {})
    optionsStr += '<br><br>\n'
    optionsStr += '<div class="options">\n'
    optionsStr += '  <div class="optionsAvatar">\n'
    optionsStr += '  <center>\n'
    optionsStr += '  <a href="' + optionsActor + '">\n'
    optionsStr += '  <img loading="lazy" src="' + optionsProfileUrl + \
        '" alt="" ' + get_broken_link_substitute() + '/></a>\n'
    handle = get_nickname_from_actor(optionsActor) + '@' + optionsDomain
    handleShown = handle
    if lockedAccount:
        handleShown += '🔒'
    if movedTo:
        handleShown += ' ⌂'
    if dormant:
        handleShown += ' 💤'
    optionsStr += \
        '  <p class="optionsText">' + translate['Options for'] + \
        ' @' + handleShown + '</p>\n'
    if followsYou:
        optionsStr += \
            '  <p class="optionsText">' + translate['Follows you'] + '</p>\n'
    if movedTo:
        newNickname = get_nickname_from_actor(movedTo)
        newDomain, newPort = get_domain_from_actor(movedTo)
        if newNickname and newDomain:
            newHandle = newNickname + '@' + newDomain
            optionsStr += \
                '  <p class="optionsText">' + \
                translate['New account'] + \
                ': <a href="' + movedTo + '">@' + newHandle + '</a></p>\n'
    elif alsoKnownAs:
        otherAccountsHtml = \
            '  <p class="optionsText">' + \
            translate['Other accounts'] + ': '

        ctr = 0
        if isinstance(alsoKnownAs, list):
            for altActor in alsoKnownAs:
                if altActor == optionsActor:
                    continue
                if ctr > 0:
                    otherAccountsHtml += ' '
                ctr += 1
                altDomain, altPort = get_domain_from_actor(altActor)
                otherAccountsHtml += \
                    '<a href="' + altActor + '">' + altDomain + '</a>'
        elif isinstance(alsoKnownAs, str):
            if alsoKnownAs != optionsActor:
                ctr += 1
                altDomain, altPort = get_domain_from_actor(alsoKnownAs)
                otherAccountsHtml += \
                    '<a href="' + alsoKnownAs + '">' + altDomain + '</a>'
        otherAccountsHtml += '</p>\n'
        if ctr > 0:
            optionsStr += otherAccountsHtml
    if email_address:
        optionsStr += \
            '<p class="imText">' + translate['Email'] + \
            ': <a href="mailto:' + \
            email_address + '">' + remove_html(email_address) + '</a></p>\n'
    if xmpp_address:
        optionsStr += \
            '<p class="imText">' + translate['XMPP'] + \
            ': <a href="xmpp:' + remove_html(xmpp_address) + '">' + \
            xmpp_address + '</a></p>\n'
    if matrix_address:
        optionsStr += \
            '<p class="imText">' + translate['Matrix'] + ': ' + \
            remove_html(matrix_address) + '</p>\n'
    if ssb_address:
        optionsStr += \
            '<p class="imText">SSB: ' + remove_html(ssb_address) + '</p>\n'
    if blog_address:
        optionsStr += \
            '<p class="imText">Blog: <a href="' + \
            remove_html(blog_address) + '">' + \
            remove_html(blog_address) + '</a></p>\n'
    if tox_address:
        optionsStr += \
            '<p class="imText">Tox: ' + remove_html(tox_address) + '</p>\n'
    if briar_address:
        if briar_address.startswith('briar://'):
            optionsStr += \
                '<p class="imText">' + \
                remove_html(briar_address) + '</p>\n'
        else:
            optionsStr += \
                '<p class="imText">briar://' + \
                remove_html(briar_address) + '</p>\n'
    if jami_address:
        optionsStr += \
            '<p class="imText">Jami: ' + remove_html(jami_address) + '</p>\n'
    if cwtch_address:
        optionsStr += \
            '<p class="imText">Cwtch: ' + remove_html(cwtch_address) + '</p>\n'
    if enigma_pub_key:
        optionsStr += \
            '<p class="imText">Enigma: ' + \
            remove_html(enigma_pub_key) + '</p>\n'
    if pgp_fingerprint:
        optionsStr += '<p class="pgp">PGP: ' + \
            remove_html(pgp_fingerprint).replace('\n', '<br>') + '</p>\n'
    if pgp_pub_key:
        optionsStr += '<p class="pgp">' + \
            remove_html(pgp_pub_key).replace('\n', '<br>') + '</p>\n'
    optionsStr += '  <form method="POST" action="' + \
        originPathStr + '/personoptions">\n'
    optionsStr += '    <input type="hidden" name="pageNumber" value="' + \
        str(pageNumber) + '">\n'
    optionsStr += '    <input type="hidden" name="actor" value="' + \
        optionsActor + '">\n'
    optionsStr += '    <input type="hidden" name="avatarUrl" value="' + \
        optionsProfileUrl + '">\n'
    if authorized:
        if originPathStr == '/users/' + nickname:
            if optionsNickname:
                # handle = optionsNickname + '@' + optionsDomainFull
                petname = get_pet_name(base_dir, nickname, domain, handle)
                optionsStr += \
                    '    ' + translate['Petname'] + ': \n' + \
                    '    <input type="text" name="optionpetname" value="' + \
                    petname + '" ' + \
                    'accesskey="' + access_keys['enterPetname'] + '">\n' \
                    '    <button type="submit" class="buttonsmall" ' + \
                    'name="submitPetname">' + \
                    translate['Submit'] + '</button><br>\n'

            # Notify when a post arrives from this person
            if is_following_actor(base_dir, nickname, domain, optionsActor):
                checkboxStr = \
                    '    <input type="checkbox" class="profilecheckbox" ' + \
                    'name="notifyOnPost" checked> 🔔' + \
                    translate['Notify me when this account posts'] + \
                    '\n    <button type="submit" class="buttonsmall" ' + \
                    'name="submitNotifyOnPost">' + \
                    translate['Submit'] + '</button><br>\n'
                if not notify_when_person_posts(base_dir, nickname, domain,
                                                optionsNickname,
                                                optionsDomainFull):
                    checkboxStr = checkboxStr.replace(' checked>', '>')
                optionsStr += checkboxStr

                checkboxStr = \
                    '    <input type="checkbox" ' + \
                    'class="profilecheckbox" name="onCalendar" checked> ' + \
                    translate['Receive calendar events from this account'] + \
                    '\n    <button type="submit" class="buttonsmall" ' + \
                    'name="submitOnCalendar">' + \
                    translate['Submit'] + '</button><br>\n'
                if not receiving_calendar_events(base_dir, nickname, domain,
                                                 optionsNickname,
                                                 optionsDomainFull):
                    checkboxStr = checkboxStr.replace(' checked>', '>')
                optionsStr += checkboxStr

            # checkbox for permission to post to newswire
            newswirePostsPermitted = False
            if optionsDomainFull == domain_full:
                admin_nickname = get_config_param(base_dir, 'admin')
                if (nickname == admin_nickname or
                    (is_moderator(base_dir, nickname) and
                     not is_moderator(base_dir, optionsNickname))):
                    newswireBlockedFilename = \
                        base_dir + '/accounts/' + \
                        optionsNickname + '@' + optionsDomain + '/.nonewswire'
                    checkboxStr = \
                        '    <input type="checkbox" ' + \
                        'class="profilecheckbox" ' + \
                        'name="postsToNews" checked> ' + \
                        translate['Allow news posts'] + \
                        '\n    <button type="submit" class="buttonsmall" ' + \
                        'name="submitPostToNews">' + \
                        translate['Submit'] + '</button><br>\n'
                    if os.path.isfile(newswireBlockedFilename):
                        checkboxStr = checkboxStr.replace(' checked>', '>')
                    else:
                        newswirePostsPermitted = True
                    optionsStr += checkboxStr

            # whether blogs created by this account are moderated on
            # the newswire
            if newswirePostsPermitted:
                moderatedFilename = \
                    base_dir + '/accounts/' + \
                    optionsNickname + '@' + \
                    optionsDomain + '/.newswiremoderated'
                checkboxStr = \
                    '    <input type="checkbox" ' + \
                    'class="profilecheckbox" name="modNewsPosts" checked> ' + \
                    translate['News posts are moderated'] + \
                    '\n    <button type="submit" class="buttonsmall" ' + \
                    'name="submitModNewsPosts">' + \
                    translate['Submit'] + '</button><br>\n'
                if not os.path.isfile(moderatedFilename):
                    checkboxStr = checkboxStr.replace(' checked>', '>')
                optionsStr += checkboxStr

            # checkbox for permission to post to featured articles
            if news_instance and optionsDomainFull == domain_full:
                admin_nickname = get_config_param(base_dir, 'admin')
                if (nickname == admin_nickname or
                    (is_moderator(base_dir, nickname) and
                     not is_moderator(base_dir, optionsNickname))):
                    checkboxStr = \
                        '    <input type="checkbox" ' + \
                        'class="profilecheckbox" ' + \
                        'name="postsToFeatures" checked> ' + \
                        translate['Featured writer'] + \
                        '\n    <button type="submit" class="buttonsmall" ' + \
                        'name="submitPostToFeatures">' + \
                        translate['Submit'] + '</button><br>\n'
                    if not is_featured_writer(base_dir, optionsNickname,
                                              optionsDomain):
                        checkboxStr = checkboxStr.replace(' checked>', '>')
                    optionsStr += checkboxStr

    optionsStr += optionsLinkStr
    backPath = '/'
    if nickname:
        backPath = '/users/' + nickname + '/' + default_timeline
        if 'moderation' in backToPath:
            backPath = '/users/' + nickname + '/moderation'
    if authorized and originPathStr == '/users/' + nickname:
        optionsStr += \
            '    <a href="' + backPath + '"><button type="button" ' + \
            'class="buttonIcon" name="submitBack" ' + \
            'accesskey="' + access_keys['menuTimeline'] + '">' + \
            translate['Go Back'] + '</button></a>\n'
    else:
        optionsStr += \
            '    <a href="' + originPathStr + '"><button type="button" ' + \
            'class="buttonIcon" name="submitBack" accesskey="' + \
            access_keys['menuTimeline'] + '">' + translate['Go Back'] + \
            '</button></a>\n'
    if authorized:
        optionsStr += \
            '    <button type="submit" class="button" ' + \
            'name="submitView" accesskey="' + \
            access_keys['viewButton'] + '">' + \
            translate['View'] + '</button>\n'
    optionsStr += donateStr
    if authorized:
        optionsStr += \
            '    <button type="submit" class="button" name="submit' + \
            followStr + \
            '" accesskey="' + access_keys['followButton'] + '">' + \
            translate[followStr] + '</button>\n'
        optionsStr += \
            '    <button type="submit" class="button" name="submit' + \
            blockStr + '" accesskey="' + access_keys['blockButton'] + '">' + \
            translate[blockStr] + '</button>\n'
        optionsStr += \
            '    <button type="submit" class="button" name="submitDM" ' + \
            'accesskey="' + access_keys['menuDM'] + '">' + \
            translate['DM'] + '</button>\n'
        optionsStr += \
            '    <button type="submit" class="button" name="submit' + \
            snoozeButtonStr + '" accesskey="' + \
            access_keys['snoozeButton'] + '">' + translate[snoozeButtonStr] + \
            '</button>\n'
        optionsStr += \
            '    <button type="submit" class="button" ' + \
            'name="submitReport" accesskey="' + \
            access_keys['reportButton'] + '">' + \
            translate['Report'] + '</button>\n'

        if is_moderator(base_dir, nickname):
            optionsStr += \
                '    <button type="submit" class="button" ' + \
                'name="submitPersonInfo" accesskey="' + \
                access_keys['infoButton'] + '">' + \
                translate['Info'] + '</button>\n'

        personNotes = ''
        if originPathStr == '/users/' + nickname:
            personNotesFilename = \
                acct_dir(base_dir, nickname, domain) + \
                '/notes/' + handle + '.txt'
            if os.path.isfile(personNotesFilename):
                with open(personNotesFilename, 'r') as fp:
                    personNotes = fp.read()

        optionsStr += \
            '    <br><br>' + translate['Notes'] + ': \n'
        optionsStr += '    <button type="submit" class="buttonsmall" ' + \
            'name="submitPersonNotes">' + \
            translate['Submit'] + '</button><br>\n'
        optionsStr += \
            '    <textarea id="message" ' + \
            'name="optionnotes" style="height:400px" spellcheck="true" ' + \
            'accesskey="' + access_keys['enterNotes'] + '">' + \
            personNotes + '</textarea>\n'

    optionsStr += \
        '  </form>\n' + \
        '</center>\n' + \
        '</div>\n' + \
        '</div>\n'
    optionsStr += html_footer()
    return optionsStr
