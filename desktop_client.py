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
from utils import get_base_content_from_post
from utils import has_object_dict
from utils import get_full_domain
from utils import isDM
from utils import loadTranslationsFromFile
from utils import removeHtml
from utils import getNicknameFromActor
from utils import getDomainFromActor
from utils import isPGPEncrypted
from utils import local_actor_url
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
        except Exception as ex:
            print('WARN: Failed to mark post as read' + str(ex))
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


def _postIsToYou(actor: str, post_json_object: {}) -> bool:
    """Returns true if the post is to the actor
    """
    toYourActor = False
    if post_json_object.get('to'):
        if actor in post_json_object['to']:
            toYourActor = True
    if not toYourActor and post_json_object.get('cc'):
        if actor in post_json_object['cc']:
            toYourActor = True
    if not toYourActor and has_object_dict(post_json_object):
        if post_json_object['object'].get('to'):
            if actor in post_json_object['object']['to']:
                toYourActor = True
        if not toYourActor and post_json_object['object'].get('cc'):
            if actor in post_json_object['object']['cc']:
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
    for post_json_object in inboxJson['orderedItems']:
        if not post_json_object.get('id'):
            continue
        if not post_json_object.get('type'):
            continue
        if post_json_object['type'] == 'Announce':
            continue
        if not _postIsToYou(actor, post_json_object):
            continue
        if isDM(post_json_object):
            if not DMdone:
                if not _hasReadPost(actor, post_json_object['id'], 'dm'):
                    changed = False
                    if not notifyJson.get('dmPostId'):
                        changed = True
                    else:
                        if notifyJson['dmPostId'] != post_json_object['id']:
                            changed = True
                    if changed:
                        notifyJson['dmNotify'] = True
                        notifyJson['dmNotifyChanged'] = True
                        notifyJson['dmPostId'] = post_json_object['id']
                    DMdone = True
        else:
            if not replyDone:
                if not _hasReadPost(actor, post_json_object['id'], 'replies'):
                    changed = False
                    if not notifyJson.get('repliesPostId'):
                        changed = True
                    else:
                        if notifyJson['repliesPostId'] != \
                           post_json_object['id']:
                            changed = True
                    if changed:
                        notifyJson['repliesNotify'] = True
                        notifyJson['repliesNotifyChanged'] = True
                        notifyJson['repliesPostId'] = post_json_object['id']
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


def _speakerPicospeaker(pitch: int, rate: int, system_language: str,
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
        if system_language.startswith(lang):
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
                  system_language: str, espeak=None) -> None:
    """Say something via TTS
    """
    # speak the post content
    if screenreader == 'espeak':
        _speakerEspeak(espeak, pitch, rate, srange, sayStr)
    elif screenreader == 'picospeaker':
        _speakerPicospeaker(pitch, rate, system_language, sayStr)


def _sayCommand(content: str, sayStr: str, screenreader: str,
                system_language: str,
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
                  system_language, espeak)


def _desktopReplyToPost(session, postId: str,
                        base_dir: str, nickname: str, password: str,
                        domain: str, port: int, http_prefix: str,
                        cached_webfingers: {}, person_cache: {},
                        debug: bool, subject: str,
                        screenreader: str, system_language: str,
                        espeak, conversationId: str,
                        low_bandwidth: bool,
                        content_license_url: str,
                        signing_priv_key_pem: str) -> None:
    """Use the desktop client to send a reply to the most recent post
    """
    if '://' not in postId:
        return
    toNickname = getNicknameFromActor(postId)
    toDomain, toPort = getDomainFromActor(postId)
    sayStr = 'Replying to ' + toNickname + '@' + toDomain
    _sayCommand(sayStr, sayStr,
                screenreader, system_language, espeak)
    sayStr = 'Type your reply message, then press Enter.'
    _sayCommand(sayStr, sayStr, screenreader, system_language, espeak)
    replyMessage = input()
    if not replyMessage:
        sayStr = 'No reply was entered.'
        _sayCommand(sayStr, sayStr, screenreader, system_language, espeak)
        return
    replyMessage = replyMessage.strip()
    if not replyMessage:
        sayStr = 'No reply was entered.'
        _sayCommand(sayStr, sayStr, screenreader, system_language, espeak)
        return
    print('')
    sayStr = 'You entered this reply:'
    _sayCommand(sayStr, sayStr, screenreader, system_language, espeak)
    _sayCommand(replyMessage, replyMessage, screenreader,
                system_language, espeak)
    sayStr = 'Send this reply, yes or no?'
    _sayCommand(sayStr, sayStr, screenreader, system_language, espeak)
    yesno = input()
    if 'y' not in yesno.lower():
        sayStr = 'Abandoning reply'
        _sayCommand(sayStr, sayStr, screenreader, system_language, espeak)
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
    _sayCommand(sayStr, sayStr, screenreader, system_language, espeak)
    if sendPostViaServer(signing_priv_key_pem, __version__,
                         base_dir, session, nickname, password,
                         domain, port,
                         toNickname, toDomain, toPort, ccUrl,
                         http_prefix, replyMessage, followersOnly,
                         commentsEnabled, attach, mediaType,
                         attachedImageDescription, city,
                         cached_webfingers, person_cache, isArticle,
                         system_language, low_bandwidth,
                         content_license_url,
                         debug, postId, postId,
                         conversationId, subject) == 0:
        sayStr = 'Reply sent'
    else:
        sayStr = 'Reply failed'
    _sayCommand(sayStr, sayStr, screenreader, system_language, espeak)


def _desktopNewPost(session,
                    base_dir: str, nickname: str, password: str,
                    domain: str, port: int, http_prefix: str,
                    cached_webfingers: {}, person_cache: {},
                    debug: bool,
                    screenreader: str, system_language: str,
                    espeak, low_bandwidth: bool,
                    content_license_url: str,
                    signing_priv_key_pem: str) -> None:
    """Use the desktop client to create a new post
    """
    conversationId = None
    sayStr = 'Create new post'
    _sayCommand(sayStr, sayStr, screenreader, system_language, espeak)
    sayStr = 'Type your post, then press Enter.'
    _sayCommand(sayStr, sayStr, screenreader, system_language, espeak)
    newMessage = input()
    if not newMessage:
        sayStr = 'No post was entered.'
        _sayCommand(sayStr, sayStr, screenreader, system_language, espeak)
        return
    newMessage = newMessage.strip()
    if not newMessage:
        sayStr = 'No post was entered.'
        _sayCommand(sayStr, sayStr, screenreader, system_language, espeak)
        return
    print('')
    sayStr = 'You entered this public post:'
    _sayCommand(sayStr, sayStr, screenreader, system_language, espeak)
    _sayCommand(newMessage, newMessage, screenreader, system_language, espeak)
    sayStr = 'Send this post, yes or no?'
    _sayCommand(sayStr, sayStr, screenreader, system_language, espeak)
    yesno = input()
    if 'y' not in yesno.lower():
        sayStr = 'Abandoning new post'
        _sayCommand(sayStr, sayStr, screenreader, system_language, espeak)
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
    _sayCommand(sayStr, sayStr, screenreader, system_language, espeak)
    if sendPostViaServer(signing_priv_key_pem, __version__,
                         base_dir, session, nickname, password,
                         domain, port,
                         None, '#Public', port, ccUrl,
                         http_prefix, newMessage, followersOnly,
                         commentsEnabled, attach, mediaType,
                         attachedImageDescription, city,
                         cached_webfingers, person_cache, isArticle,
                         system_language, low_bandwidth,
                         content_license_url,
                         debug, None, None,
                         conversationId, subject) == 0:
        sayStr = 'Post sent'
    else:
        sayStr = 'Post failed'
    _sayCommand(sayStr, sayStr, screenreader, system_language, espeak)


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


