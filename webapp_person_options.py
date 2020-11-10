__filename__ = "webapp_person_options.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.1.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

import os
from shutil import copyfile
from petnames import getPetName
from person import isPersonSnoozed
from posts import isModerator
from utils import getDomainFromActor
from utils import getNicknameFromActor
from utils import getCSS
from blocking import isBlocked
from follow import isFollowingActor
from followingCalendar import receivingCalendarEvents
from webapp_utils import htmlHeader
from webapp_utils import htmlFooter


def htmlPersonOptions(cssCache: {}, translate: {}, baseDir: str,
                      domain: str, domainFull: str,
                      originPathStr: str,
                      optionsActor: str,
                      optionsProfileUrl: str,
                      optionsLink: str,
                      pageNumber: int,
                      donateUrl: str,
                      xmppAddress: str,
                      matrixAddress: str,
                      ssbAddress: str,
                      blogAddress: str,
                      toxAddress: str,
                      PGPpubKey: str,
                      PGPfingerprint: str,
                      emailAddress) -> str:
    """Show options for a person: view/follow/block/report
    """
    optionsDomain, optionsPort = getDomainFromActor(optionsActor)
    optionsDomainFull = optionsDomain
    if optionsPort:
        if optionsPort != 80 and optionsPort != 443:
            optionsDomainFull = optionsDomain + ':' + str(optionsPort)

    if os.path.isfile(baseDir + '/accounts/options-background-custom.jpg'):
        if not os.path.isfile(baseDir + '/accounts/options-background.jpg'):
            copyfile(baseDir + '/accounts/options-background.jpg',
                     baseDir + '/accounts/options-background.jpg')

    followStr = 'Follow'
    blockStr = 'Block'
    nickname = None
    optionsNickname = None
    if originPathStr.startswith('/users/'):
        nickname = originPathStr.split('/users/')[1]
        if '/' in nickname:
            nickname = nickname.split('/')[0]
        if '?' in nickname:
            nickname = nickname.split('?')[0]
        followerDomain, followerPort = getDomainFromActor(optionsActor)
        if isFollowingActor(baseDir, nickname, domain, optionsActor):
            followStr = 'Unfollow'

        optionsNickname = getNicknameFromActor(optionsActor)
        optionsDomainFull = optionsDomain
        if optionsPort:
            if optionsPort != 80 and optionsPort != 443:
                optionsDomainFull = optionsDomain + ':' + str(optionsPort)
        if isBlocked(baseDir, nickname, domain,
                     optionsNickname, optionsDomainFull):
            blockStr = 'Block'

    optionsLinkStr = ''
    if optionsLink:
        optionsLinkStr = \
            '    <input type="hidden" name="postUrl" value="' + \
            optionsLink + '">\n'
    cssFilename = baseDir + '/epicyon-options.css'
    if os.path.isfile(baseDir + '/options.css'):
        cssFilename = baseDir + '/options.css'

    profileStyle = getCSS(baseDir, cssFilename, cssCache)
    if profileStyle:
        profileStyle = \
            profileStyle.replace('--follow-text-entry-width: 90%;',
                                 '--follow-text-entry-width: 20%;')

    if not os.path.isfile(baseDir + '/accounts/' +
                          'options-background.jpg'):
        profileStyle = \
            profileStyle.replace('background-image: ' +
                                 'url("options-background.jpg");',
                                 'background-image: none;')

    # To snooze, or not to snooze? That is the question
    snoozeButtonStr = 'Snooze'
    if nickname:
        if isPersonSnoozed(baseDir, nickname, domain, optionsActor):
            snoozeButtonStr = 'Unsnooze'

    donateStr = ''
    if donateUrl:
        donateStr = \
            '    <a href="' + donateUrl + \
            '"><button class="button" name="submitDonate">' + \
            translate['Donate'] + '</button></a>\n'

    optionsStr = htmlHeader(cssFilename, profileStyle)
    optionsStr += '<br><br>\n'
    optionsStr += '<div class="options">\n'
    optionsStr += '  <div class="optionsAvatar">\n'
    optionsStr += '  <center>\n'
    optionsStr += '  <a href="' + optionsActor + '">\n'
    optionsStr += '  <img loading="lazy" src="' + optionsProfileUrl + \
        '"/></a>\n'
    handle = getNicknameFromActor(optionsActor) + '@' + optionsDomain
    optionsStr += \
        '  <p class="optionsText">' + translate['Options for'] + \
        ' @' + handle + '</p>\n'
    if emailAddress:
        optionsStr += \
            '<p class="imText">' + translate['Email'] + \
            ': <a href="mailto:' + \
            emailAddress + '">' + emailAddress + '</a></p>\n'
    if xmppAddress:
        optionsStr += \
            '<p class="imText">' + translate['XMPP'] + \
            ': <a href="xmpp:' + xmppAddress + '">' + \
            xmppAddress + '</a></p>\n'
    if matrixAddress:
        optionsStr += \
            '<p class="imText">' + translate['Matrix'] + ': ' + \
            matrixAddress + '</p>\n'
    if ssbAddress:
        optionsStr += \
            '<p class="imText">SSB: ' + ssbAddress + '</p>\n'
    if blogAddress:
        optionsStr += \
            '<p class="imText">Blog: <a href="' + blogAddress + '">' + \
            blogAddress + '</a></p>\n'
    if toxAddress:
        optionsStr += \
            '<p class="imText">Tox: ' + toxAddress + '</p>\n'
    if PGPfingerprint:
        optionsStr += '<p class="pgp">PGP: ' + \
            PGPfingerprint.replace('\n', '<br>') + '</p>\n'
    if PGPpubKey:
        optionsStr += '<p class="pgp">' + \
            PGPpubKey.replace('\n', '<br>') + '</p>\n'
    optionsStr += '  <form method="POST" action="' + \
        originPathStr + '/personoptions">\n'
    optionsStr += '    <input type="hidden" name="pageNumber" value="' + \
        str(pageNumber) + '">\n'
    optionsStr += '    <input type="hidden" name="actor" value="' + \
        optionsActor + '">\n'
    optionsStr += '    <input type="hidden" name="avatarUrl" value="' + \
        optionsProfileUrl + '">\n'
    if optionsNickname:
        handle = optionsNickname + '@' + optionsDomainFull
        petname = getPetName(baseDir, nickname, domain, handle)
        optionsStr += \
            '    ' + translate['Petname'] + ': \n' + \
            '    <input type="text" name="optionpetname" value="' + \
            petname + '">\n' \
            '    <button type="submit" class="buttonsmall" ' + \
            'name="submitPetname">' + \
            translate['Submit'] + '</button><br>\n'

    # checkbox for receiving calendar events
    if isFollowingActor(baseDir, nickname, domain, optionsActor):
        checkboxStr = \
            '    <input type="checkbox" ' + \
            'class="profilecheckbox" name="onCalendar" checked> ' + \
            translate['Receive calendar events from this account'] + \
            '\n    <button type="submit" class="buttonsmall" ' + \
            'name="submitOnCalendar">' + \
            translate['Submit'] + '</button><br>\n'
        if not receivingCalendarEvents(baseDir, nickname, domain,
                                       optionsNickname, optionsDomainFull):
            checkboxStr = checkboxStr.replace(' checked>', '>')
        optionsStr += checkboxStr

    # checkbox for permission to post to newswire
    if optionsDomainFull == domainFull:
        if isModerator(baseDir, nickname) and \
           not isModerator(baseDir, optionsNickname):
            newswireBlockedFilename = \
                baseDir + '/accounts/' + \
                optionsNickname + '@' + optionsDomain + '/.nonewswire'
            checkboxStr = \
                '    <input type="checkbox" ' + \
                'class="profilecheckbox" name="postsToNews" checked> ' + \
                translate['Allow news posts'] + \
                '\n    <button type="submit" class="buttonsmall" ' + \
                'name="submitPostToNews">' + \
                translate['Submit'] + '</button><br>\n'
            if os.path.isfile(newswireBlockedFilename):
                checkboxStr = checkboxStr.replace(' checked>', '>')
            optionsStr += checkboxStr

    optionsStr += optionsLinkStr
    backPath = '/'
    if nickname:
        backPath = '/users/' + nickname
    optionsStr += \
        '    <a href="' + backPath + '"><button type="button" ' + \
        'class="buttonIcon" name="submitBack">' + translate['Go Back'] + \
        '</button></a>'
    optionsStr += \
        '    <button type="submit" class="button" name="submitView">' + \
        translate['View'] + '</button>'
    optionsStr += donateStr
    optionsStr += \
        '    <button type="submit" class="button" name="submit' + \
        followStr + '">' + translate[followStr] + '</button>'
    optionsStr += \
        '    <button type="submit" class="button" name="submit' + \
        blockStr + '">' + translate[blockStr] + '</button>'
    optionsStr += \
        '    <button type="submit" class="button" name="submitDM">' + \
        translate['DM'] + '</button>'
    optionsStr += \
        '    <button type="submit" class="button" name="submit' + \
        snoozeButtonStr + '">' + translate[snoozeButtonStr] + '</button>'
    optionsStr += \
        '    <button type="submit" class="button" name="submitReport">' + \
        translate['Report'] + '</button>'

    personNotes = ''
    personNotesFilename = \
        baseDir + '/accounts/' + nickname + '@' + domain + \
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
        'name="optionnotes" style="height:400px">' + \
        personNotes + '</textarea>\n'

    optionsStr += '  </form>\n'
    optionsStr += '</center>\n'
    optionsStr += '</div>\n'
    optionsStr += '</div>\n'
    optionsStr += htmlFooter()
    return optionsStr
