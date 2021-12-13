__filename__ = "desktop_client.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Client"

import os
import html
import time
import sys
import select
import webbrowser
import urllib.parse
from pathlib import Path
from random import randint
from utils import getBaseContentFromPost
from utils import hasObjectDict
from utils import getFullDomain
from utils import isDM
from utils import loadTranslationsFromFile
from utils import removeHtml
from utils import getNicknameFromActor
from utils import getDomainFromActor
from utils import isPGPEncrypted
from utils import localActorUrl
from session import createSession
from speaker import speakableText
from speaker import getSpeakerPitch
from speaker import getSpeakerRate
from speaker import getSpeakerRange
from like import sendLikeViaServer
from like import sendUndoLikeViaServer
from follow import approveFollowRequestViaServer
from follow import denyFollowRequestViaServer
from follow import getFollowRequestsViaServer
from follow import getFollowingViaServer
from follow import getFollowersViaServer
from follow import sendFollowRequestViaServer
from follow import sendUnfollowRequestViaServer
from posts import sendBlockViaServer
from posts import sendUndoBlockViaServer
from posts import sendMuteViaServer
from posts import sendUndoMuteViaServer
from posts import sendPostViaServer
from posts import c2sBoxJson
from posts import downloadAnnounce
from announce import sendAnnounceViaServer
from announce import sendUndoAnnounceViaServer
from pgp import pgpLocalPublicKey
from pgp import pgpDecrypt
from pgp import hasLocalPGPkey
from pgp import pgpEncryptToActor
from pgp import pgpPublicKeyUpload
from like import noOfLikes
from bookmarks import sendBookmarkViaServer
from bookmarks import sendUndoBookmarkViaServer
from delete import sendDeleteViaServer
from person import getActorJson


def _desktopHelp() -> None:
    """Shows help
    """
    _desktopClearScreen()
    indent = '   '
    print('')
    print(indent + _highlightText('Help Commands:'))
    print('')
    print(indent + 'quit                                  ' +
          'Exit from the desktop client')
    print(indent + 'show dm|sent|inbox|replies|bookmarks  ' +
          'Show a timeline')
    print(indent + 'mute                                  ' +
          'Turn off the screen reader')
    print(indent + 'speak                                 ' +
          'Turn on the screen reader')
    print(indent + 'sounds on                             ' +
          'Turn on notification sounds')
    print(indent + 'sounds off                            ' +
          'Turn off notification sounds')
    print(indent + 'rp                                    ' +
          'Repeat the last post')
    print(indent + 'like                                  ' +
          'Like the last post')
    print(indent + 'unlike                                ' +
          'Unlike the last post')
    print(indent + 'bookmark                              ' +
          'Bookmark the last post')
    print(indent + 'unbookmark                            ' +
          'Unbookmark the last post')
    print(indent + 'block [post number|handle]            ' +
          'Block someone via post number or handle')
    print(indent + 'unblock [handle]                      ' +
          'Unblock someone')
    print(indent + 'mute                                  ' +
          'Mute the last post')
    print(indent + 'unmute                                ' +
          'Unmute the last post')
    print(indent + 'reply                                 ' +
          'Reply to the last post')
    print(indent + 'post                                  ' +
          'Create a new post')
    print(indent + 'post to [handle]                      ' +
          'Create a new direct message')
    print(indent + 'announce/boost                        ' +
          'Boost the last post')
    print(indent + 'follow [handle]                       ' +
          'Make a follow request')
    print(indent + 'unfollow [handle]                     ' +
          'Stop following the give handle')
    print(indent + 'next                                  ' +
          'Next page in the timeline')
    print(indent + 'prev                                  ' +
          'Previous page in the timeline')
    print(indent + 'read [post number]                    ' +
          'Read a post from a timeline')
    print(indent + 'open [post number]                    ' +
          'Open web links within a timeline post')
    print(indent + 'profile [post number or handle]       ' +
          'Show profile for the person who made the given post')
    print(indent + 'following [page number]               ' +
          'Show accounts that you are following')
    print(indent + 'followers [page number]               ' +
          'Show accounts that are following you')
    print(indent + 'approve [handle]                      ' +
          'Approve a follow request')
    print(indent + 'deny [handle]                         ' +
          'Deny a follow request')
    print(indent + 'pgp                                   ' +
          'Show your PGP public key')
    print('')


def _createDesktopConfig(actor: str) -> None:
    """Sets up directories for desktop client configuration
    """
    homeDir = str(Path.home())
    if not os.path.isdir(homeDir + '/.config'):
        os.mkdir(homeDir + '/.config')
    if not os.path.isdir(homeDir + '/.config/epicyon'):
        os.mkdir(homeDir + '/.config/epicyon')
    nickname = getNicknameFromActor(actor)
    domain, port = getDomainFromActor(actor)
    handle = nickname + '@' + domain
    if port != 443 and port != 80:
        handle += '_' + str(port)
    readPostsDir = homeDir + '/.config/epicyon/' + handle
    if not os.path.isdir(readPostsDir):
        os.mkdir(readPostsDir)


def _markPostAsRead(actor: str, postId: str, postCategory: str) -> None:
    """Marks the given post as read by the given actor
    """
    homeDir = str(Path.home())
    _createDesktopConfig(actor)
    nickname = getNicknameFromActor(actor)
    domain, port = getDomainFromActor(actor)
    handle = nickname + '@' + domain
    if port != 443 and port != 80:
        handle += '_' + str(port)
    readPostsDir = homeDir + '/.config/epicyon/' + handle
    readPostsFilename = readPostsDir + '/' + postCategory + '.txt'
    if os.path.isfile(readPostsFilename):
        if postId in open(readPostsFilename).read():
            return
        try:
            # prepend to read posts file
            postId += '\n'
            with open(readPostsFilename, 'r+') as readFile:
                content = readFile.read()
                if postId not in content:
                    readFile.seek(0, 0)
                    readFile.write(postId + content)
        except Exception as e:
            print('WARN: Failed to mark post as read' + str(e))
    else:
        with open(readPostsFilename, 'w+') as readFile:
            readFile.write(postId + '\n')


def _hasReadPost(actor: str, postId: str, postCategory: str) -> bool:
    """Returns true if the given post has been read by the actor
    """
    homeDir = str(Path.home())
    _createDesktopConfig(actor)
    nickname = getNicknameFromActor(actor)
    domain, port = getDomainFromActor(actor)
    handle = nickname + '@' + domain
    if port != 443 and port != 80:
        handle += '_' + str(port)
    readPostsDir = homeDir + '/.config/epicyon/' + handle
    readPostsFilename = readPostsDir + '/' + postCategory + '.txt'
    if os.path.isfile(readPostsFilename):
        if postId in open(readPostsFilename).read():
            return True
    return False


def _postIsToYou(actor: str, postJsonObject: {}) -> bool:
    """Returns true if the post is to the actor
    """
    toYourActor = False
    if postJsonObject.get('to'):
        if actor in postJsonObject['to']:
            toYourActor = True
    if not toYourActor and postJsonObject.get('cc'):
        if actor in postJsonObject['cc']:
            toYourActor = True
    if not toYourActor and hasObjectDict(postJsonObject):
        if postJsonObject['object'].get('to'):
            if actor in postJsonObject['object']['to']:
                toYourActor = True
        if not toYourActor and postJsonObject['object'].get('cc'):
            if actor in postJsonObject['object']['cc']:
                toYourActor = True
    return toYourActor


def _newDesktopNotifications(actor: str, inboxJson: {},
                             notifyJson: {}) -> None:
    """Looks for changes in the inbox and adds notifications
    """
    notifyJson['dmNotifyChanged'] = False
    notifyJson['repliesNotifyChanged'] = False
    if not inboxJson:
        return
    if not inboxJson.get('orderedItems'):
        return
    DMdone = False
    replyDone = False
    for postJsonObject in inboxJson['orderedItems']:
        if not postJsonObject.get('id'):
            continue
        if not postJsonObject.get('type'):
            continue
        if postJsonObject['type'] == 'Announce':
            continue
        if not _postIsToYou(actor, postJsonObject):
            continue
        if isDM(postJsonObject):
            if not DMdone:
                if not _hasReadPost(actor, postJsonObject['id'], 'dm'):
                    changed = False
                    if not notifyJson.get('dmPostId'):
                        changed = True
                    else:
                        if notifyJson['dmPostId'] != postJsonObject['id']:
                            changed = True
                    if changed:
                        notifyJson['dmNotify'] = True
                        notifyJson['dmNotifyChanged'] = True
                        notifyJson['dmPostId'] = postJsonObject['id']
                    DMdone = True
        else:
            if not replyDone:
                if not _hasReadPost(actor, postJsonObject['id'], 'replies'):
                    changed = False
                    if not notifyJson.get('repliesPostId'):
                        changed = True
                    else:
                        if notifyJson['repliesPostId'] != postJsonObject['id']:
                            changed = True
                    if changed:
                        notifyJson['repliesNotify'] = True
                        notifyJson['repliesNotifyChanged'] = True
                        notifyJson['repliesPostId'] = postJsonObject['id']
                    replyDone = True


def _desktopClearScreen() -> None:
    """Clears the screen
    """
    os.system('cls' if os.name == 'nt' else 'clear')


def _desktopShowBanner() -> None:
    """Shows the banner at the top
    """
    bannerFilename = 'banner.txt'
    if not os.path.isfile(bannerFilename):
        bannerTheme = 'starlight'
        bannerFilename = 'theme/' + bannerTheme + '/banner.txt'
        if not os.path.isfile(bannerFilename):
            return
    with open(bannerFilename, 'r') as bannerFile:
        banner = bannerFile.read()
        if banner:
            print(banner + '\n')


def _desktopWaitForCmd(timeout: int, debug: bool) -> str:
    """Waits for a command to be entered with a timeout
    Returns the command, or None on timeout
    """
    i, o, e = select.select([sys.stdin], [], [], timeout)

    if (i):
        text = sys.stdin.readline().strip()
        if debug:
            print("Text entered: " + text)
        return text
    else:
        if debug:
            print("Timeout")
        return None


def _speakerEspeak(espeak, pitch: int, rate: int, srange: int,
                   sayText: str) -> None:
    """Speaks the given text with espeak
    """
    espeak.set_parameter(espeak.Parameter.Pitch, pitch)
    espeak.set_parameter(espeak.Parameter.Rate, rate)
    espeak.set_parameter(espeak.Parameter.Range, srange)
    espeak.synth(html.unescape(sayText))


def _speakerPicospeaker(pitch: int, rate: int, systemLanguage: str,
                        sayText: str) -> None:
    """TTS using picospeaker
    """
    speakerLang = 'en-GB'
    supportedLanguages = {
        "fr": "fr-FR",
        "es": "es-ES",
        "de": "de-DE",
        "it": "it-IT"
    }
    for lang, speakerStr in supportedLanguages.items():
        if systemLanguage.startswith(lang):
            speakerLang = speakerStr
            break
    sayText = str(sayText).replace('"', "'")
    speakerCmd = 'picospeaker ' + \
        '-l ' + speakerLang + \
        ' -r ' + str(rate) + \
        ' -p ' + str(pitch) + ' "' + \
        html.unescape(str(sayText)) + '" 2> /dev/null'
    os.system(speakerCmd)