def _getImageDescription(post_json_object: {}) -> str:
    """Returns a image description/s on a post
    """
    imageDescription = ''
    if not post_json_object['object'].get('attachment'):
        return imageDescription

    attachList = post_json_object['object']['attachment']
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


def _showLikesOnPost(post_json_object: {}, maxLikes: int) -> None:
    """Shows the likes on a post
    """
    if not has_object_dict(post_json_object):
        return
    if not post_json_object['object'].get('likes'):
        return
    objectLikes = post_json_object['object']['likes']
    if not isinstance(objectLikes, dict):
        return
    if not objectLikes.get('items'):
        return
    if not isinstance(objectLikes['items'], list):
        return
    print('')
    ctr = 0
    for item in objectLikes['items']:
        print('  ❤ ' + str(item['actor']))
        ctr += 1
        if ctr >= maxLikes:
            break


def _showRepliesOnPost(post_json_object: {}, max_replies: int) -> None:
    """Shows the replies on a post
    """
    if not has_object_dict(post_json_object):
        return
    if not post_json_object['object'].get('replies'):
        return
    objectReplies = post_json_object['object']['replies']
    if not isinstance(objectReplies, dict):
        return
    if not objectReplies.get('items'):
        return
    if not isinstance(objectReplies['items'], list):
        return
    print('')
    ctr = 0
    for item in objectReplies['items']:
        print('  ↰ ' + str(item['url']))
        ctr += 1
        if ctr >= max_replies:
            break


def _readLocalBoxPost(session, nickname: str, domain: str,
                      http_prefix: str, base_dir: str, boxName: str,
                      pageNumber: int, index: int, boxJson: {},
                      system_language: str,
                      screenreader: str, espeak,
                      translate: {}, yourActor: str,
                      domain_full: str, person_cache: {},
                      signing_priv_key_pem: str,
                      blockedCache: {}) -> {}:
    """Reads a post from the given timeline
    Returns the post json
    """
    if _timelineIsEmpty(boxJson):
        return {}

    post_json_object = _desktopGetBoxPostObject(boxJson, index)
    if not post_json_object:
        return {}
    gender = 'They/Them'

    boxNameStr = boxName
    if boxName.startswith('tl'):
        boxNameStr = boxName[2:]
    sayStr = 'Reading ' + boxNameStr + ' post ' + str(index) + \
        ' from page ' + str(pageNumber) + '.'
    sayStr2 = sayStr.replace(' dm ', ' DM ')
    _sayCommand(sayStr, sayStr2, screenreader, system_language, espeak)
    print('')

    if post_json_object['type'] == 'Announce':
        actor = post_json_object['actor']
        nameStr = getNicknameFromActor(actor)
        recentPostsCache = {}
        allow_local_network_access = False
        yt_replace_domain = None
        twitter_replacement_domain = None
        post_json_object2 = \
            downloadAnnounce(session, base_dir,
                             http_prefix,
                             nickname, domain,
                             post_json_object,
                             __version__, translate,
                             yt_replace_domain,
                             twitter_replacement_domain,
                             allow_local_network_access,
                             recentPostsCache, False,
                             system_language,
                             domain_full, person_cache,
                             signing_priv_key_pem,
                             blockedCache)
        if post_json_object2:
            if has_object_dict(post_json_object2):
                if post_json_object2['object'].get('attributedTo') and \
                   post_json_object2['object'].get('content'):
                    attributedTo = post_json_object2['object']['attributedTo']
                    content = \
                        get_base_content_from_post(post_json_object2,
                                                   system_language)
                    if isinstance(attributedTo, str) and content:
                        actor = attributedTo
                        nameStr += ' ' + translate['announces'] + ' ' + \
                            getNicknameFromActor(actor)
                        sayStr = nameStr
                        _sayCommand(sayStr, sayStr, screenreader,
                                    system_language, espeak)
                        print('')
                        if screenreader:
                            time.sleep(2)
                        content = \
                            _textOnlyContent(content)
                        content += _getImageDescription(post_json_object2)
                        messageStr, detectedLinks = \
                            speakableText(base_dir, content, translate)
                        sayStr = content
                        _sayCommand(sayStr, messageStr, screenreader,
                                    system_language, espeak)
                        return post_json_object2
        return {}

    attributedTo = post_json_object['object']['attributedTo']
    if not attributedTo:
        return {}
    content = get_base_content_from_post(post_json_object, system_language)
    if not isinstance(attributedTo, str) or \
       not isinstance(content, str):
        return {}
    actor = attributedTo
    nameStr = getNicknameFromActor(actor)
    content = _textOnlyContent(content)
    content += _getImageDescription(post_json_object)

    if isPGPEncrypted(content):
        sayStr = 'Encrypted message. Please enter your passphrase.'
        _sayCommand(sayStr, sayStr, screenreader, system_language, espeak)
        content = pgpDecrypt(domain, content, actor, signing_priv_key_pem)
        if isPGPEncrypted(content):
            sayStr = 'Message could not be decrypted'
            _sayCommand(sayStr, sayStr, screenreader, system_language, espeak)
            return {}

    content = _safeMessage(content)
    messageStr, detectedLinks = speakableText(base_dir, content, translate)

    if screenreader:
        time.sleep(2)

    # say the speaker's name
    _sayCommand(nameStr, nameStr, screenreader,
                system_language, espeak, nameStr, gender)
    print('')

    if post_json_object['object'].get('inReplyTo'):
        print('Replying to ' + post_json_object['object']['inReplyTo'] + '\n')

    if screenreader:
        time.sleep(2)

    # speak the post content
    _sayCommand(content, messageStr, screenreader,
                system_language, espeak, nameStr, gender)

    _showLikesOnPost(post_json_object, 10)
    _showRepliesOnPost(post_json_object, 10)

    # if the post is addressed to you then mark it as read
    if _postIsToYou(yourActor, post_json_object):
        if isDM(post_json_object):
            _markPostAsRead(yourActor, post_json_object['id'], 'dm')
        else:
            _markPostAsRead(yourActor, post_json_object['id'], 'replies')

    return post_json_object