def _playNotificationSound(soundFilename: str, player: str = 'ffplay') -> None:
    """Plays a sound
    """
    if not os.path.isfile(soundFilename):
        return

    if player == 'ffplay':
        os.system('ffplay ' + soundFilename +
                  ' -autoexit -hide_banner -nodisp 2> /dev/null')


def _desktopNotification(notificationType: str,
                         title: str, message: str) -> None:
    """Shows a desktop notification
    """
    if not notificationType:
        return

    if notificationType == 'notify-send':
        # Ubuntu
        os.system('notify-send "' + title + '" "' + message + '"')
    elif notificationType == 'zenity':
        # Zenity
        os.system('zenity --notification --title "' + title +
                  '" --text="' + message + '"')
    elif notificationType == 'osascript':
        # Mac
        os.system("osascript -e 'display notification \"" +
                  message + "\" with title \"" + title + "\"'")
    elif notificationType == 'New-BurntToastNotification':
        # Windows
        os.system("New-BurntToastNotification -Text \"" +
                  title + "\", '" + message + "'")


def _textToSpeech(sayStr: str, screenreader: str,
                  pitch: int, rate: int, srange: int,
                  systemLanguage: str, espeak=None) -> None:
    """Say something via TTS
    """
    # speak the post content
    if screenreader == 'espeak':
        _speakerEspeak(espeak, pitch, rate, srange, sayStr)
    elif screenreader == 'picospeaker':
        _speakerPicospeaker(pitch, rate,
                            systemLanguage, sayStr)


def _sayCommand(content: str, sayStr: str, screenreader: str,
                systemLanguage: str,
                espeak=None,
                speakerName: str = 'screen reader',
                speakerGender: str = 'They/Them') -> None:
    """Speaks a command
    """
    print(content)
    if not screenreader:
        return

    pitch = getSpeakerPitch(speakerName,
                            screenreader, speakerGender)
    rate = getSpeakerRate(speakerName, screenreader)
    srange = getSpeakerRange(speakerName)

    _textToSpeech(sayStr, screenreader,
                  pitch, rate, srange,
                  systemLanguage, espeak)


def _desktopReplyToPost(session, postId: str,
                        baseDir: str, nickname: str, password: str,
                        domain: str, port: int, httpPrefix: str,
                        cachedWebfingers: {}, personCache: {},
                        debug: bool, subject: str,
                        screenreader: str, systemLanguage: str,
                        espeak, conversationId: str,
                        lowBandwidth: bool,
                        contentLicenseUrl: str,
                        signingPrivateKeyPem: str) -> None:
    """Use the desktop client to send a reply to the most recent post
    """
    if '://' not in postId:
        return
    toNickname = getNicknameFromActor(postId)
    toDomain, toPort = getDomainFromActor(postId)
    sayStr = 'Replying to ' + toNickname + '@' + toDomain
    _sayCommand(sayStr, sayStr,
                screenreader, systemLanguage, espeak)
    sayStr = 'Type your reply message, then press Enter.'
    _sayCommand(sayStr, sayStr, screenreader, systemLanguage, espeak)
    replyMessage = input()
    if not replyMessage:
        sayStr = 'No reply was entered.'
        _sayCommand(sayStr, sayStr, screenreader, systemLanguage, espeak)
        return
    replyMessage = replyMessage.strip()
    if not replyMessage:
        sayStr = 'No reply was entered.'
        _sayCommand(sayStr, sayStr, screenreader, systemLanguage, espeak)
        return
    print('')
    sayStr = 'You entered this reply:'
    _sayCommand(sayStr, sayStr, screenreader, systemLanguage, espeak)
    _sayCommand(replyMessage, replyMessage, screenreader,
                systemLanguage, espeak)
    sayStr = 'Send this reply, yes or no?'
    _sayCommand(sayStr, sayStr, screenreader, systemLanguage, espeak)
    yesno = input()
    if 'y' not in yesno.lower():
        sayStr = 'Abandoning reply'
        _sayCommand(sayStr, sayStr, screenreader, systemLanguage, espeak)
        return
    ccUrl = None
    followersOnly = False
    attach = None
    mediaType = None
    attachedImageDescription = None
    isArticle = False
    subject = None
    commentsEnabled = True
    city = 'London, England'
    sayStr = 'Sending reply'
    _sayCommand(sayStr, sayStr, screenreader, systemLanguage, espeak)
    if sendPostViaServer(signingPrivateKeyPem, __version__,
                         baseDir, session, nickname, password,
                         domain, port,
                         toNickname, toDomain, toPort, ccUrl,
                         httpPrefix, replyMessage, followersOnly,
                         commentsEnabled, attach, mediaType,
                         attachedImageDescription, city,
                         cachedWebfingers, personCache, isArticle,
                         systemLanguage, lowBandwidth,
                         contentLicenseUrl,
                         debug, postId, postId,
                         conversationId, subject) == 0:
        sayStr = 'Reply sent'
    else:
        sayStr = 'Reply failed'
    _sayCommand(sayStr, sayStr, screenreader, systemLanguage, espeak)


def _desktopNewPost(session,
                    baseDir: str, nickname: str, password: str,
                    domain: str, port: int, httpPrefix: str,
                    cachedWebfingers: {}, personCache: {},
                    debug: bool,
                    screenreader: str, systemLanguage: str,
                    espeak, lowBandwidth: bool,
                    contentLicenseUrl: str,
                    signingPrivateKeyPem: str) -> None:
    """Use the desktop client to create a new post
    """
    conversationId = None
    sayStr = 'Create new post'
    _sayCommand(sayStr, sayStr, screenreader, systemLanguage, espeak)
    sayStr = 'Type your post, then press Enter.'
    _sayCommand(sayStr, sayStr, screenreader, systemLanguage, espeak)
    newMessage = input()
    if not newMessage:
        sayStr = 'No post was entered.'
        _sayCommand(sayStr, sayStr, screenreader, systemLanguage, espeak)
        return
    newMessage = newMessage.strip()
    if not newMessage:
        sayStr = 'No post was entered.'
        _sayCommand(sayStr, sayStr, screenreader, systemLanguage, espeak)
        return
    print('')
    sayStr = 'You entered this public post:'
    _sayCommand(sayStr, sayStr, screenreader, systemLanguage, espeak)
    _sayCommand(newMessage, newMessage, screenreader, systemLanguage, espeak)
    sayStr = 'Send this post, yes or no?'
    _sayCommand(sayStr, sayStr, screenreader, systemLanguage, espeak)
    yesno = input()
    if 'y' not in yesno.lower():
        sayStr = 'Abandoning new post'
        _sayCommand(sayStr, sayStr, screenreader, systemLanguage, espeak)
        return
    ccUrl = None
    followersOnly = False
    attach = None
    mediaType = None
    attachedImageDescription = None
    city = 'London, England'
    isArticle = False
    subject = None
    commentsEnabled = True
    subject = None
    sayStr = 'Sending'
    _sayCommand(sayStr, sayStr, screenreader, systemLanguage, espeak)
    if sendPostViaServer(signingPrivateKeyPem, __version__,
                         baseDir, session, nickname, password,
                         domain, port,
                         None, '#Public', port, ccUrl,
                         httpPrefix, newMessage, followersOnly,
                         commentsEnabled, attach, mediaType,
                         attachedImageDescription, city,
                         cachedWebfingers, personCache, isArticle,
                         systemLanguage, lowBandwidth,
                         contentLicenseUrl,
                         debug, None, None,
                         conversationId, subject) == 0:
        sayStr = 'Post sent'
    else:
        sayStr = 'Post failed'
    _sayCommand(sayStr, sayStr, screenreader, systemLanguage, espeak)


def _safeMessage(content: str) -> str:
    """Removes anything potentially unsafe from a string
    """
    return content.replace('`', '').replace('$(', '$ (')


def _timelineIsEmpty(boxJson: {}) -> bool:
    """Returns true if the given timeline is empty
    """
    empty = False
    if not boxJson:
        empty = True
    else:
        if not isinstance(boxJson, dict):
            empty = True
        elif not boxJson.get('orderedItems'):
            empty = True
    return empty


def _getFirstItemId(boxJson: {}) -> str:
    """Returns the id of the first item in the timeline
    """
    if _timelineIsEmpty(boxJson):
        return
    if len(boxJson['orderedItems']) == 0:
        return
    return boxJson['orderedItems'][0]['id']


def _textOnlyContent(content: str) -> str:
    """Remove formatting from the given string
    """
    content = urllib.parse.unquote_plus(content)
    content = html.unescape(content)
    return removeHtml(content)


def _getImageDescription(postJsonObject: {}) -> str:
    """Returns a image description/s on a post
    """
    imageDescription = ''
    if not postJsonObject['object'].get('attachment'):
        return imageDescription

    attachList = postJsonObject['object']['attachment']
    if not isinstance(attachList, list):
        return imageDescription

    # for each attachment
    for img in attachList:
        if not isinstance(img, dict):
            continue
        if not img.get('name'):
            continue
        if not isinstance(img['name'], str):
            continue
        messageStr = img['name']
        if messageStr:
            messageStr = messageStr.strip()
            if not messageStr.endswith('.'):
                imageDescription += messageStr + '. '
            else:
                imageDescription += messageStr + ' '
    return imageDescription


def _showLikesOnPost(postJsonObject: {}, maxLikes: int) -> None:
    """Shows the likes on a post
    """
    if not hasObjectDict(postJsonObject):
        return
    if not postJsonObject['object'].get('likes'):
        return
    if not isinstance(postJsonObject['object']['likes'], dict):
        return
    if not postJsonObject['object']['likes'].get('items'):
        return
    if not isinstance(postJsonObject['object']['likes']['items'], list):
        return
    print('')
    ctr = 0
    for item in postJsonObject['object']['likes']['items']:
        print('  ❤ ' + str(item['actor']))
        ctr += 1
        if ctr >= maxLikes:
            break


def _showRepliesOnPost(postJsonObject: {}, maxReplies: int) -> None:
    """Shows the replies on a post
    """
    if not hasObjectDict(postJsonObject):
        return
    if not postJsonObject['object'].get('replies'):
        return
    if not isinstance(postJsonObject['object']['replies'], dict):
        return
    if not postJsonObject['object']['replies'].get('items'):
        return
    if not isinstance(postJsonObject['object']['replies']['items'], list):
        return
    print('')
    ctr = 0
    for item in postJsonObject['object']['replies']['items']:
        print('  ↰ ' + str(item['url']))
        ctr += 1
        if ctr >= maxReplies:
            break