def _desktopShowActor(base_dir: str, actor_json: {}, translate: {},
                      system_language: str, screenreader: str,
                      espeak) -> None:
    """Shows information for the given actor
    """
    actor = actor_json['id']
    actorNickname = getNicknameFromActor(actor)
    actorDomain, actorPort = getDomainFromActor(actor)
    actorDomainFull = get_full_domain(actorDomain, actorPort)
    handle = '@' + actorNickname + '@' + actorDomainFull

    sayStr = 'Profile for ' + html.unescape(handle)
    _sayCommand(sayStr, sayStr, screenreader, system_language, espeak)
    print(actor)
    if actor_json.get('movedTo'):
        sayStr = 'Moved to ' + html.unescape(actor_json['movedTo'])
        _sayCommand(sayStr, sayStr, screenreader, system_language, espeak)
    if actor_json.get('alsoKnownAs'):
        alsoKnownAsStr = ''
        ctr = 0
        for altActor in actor_json['alsoKnownAs']:
            if ctr > 0:
                alsoKnownAsStr += ', '
            ctr += 1
            alsoKnownAsStr += altActor

        sayStr = 'Also known as ' + html.unescape(alsoKnownAsStr)
        _sayCommand(sayStr, sayStr, screenreader, system_language, espeak)
    if actor_json.get('summary'):
        sayStr = html.unescape(removeHtml(actor_json['summary']))
        sayStr = sayStr.replace('"', "'")
        sayStr2 = speakableText(base_dir, sayStr, translate)[0]
        _sayCommand(sayStr, sayStr2, screenreader, system_language, espeak)


def _desktopShowProfile(session, nickname: str, domain: str,
                        http_prefix: str, base_dir: str, boxName: str,
                        pageNumber: int, index: int, boxJson: {},
                        system_language: str,
                        screenreader: str, espeak,
                        translate: {}, yourActor: str,
                        post_json_object: {}, signing_priv_key_pem: str) -> {}:
    """Shows the profile of the actor for the given post
    Returns the actor json
    """
    if _timelineIsEmpty(boxJson):
        return {}

    if not post_json_object:
        post_json_object = _desktopGetBoxPostObject(boxJson, index)
        if not post_json_object:
            return {}

    actor = None
    if post_json_object['type'] == 'Announce':
        nickname = getNicknameFromActor(post_json_object['object'])
        if nickname:
            nickStr = '/' + nickname + '/'
            if nickStr in post_json_object['object']:
                actor = \
                    post_json_object['object'].split(nickStr)[0] + \
                    '/' + nickname
    else:
        actor = post_json_object['object']['attributedTo']

    if not actor:
        return {}

    isHttp = False
    if 'http://' in actor:
        isHttp = True
    actor_json, asHeader = \
        getActorJson(domain, actor, isHttp, False, False, True,
                     signing_priv_key_pem, session)

    _desktopShowActor(base_dir, actor_json, translate,
                      system_language, screenreader, espeak)

    return actor_json


def _desktopShowProfileFromHandle(session, nickname: str, domain: str,
                                  http_prefix: str, base_dir: str,
                                  boxName: str, handle: str,
                                  system_language: str,
                                  screenreader: str, espeak,
                                  translate: {}, yourActor: str,
                                  post_json_object: {},
                                  signing_priv_key_pem: str) -> {}:
    """Shows the profile for a handle
    Returns the actor json
    """
    actor_json, asHeader = \
        getActorJson(domain, handle, False, False, False, True,
                     signing_priv_key_pem, session)

    _desktopShowActor(base_dir, actor_json, translate,
                      system_language, screenreader, espeak)

    return actor_json


def _desktopGetBoxPostObject(boxJson: {}, index: int) -> {}:
    """Gets the post with the given index from the timeline
    """
    ctr = 0
    for post_json_object in boxJson['orderedItems']:
        if not post_json_object.get('type'):
            continue
        if not post_json_object.get('object'):
            continue
        if post_json_object['type'] == 'Announce':
            if not isinstance(post_json_object['object'], str):
                continue
            ctr += 1
            if ctr == index:
                return post_json_object
            continue
        if not has_object_dict(post_json_object):
            continue
        if not post_json_object['object'].get('published'):
            continue
        if not post_json_object['object'].get('content'):
            continue
        ctr += 1
        if ctr == index:
            return post_json_object
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
                    screenreader: str, system_language: str, espeak,
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
        _sayCommand(sayStr, sayStr, screenreader, system_language, espeak)
        print('')
        return False

    ctr = 1
    for post_json_object in boxJson['orderedItems']:
        if not post_json_object.get('type'):
            continue
        if post_json_object['type'] == 'Announce':
            if post_json_object.get('actor') and \
               post_json_object.get('object'):
                if isinstance(post_json_object['object'], str):
                    authorActor = post_json_object['actor']
                    name = getNicknameFromActor(authorActor) + ' ⮌'
                    name = _padToWidth(name, nameWidth)
                    ctrStr = str(ctr)
                    posStr = _padToWidth(ctrStr, numberWidth)
                    published = _formatPublished(post_json_object['published'])
                    announcedNickname = \
                        getNicknameFromActor(post_json_object['object'])
                    announcedDomain, announcedPort = \
                        getDomainFromActor(post_json_object['object'])
                    announcedHandle = announcedNickname + '@' + announcedDomain
                    lineStr = \
                        indent + str(posStr) + ' | ' + name + ' | ' + \
                        published + ' | ' + \
                        _padToWidth(announcedHandle, contentWidth)
                    print(lineStr)
                    ctr += 1
                    continue

        if not has_object_dict(post_json_object):
            continue
        if not post_json_object['object'].get('published'):
            continue
        if not post_json_object['object'].get('content'):
            continue
        ctrStr = str(ctr)
        posStr = _padToWidth(ctrStr, numberWidth)

        authorActor = post_json_object['object']['attributedTo']
        contentWarning = None
        if post_json_object['object'].get('summary'):
            contentWarning = '⚡' + \
                _padToWidth(post_json_object['object']['summary'],
                            contentWidth)
        name = getNicknameFromActor(authorActor)

        # append icons to the end of the name
        spaceAdded = False
        if post_json_object['object'].get('inReplyTo'):
            if not spaceAdded:
                spaceAdded = True
                name += ' '
            name += '↲'
            if post_json_object['object'].get('replies'):
                repliesList = post_json_object['object']['replies']
                if repliesList.get('items'):
                    items = repliesList['items']
                    for i in range(int(items)):
                        name += '↰'
                        if i > 10:
                            break
        likesCount = noOfLikes(post_json_object)
        if likesCount > 10:
            likesCount = 10
        for like in range(likesCount):
            if not spaceAdded:
                spaceAdded = True
                name += ' '
            name += '❤'
        name = _padToWidth(name, nameWidth)

        published = _formatPublished(post_json_object['published'])

        contentStr = get_base_content_from_post(post_json_object,
                                                system_language)
        content = _textOnlyContent(contentStr)
        if boxName != 'dm':
            if isDM(post_json_object):
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
        if post_json_object['object'].get('ignores'):
            content = '🔇'
        if post_json_object['object'].get('bookmarks'):
            content = '🔖' + content
        if '\n' in content:
            content = content.replace('\n', ' ')
        lineStr = indent + str(posStr) + ' | ' + name + ' | ' + \
            published + ' | ' + content
        if boxName == 'inbox' and \
           _postIsToYou(yourActor, post_json_object):
            if not _hasReadPost(yourActor, post_json_object['id'], 'dm'):
                if not _hasReadPost(yourActor, post_json_object['id'],
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
    _sayCommand(sayStr, sayStr2, screenreader, system_language, espeak)
    print('')
    return True


def _desktopNewDM(session, toHandle: str,
                  base_dir: str, nickname: str, password: str,
                  domain: str, port: int, http_prefix: str,
                  cached_webfingers: {}, person_cache: {},
                  debug: bool,
                  screenreader: str, system_language: str,
                  espeak, low_bandwidth: bool,
                  content_license_url: str,
                  signing_priv_key_pem: str) -> None:
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
                          base_dir, nickname, password,
                          domain, port, http_prefix,
                          cached_webfingers, person_cache,
                          debug,
                          screenreader, system_language,
                          espeak, low_bandwidth,
                          content_license_url,
                          signing_priv_key_pem)


def _desktopNewDMbase(session, toHandle: str,
                      base_dir: str, nickname: str, password: str,
                      domain: str, port: int, http_prefix: str,
                      cached_webfingers: {}, person_cache: {},
                      debug: bool,
                      screenreader: str, system_language: str,
                      espeak, low_bandwidth: bool,
                      content_license_url: str,
                      signing_priv_key_pem: str) -> None:
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
    _sayCommand(sayStr, sayStr, screenreader, system_language, espeak)
    sayStr = 'Type your direct message, then press Enter.'
    _sayCommand(sayStr, sayStr, screenreader, system_language, espeak)
    newMessage = input()
    if not newMessage:
        sayStr = 'No direct message was entered.'
        _sayCommand(sayStr, sayStr, screenreader, system_language, espeak)
        return
    newMessage = newMessage.strip()
    if not newMessage:
        sayStr = 'No direct message was entered.'
        _sayCommand(sayStr, sayStr, screenreader, system_language, espeak)
        return
    sayStr = 'You entered this direct message to ' + toHandle + ':'
    _sayCommand(sayStr, sayStr, screenreader, system_language, espeak)
    _sayCommand(newMessage, newMessage, screenreader, system_language, espeak)
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
        _sayCommand(sayStr, sayStr, screenreader, system_language, espeak)
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
                              signing_priv_key_pem)
        if not cipherText:
            sayStr = \
                toHandle + ' has no PGP public key. ' + \
                'Your message will be sent in clear text'
            _sayCommand(sayStr, sayStr, screenreader, system_language, espeak)
        else:
            newMessage = cipherText
            sayStr = 'Message encrypted'
            _sayCommand(sayStr, sayStr, screenreader, system_language, espeak)

    sayStr = 'Send this direct message, yes or no?'
    _sayCommand(sayStr, sayStr, screenreader, system_language, espeak)
    yesno = input()
    if 'y' not in yesno.lower():
        sayStr = 'Abandoning new direct message'
        _sayCommand(sayStr, sayStr, screenreader, system_language, espeak)
        return

    sayStr = 'Sending'
    _sayCommand(sayStr, sayStr, screenreader, system_language, espeak)
    if sendPostViaServer(signing_priv_key_pem, __version__,
                         base_dir, session, nickname, password,
                         domain, port,
                         toNickname, toDomain, toPort, ccUrl,
                         http_prefix, newMessage, followersOnly,
                         commentsEnabled, attach, mediaType,
                         attachedImageDescription, city,
                         cached_webfingers, person_cache, isArticle,
                         system_language, low_bandwidth,
                         content_license_url,
                         debug, None, None,
                         conversationId, subject) == 0:
        sayStr = 'Direct message sent'
    else:
        sayStr = 'Direct message failed'
    _sayCommand(sayStr, sayStr, screenreader, system_language, espeak)


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
            get_full_domain(handleDomain, handlePort)
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
            get_full_domain(handleDomain, handlePort)
        print(indent + '  👤 ' +
              handleNickname + '@' + handleDomainFull)