def _readLocalBoxPost(session, nickname: str, domain: str,
                      httpPrefix: str, baseDir: str, boxName: str,
                      pageNumber: int, index: int, boxJson: {},
                      systemLanguage: str,
                      screenreader: str, espeak,
                      translate: {}, yourActor: str,
                      domainFull: str, personCache: {},
                      signingPrivateKeyPem: str,
                      blockedCache: {}) -> {}:
    """Reads a post from the given timeline
    Returns the post json
    """
    if _timelineIsEmpty(boxJson):
        return {}

    postJsonObject = _desktopGetBoxPostObject(boxJson, index)
    if not postJsonObject:
        return {}
    gender = 'They/Them'

    boxNameStr = boxName
    if boxName.startswith('tl'):
        boxNameStr = boxName[2:]
    sayStr = 'Reading ' + boxNameStr + ' post ' + str(index) + \
        ' from page ' + str(pageNumber) + '.'
    sayStr2 = sayStr.replace(' dm ', ' DM ')
    _sayCommand(sayStr, sayStr2, screenreader, systemLanguage, espeak)
    print('')

    if postJsonObject['type'] == 'Announce':
        actor = postJsonObject['actor']
        nameStr = getNicknameFromActor(actor)
        recentPostsCache = {}
        allowLocalNetworkAccess = False
        YTReplacementDomain = None
        twitterReplacementDomain = None
        postJsonObject2 = \
            downloadAnnounce(session, baseDir,
                             httpPrefix,
                             nickname, domain,
                             postJsonObject,
                             __version__, translate,
                             YTReplacementDomain,
                             twitterReplacementDomain,
                             allowLocalNetworkAccess,
                             recentPostsCache, False,
                             systemLanguage,
                             domainFull, personCache,
                             signingPrivateKeyPem,
                             blockedCache)
        if postJsonObject2:
            if hasObjectDict(postJsonObject2):
                if postJsonObject2['object'].get('attributedTo') and \
                   postJsonObject2['object'].get('content'):
                    attributedTo = postJsonObject2['object']['attributedTo']
                    content = \
                        getBaseContentFromPost(postJsonObject2, systemLanguage)
                    if isinstance(attributedTo, str) and content:
                        actor = attributedTo
                        nameStr += ' ' + translate['announces'] + ' ' + \
                            getNicknameFromActor(actor)
                        sayStr = nameStr
                        _sayCommand(sayStr, sayStr, screenreader,
                                    systemLanguage, espeak)
                        print('')
                        if screenreader:
                            time.sleep(2)
                        content = \
                            _textOnlyContent(content)
                        content += _getImageDescription(postJsonObject2)
                        messageStr, detectedLinks = \
                            speakableText(baseDir, content, translate)
                        sayStr = content
                        _sayCommand(sayStr, messageStr, screenreader,
                                    systemLanguage, espeak)
                        return postJsonObject2
        return {}

    attributedTo = postJsonObject['object']['attributedTo']
    if not attributedTo:
        return {}
    content = getBaseContentFromPost(postJsonObject, systemLanguage)
    if not isinstance(attributedTo, str) or \
       not isinstance(content, str):
        return {}
    actor = attributedTo
    nameStr = getNicknameFromActor(actor)
    content = _textOnlyContent(content)
    content += _getImageDescription(postJsonObject)

    if isPGPEncrypted(content):
        sayStr = 'Encrypted message. Please enter your passphrase.'
        _sayCommand(sayStr, sayStr, screenreader, systemLanguage, espeak)
        content = pgpDecrypt(domain, content, actor, signingPrivateKeyPem)
        if isPGPEncrypted(content):
            sayStr = 'Message could not be decrypted'
            _sayCommand(sayStr, sayStr, screenreader, systemLanguage, espeak)
            return {}

    content = _safeMessage(content)
    messageStr, detectedLinks = speakableText(baseDir, content, translate)

    if screenreader:
        time.sleep(2)

    # say the speaker's name
    _sayCommand(nameStr, nameStr, screenreader,
                systemLanguage, espeak, nameStr, gender)
    print('')

    if postJsonObject['object'].get('inReplyTo'):
        print('Replying to ' + postJsonObject['object']['inReplyTo'] + '\n')

    if screenreader:
        time.sleep(2)

    # speak the post content
    _sayCommand(content, messageStr, screenreader,
                systemLanguage, espeak, nameStr, gender)

    _showLikesOnPost(postJsonObject, 10)
    _showRepliesOnPost(postJsonObject, 10)

    # if the post is addressed to you then mark it as read
    if _postIsToYou(yourActor, postJsonObject):
        if isDM(postJsonObject):
            _markPostAsRead(yourActor, postJsonObject['id'], 'dm')
        else:
            _markPostAsRead(yourActor, postJsonObject['id'], 'replies')

    return postJsonObject


def _desktopShowActor(baseDir: str, actorJson: {}, translate: {},
                      systemLanguage: str, screenreader: str,
                      espeak) -> None:
    """Shows information for the given actor
    """
    actor = actorJson['id']
    actorNickname = getNicknameFromActor(actor)
    actorDomain, actorPort = getDomainFromActor(actor)
    actorDomainFull = getFullDomain(actorDomain, actorPort)
    handle = '@' + actorNickname + '@' + actorDomainFull

    sayStr = 'Profile for ' + html.unescape(handle)
    _sayCommand(sayStr, sayStr, screenreader, systemLanguage, espeak)
    print(actor)
    if actorJson.get('movedTo'):
        sayStr = 'Moved to ' + html.unescape(actorJson['movedTo'])
        _sayCommand(sayStr, sayStr, screenreader, systemLanguage, espeak)
    if actorJson.get('alsoKnownAs'):
        alsoKnownAsStr = ''
        ctr = 0
        for altActor in actorJson['alsoKnownAs']:
            if ctr > 0:
                alsoKnownAsStr += ', '
            ctr += 1
            alsoKnownAsStr += altActor

        sayStr = 'Also known as ' + html.unescape(alsoKnownAsStr)
        _sayCommand(sayStr, sayStr, screenreader, systemLanguage, espeak)
    if actorJson.get('summary'):
        sayStr = html.unescape(removeHtml(actorJson['summary']))
        sayStr = sayStr.replace('"', "'")
        sayStr2 = speakableText(baseDir, sayStr, translate)[0]
        _sayCommand(sayStr, sayStr2, screenreader, systemLanguage, espeak)


def _desktopShowProfile(session, nickname: str, domain: str,
                        httpPrefix: str, baseDir: str, boxName: str,
                        pageNumber: int, index: int, boxJson: {},
                        systemLanguage: str,
                        screenreader: str, espeak,
                        translate: {}, yourActor: str,
                        postJsonObject: {}, signingPrivateKeyPem: str) -> {}:
    """Shows the profile of the actor for the given post
    Returns the actor json
    """
    if _timelineIsEmpty(boxJson):
        return {}

    if not postJsonObject:
        postJsonObject = _desktopGetBoxPostObject(boxJson, index)
        if not postJsonObject:
            return {}

    actor = None
    if postJsonObject['type'] == 'Announce':
        nickname = getNicknameFromActor(postJsonObject['object'])
        if nickname:
            nickStr = '/' + nickname + '/'
            if nickStr in postJsonObject['object']:
                actor = \
                    postJsonObject['object'].split(nickStr)[0] + \
                    '/' + nickname
    else:
        actor = postJsonObject['object']['attributedTo']

    if not actor:
        return {}

    isHttp = False
    if 'http://' in actor:
        isHttp = True
    actorJson, asHeader = \
        getActorJson(domain, actor, isHttp, False, False, True,
                     signingPrivateKeyPem)

    _desktopShowActor(baseDir, actorJson, translate,
                      systemLanguage, screenreader, espeak)

    return actorJson


def _desktopShowProfileFromHandle(session, nickname: str, domain: str,
                                  httpPrefix: str, baseDir: str, boxName: str,
                                  handle: str,
                                  systemLanguage: str,
                                  screenreader: str, espeak,
                                  translate: {}, yourActor: str,
                                  postJsonObject: {},
                                  signingPrivateKeyPem: str) -> {}:
    """Shows the profile for a handle
    Returns the actor json
    """
    actorJson, asHeader = \
        getActorJson(domain, handle, False, False, False, True,
                     signingPrivateKeyPem)

    _desktopShowActor(baseDir, actorJson, translate,
                      systemLanguage, screenreader, espeak)

    return actorJson


def _desktopGetBoxPostObject(boxJson: {}, index: int) -> {}:
    """Gets the post with the given index from the timeline
    """
    ctr = 0
    for postJsonObject in boxJson['orderedItems']:
        if not postJsonObject.get('type'):
            continue
        if not postJsonObject.get('object'):
            continue
        if postJsonObject['type'] == 'Announce':
            if not isinstance(postJsonObject['object'], str):
                continue
            ctr += 1
            if ctr == index:
                return postJsonObject
            continue
        if not hasObjectDict(postJsonObject):
            continue
        if not postJsonObject['object'].get('published'):
            continue
        if not postJsonObject['object'].get('content'):
            continue
        ctr += 1
        if ctr == index:
            return postJsonObject
    return None


def _formatPublished(published: str) -> str:
    """Formats the published time for display on timeline
    """
    dateStr = published.split('T')[0]
    monthStr = dateStr.split('-')[1]
    dayStr = dateStr.split('-')[2]
    timeStr = published.split('T')[1]
    hourStr = timeStr.split(':')[0]
    minStr = timeStr.split(':')[1]
    return monthStr + '-' + dayStr + ' ' + hourStr + ':' + minStr + 'Z'


def _padToWidth(content: str, width: int) -> str:
    """Pads the given string to the given width
    """
    if len(content) > width:
        content = content[:width]
    else:
        while len(content) < width:
            content += ' '
    return content


def _highlightText(text: str) -> str:
    """Returns a highlighted version of the given text
    """
    return '\33[7m' + text + '\33[0m'


def _desktopShowBox(indent: str,
                    followRequestsJson: {},
                    yourActor: str, boxName: str, boxJson: {},
                    translate: {},
                    screenreader: str, systemLanguage: str, espeak,
                    pageNumber: int,
                    newReplies: bool,
                    newDMs: bool) -> bool:
    """Shows online timeline
    """
    numberWidth = 2
    nameWidth = 16
    contentWidth = 50

    # title
    _desktopClearScreen()
    _desktopShowBanner()

    notificationIcons = ''
    if boxName.startswith('tl'):
        boxNameStr = boxName[2:]
    else:
        boxNameStr = boxName
    titleStr = _highlightText(boxNameStr.upper())
    # if newDMs:
    #     notificationIcons += ' 📩'
    # if newReplies:
    #     notificationIcons += ' 📨'

    if notificationIcons:
        while len(titleStr) < 95 - len(notificationIcons):
            titleStr += ' '
        titleStr += notificationIcons
    print(indent + titleStr + '\n')

    if _timelineIsEmpty(boxJson):
        boxStr = boxNameStr
        if boxName == 'dm':
            boxStr = 'DM'
        sayStr = indent + 'You have no ' + boxStr + ' posts yet.'
        _sayCommand(sayStr, sayStr, screenreader, systemLanguage, espeak)
        print('')
        return False

    ctr = 1
    for postJsonObject in boxJson['orderedItems']:
        if not postJsonObject.get('type'):
            continue
        if postJsonObject['type'] == 'Announce':
            if postJsonObject.get('actor') and \
               postJsonObject.get('object'):
                if isinstance(postJsonObject['object'], str):
                    authorActor = postJsonObject['actor']
                    name = getNicknameFromActor(authorActor) + ' ⮌'
                    name = _padToWidth(name, nameWidth)
                    ctrStr = str(ctr)
                    posStr = _padToWidth(ctrStr, numberWidth)
                    published = _formatPublished(postJsonObject['published'])
                    announcedNickname = \
                        getNicknameFromActor(postJsonObject['object'])
                    announcedDomain, announcedPort = \
                        getDomainFromActor(postJsonObject['object'])
                    announcedHandle = announcedNickname + '@' + announcedDomain
                    lineStr = \
                        indent + str(posStr) + ' | ' + name + ' | ' + \
                        published + ' | ' + \
                        _padToWidth(announcedHandle, contentWidth)
                    print(lineStr)
                    ctr += 1
                    continue

        if not hasObjectDict(postJsonObject):
            continue
        if not postJsonObject['object'].get('published'):
            continue
        if not postJsonObject['object'].get('content'):
            continue
        ctrStr = str(ctr)
        posStr = _padToWidth(ctrStr, numberWidth)

        authorActor = postJsonObject['object']['attributedTo']
        contentWarning = None
        if postJsonObject['object'].get('summary'):
            contentWarning = '⚡' + \
                _padToWidth(postJsonObject['object']['summary'],
                            contentWidth)
        name = getNicknameFromActor(authorActor)

        # append icons to the end of the name
        spaceAdded = False
        if postJsonObject['object'].get('inReplyTo'):
            if not spaceAdded:
                spaceAdded = True
                name += ' '
            name += '↲'
            if postJsonObject['object'].get('replies'):
                repliesList = postJsonObject['object']['replies']
                if repliesList.get('items'):
                    items = repliesList['items']
                    for i in range(int(items)):
                        name += '↰'
                        if i > 10:
                            break
        likesCount = noOfLikes(postJsonObject)
        if likesCount > 10:
            likesCount = 10
        for like in range(likesCount):
            if not spaceAdded:
                spaceAdded = True
                name += ' '
            name += '❤'
        name = _padToWidth(name, nameWidth)

        published = _formatPublished(postJsonObject['published'])

        contentStr = getBaseContentFromPost(postJsonObject, systemLanguage)
        content = _textOnlyContent(contentStr)
        if boxName != 'dm':
            if isDM(postJsonObject):
                content = '📧' + content
        if not contentWarning:
            if isPGPEncrypted(content):
                content = '🔒' + content
            elif '://' in content:
                content = '🔗' + content
            content = _padToWidth(content, contentWidth)
        else:
            # display content warning
            if isPGPEncrypted(content):
                content = '🔒' + contentWarning
            else:
                if '://' in content:
                    content = '🔗' + contentWarning
                else:
                    content = contentWarning
        if postJsonObject['object'].get('ignores'):
            content = '🔇'
        if postJsonObject['object'].get('bookmarks'):
            content = '🔖' + content
        if '\n' in content:
            content = content.replace('\n', ' ')
        lineStr = indent + str(posStr) + ' | ' + name + ' | ' + \
            published + ' | ' + content
        if boxName == 'inbox' and \
           _postIsToYou(yourActor, postJsonObject):
            if not _hasReadPost(yourActor, postJsonObject['id'], 'dm'):
                if not _hasReadPost(yourActor, postJsonObject['id'],
                                    'replies'):
                    lineStr = _highlightText(lineStr)
        print(lineStr)
        ctr += 1

    if followRequestsJson:
        _desktopShowFollowRequests(followRequestsJson, translate)

    print('')

    # say the post number range
    sayStr = indent + boxNameStr + ' page ' + str(pageNumber) + \
        ' containing ' + str(ctr - 1) + ' posts. '
    sayStr2 = sayStr.replace('\33[3m', '').replace('\33[0m', '')
    sayStr2 = sayStr2.replace('show dm', 'show DM')
    sayStr2 = sayStr2.replace('dm post', 'Direct message post')
    _sayCommand(sayStr, sayStr2, screenreader, systemLanguage, espeak)
    print('')
    return True


def _desktopNewDM(session, toHandle: str,
                  baseDir: str, nickname: str, password: str,
                  domain: str, port: int, httpPrefix: str,
                  cachedWebfingers: {}, personCache: {},
                  debug: bool,
                  screenreader: str, systemLanguage: str,
                  espeak, lowBandwidth: bool,
                  contentLicenseUrl: str,
                  signingPrivateKeyPem: str) -> None:
    """Use the desktop client to create a new direct message
    which can include multiple destination handles
    """
    if ' ' in toHandle:
        handlesList = toHandle.split(' ')
    elif ',' in toHandle:
        handlesList = toHandle.split(',')
    elif ';' in toHandle:
        handlesList = toHandle.split(';')
    else:
        handlesList = [toHandle]

    for handle in handlesList:
        handle = handle.strip()
        _desktopNewDMbase(session, handle,
                          baseDir, nickname, password,
                          domain, port, httpPrefix,
                          cachedWebfingers, personCache,
                          debug,
                          screenreader, systemLanguage,
                          espeak, lowBandwidth,
                          contentLicenseUrl,
                          signingPrivateKeyPem)


def _desktopNewDMbase(session, toHandle: str,
                      baseDir: str, nickname: str, password: str,
                      domain: str, port: int, httpPrefix: str,
                      cachedWebfingers: {}, personCache: {},
                      debug: bool,
                      screenreader: str, systemLanguage: str,
                      espeak, lowBandwidth: bool,
                      contentLicenseUrl: str,
                      signingPrivateKeyPem: str) -> None:
    """Use the desktop client to create a new direct message
    """
    conversationId = None
    toPort = port
    if '://' in toHandle:
        toNickname = getNicknameFromActor(toHandle)
        toDomain, toPort = getDomainFromActor(toHandle)
        toHandle = toNickname + '@' + toDomain
    else:
        if toHandle.startswith('@'):
            toHandle = toHandle[1:]
        toNickname = toHandle.split('@')[0]
        toDomain = toHandle.split('@')[1]

    sayStr = 'Create new direct message to ' + toHandle
    _sayCommand(sayStr, sayStr, screenreader, systemLanguage, espeak)
    sayStr = 'Type your direct message, then press Enter.'
    _sayCommand(sayStr, sayStr, screenreader, systemLanguage, espeak)
    newMessage = input()
    if not newMessage:
        sayStr = 'No direct message was entered.'
        _sayCommand(sayStr, sayStr, screenreader, systemLanguage, espeak)
        return
    newMessage = newMessage.strip()
    if not newMessage:
        sayStr = 'No direct message was entered.'
        _sayCommand(sayStr, sayStr, screenreader, systemLanguage, espeak)
        return
    sayStr = 'You entered this direct message to ' + toHandle + ':'
    _sayCommand(sayStr, sayStr, screenreader, systemLanguage, espeak)
    _sayCommand(newMessage, newMessage, screenreader, systemLanguage, espeak)
    ccUrl = None
    followersOnly = False
    attach = None
    mediaType = None
    attachedImageDescription = None
    city = 'London, England'
    isArticle = False
    subject = None
    commentsEnabled = True
    subject = None

    # if there is a local PGP key then attempt to encrypt the DM
    # using the PGP public key of the recipient
    if hasLocalPGPkey():
        sayStr = \
            'Local PGP key detected...' + \
            'Fetching PGP public key for ' + toHandle
        _sayCommand(sayStr, sayStr, screenreader, systemLanguage, espeak)
        paddedMessage = newMessage
        if len(paddedMessage) < 32:
            # add some padding before and after
            # This is to guard against cribs based on small messages, like "Hi"
            for before in range(randint(1, 16)):
                paddedMessage = ' ' + paddedMessage
            for after in range(randint(1, 16)):
                paddedMessage += ' '
        cipherText = \
            pgpEncryptToActor(domain, paddedMessage, toHandle,
                              signingPrivateKeyPem)
        if not cipherText:
            sayStr = \
                toHandle + ' has no PGP public key. ' + \
                'Your message will be sent in clear text'
            _sayCommand(sayStr, sayStr, screenreader, systemLanguage, espeak)
        else:
            newMessage = cipherText
            sayStr = 'Message encrypted'
            _sayCommand(sayStr, sayStr, screenreader, systemLanguage, espeak)

    sayStr = 'Send this direct message, yes or no?'
    _sayCommand(sayStr, sayStr, screenreader, systemLanguage, espeak)
    yesno = input()
    if 'y' not in yesno.lower():
        sayStr = 'Abandoning new direct message'
        _sayCommand(sayStr, sayStr, screenreader, systemLanguage, espeak)
        return

    sayStr = 'Sending'
    _sayCommand(sayStr, sayStr, screenreader, systemLanguage, espeak)
    if sendPostViaServer(signingPrivateKeyPem, __version__,
                         baseDir, session, nickname, password,
                         domain, port,
                         toNickname, toDomain, toPort, ccUrl,
                         httpPrefix, newMessage, followersOnly,
                         commentsEnabled, attach, mediaType,
                         attachedImageDescription, city,
                         cachedWebfingers, personCache, isArticle,
                         systemLanguage, lowBandwidth,
                         contentLicenseUrl,
                         debug, None, None,
                         conversationId, subject) == 0:
        sayStr = 'Direct message sent'
    else:
        sayStr = 'Direct message failed'
    _sayCommand(sayStr, sayStr, screenreader, systemLanguage, espeak)


def _desktopShowFollowRequests(followRequestsJson: {}, translate: {}) -> None:
    """Shows any follow requests
    """
    if not isinstance(followRequestsJson, dict):
        return
    if not followRequestsJson.get('orderedItems'):
        return
    if not followRequestsJson['orderedItems']:
        return
    indent = '   '
    print('')
    print(indent + 'Follow requests:')
    print('')
    for item in followRequestsJson['orderedItems']:
        handleNickname = getNicknameFromActor(item)
        handleDomain, handlePort = getDomainFromActor(item)
        handleDomainFull = \
            getFullDomain(handleDomain, handlePort)
        print(indent + '  👤 ' +
              handleNickname + '@' + handleDomainFull)


def _desktopShowFollowing(followingJson: {}, translate: {},
                          pageNumber: int, indent: str,
                          followType='following') -> None:
    """Shows a page of accounts followed
    """
    if not isinstance(followingJson, dict):
        return
    if not followingJson.get('orderedItems'):
        return
    if not followingJson['orderedItems']:
        return
    print('')
    if followType == 'following':
        print(indent + 'Following page ' + str(pageNumber))
    elif followType == 'followers':
        print(indent + 'Followers page ' + str(pageNumber))
    print('')
    for item in followingJson['orderedItems']:
        handleNickname = getNicknameFromActor(item)
        handleDomain, handlePort = getDomainFromActor(item)
        handleDomainFull = \
            getFullDomain(handleDomain, handlePort)
        print(indent + '  👤 ' +
              handleNickname + '@' + handleDomainFull)