def runDesktopClient(base_dir: str, proxy_type: str, http_prefix: str,
                     nickname: str, domain: str, port: int,
                     password: str, screenreader: str,
                     system_language: str,
                     notificationSounds: bool,
                     notificationType: str,
                     noKeyPress: bool,
                     storeInboxPosts: bool,
                     showNewPosts: bool,
                     language: str,
                     debug: bool, low_bandwidth: bool) -> None:
    """Runs the desktop and screen reader client,
    which announces new inbox items
    """
    # TODO: this should probably be retrieved somehow from the server
    signing_priv_key_pem = None

    content_license_url = 'https://creativecommons.org/licenses/by/4.0'

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
                    system_language, espeak)
    else:
        print(indent + 'Running desktop notifications for ' +
              nickname + '@' + domain)
    if notificationSounds:
        sayStr = indent + 'Notification sounds on'
    else:
        sayStr = indent + 'Notification sounds off'
    _sayCommand(sayStr, sayStr, screenreader,
                system_language, espeak)

    currTimeline = 'inbox'
    pageNumber = 1

    post_json_object = {}
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
    cached_webfingers = {}
    person_cache = {}
    newRepliesExist = False
    newDMsExist = False
    pgpKeyUpload = False

    sayStr = indent + 'Loading translations file'
    _sayCommand(sayStr, sayStr, screenreader,
                system_language, espeak)
    translate, system_language = \
        loadTranslationsFromFile(base_dir, language)

    sayStr = indent + 'Connecting...'
    _sayCommand(sayStr, sayStr, screenreader,
                system_language, espeak)
    session = createSession(proxy_type)

    sayStr = indent + '/q or /quit to exit'
    _sayCommand(sayStr, sayStr, screenreader,
                system_language, espeak)

    domain_full = get_full_domain(domain, port)
    yourActor = local_actor_url(http_prefix, nickname, domain_full)
    actor_json = None

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
                            system_language, espeak)
                pgpPublicKeyUpload(base_dir, session,
                                   nickname, password,
                                   domain, port, http_prefix,
                                   cached_webfingers, person_cache,
                                   debug, False,
                                   signing_priv_key_pem)
                sayStr = indent + 'PGP public key uploaded'
                _sayCommand(sayStr, sayStr, screenreader,
                            system_language, espeak)
            pgpKeyUpload = True

        boxJson = c2sBoxJson(base_dir, session,
                             nickname, password,
                             domain, port, http_prefix,
                             currTimeline, pageNumber,
                             debug, signing_priv_key_pem)

        followRequestsJson = \
            getFollowRequestsViaServer(base_dir, session,
                                       nickname, password,
                                       domain, port,
                                       http_prefix, 1,
                                       cached_webfingers, person_cache,
                                       debug, __version__,
                                       signing_priv_key_pem)

        if not (currTimeline == 'inbox' and pageNumber == 1):
            # monitor the inbox to generate notifications
            inboxJson = c2sBoxJson(base_dir, session,
                                   nickname, password,
                                   domain, port, http_prefix,
                                   'inbox', 1, debug,
                                   signing_priv_key_pem)
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
                                None, system_language, espeak,
                                pageNumber,
                                newRepliesExist,
                                newDMsExist)
                desktopShown = True
            prevTimelineFirstId = timelineFirstId
        else:
            session = createSession(proxy_type)
            if not desktopShown:
                if not session:
                    print('No session\n')

                _desktopClearScreen()
                _desktopShowBanner()
                print('No posts\n')
                if proxy_type == 'tor':
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
                            system_language, espeak)
                if screenreader:
                    commandStr = _desktopWaitForCmd(2, debug)
                break
            elif commandStr.startswith('show dm'):
                pageNumber = 1
                prevTimelineFirstId = ''
                currTimeline = 'dm'
                boxJson = c2sBoxJson(base_dir, session,
                                     nickname, password,
                                     domain, port, http_prefix,
                                     currTimeline, pageNumber,
                                     debug, signing_priv_key_pem)
                if boxJson:
                    _desktopShowBox(indent, followRequestsJson,
                                    yourActor, currTimeline, boxJson,
                                    translate,
                                    screenreader, system_language, espeak,
                                    pageNumber,
                                    newRepliesExist, newDMsExist)
                newDMsExist = False
            elif commandStr.startswith('show rep'):
                pageNumber = 1
                prevTimelineFirstId = ''
                currTimeline = 'tlreplies'
                boxJson = c2sBoxJson(base_dir, session,
                                     nickname, password,
                                     domain, port, http_prefix,
                                     currTimeline, pageNumber,
                                     debug, signing_priv_key_pem)
                if boxJson:
                    _desktopShowBox(indent, followRequestsJson,
                                    yourActor, currTimeline, boxJson,
                                    translate,
                                    screenreader, system_language, espeak,
                                    pageNumber,
                                    newRepliesExist, newDMsExist)
                # Turn off the replies indicator
                newRepliesExist = False
            elif commandStr.startswith('show b'):
                pageNumber = 1
                prevTimelineFirstId = ''
                currTimeline = 'tlbookmarks'
                boxJson = c2sBoxJson(base_dir, session,
                                     nickname, password,
                                     domain, port, http_prefix,
                                     currTimeline, pageNumber,
                                     debug, signing_priv_key_pem)
                if boxJson:
                    _desktopShowBox(indent, followRequestsJson,
                                    yourActor, currTimeline, boxJson,
                                    translate,
                                    screenreader, system_language, espeak,
                                    pageNumber,
                                    newRepliesExist, newDMsExist)
                # Turn off the replies indicator
                newRepliesExist = False
            elif (commandStr.startswith('show sen') or
                  commandStr.startswith('show out')):
                pageNumber = 1
                prevTimelineFirstId = ''
                currTimeline = 'outbox'
                boxJson = c2sBoxJson(base_dir, session,
                                     nickname, password,
                                     domain, port, http_prefix,
                                     currTimeline, pageNumber,
                                     debug, signing_priv_key_pem)
                if boxJson:
                    _desktopShowBox(indent, followRequestsJson,
                                    yourActor, currTimeline, boxJson,
                                    translate,
                                    screenreader, system_language, espeak,
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
                boxJson = c2sBoxJson(base_dir, session,
                                     nickname, password,
                                     domain, port, http_prefix,
                                     currTimeline, pageNumber,
                                     debug, signing_priv_key_pem)
                if boxJson:
                    _desktopShowBox(indent, followRequestsJson,
                                    yourActor, currTimeline, boxJson,
                                    translate,
                                    screenreader, system_language, espeak,
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
                    post_json_object = \
                        _readLocalBoxPost(session, nickname, domain,
                                          http_prefix, base_dir, currTimeline,
                                          pageNumber, postIndex, boxJson,
                                          system_language, screenreader,
                                          espeak, translate, yourActor,
                                          domain_full, person_cache,
                                          signing_priv_key_pem,
                                          blockedCache)
                    print('')
                    sayStr = 'Press Enter to continue...'
                    sayStr2 = _highlightText(sayStr)
                    _sayCommand(sayStr2, sayStr,
                                screenreader, system_language, espeak)
                    input()
                    prevTimelineFirstId = ''
                    refreshTimeline = True
                print('')
            elif commandStr.startswith('profile ') or commandStr == 'profile':
                actor_json = None
                if commandStr == 'profile':
                    if post_json_object:
                        actor_json = \
                            _desktopShowProfile(session, nickname, domain,
                                                http_prefix, base_dir,
                                                currTimeline,
                                                pageNumber, postIndex,
                                                boxJson,
                                                system_language, screenreader,
                                                espeak, translate, yourActor,
                                                post_json_object,
                                                signing_priv_key_pem)
                    else:
                        postIndexStr = '1'
                else:
                    postIndexStr = commandStr.split('profile ')[1]

                if not postIndexStr.isdigit():
                    profileHandle = postIndexStr
                    _desktopClearScreen()
                    _desktopShowBanner()
                    _desktopShowProfileFromHandle(session, nickname, domain,
                                                  http_prefix, base_dir,
                                                  currTimeline,
                                                  profileHandle,
                                                  system_language,
                                                  screenreader,
                                                  espeak, translate,
                                                  yourActor,
                                                  None,
                                                  signing_priv_key_pem)
                    sayStr = 'Press Enter to continue...'
                    sayStr2 = _highlightText(sayStr)
                    _sayCommand(sayStr2, sayStr,
                                screenreader, system_language, espeak)
                    input()
                    prevTimelineFirstId = ''
                    refreshTimeline = True
                elif not actor_json and boxJson:
                    _desktopClearScreen()
                    _desktopShowBanner()
                    postIndex = int(postIndexStr)
                    actor_json = \
                        _desktopShowProfile(session, nickname, domain,
                                            http_prefix, base_dir,
                                            currTimeline,
                                            pageNumber, postIndex,
                                            boxJson,
                                            system_language, screenreader,
                                            espeak, translate, yourActor,
                                            None, signing_priv_key_pem)
                    sayStr = 'Press Enter to continue...'
                    sayStr2 = _highlightText(sayStr)
                    _sayCommand(sayStr2, sayStr,
                                screenreader, system_language, espeak)
                    input()
                    prevTimelineFirstId = ''
                    refreshTimeline = True
                print('')
            elif commandStr == 'reply' or commandStr == 'r':
                if post_json_object:
                    if post_json_object.get('id'):
                        postId = post_json_object['id']
                        subject = None
                        if post_json_object['object'].get('summary'):
                            subject = post_json_object['object']['summary']
                        conversationId = None
                        if post_json_object['object'].get('conversation'):
                            conversationId = \
                                post_json_object['object']['conversation']
                        sessionReply = createSession(proxy_type)
                        _desktopReplyToPost(sessionReply, postId,
                                            base_dir, nickname, password,
                                            domain, port, http_prefix,
                                            cached_webfingers, person_cache,
                                            debug, subject,
                                            screenreader, system_language,
                                            espeak, conversationId,
                                            low_bandwidth,
                                            content_license_url,
                                            signing_priv_key_pem)
                refreshTimeline = True
                print('')
            elif (commandStr == 'post' or commandStr == 'p' or
                  commandStr == 'send' or
                  commandStr.startswith('dm ') or
                  commandStr.startswith('direct message ') or
                  commandStr.startswith('post ') or
                  commandStr.startswith('send ')):
                sessionPost = createSession(proxy_type)
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
                                      base_dir, nickname, password,
                                      domain, port, http_prefix,
                                      cached_webfingers, person_cache,
                                      debug,
                                      screenreader, system_language,
                                      espeak, low_bandwidth,
                                      content_license_url,
                                      signing_priv_key_pem)
                        refreshTimeline = True
                else:
                    # public post
                    _desktopNewPost(sessionPost,
                                    base_dir, nickname, password,
                                    domain, port, http_prefix,
                                    cached_webfingers, person_cache,
                                    debug,
                                    screenreader, system_language,
                                    espeak, low_bandwidth,
                                    content_license_url,
                                    signing_priv_key_pem)
                    refreshTimeline = True
                print('')
            elif commandStr == 'like' or commandStr.startswith('like '):
                currIndex = 0
                if ' ' in commandStr:
                    postIndex = commandStr.split(' ')[-1].strip()
                    if postIndex.isdigit():
                        currIndex = int(postIndex)
                if currIndex > 0 and boxJson:
                    post_json_object = \
                        _desktopGetBoxPostObject(boxJson, currIndex)
                if post_json_object:
                    if post_json_object.get('id'):
                        likeActor = post_json_object['object']['attributedTo']
                        sayStr = 'Liking post by ' + \
                            getNicknameFromActor(likeActor)
                        _sayCommand(sayStr, sayStr,
                                    screenreader,
                                    system_language, espeak)
                        sessionLike = createSession(proxy_type)
                        sendLikeViaServer(base_dir, sessionLike,
                                          nickname, password,
                                          domain, port, http_prefix,
                                          post_json_object['id'],
                                          cached_webfingers, person_cache,
                                          False, __version__,
                                          signing_priv_key_pem)
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
                    post_json_object = \
                        _desktopGetBoxPostObject(boxJson, currIndex)
                if post_json_object:
                    if post_json_object.get('id'):
                        muteActor = post_json_object['object']['attributedTo']
                        sayStr = 'Unmuting post by ' + \
                            getNicknameFromActor(muteActor)
                        _sayCommand(sayStr, sayStr,
                                    screenreader,
                                    system_language, espeak)
                        sessionMute = createSession(proxy_type)
                        sendUndoMuteViaServer(base_dir, sessionMute,
                                              nickname, password,
                                              domain, port,
                                              http_prefix,
                                              post_json_object['id'],
                                              cached_webfingers,
                                              person_cache,
                                              False, __version__,
                                              signing_priv_key_pem)
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
                    post_json_object = \
                        _desktopGetBoxPostObject(boxJson, currIndex)
                if post_json_object:
                    if post_json_object.get('id'):
                        muteActor = post_json_object['object']['attributedTo']
                        sayStr = 'Muting post by ' + \
                            getNicknameFromActor(muteActor)
                        _sayCommand(sayStr, sayStr,
                                    screenreader,
                                    system_language, espeak)
                        sessionMute = createSession(proxy_type)
                        sendMuteViaServer(base_dir, sessionMute,
                                          nickname, password,
                                          domain, port,
                                          http_prefix, post_json_object['id'],
                                          cached_webfingers, person_cache,
                                          False, __version__,
                                          signing_priv_key_pem)
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
                    post_json_object = \
                        _desktopGetBoxPostObject(boxJson, currIndex)
                if post_json_object:
                    if post_json_object.get('id'):
                        bmActor = post_json_object['object']['attributedTo']
                        sayStr = 'Unbookmarking post by ' + \
                            getNicknameFromActor(bmActor)
                        _sayCommand(sayStr, sayStr,
                                    screenreader,
                                    system_language, espeak)
                        sessionbm = createSession(proxy_type)
                        sendUndoBookmarkViaServer(base_dir, sessionbm,
                                                  nickname, password,
                                                  domain, port, http_prefix,
                                                  post_json_object['id'],
                                                  cached_webfingers,
                                                  person_cache,
                                                  False, __version__,
                                                  signing_priv_key_pem)
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
                    post_json_object = \
                        _desktopGetBoxPostObject(boxJson, currIndex)
                if post_json_object:
                    if post_json_object.get('id'):
                        bmActor = post_json_object['object']['attributedTo']
                        sayStr = 'Bookmarking post by ' + \
                            getNicknameFromActor(bmActor)
                        _sayCommand(sayStr, sayStr,
                                    screenreader,
                                    system_language, espeak)
                        sessionbm = createSession(proxy_type)
                        sendBookmarkViaServer(base_dir, sessionbm,
                                              nickname, password,
                                              domain, port, http_prefix,
                                              post_json_object['id'],
                                              cached_webfingers, person_cache,
                                              False, __version__,
                                              signing_priv_key_pem)
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
                    post_json_object = \
                        _desktopGetBoxPostObject(boxJson, currIndex)
                if post_json_object:
                    if post_json_object.get('id') and \
                       post_json_object.get('object'):
                        if has_object_dict(post_json_object):
                            if post_json_object['object'].get('attributedTo'):
                                blockActor = \
                                    post_json_object['object']['attributedTo']
                                sayStr = 'Unblocking ' + \
                                    getNicknameFromActor(blockActor)
                                _sayCommand(sayStr, sayStr,
                                            screenreader,
                                            system_language, espeak)
                                sessionBlock = createSession(proxy_type)
                                sendUndoBlockViaServer(base_dir, sessionBlock,
                                                       nickname, password,
                                                       domain, port,
                                                       http_prefix,
                                                       blockActor,
                                                       cached_webfingers,
                                                       person_cache,
                                                       False, __version__,
                                                       signing_priv_key_pem)
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
                                    local_actor_url(http_prefix,
                                                    blockNickname,
                                                    blockDomain)
                if currIndex > 0 and boxJson and not blockActor:
                    post_json_object = \
                        _desktopGetBoxPostObject(boxJson, currIndex)
                if post_json_object and not blockActor:
                    if post_json_object.get('id') and \
                       post_json_object.get('object'):
                        if has_object_dict(post_json_object):
                            if post_json_object['object'].get('attributedTo'):
                                blockActor = \
                                    post_json_object['object']['attributedTo']
                if blockActor:
                    sayStr = 'Blocking ' + \
                        getNicknameFromActor(blockActor)
                    _sayCommand(sayStr, sayStr,
                                screenreader,
                                system_language, espeak)
                    sessionBlock = createSession(proxy_type)
                    sendBlockViaServer(base_dir, sessionBlock,
                                       nickname, password,
                                       domain, port,
                                       http_prefix,
                                       blockActor,
                                       cached_webfingers,
                                       person_cache,
                                       False, __version__,
                                       signing_priv_key_pem)
                refreshTimeline = True
                print('')
            elif commandStr == 'unlike' or commandStr == 'undo like':
                currIndex = 0
                if ' ' in commandStr:
                    postIndex = commandStr.split(' ')[-1].strip()
                    if postIndex.isdigit():
                        currIndex = int(postIndex)
                if currIndex > 0 and boxJson:
                    post_json_object = \
                        _desktopGetBoxPostObject(boxJson, currIndex)
                if post_json_object:
                    if post_json_object.get('id'):
                        unlikeActor = \
                            post_json_object['object']['attributedTo']
                        sayStr = \
                            'Undoing like of post by ' + \
                            getNicknameFromActor(unlikeActor)
                        _sayCommand(sayStr, sayStr,
                                    screenreader,
                                    system_language, espeak)
                        sessionUnlike = createSession(proxy_type)
                        sendUndoLikeViaServer(base_dir, sessionUnlike,
                                              nickname, password,
                                              domain, port, http_prefix,
                                              post_json_object['id'],
                                              cached_webfingers, person_cache,
                                              False, __version__,
                                              signing_priv_key_pem)
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
                    post_json_object = \
                        _desktopGetBoxPostObject(boxJson, currIndex)
                if post_json_object:
                    if post_json_object.get('id'):
                        postId = post_json_object['id']
                        announceActor = \
                            post_json_object['object']['attributedTo']
                        sayStr = 'Announcing post by ' + \
                            getNicknameFromActor(announceActor)
                        _sayCommand(sayStr, sayStr,
                                    screenreader,
                                    system_language, espeak)
                        sessionAnnounce = createSession(proxy_type)
                        sendAnnounceViaServer(base_dir, sessionAnnounce,
                                              nickname, password,
                                              domain, port,
                                              http_prefix, postId,
                                              cached_webfingers, person_cache,
                                              True, __version__,
                                              signing_priv_key_pem)
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
                    post_json_object = \
                        _desktopGetBoxPostObject(boxJson, currIndex)
                if post_json_object:
                    if post_json_object.get('id'):
                        postId = post_json_object['id']
                        announceActor = \
                            post_json_object['object']['attributedTo']
                        sayStr = 'Undoing announce post by ' + \
                            getNicknameFromActor(announceActor)
                        _sayCommand(sayStr, sayStr,
                                    screenreader,
                                    system_language, espeak)
                        sessionAnnounce = createSession(proxy_type)
                        sendUndoAnnounceViaServer(base_dir, sessionAnnounce,
                                                  post_json_object,
                                                  nickname, password,
                                                  domain, port,
                                                  http_prefix, postId,
                                                  cached_webfingers,
                                                  person_cache,
                                                  True, __version__,
                                                  signing_priv_key_pem)
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
                    getFollowRequestsViaServer(base_dir, session,
                                               nickname, password,
                                               domain, port,
                                               http_prefix, currPage,
                                               cached_webfingers, person_cache,
                                               debug, __version__,
                                               signing_priv_key_pem)
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
                    getFollowingViaServer(base_dir, session,
                                          nickname, password,
                                          domain, port,
                                          http_prefix, currPage,
                                          cached_webfingers, person_cache,
                                          debug, __version__,
                                          signing_priv_key_pem)
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
                    getFollowersViaServer(base_dir, session,
                                          nickname, password,
                                          domain, port,
                                          http_prefix, currPage,
                                          cached_webfingers, person_cache,
                                          debug, __version__,
                                          signing_priv_key_pem)
                if followersJson:
                    if isinstance(followersJson, dict):
                        _desktopShowFollowing(followersJson, translate,
                                              currPage, indent,
                                              'followers')
                print('')
            elif (commandStr == 'follow' or
                  commandStr.startswith('follow ')):
                if commandStr == 'follow':
                    if actor_json:
                        followHandle = actor_json['id']
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
                                    screenreader, system_language, espeak)
                        sessionFollow = createSession(proxy_type)
                        sendFollowRequestViaServer(base_dir,
                                                   sessionFollow,
                                                   nickname, password,
                                                   domain, port,
                                                   followNickname,
                                                   followDomain,
                                                   followPort,
                                                   http_prefix,
                                                   cached_webfingers,
                                                   person_cache,
                                                   debug, __version__,
                                                   signing_priv_key_pem)
                    else:
                        if followHandle:
                            sayStr = followHandle + ' is not valid'
                        else:
                            sayStr = 'Specify a handle to follow'
                        _sayCommand(sayStr,
                                    screenreader, system_language, espeak)
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
                                    screenreader, system_language, espeak)
                        sessionUnfollow = createSession(proxy_type)
                        sendUnfollowRequestViaServer(base_dir, sessionUnfollow,
                                                     nickname, password,
                                                     domain, port,
                                                     followNickname,
                                                     followDomain,
                                                     followPort,
                                                     http_prefix,
                                                     cached_webfingers,
                                                     person_cache,
                                                     debug, __version__,
                                                     signing_priv_key_pem)
                    else:
                        sayStr = followHandle + ' is not valid'
                        _sayCommand(sayStr, sayStr,
                                    screenreader, system_language, espeak)
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
                                    screenreader, system_language, espeak)
                        sessionApprove = createSession(proxy_type)
                        approveFollowRequestViaServer(base_dir, sessionApprove,
                                                      nickname, password,
                                                      domain, port,
                                                      http_prefix,
                                                      approveHandle,
                                                      cached_webfingers,
                                                      person_cache,
                                                      debug,
                                                      __version__,
                                                      signing_priv_key_pem)
                    else:
                        if approveHandle:
                            sayStr = approveHandle + ' is not valid'
                        else:
                            sayStr = 'Specify a handle to approve'
                        _sayCommand(sayStr,
                                    screenreader, system_language, espeak)
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
                                    screenreader, system_language, espeak)
                        sessionDeny = createSession(proxy_type)
                        denyFollowRequestViaServer(base_dir, sessionDeny,
                                                   nickname, password,
                                                   domain, port,
                                                   http_prefix,
                                                   denyHandle,
                                                   cached_webfingers,
                                                   person_cache,
                                                   debug,
                                                   __version__,
                                                   signing_priv_key_pem)
                    else:
                        if denyHandle:
                            sayStr = denyHandle + ' is not valid'
                        else:
                            sayStr = 'Specify a handle to deny'
                        _sayCommand(sayStr,
                                    screenreader, system_language, espeak)
                    print('')
            elif (commandStr == 'repeat' or commandStr == 'replay' or
                  commandStr == 'rp' or commandStr == 'again' or
                  commandStr == 'say again'):
                if screenreader and nameStr and \
                   gender and messageStr and content:
                    sayStr = 'Repeating ' + nameStr
                    _sayCommand(sayStr, sayStr, screenreader,
                                system_language, espeak,
                                nameStr, gender)
                    time.sleep(2)
                    _sayCommand(content, messageStr, screenreader,
                                system_language, espeak,
                                nameStr, gender)
                    print('')
            elif (commandStr == 'sounds on' or
                  commandStr == 'sound on' or
                  commandStr == 'sound'):
                sayStr = 'Notification sounds on'
                _sayCommand(sayStr, sayStr, screenreader,
                            system_language, espeak)
                notificationSounds = True
            elif (commandStr == 'sounds off' or
                  commandStr == 'sound off' or
                  commandStr == 'nosound'):
                sayStr = 'Notification sounds off'
                _sayCommand(sayStr, sayStr, screenreader,
                            system_language, espeak)
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
                                system_language, espeak)
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
                                system_language, espeak)
                else:
                    print('No --screenreader option was specified')
            elif commandStr.startswith('open'):
                currIndex = 0
                if ' ' in commandStr:
                    postIndex = commandStr.split(' ')[-1].strip()
                    if postIndex.isdigit():
                        currIndex = int(postIndex)
                if currIndex > 0 and boxJson:
                    post_json_object = \
                        _desktopGetBoxPostObject(boxJson, currIndex)
                if post_json_object:
                    if post_json_object['type'] == 'Announce':
                        recentPostsCache = {}
                        allow_local_network_access = False
                        yt_replace_domain = None
                        twitter_replacement_domain = None
                        post_json_object2 = \
                            downloadAnnounce(session, base_dir,
                                             http_prefix,
                                             nickname, domain,
                                             post_json_object,
                                             __version__, translate,
                                             yt_replace_domain,
                                             twitter_replacement_domain,
                                             allow_local_network_access,
                                             recentPostsCache, False,
                                             system_language,
                                             domain_full, person_cache,
                                             signing_priv_key_pem,
                                             blockedCache)
                        if post_json_object2:
                            post_json_object = post_json_object2
                if post_json_object:
                    content = \
                        get_base_content_from_post(post_json_object,
                                                   system_language)
                    messageStr, detectedLinks = \
                        speakableText(base_dir, content, translate)
                    linkOpened = False
                    for url in detectedLinks:
                        if '://' in url:
                            webbrowser.open(url)
                            linkOpened = True
                    if linkOpened:
                        sayStr = 'Opened web links'
                        _sayCommand(sayStr, sayStr, originalScreenReader,
                                    system_language, espeak)
                    else:
                        sayStr = 'There are no web links to open.'
                        _sayCommand(sayStr, sayStr, originalScreenReader,
                                    system_language, espeak)
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
                            screenreader, system_language, espeak)
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
                    post_json_object = \
                        _desktopGetBoxPostObject(boxJson, currIndex)
                if post_json_object:
                    if post_json_object.get('id'):
                        rmActor = post_json_object['object']['attributedTo']
                        if rmActor != yourActor:
                            sayStr = 'You can only delete your own posts'
                            _sayCommand(sayStr, sayStr,
                                        screenreader,
                                        system_language, espeak)
                        else:
                            print('')
                            if post_json_object['object'].get('summary'):
                                print(post_json_object['object']['summary'])
                            contentStr = \
                                get_base_content_from_post(post_json_object,
                                                           system_language)
                            print(contentStr)
                            print('')
                            sayStr = 'Confirm delete, yes or no?'
                            _sayCommand(sayStr, sayStr, screenreader,
                                        system_language, espeak)
                            yesno = input()
                            if 'y' not in yesno.lower():
                                sayStr = 'Deleting post'
                                _sayCommand(sayStr, sayStr,
                                            screenreader,
                                            system_language, espeak)
                                sessionrm = createSession(proxy_type)
                                sendDeleteViaServer(base_dir, sessionrm,
                                                    nickname, password,
                                                    domain, port,
                                                    http_prefix,
                                                    post_json_object['id'],
                                                    cached_webfingers,
                                                    person_cache,
                                                    False, __version__,
                                                    signing_priv_key_pem)
                                refreshTimeline = True
                print('')

            if refreshTimeline:
                if boxJson:
                    _desktopShowBox(indent, followRequestsJson,
                                    yourActor, currTimeline, boxJson,
                                    translate,
                                    screenreader, system_language,
                                    espeak, pageNumber,
                                    newRepliesExist, newDMsExist)