def runDesktopClient(baseDir: str, proxyType: str, httpPrefix: str,
                     nickname: str, domain: str, port: int,
                     password: str, screenreader: str,
                     systemLanguage: str,
                     notificationSounds: bool,
                     notificationType: str,
                     noKeyPress: bool,
                     storeInboxPosts: bool,
                     showNewPosts: bool,
                     language: str,
                     debug: bool, lowBandwidth: bool) -> None:
    """Runs the desktop and screen reader client,
    which announces new inbox items
    """
    # TODO: this should probably be retrieved somehow from the server
    signingPrivateKeyPem = None

    contentLicenseUrl = 'https://creativecommons.org/licenses/by/4.0'

    blockedCache = {}

    indent = '   '
    if showNewPosts:
        indent = ''

    _desktopClearScreen()
    _desktopShowBanner()

    espeak = None
    if screenreader:
        if screenreader == 'espeak':
            print('Setting up espeak')
            from espeak import espeak
        elif screenreader != 'picospeaker':
            print(screenreader + ' is not a supported TTS system')
            return

        sayStr = indent + 'Running ' + screenreader + ' for ' + \
            nickname + '@' + domain
        _sayCommand(sayStr, sayStr, screenreader,
                    systemLanguage, espeak)
    else:
        print(indent + 'Running desktop notifications for ' +
              nickname + '@' + domain)
    if notificationSounds:
        sayStr = indent + 'Notification sounds on'
    else:
        sayStr = indent + 'Notification sounds off'
    _sayCommand(sayStr, sayStr, screenreader,
                systemLanguage, espeak)

    currTimeline = 'inbox'
    pageNumber = 1

    postJsonObject = {}
    originalScreenReader = screenreader
    soundsDir = 'theme/default/sounds/'
    # prevSay = ''
    # prevCalendar = False
    # prevFollow = False
    # prevLike = ''
    # prevShare = False
    dmSoundFilename = soundsDir + 'dm.ogg'
    replySoundFilename = soundsDir + 'reply.ogg'
    # calendarSoundFilename = soundsDir + 'calendar.ogg'
    # followSoundFilename = soundsDir + 'follow.ogg'
    # likeSoundFilename = soundsDir + 'like.ogg'
    # shareSoundFilename = soundsDir + 'share.ogg'
    player = 'ffplay'
    nameStr = None
    gender = None
    messageStr = None
    content = None
    cachedWebfingers = {}
    personCache = {}
    newRepliesExist = False
    newDMsExist = False
    pgpKeyUpload = False

    sayStr = indent + 'Loading translations file'
    _sayCommand(sayStr, sayStr, screenreader,
                systemLanguage, espeak)
    translate, systemLanguage = \
        loadTranslationsFromFile(baseDir, language)

    sayStr = indent + 'Connecting...'
    _sayCommand(sayStr, sayStr, screenreader,
                systemLanguage, espeak)
    session = createSession(proxyType)

    sayStr = indent + '/q or /quit to exit'
    _sayCommand(sayStr, sayStr, screenreader,
                systemLanguage, espeak)

    domainFull = getFullDomain(domain, port)
    yourActor = localActorUrl(httpPrefix, nickname, domainFull)
    actorJson = None

    notifyJson = {
        "dmPostId": "Initial",
        "dmNotify": False,
        "dmNotifyChanged": False,
        "repliesPostId": "Initial",
        "repliesNotify": False,
        "repliesNotifyChanged": False
    }
    prevTimelineFirstId = ''
    desktopShown = False
    while (1):
        if not pgpKeyUpload:
            if not hasLocalPGPkey():
                print('No PGP public key was found')
            else:
                sayStr = indent + 'Uploading PGP public key'
                _sayCommand(sayStr, sayStr, screenreader,
                            systemLanguage, espeak)
                pgpPublicKeyUpload(baseDir, session,
                                   nickname, password,
                                   domain, port, httpPrefix,
                                   cachedWebfingers, personCache,
                                   debug, False,
                                   signingPrivateKeyPem)
                sayStr = indent + 'PGP public key uploaded'
                _sayCommand(sayStr, sayStr, screenreader,
                            systemLanguage, espeak)
            pgpKeyUpload = True

        boxJson = c2sBoxJson(baseDir, session,
                             nickname, password,
                             domain, port, httpPrefix,
                             currTimeline, pageNumber,
                             debug, signingPrivateKeyPem)

        followRequestsJson = \
            getFollowRequestsViaServer(baseDir, session,
                                       nickname, password,
                                       domain, port,
                                       httpPrefix, 1,
                                       cachedWebfingers, personCache,
                                       debug, __version__,
                                       signingPrivateKeyPem)

        if not (currTimeline == 'inbox' and pageNumber == 1):
            # monitor the inbox to generate notifications
            inboxJson = c2sBoxJson(baseDir, session,
                                   nickname, password,
                                   domain, port, httpPrefix,
                                   'inbox', 1, debug,
                                   signingPrivateKeyPem)
        else:
            inboxJson = boxJson
        newDMsExist = False
        newRepliesExist = False
        if inboxJson:
            _newDesktopNotifications(yourActor, inboxJson, notifyJson)
            if notifyJson.get('dmNotify'):
                newDMsExist = True
                if notifyJson.get('dmNotifyChanged'):
                    _desktopNotification(notificationType,
                                         "Epicyon",
                                         "New DM " + yourActor + '/dm')
                    if notificationSounds:
                        _playNotificationSound(dmSoundFilename, player)
            if notifyJson.get('repliesNotify'):
                newRepliesExist = True
                if notifyJson.get('repliesNotifyChanged'):
                    _desktopNotification(notificationType,
                                         "Epicyon",
                                         "New reply " + yourActor + '/replies')
                    if notificationSounds:
                        _playNotificationSound(replySoundFilename, player)

        if boxJson:
            timelineFirstId = _getFirstItemId(boxJson)
            if timelineFirstId != prevTimelineFirstId:
                _desktopClearScreen()
                _desktopShowBox(indent, followRequestsJson,
                                yourActor, currTimeline, boxJson,
                                translate,
                                None, systemLanguage, espeak,
                                pageNumber,
                                newRepliesExist,
                                newDMsExist)
                desktopShown = True
            prevTimelineFirstId = timelineFirstId
        else:
            session = createSession(proxyType)
            if not desktopShown:
                if not session:
                    print('No session\n')

                _desktopClearScreen()
                _desktopShowBanner()
                print('No posts\n')
                if proxyType == 'tor':
                    print('You may need to run the desktop client ' +
                          'with the --http option')

        # wait for a while, or until a key is pressed
        if noKeyPress:
            time.sleep(10)
        else:
            commandStr = _desktopWaitForCmd(30, debug)
        if commandStr:
            refreshTimeline = False

            if commandStr.startswith('/'):
                commandStr = commandStr[1:]
            if commandStr == 'q' or \
               commandStr == 'quit' or \
               commandStr == 'exit':
                sayStr = 'Quit'
                _sayCommand(sayStr, sayStr, screenreader,
                            systemLanguage, espeak)
                if screenreader:
                    commandStr = _desktopWaitForCmd(2, debug)
                break
            elif commandStr.startswith('show dm'):
                pageNumber = 1
                prevTimelineFirstId = ''
                currTimeline = 'dm'
                boxJson = c2sBoxJson(baseDir, session,
                                     nickname, password,
                                     domain, port, httpPrefix,
                                     currTimeline, pageNumber,
                                     debug, signingPrivateKeyPem)
                if boxJson:
                    _desktopShowBox(indent, followRequestsJson,
                                    yourActor, currTimeline, boxJson,
                                    translate,
                                    screenreader, systemLanguage, espeak,
                                    pageNumber,
                                    newRepliesExist, newDMsExist)
                newDMsExist = False
            elif commandStr.startswith('show rep'):
                pageNumber = 1
                prevTimelineFirstId = ''
                currTimeline = 'tlreplies'
                boxJson = c2sBoxJson(baseDir, session,
                                     nickname, password,
                                     domain, port, httpPrefix,
                                     currTimeline, pageNumber,
                                     debug, signingPrivateKeyPem)
                if boxJson:
                    _desktopShowBox(indent, followRequestsJson,
                                    yourActor, currTimeline, boxJson,
                                    translate,
                                    screenreader, systemLanguage, espeak,
                                    pageNumber,
                                    newRepliesExist, newDMsExist)
                # Turn off the replies indicator
                newRepliesExist = False
            elif commandStr.startswith('show b'):
                pageNumber = 1
                prevTimelineFirstId = ''
                currTimeline = 'tlbookmarks'
                boxJson = c2sBoxJson(baseDir, session,
                                     nickname, password,
                                     domain, port, httpPrefix,
                                     currTimeline, pageNumber,
                                     debug, signingPrivateKeyPem)
                if boxJson:
                    _desktopShowBox(indent, followRequestsJson,
                                    yourActor, currTimeline, boxJson,
                                    translate,
                                    screenreader, systemLanguage, espeak,
                                    pageNumber,
                                    newRepliesExist, newDMsExist)
                # Turn off the replies indicator
                newRepliesExist = False
            elif (commandStr.startswith('show sen') or
                  commandStr.startswith('show out')):
                pageNumber = 1
                prevTimelineFirstId = ''
                currTimeline = 'outbox'
                boxJson = c2sBoxJson(baseDir, session,
                                     nickname, password,
                                     domain, port, httpPrefix,
                                     currTimeline, pageNumber,
                                     debug, signingPrivateKeyPem)
                if boxJson:
                    _desktopShowBox(indent, followRequestsJson,
                                    yourActor, currTimeline, boxJson,
                                    translate,
                                    screenreader, systemLanguage, espeak,
                                    pageNumber,
                                    newRepliesExist, newDMsExist)
            elif (commandStr == 'show' or commandStr.startswith('show in') or
                  commandStr == 'clear'):
                pageNumber = 1
                prevTimelineFirstId = ''
                currTimeline = 'inbox'
                refreshTimeline = True
            elif commandStr.startswith('next'):
                pageNumber += 1
                prevTimelineFirstId = ''
                refreshTimeline = True
            elif commandStr.startswith('prev'):
                pageNumber -= 1
                if pageNumber < 1:
                    pageNumber = 1
                prevTimelineFirstId = ''
                boxJson = c2sBoxJson(baseDir, session,
                                     nickname, password,
                                     domain, port, httpPrefix,
                                     currTimeline, pageNumber,
                                     debug, signingPrivateKeyPem)
                if boxJson:
                    _desktopShowBox(indent, followRequestsJson,
                                    yourActor, currTimeline, boxJson,
                                    translate,
                                    screenreader, systemLanguage, espeak,
                                    pageNumber,
                                    newRepliesExist, newDMsExist)
            elif commandStr.startswith('read ') or commandStr == 'read':
                if commandStr == 'read':
                    postIndexStr = '1'
                else:
                    postIndexStr = commandStr.split('read ')[1]
                if boxJson and postIndexStr.isdigit():
                    _desktopClearScreen()
                    _desktopShowBanner()
                    postIndex = int(postIndexStr)
                    postJsonObject = \
                        _readLocalBoxPost(session, nickname, domain,
                                          httpPrefix, baseDir, currTimeline,
                                          pageNumber, postIndex, boxJson,
                                          systemLanguage, screenreader,
                                          espeak, translate, yourActor,
                                          domainFull, personCache,
                                          signingPrivateKeyPem,
                                          blockedCache)
                    print('')
                    sayStr = 'Press Enter to continue...'
                    sayStr2 = _highlightText(sayStr)
                    _sayCommand(sayStr2, sayStr,
                                screenreader, systemLanguage, espeak)
                    input()
                    prevTimelineFirstId = ''
                    refreshTimeline = True
                print('')
            elif commandStr.startswith('profile ') or commandStr == 'profile':
                actorJson = None
                if commandStr == 'profile':
                    if postJsonObject:
                        actorJson = \
                            _desktopShowProfile(session, nickname, domain,
                                                httpPrefix, baseDir,
                                                currTimeline,
                                                pageNumber, postIndex,
                                                boxJson,
                                                systemLanguage, screenreader,
                                                espeak, translate, yourActor,
                                                postJsonObject,
                                                signingPrivateKeyPem)
                    else:
                        postIndexStr = '1'
                else:
                    postIndexStr = commandStr.split('profile ')[1]

                if not postIndexStr.isdigit():
                    profileHandle = postIndexStr
                    _desktopClearScreen()
                    _desktopShowBanner()
                    _desktopShowProfileFromHandle(session, nickname, domain,
                                                  httpPrefix, baseDir,
                                                  currTimeline, profileHandle,
                                                  systemLanguage, screenreader,
                                                  espeak, translate, yourActor,
                                                  None, signingPrivateKeyPem)
                    sayStr = 'Press Enter to continue...'
                    sayStr2 = _highlightText(sayStr)
                    _sayCommand(sayStr2, sayStr,
                                screenreader, systemLanguage, espeak)
                    input()
                    prevTimelineFirstId = ''
                    refreshTimeline = True
                elif not actorJson and boxJson:
                    _desktopClearScreen()
                    _desktopShowBanner()
                    postIndex = int(postIndexStr)
                    actorJson = \
                        _desktopShowProfile(session, nickname, domain,
                                            httpPrefix, baseDir, currTimeline,
                                            pageNumber, postIndex, boxJson,
                                            systemLanguage, screenreader,
                                            espeak, translate, yourActor,
                                            None, signingPrivateKeyPem)
                    sayStr = 'Press Enter to continue...'
                    sayStr2 = _highlightText(sayStr)
                    _sayCommand(sayStr2, sayStr,
                                screenreader, systemLanguage, espeak)
                    input()
                    prevTimelineFirstId = ''
                    refreshTimeline = True
                print('')
            elif commandStr == 'reply' or commandStr == 'r':
                if postJsonObject:
                    if postJsonObject.get('id'):
                        postId = postJsonObject['id']
                        subject = None
                        if postJsonObject['object'].get('summary'):
                            subject = postJsonObject['object']['summary']
                        conversationId = None
                        if postJsonObject['object'].get('conversation'):
                            conversationId = \
                                postJsonObject['object']['conversation']
                        sessionReply = createSession(proxyType)
                        _desktopReplyToPost(sessionReply, postId,
                                            baseDir, nickname, password,
                                            domain, port, httpPrefix,
                                            cachedWebfingers, personCache,
                                            debug, subject,
                                            screenreader, systemLanguage,
                                            espeak, conversationId,
                                            lowBandwidth,
                                            contentLicenseUrl,
                                            signingPrivateKeyPem)
                refreshTimeline = True
                print('')
            elif (commandStr == 'post' or commandStr == 'p' or
                  commandStr == 'send' or
                  commandStr.startswith('dm ') or
                  commandStr.startswith('direct message ') or
                  commandStr.startswith('post ') or
                  commandStr.startswith('send ')):
                sessionPost = createSession(proxyType)
                if commandStr.startswith('dm ') or \
                   commandStr.startswith('direct message ') or \
                   commandStr.startswith('post ') or \
                   commandStr.startswith('send '):
                    commandStr = commandStr.replace(' to ', ' ')
                    commandStr = commandStr.replace(' dm ', ' ')
                    commandStr = commandStr.replace(' DM ', ' ')
                    # direct message
                    toHandle = None
                    if commandStr.startswith('post '):
                        toHandle = commandStr.split('post ', 1)[1]
                    elif commandStr.startswith('send '):
                        toHandle = commandStr.split('send ', 1)[1]
                    elif commandStr.startswith('dm '):
                        toHandle = commandStr.split('dm ', 1)[1]
                    elif commandStr.startswith('direct message '):
                        toHandle = commandStr.split('direct message ', 1)[1]
                    if toHandle:
                        _desktopNewDM(sessionPost, toHandle,
                                      baseDir, nickname, password,
                                      domain, port, httpPrefix,
                                      cachedWebfingers, personCache,
                                      debug,
                                      screenreader, systemLanguage,
                                      espeak, lowBandwidth,
                                      contentLicenseUrl,
                                      signingPrivateKeyPem)
                        refreshTimeline = True
                else:
                    # public post
                    _desktopNewPost(sessionPost,
                                    baseDir, nickname, password,
                                    domain, port, httpPrefix,
                                    cachedWebfingers, personCache,
                                    debug,
                                    screenreader, systemLanguage,
                                    espeak, lowBandwidth,
                                    contentLicenseUrl,
                                    signingPrivateKeyPem)
                    refreshTimeline = True
                print('')
            elif commandStr == 'like' or commandStr.startswith('like '):
                currIndex = 0
                if ' ' in commandStr:
                    postIndex = commandStr.split(' ')[-1].strip()
                    if postIndex.isdigit():
                        currIndex = int(postIndex)
                if currIndex > 0 and boxJson:
                    postJsonObject = \
                        _desktopGetBoxPostObject(boxJson, currIndex)
                if postJsonObject:
                    if postJsonObject.get('id'):
                        likeActor = postJsonObject['object']['attributedTo']
                        sayStr = 'Liking post by ' + \
                            getNicknameFromActor(likeActor)
                        _sayCommand(sayStr, sayStr,
                                    screenreader,
                                    systemLanguage, espeak)
                        sessionLike = createSession(proxyType)
                        sendLikeViaServer(baseDir, sessionLike,
                                          nickname, password,
                                          domain, port, httpPrefix,
                                          postJsonObject['id'],
                                          cachedWebfingers, personCache,
                                          False, __version__,
                                          signingPrivateKeyPem)
                        refreshTimeline = True
                print('')
            elif (commandStr == 'undo mute' or
                  commandStr == 'undo ignore' or
                  commandStr == 'remove mute' or
                  commandStr == 'rm mute' or
                  commandStr == 'unmute' or
                  commandStr == 'unignore' or
                  commandStr == 'mute undo' or
                  commandStr.startswith('undo mute ') or
                  commandStr.startswith('undo ignore ') or
                  commandStr.startswith('remove mute ') or
                  commandStr.startswith('remove ignore ') or
                  commandStr.startswith('unignore ') or
                  commandStr.startswith('unmute ')):
                currIndex = 0
                if ' ' in commandStr:
                    postIndex = commandStr.split(' ')[-1].strip()
                    if postIndex.isdigit():
                        currIndex = int(postIndex)
                if currIndex > 0 and boxJson:
                    postJsonObject = \
                        _desktopGetBoxPostObject(boxJson, currIndex)
                if postJsonObject:
                    if postJsonObject.get('id'):
                        muteActor = postJsonObject['object']['attributedTo']
                        sayStr = 'Unmuting post by ' + \
                            getNicknameFromActor(muteActor)
                        _sayCommand(sayStr, sayStr,
                                    screenreader,
                                    systemLanguage, espeak)
                        sessionMute = createSession(proxyType)
                        sendUndoMuteViaServer(baseDir, sessionMute,
                                              nickname, password,
                                              domain, port,
                                              httpPrefix, postJsonObject['id'],
                                              cachedWebfingers, personCache,
                                              False, __version__,
                                              signingPrivateKeyPem)
                        refreshTimeline = True
                print('')
            elif (commandStr == 'mute' or
                  commandStr == 'ignore' or
                  commandStr.startswith('mute ') or
                  commandStr.startswith('ignore ')):
                currIndex = 0
                if ' ' in commandStr:
                    postIndex = commandStr.split(' ')[-1].strip()
                    if postIndex.isdigit():
                        currIndex = int(postIndex)
                if currIndex > 0 and boxJson:
                    postJsonObject = \
                        _desktopGetBoxPostObject(boxJson, currIndex)
                if postJsonObject:
                    if postJsonObject.get('id'):
                        muteActor = postJsonObject['object']['attributedTo']
                        sayStr = 'Muting post by ' + \
                            getNicknameFromActor(muteActor)
                        _sayCommand(sayStr, sayStr,
                                    screenreader,
                                    systemLanguage, espeak)
                        sessionMute = createSession(proxyType)
                        sendMuteViaServer(baseDir, sessionMute,
                                          nickname, password,
                                          domain, port,
                                          httpPrefix, postJsonObject['id'],
                                          cachedWebfingers, personCache,
                                          False, __version__,
                                          signingPrivateKeyPem)
                        refreshTimeline = True
                print('')
            elif (commandStr == 'undo bookmark' or
                  commandStr == 'remove bookmark' or
                  commandStr == 'rm bookmark' or
                  commandStr == 'undo bm' or
                  commandStr == 'rm bm' or
                  commandStr == 'remove bm' or
                  commandStr == 'unbookmark' or
                  commandStr == 'bookmark undo' or
                  commandStr == 'bm undo ' or
                  commandStr.startswith('undo bm ') or
                  commandStr.startswith('remove bm ') or
                  commandStr.startswith('undo bookmark ') or
                  commandStr.startswith('remove bookmark ') or
                  commandStr.startswith('unbookmark ') or
                  commandStr.startswith('unbm ')):
                currIndex = 0
                if ' ' in commandStr:
                    postIndex = commandStr.split(' ')[-1].strip()
                    if postIndex.isdigit():
                        currIndex = int(postIndex)
                if currIndex > 0 and boxJson:
                    postJsonObject = \
                        _desktopGetBoxPostObject(boxJson, currIndex)
                if postJsonObject:
                    if postJsonObject.get('id'):
                        bmActor = postJsonObject['object']['attributedTo']
                        sayStr = 'Unbookmarking post by ' + \
                            getNicknameFromActor(bmActor)
                        _sayCommand(sayStr, sayStr,
                                    screenreader,
                                    systemLanguage, espeak)
                        sessionbm = createSession(proxyType)
                        sendUndoBookmarkViaServer(baseDir, sessionbm,
                                                  nickname, password,
                                                  domain, port, httpPrefix,
                                                  postJsonObject['id'],
                                                  cachedWebfingers,
                                                  personCache,
                                                  False, __version__,
                                                  signingPrivateKeyPem)
                        refreshTimeline = True
                print('')
            elif (commandStr == 'bookmark' or
                  commandStr == 'bm' or
                  commandStr.startswith('bookmark ') or
                  commandStr.startswith('bm ')):
                currIndex = 0
                if ' ' in commandStr:
                    postIndex = commandStr.split(' ')[-1].strip()
                    if postIndex.isdigit():
                        currIndex = int(postIndex)
                if currIndex > 0 and boxJson:
                    postJsonObject = \
                        _desktopGetBoxPostObject(boxJson, currIndex)
                if postJsonObject:
                    if postJsonObject.get('id'):
                        bmActor = postJsonObject['object']['attributedTo']
                        sayStr = 'Bookmarking post by ' + \
                            getNicknameFromActor(bmActor)
                        _sayCommand(sayStr, sayStr,
                                    screenreader,
                                    systemLanguage, espeak)
                        sessionbm = createSession(proxyType)
                        sendBookmarkViaServer(baseDir, sessionbm,
                                              nickname, password,
                                              domain, port, httpPrefix,
                                              postJsonObject['id'],
                                              cachedWebfingers, personCache,
                                              False, __version__,
                                              signingPrivateKeyPem)
                        refreshTimeline = True
                print('')
            elif (commandStr.startswith('undo block ') or
                  commandStr.startswith('remove block ') or
                  commandStr.startswith('rm block ') or
                  commandStr.startswith('unblock ')):
                currIndex = 0
                if ' ' in commandStr:
                    postIndex = commandStr.split(' ')[-1].strip()
                    if postIndex.isdigit():
                        currIndex = int(postIndex)
                if currIndex > 0 and boxJson:
                    postJsonObject = \
                        _desktopGetBoxPostObject(boxJson, currIndex)
                if postJsonObject:
                    if postJsonObject.get('id') and \
                       postJsonObject.get('object'):
                        if hasObjectDict(postJsonObject):
                            if postJsonObject['object'].get('attributedTo'):
                                blockActor = \
                                    postJsonObject['object']['attributedTo']
                                sayStr = 'Unblocking ' + \
                                    getNicknameFromActor(blockActor)
                                _sayCommand(sayStr, sayStr,
                                            screenreader,
                                            systemLanguage, espeak)
                                sessionBlock = createSession(proxyType)
                                sendUndoBlockViaServer(baseDir, sessionBlock,
                                                       nickname, password,
                                                       domain, port,
                                                       httpPrefix,
                                                       blockActor,
                                                       cachedWebfingers,
                                                       personCache,
                                                       False, __version__,
                                                       signingPrivateKeyPem)
                refreshTimeline = True
                print('')
            elif commandStr.startswith('block '):
                blockActor = None
                currIndex = 0
                if ' ' in commandStr:
                    postIndex = commandStr.split(' ')[-1].strip()
                    if postIndex.isdigit():
                        currIndex = int(postIndex)
                    else:
                        if '@' in postIndex:
                            blockHandle = postIndex
                            if blockHandle.startswith('@'):
                                blockHandle = blockHandle[1:]
                            if '@' in blockHandle:
                                blockDomain = blockHandle.split('@')[1]
                                blockNickname = blockHandle.split('@')[0]
                                blockActor = \
                                    localActorUrl(httpPrefix,
                                                  blockNickname, blockDomain)
                if currIndex > 0 and boxJson and not blockActor:
                    postJsonObject = \
                        _desktopGetBoxPostObject(boxJson, currIndex)
                if postJsonObject and not blockActor:
                    if postJsonObject.get('id') and \
                       postJsonObject.get('object'):
                        if hasObjectDict(postJsonObject):
                            if postJsonObject['object'].get('attributedTo'):
                                blockActor = \
                                    postJsonObject['object']['attributedTo']
                if blockActor:
                    sayStr = 'Blocking ' + \
                        getNicknameFromActor(blockActor)
                    _sayCommand(sayStr, sayStr,
                                screenreader,
                                systemLanguage, espeak)
                    sessionBlock = createSession(proxyType)
                    sendBlockViaServer(baseDir, sessionBlock,
                                       nickname, password,
                                       domain, port,
                                       httpPrefix,
                                       blockActor,
                                       cachedWebfingers,
                                       personCache,
                                       False, __version__,
                                       signingPrivateKeyPem)
                refreshTimeline = True
                print('')
            elif commandStr == 'unlike' or commandStr == 'undo like':
                currIndex = 0
                if ' ' in commandStr:
                    postIndex = commandStr.split(' ')[-1].strip()
                    if postIndex.isdigit():
                        currIndex = int(postIndex)
                if currIndex > 0 and boxJson:
                    postJsonObject = \
                        _desktopGetBoxPostObject(boxJson, currIndex)
                if postJsonObject:
                    if postJsonObject.get('id'):
                        unlikeActor = postJsonObject['object']['attributedTo']
                        sayStr = \
                            'Undoing like of post by ' + \
                            getNicknameFromActor(unlikeActor)
                        _sayCommand(sayStr, sayStr,
                                    screenreader,
                                    systemLanguage, espeak)
                        sessionUnlike = createSession(proxyType)
                        sendUndoLikeViaServer(baseDir, sessionUnlike,
                                              nickname, password,
                                              domain, port, httpPrefix,
                                              postJsonObject['id'],
                                              cachedWebfingers, personCache,
                                              False, __version__,
                                              signingPrivateKeyPem)
                        refreshTimeline = True
                print('')
            elif (commandStr.startswith('announce') or
                  commandStr.startswith('boost') or
                  commandStr.startswith('retweet')):
                currIndex = 0
                if ' ' in commandStr:
                    postIndex = commandStr.split(' ')[-1].strip()
                    if postIndex.isdigit():
                        currIndex = int(postIndex)
                if currIndex > 0 and boxJson:
                    postJsonObject = \
                        _desktopGetBoxPostObject(boxJson, currIndex)
                if postJsonObject:
                    if postJsonObject.get('id'):
                        postId = postJsonObject['id']
                        announceActor = \
                            postJsonObject['object']['attributedTo']
                        sayStr = 'Announcing post by ' + \
                            getNicknameFromActor(announceActor)
                        _sayCommand(sayStr, sayStr,
                                    screenreader,
                                    systemLanguage, espeak)
                        sessionAnnounce = createSession(proxyType)
                        sendAnnounceViaServer(baseDir, sessionAnnounce,
                                              nickname, password,
                                              domain, port,
                                              httpPrefix, postId,
                                              cachedWebfingers, personCache,
                                              True, __version__,
                                              signingPrivateKeyPem)
                        refreshTimeline = True
                print('')
            elif (commandStr.startswith('unannounce') or
                  commandStr.startswith('undo announce') or
                  commandStr.startswith('unboost') or
                  commandStr.startswith('undo boost') or
                  commandStr.startswith('undo retweet')):
                currIndex = 0
                if ' ' in commandStr:
                    postIndex = commandStr.split(' ')[-1].strip()
                    if postIndex.isdigit():
                        currIndex = int(postIndex)
                if currIndex > 0 and boxJson:
                    postJsonObject = \
                        _desktopGetBoxPostObject(boxJson, currIndex)
                if postJsonObject:
                    if postJsonObject.get('id'):
                        postId = postJsonObject['id']
                        announceActor = \
                            postJsonObject['object']['attributedTo']
                        sayStr = 'Undoing announce post by ' + \
                            getNicknameFromActor(announceActor)
                        _sayCommand(sayStr, sayStr,
                                    screenreader,
                                    systemLanguage, espeak)
                        sessionAnnounce = createSession(proxyType)
                        sendUndoAnnounceViaServer(baseDir, sessionAnnounce,
                                                  postJsonObject,
                                                  nickname, password,
                                                  domain, port,
                                                  httpPrefix, postId,
                                                  cachedWebfingers,
                                                  personCache,
                                                  True, __version__,
                                                  signingPrivateKeyPem)
                        refreshTimeline = True
                print('')
            elif (commandStr == 'follow requests' or
                  commandStr.startswith('follow requests ')):
                currPage = 1
                if ' ' in commandStr:
                    pageNum = commandStr.split(' ')[-1].strip()
                    if pageNum.isdigit():
                        currPage = int(pageNum)
                followRequestsJson = \
                    getFollowRequestsViaServer(baseDir, session,
                                               nickname, password,
                                               domain, port,
                                               httpPrefix, currPage,
                                               cachedWebfingers, personCache,
                                               debug, __version__,
                                               signingPrivateKeyPem)
                if followRequestsJson:
                    if isinstance(followRequestsJson, dict):
                        _desktopShowFollowRequests(followRequestsJson,
                                                   translate)
                print('')
            elif (commandStr == 'following' or
                  commandStr.startswith('following ')):
                currPage = 1
                if ' ' in commandStr:
                    pageNum = commandStr.split(' ')[-1].strip()
                    if pageNum.isdigit():
                        currPage = int(pageNum)
                followingJson = \
                    getFollowingViaServer(baseDir, session,
                                          nickname, password,
                                          domain, port,
                                          httpPrefix, currPage,
                                          cachedWebfingers, personCache,
                                          debug, __version__,
                                          signingPrivateKeyPem)
                if followingJson:
                    if isinstance(followingJson, dict):
                        _desktopShowFollowing(followingJson, translate,
                                              currPage, indent,
                                              'following')
                print('')
            elif (commandStr == 'followers' or
                  commandStr.startswith('followers ')):
                currPage = 1
                if ' ' in commandStr:
                    pageNum = commandStr.split(' ')[-1].strip()
                    if pageNum.isdigit():
                        currPage = int(pageNum)
                followersJson = \
                    getFollowersViaServer(baseDir, session,
                                          nickname, password,
                                          domain, port,
                                          httpPrefix, currPage,
                                          cachedWebfingers, personCache,
                                          debug, __version__,
                                          signingPrivateKeyPem)
                if followersJson:
                    if isinstance(followersJson, dict):
                        _desktopShowFollowing(followersJson, translate,
                                              currPage, indent,
                                              'followers')
                print('')
            elif (commandStr == 'follow' or
                  commandStr.startswith('follow ')):
                if commandStr == 'follow':
                    if actorJson:
                        followHandle = actorJson['id']
                    else:
                        followHandle = ''
                else:
                    followHandle = commandStr.replace('follow ', '').strip()
                    if followHandle.startswith('@'):
                        followHandle = followHandle[1:]

                if '@' in followHandle or '://' in followHandle:
                    followNickname = getNicknameFromActor(followHandle)
                    followDomain, followPort = \
                        getDomainFromActor(followHandle)
                    if followNickname and followDomain:
                        sayStr = 'Sending follow request to ' + \
                            followNickname + '@' + followDomain
                        _sayCommand(sayStr, sayStr,
                                    screenreader, systemLanguage, espeak)
                        sessionFollow = createSession(proxyType)
                        sendFollowRequestViaServer(baseDir,
                                                   sessionFollow,
                                                   nickname, password,
                                                   domain, port,
                                                   followNickname,
                                                   followDomain,
                                                   followPort,
                                                   httpPrefix,
                                                   cachedWebfingers,
                                                   personCache,
                                                   debug, __version__,
                                                   signingPrivateKeyPem)
                    else:
                        if followHandle:
                            sayStr = followHandle + ' is not valid'
                        else:
                            sayStr = 'Specify a handle to follow'
                        _sayCommand(sayStr,
                                    screenreader, systemLanguage, espeak)
                    print('')
            elif (commandStr.startswith('unfollow ') or
                  commandStr.startswith('stop following ')):
                followHandle = commandStr.replace('unfollow ', '').strip()
                followHandle = followHandle.replace('stop following ', '')
                if followHandle.startswith('@'):
                    followHandle = followHandle[1:]
                if '@' in followHandle or '://' in followHandle:
                    followNickname = getNicknameFromActor(followHandle)
                    followDomain, followPort = \
                        getDomainFromActor(followHandle)
                    if followNickname and followDomain:
                        sayStr = 'Stop following ' + \
                            followNickname + '@' + followDomain
                        _sayCommand(sayStr, sayStr,
                                    screenreader, systemLanguage, espeak)
                        sessionUnfollow = createSession(proxyType)
                        sendUnfollowRequestViaServer(baseDir, sessionUnfollow,
                                                     nickname, password,
                                                     domain, port,
                                                     followNickname,
                                                     followDomain,
                                                     followPort,
                                                     httpPrefix,
                                                     cachedWebfingers,
                                                     personCache,
                                                     debug, __version__,
                                                     signingPrivateKeyPem)
                    else:
                        sayStr = followHandle + ' is not valid'
                        _sayCommand(sayStr, sayStr,
                                    screenreader, systemLanguage, espeak)
                    print('')
            elif commandStr.startswith('approve '):
                approveHandle = commandStr.replace('approve ', '').strip()
                if approveHandle.startswith('@'):
                    approveHandle = approveHandle[1:]

                if '@' in approveHandle or '://' in approveHandle:
                    approveNickname = getNicknameFromActor(approveHandle)
                    approveDomain, approvePort = \
                        getDomainFromActor(approveHandle)
                    if approveNickname and approveDomain:
                        sayStr = 'Sending approve follow request for ' + \
                            approveNickname + '@' + approveDomain
                        _sayCommand(sayStr, sayStr,
                                    screenreader, systemLanguage, espeak)
                        sessionApprove = createSession(proxyType)
                        approveFollowRequestViaServer(baseDir, sessionApprove,
                                                      nickname, password,
                                                      domain, port,
                                                      httpPrefix,
                                                      approveHandle,
                                                      cachedWebfingers,
                                                      personCache,
                                                      debug,
                                                      __version__,
                                                      signingPrivateKeyPem)
                    else:
                        if approveHandle:
                            sayStr = approveHandle + ' is not valid'
                        else:
                            sayStr = 'Specify a handle to approve'
                        _sayCommand(sayStr,
                                    screenreader, systemLanguage, espeak)
                    print('')
            elif commandStr.startswith('deny '):
                denyHandle = commandStr.replace('deny ', '').strip()
                if denyHandle.startswith('@'):
                    denyHandle = denyHandle[1:]

                if '@' in denyHandle or '://' in denyHandle:
                    denyNickname = getNicknameFromActor(denyHandle)
                    denyDomain, denyPort = \
                        getDomainFromActor(denyHandle)
                    if denyNickname and denyDomain:
                        sayStr = 'Sending deny follow request for ' + \
                            denyNickname + '@' + denyDomain
                        _sayCommand(sayStr, sayStr,
                                    screenreader, systemLanguage, espeak)
                        sessionDeny = createSession(proxyType)
                        denyFollowRequestViaServer(baseDir, sessionDeny,
                                                   nickname, password,
                                                   domain, port,
                                                   httpPrefix,
                                                   denyHandle,
                                                   cachedWebfingers,
                                                   personCache,
                                                   debug,
                                                   __version__,
                                                   signingPrivateKeyPem)
                    else:
                        if denyHandle:
                            sayStr = denyHandle + ' is not valid'
                        else:
                            sayStr = 'Specify a handle to deny'
                        _sayCommand(sayStr,
                                    screenreader, systemLanguage, espeak)
                    print('')
            elif (commandStr == 'repeat' or commandStr == 'replay' or
                  commandStr == 'rp' or commandStr == 'again' or
                  commandStr == 'say again'):
                if screenreader and nameStr and \
                   gender and messageStr and content:
                    sayStr = 'Repeating ' + nameStr
                    _sayCommand(sayStr, sayStr, screenreader,
                                systemLanguage, espeak,
                                nameStr, gender)
                    time.sleep(2)
                    _sayCommand(content, messageStr, screenreader,
                                systemLanguage, espeak,
                                nameStr, gender)
                    print('')
            elif (commandStr == 'sounds on' or
                  commandStr == 'sound on' or
                  commandStr == 'sound'):
                sayStr = 'Notification sounds on'
                _sayCommand(sayStr, sayStr, screenreader,
                            systemLanguage, espeak)
                notificationSounds = True
            elif (commandStr == 'sounds off' or
                  commandStr == 'sound off' or
                  commandStr == 'nosound'):
                sayStr = 'Notification sounds off'
                _sayCommand(sayStr, sayStr, screenreader,
                            systemLanguage, espeak)
                notificationSounds = False
            elif (commandStr == 'speak' or
                  commandStr == 'screen reader on' or
                  commandStr == 'speaker on' or
                  commandStr == 'talker on' or
                  commandStr == 'reader on'):
                if originalScreenReader:
                    screenreader = originalScreenReader
                    sayStr = 'Screen reader on'
                    _sayCommand(sayStr, sayStr, screenreader,
                                systemLanguage, espeak)
                else:
                    print('No --screenreader option was specified')
            elif (commandStr == 'mute' or
                  commandStr == 'screen reader off' or
                  commandStr == 'speaker off' or
                  commandStr == 'talker off' or
                  commandStr == 'reader off'):
                if originalScreenReader:
                    screenreader = None
                    sayStr = 'Screen reader off'
                    _sayCommand(sayStr, sayStr, originalScreenReader,
                                systemLanguage, espeak)
                else:
                    print('No --screenreader option was specified')
            elif commandStr.startswith('open'):
                currIndex = 0
                if ' ' in commandStr:
                    postIndex = commandStr.split(' ')[-1].strip()
                    if postIndex.isdigit():
                        currIndex = int(postIndex)
                if currIndex > 0 and boxJson:
                    postJsonObject = \
                        _desktopGetBoxPostObject(boxJson, currIndex)
                if postJsonObject:
                    if postJsonObject['type'] == 'Announce':
                        recentPostsCache = {}
                        allowLocalNetworkAccess = False
                        YTReplacementDomain = None
                        twitterReplacementDomain = None
                        postJsonObject2 = \
                            downloadAnnounce(session, baseDir,
                                             httpPrefix,
                                             nickname, domain,
                                             postJsonObject,
                                             __version__, translate,
                                             YTReplacementDomain,
                                             twitterReplacementDomain,
                                             allowLocalNetworkAccess,
                                             recentPostsCache, False,
                                             systemLanguage,
                                             domainFull, personCache,
                                             signingPrivateKeyPem,
                                             blockedCache)
                        if postJsonObject2:
                            postJsonObject = postJsonObject2
                if postJsonObject:
                    content = \
                        getBaseContentFromPost(postJsonObject, systemLanguage)
                    messageStr, detectedLinks = \
                        speakableText(baseDir, content, translate)
                    linkOpened = False
                    for url in detectedLinks:
                        if '://' in url:
                            webbrowser.open(url)
                            linkOpened = True
                    if linkOpened:
                        sayStr = 'Opened web links'
                        _sayCommand(sayStr, sayStr, originalScreenReader,
                                    systemLanguage, espeak)
                    else:
                        sayStr = 'There are no web links to open.'
                        _sayCommand(sayStr, sayStr, originalScreenReader,
                                    systemLanguage, espeak)
                print('')
            elif commandStr.startswith('pgp') or commandStr.startswith('gpg'):
                if not hasLocalPGPkey():
                    print('No PGP public key was found')
                else:
                    print(pgpLocalPublicKey())
                print('')
            elif commandStr.startswith('h'):
                _desktopHelp()
                sayStr = 'Press Enter to continue...'
                sayStr2 = _highlightText(sayStr)
                _sayCommand(sayStr2, sayStr,
                            screenreader, systemLanguage, espeak)
                input()
                prevTimelineFirstId = ''
                refreshTimeline = True
            elif (commandStr == 'delete' or
                  commandStr == 'rm' or
                  commandStr.startswith('delete ') or
                  commandStr.startswith('rm ')):
                currIndex = 0
                if ' ' in commandStr:
                    postIndex = commandStr.split(' ')[-1].strip()
                    if postIndex.isdigit():
                        currIndex = int(postIndex)
                if currIndex > 0 and boxJson:
                    postJsonObject = \
                        _desktopGetBoxPostObject(boxJson, currIndex)
                if postJsonObject:
                    if postJsonObject.get('id'):
                        rmActor = postJsonObject['object']['attributedTo']
                        if rmActor != yourActor:
                            sayStr = 'You can only delete your own posts'
                            _sayCommand(sayStr, sayStr,
                                        screenreader,
                                        systemLanguage, espeak)
                        else:
                            print('')
                            if postJsonObject['object'].get('summary'):
                                print(postJsonObject['object']['summary'])
                            contentStr = getBaseContentFromPost(postJsonObject,
                                                                systemLanguage)
                            print(contentStr)
                            print('')
                            sayStr = 'Confirm delete, yes or no?'
                            _sayCommand(sayStr, sayStr, screenreader,
                                        systemLanguage, espeak)
                            yesno = input()
                            if 'y' not in yesno.lower():
                                sayStr = 'Deleting post'
                                _sayCommand(sayStr, sayStr,
                                            screenreader,
                                            systemLanguage, espeak)
                                sessionrm = createSession(proxyType)
                                sendDeleteViaServer(baseDir, sessionrm,
                                                    nickname, password,
                                                    domain, port,
                                                    httpPrefix,
                                                    postJsonObject['id'],
                                                    cachedWebfingers,
                                                    personCache,
                                                    False, __version__,
                                                    signingPrivateKeyPem)
                                refreshTimeline = True
                print('')

            if refreshTimeline:
                if boxJson:
                    _desktopShowBox(indent, followRequestsJson,
                                    yourActor, currTimeline, boxJson,
                                    translate,
                                    screenreader, systemLanguage,
                                    espeak, pageNumber,
                                    newRepliesExist, newDMsExist)
