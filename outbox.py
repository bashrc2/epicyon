__filename__ = "outbox.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Timeline"

import os
from shutil import copyfile
from session import create_session
from auth import createPassword
from posts import isImageMedia
from posts import outbox_message_create_wrap
from posts import save_post_to_box
from posts import sendToFollowersThread
from posts import sendToNamedAddressesThread
from utils import has_object_stringType
from utils import get_base_content_from_post
from utils import has_object_dict
from utils import get_local_network_addresses
from utils import get_full_domain
from utils import remove_id_ending
from utils import get_domain_from_actor
from utils import dangerous_markup
from utils import is_featured_writer
from utils import load_json
from utils import save_json
from utils import acct_dir
from utils import local_actor_url
from utils import has_actor
from blocking import isBlockedDomain
from blocking import outboxBlock
from blocking import outboxUndoBlock
from blocking import outboxMute
from blocking import outboxUndoMute
from media import replaceYouTube
from media import replaceTwitter
from media import getMediaPath
from media import createMediaDirs
from inbox import inboxUpdateIndex
from announce import outboxAnnounce
from announce import outboxUndoAnnounce
from follow import outboxUndoFollow
from follow import follower_approval_active
from skills import outboxSkills
from availability import outboxAvailability
from like import outboxLike
from like import outboxUndoLike
from reaction import outboxReaction
from reaction import outboxUndoReaction
from bookmarks import outboxBookmark
from bookmarks import outboxUndoBookmark
from delete import outboxDelete
from shares import outboxShareUpload
from shares import outboxUndoShareUpload
from webapp_post import individualPostAsHtml


def _outboxPersonReceiveUpdate(recent_posts_cache: {},
                               base_dir: str, http_prefix: str,
                               nickname: str, domain: str, port: int,
                               message_json: {}, debug: bool) -> None:
    """ Receive an actor update from c2s
    For example, setting the PGP key from the desktop client
    """
    # these attachments are updatable via c2s
    updatableAttachments = ('PGP', 'OpenPGP', 'Email')

    if not message_json.get('type'):
        return
    if not isinstance(message_json['type'], str):
        if debug:
            print('DEBUG: c2s actor update type is not a string')
        return
    if message_json['type'] != 'Update':
        return
    if not has_object_stringType(message_json, debug):
        return
    if not isinstance(message_json['object']['type'], str):
        if debug:
            print('DEBUG: c2s actor update object type is not a string')
        return
    if message_json['object']['type'] != 'Person':
        if debug:
            print('DEBUG: not a c2s actor update')
        return
    if not message_json.get('to'):
        if debug:
            print('DEBUG: c2s actor update has no "to" field')
        return
    if not has_actor(message_json, debug):
        return
    if not message_json.get('id'):
        if debug:
            print('DEBUG: c2s actor update has no id field')
        return
    if not isinstance(message_json['id'], str):
        if debug:
            print('DEBUG: c2s actor update id is not a string')
        return
    domain_full = get_full_domain(domain, port)
    actor = local_actor_url(http_prefix, nickname, domain_full)
    if len(message_json['to']) != 1:
        if debug:
            print('DEBUG: c2s actor update - to does not contain one actor ' +
                  str(message_json['to']))
        return
    if message_json['to'][0] != actor:
        if debug:
            print('DEBUG: c2s actor update - to does not contain actor ' +
                  str(message_json['to']) + ' ' + actor)
        return
    if not message_json['id'].startswith(actor + '#updates/'):
        if debug:
            print('DEBUG: c2s actor update - unexpected id ' +
                  message_json['id'])
        return
    updatedActorJson = message_json['object']
    # load actor from file
    actorFilename = acct_dir(base_dir, nickname, domain) + '.json'
    if not os.path.isfile(actorFilename):
        print('actorFilename not found: ' + actorFilename)
        return
    actor_json = load_json(actorFilename)
    if not actor_json:
        return
    actorChanged = False
    # update fields within actor
    if 'attachment' in updatedActorJson:
        for newPropertyValue in updatedActorJson['attachment']:
            if not newPropertyValue.get('name'):
                continue
            if newPropertyValue['name'] not in updatableAttachments:
                continue
            if not newPropertyValue.get('type'):
                continue
            if not newPropertyValue.get('value'):
                continue
            if newPropertyValue['type'] != 'PropertyValue':
                continue
            if 'attachment' not in actor_json:
                continue
            found = False
            for attachIdx in range(len(actor_json['attachment'])):
                if actor_json['attachment'][attachIdx]['type'] != \
                   'PropertyValue':
                    continue
                if actor_json['attachment'][attachIdx]['name'] != \
                   newPropertyValue['name']:
                    continue
                else:
                    if actor_json['attachment'][attachIdx]['value'] != \
                       newPropertyValue['value']:
                        actor_json['attachment'][attachIdx]['value'] = \
                            newPropertyValue['value']
                        actorChanged = True
                    found = True
                    break
            if not found:
                actor_json['attachment'].append({
                    "name": newPropertyValue['name'],
                    "type": "PropertyValue",
                    "value": newPropertyValue['value']
                })
                actorChanged = True
    # save actor to file
    if actorChanged:
        save_json(actor_json, actorFilename)
        if debug:
            print('actor saved: ' + actorFilename)
    if debug:
        print('New attachment: ' + str(actor_json['attachment']))
    message_json['object'] = actor_json
    if debug:
        print('DEBUG: actor update via c2s - ' + nickname + '@' + domain)


def postMessageToOutbox(session, translate: {},
                        message_json: {}, postToNickname: str,
                        server, base_dir: str, http_prefix: str,
                        domain: str, domain_full: str,
                        onion_domain: str, i2p_domain: str, port: int,
                        recent_posts_cache: {}, followers_threads: [],
                        federation_list: [], send_threads: [],
                        postLog: [], cached_webfingers: {},
                        person_cache: {}, allow_deletion: bool,
                        proxy_type: str, version: str, debug: bool,
                        yt_replace_domain: str,
                        twitter_replacement_domain: str,
                        show_published_date_only: bool,
                        allow_local_network_access: bool,
                        city: str, system_language: str,
                        shared_items_federated_domains: [],
                        sharedItemFederationTokens: {},
                        low_bandwidth: bool,
                        signing_priv_key_pem: str,
                        peertube_instances: str, theme: str,
                        max_like_count: int,
                        max_recent_posts: int, cw_lists: {},
                        lists_enabled: str,
                        content_license_url: str) -> bool:
    """post is received by the outbox
    Client to server message post
    https://www.w3.org/TR/activitypub/#client-to-server-outbox-delivery
    """
    if not message_json.get('type'):
        if debug:
            print('DEBUG: POST to outbox has no "type" parameter')
        return False
    if not message_json.get('object') and message_json.get('content'):
        if message_json['type'] != 'Create':
            # https://www.w3.org/TR/activitypub/#object-without-create
            if debug:
                print('DEBUG: POST to outbox - adding Create wrapper')
            message_json = \
                outbox_message_create_wrap(http_prefix,
                                           postToNickname,
                                           domain, port,
                                           message_json)

    # check that the outgoing post doesn't contain any markup
    # which can be used to implement exploits
    if has_object_dict(message_json):
        contentStr = get_base_content_from_post(message_json, system_language)
        if contentStr:
            if dangerous_markup(contentStr, allow_local_network_access):
                print('POST to outbox contains dangerous markup: ' +
                      str(message_json))
                return False

    if message_json['type'] == 'Create':
        if not (message_json.get('id') and
                message_json.get('type') and
                message_json.get('actor') and
                message_json.get('object') and
                message_json.get('to')):
            if not message_json.get('id'):
                if debug:
                    print('DEBUG: POST to outbox - ' +
                          'Create does not have the id parameter ' +
                          str(message_json))
            elif not message_json.get('id'):
                if debug:
                    print('DEBUG: POST to outbox - ' +
                          'Create does not have the type parameter ' +
                          str(message_json))
            elif not message_json.get('id'):
                if debug:
                    print('DEBUG: POST to outbox - ' +
                          'Create does not have the actor parameter ' +
                          str(message_json))
            elif not message_json.get('id'):
                if debug:
                    print('DEBUG: POST to outbox - ' +
                          'Create does not have the object parameter ' +
                          str(message_json))
            else:
                if debug:
                    print('DEBUG: POST to outbox - ' +
                          'Create does not have the "to" parameter ' +
                          str(message_json))
            return False

        # actor should be a string
        if not isinstance(message_json['actor'], str):
            return False

        # actor should look like a url
        if '://' not in message_json['actor'] or \
           '.' not in message_json['actor']:
            return False

        # sent by an actor on a local network address?
        if not allow_local_network_access:
            localNetworkPatternList = get_local_network_addresses()
            for localNetworkPattern in localNetworkPatternList:
                if localNetworkPattern in message_json['actor']:
                    return False

        testDomain, testPort = get_domain_from_actor(message_json['actor'])
        testDomain = get_full_domain(testDomain, testPort)
        if isBlockedDomain(base_dir, testDomain):
            if debug:
                print('DEBUG: domain is blocked: ' + message_json['actor'])
            return False
        # replace youtube, so that google gets less tracking data
        replaceYouTube(message_json, yt_replace_domain, system_language)
        # replace twitter, so that twitter posts can be shown without
        # having a twitter account
        replaceTwitter(message_json, twitter_replacement_domain,
                       system_language)
        # https://www.w3.org/TR/activitypub/#create-activity-outbox
        message_json['object']['attributedTo'] = message_json['actor']
        if message_json['object'].get('attachment'):
            attachmentIndex = 0
            attach = message_json['object']['attachment'][attachmentIndex]
            if attach.get('mediaType'):
                fileExtension = 'png'
                mediaTypeStr = \
                    attach['mediaType']

                extensions = {
                    "jpeg": "jpg",
                    "gif": "gif",
                    "svg": "svg",
                    "webp": "webp",
                    "avif": "avif",
                    "audio/mpeg": "mp3",
                    "ogg": "ogg",
                    "mp4": "mp4",
                    "webm": "webm",
                    "ogv": "ogv"
                }
                for matchExt, ext in extensions.items():
                    if mediaTypeStr.endswith(matchExt):
                        fileExtension = ext
                        break

                mediaDir = \
                    base_dir + '/accounts/' + \
                    postToNickname + '@' + domain
                uploadMediaFilename = mediaDir + '/upload.' + fileExtension
                if not os.path.isfile(uploadMediaFilename):
                    del message_json['object']['attachment']
                else:
                    # generate a path for the uploaded image
                    mPath = getMediaPath()
                    mediaPath = mPath + '/' + \
                        createPassword(16).lower() + '.' + fileExtension
                    createMediaDirs(base_dir, mPath)
                    mediaFilename = base_dir + '/' + mediaPath
                    # move the uploaded image to its new path
                    os.rename(uploadMediaFilename, mediaFilename)
                    # change the url of the attachment
                    attach['url'] = \
                        http_prefix + '://' + domain_full + '/' + mediaPath
                    attach['url'] = \
                        attach['url'].replace('/media/',
                                              '/system/' +
                                              'media_attachments/files/')

    permittedOutboxTypes = (
        'Create', 'Announce', 'Like', 'EmojiReact', 'Follow', 'Undo',
        'Update', 'Add', 'Remove', 'Block', 'Delete', 'Skill', 'Ignore'
    )
    if message_json['type'] not in permittedOutboxTypes:
        if debug:
            print('DEBUG: POST to outbox - ' + message_json['type'] +
                  ' is not a permitted activity type')
        return False
    if message_json.get('id'):
        post_id = remove_id_ending(message_json['id'])
        if debug:
            print('DEBUG: id attribute exists within POST to outbox')
    else:
        if debug:
            print('DEBUG: No id attribute within POST to outbox')
        post_id = None
    if debug:
        print('DEBUG: save_post_to_box')
    if message_json['type'] != 'Upgrade':
        outboxName = 'outbox'

        # if this is a blog post or an event then save to its own box
        if message_json['type'] == 'Create':
            if has_object_dict(message_json):
                if message_json['object'].get('type'):
                    if message_json['object']['type'] == 'Article':
                        outboxName = 'tlblogs'

        savedFilename = \
            save_post_to_box(base_dir,
                             http_prefix,
                             post_id,
                             postToNickname, domain_full,
                             message_json, outboxName)
        if not savedFilename:
            print('WARN: post not saved to outbox ' + outboxName)
            return False

        # save all instance blogs to the news actor
        if postToNickname != 'news' and outboxName == 'tlblogs':
            if '/' in savedFilename:
                if is_featured_writer(base_dir, postToNickname, domain):
                    savedPostId = savedFilename.split('/')[-1]
                    blogsDir = \
                        base_dir + '/accounts/news@' + domain + '/tlblogs'
                    if not os.path.isdir(blogsDir):
                        os.mkdir(blogsDir)
                    copyfile(savedFilename, blogsDir + '/' + savedPostId)
                    inboxUpdateIndex('tlblogs', base_dir,
                                     'news@' + domain,
                                     savedFilename, debug)

                # clear the citations file if it exists
                citationsFilename = \
                    base_dir + '/accounts/' + \
                    postToNickname + '@' + domain + '/.citations.txt'
                if os.path.isfile(citationsFilename):
                    try:
                        os.remove(citationsFilename)
                    except OSError:
                        print('EX: postMessageToOutbox unable to delete ' +
                              citationsFilename)

        # The following activity types get added to the index files
        indexedActivities = (
            'Create', 'Question', 'Note', 'EncryptedMessage', 'Article',
            'Patch', 'Announce'
        )
        if message_json['type'] in indexedActivities:
            indexes = [outboxName, "inbox"]
            selfActor = \
                local_actor_url(http_prefix, postToNickname, domain_full)
            for boxNameIndex in indexes:
                if not boxNameIndex:
                    continue

                # should this also go to the media timeline?
                if boxNameIndex == 'inbox':
                    if isImageMedia(session, base_dir, http_prefix,
                                    postToNickname, domain,
                                    message_json,
                                    translate,
                                    yt_replace_domain,
                                    twitter_replacement_domain,
                                    allow_local_network_access,
                                    recent_posts_cache, debug, system_language,
                                    domain_full, person_cache,
                                    signing_priv_key_pem):
                        inboxUpdateIndex('tlmedia', base_dir,
                                         postToNickname + '@' + domain,
                                         savedFilename, debug)

                if boxNameIndex == 'inbox' and outboxName == 'tlblogs':
                    continue

                # avoid duplicates of the message if already going
                # back to the inbox of the same account
                if selfActor not in message_json['to']:
                    # show sent post within the inbox,
                    # as is the typical convention
                    inboxUpdateIndex(boxNameIndex, base_dir,
                                     postToNickname + '@' + domain,
                                     savedFilename, debug)

                    # regenerate the html
                    useCacheOnly = False
                    pageNumber = 1
                    showIndividualPostIcons = True
                    manuallyApproveFollowers = \
                        follower_approval_active(base_dir,
                                                 postToNickname, domain)
                    individualPostAsHtml(signing_priv_key_pem,
                                         False, recent_posts_cache,
                                         max_recent_posts,
                                         translate, pageNumber,
                                         base_dir, session,
                                         cached_webfingers,
                                         person_cache,
                                         postToNickname, domain, port,
                                         message_json, None, True,
                                         allow_deletion,
                                         http_prefix, __version__,
                                         boxNameIndex,
                                         yt_replace_domain,
                                         twitter_replacement_domain,
                                         show_published_date_only,
                                         peertube_instances,
                                         allow_local_network_access,
                                         theme, system_language,
                                         max_like_count,
                                         boxNameIndex != 'dm',
                                         showIndividualPostIcons,
                                         manuallyApproveFollowers,
                                         False, True, useCacheOnly,
                                         cw_lists, lists_enabled)

    if outboxAnnounce(recent_posts_cache,
                      base_dir, message_json, debug):
        if debug:
            print('DEBUG: Updated announcements (shares) collection ' +
                  'for the post associated with the Announce activity')
    if not server.session:
        print('DEBUG: creating new session for c2s')
        server.session = create_session(proxy_type)
        if not server.session:
            print('ERROR: Failed to create session for postMessageToOutbox')
            return False
    if debug:
        print('DEBUG: sending c2s post to followers')
    # remove inactive threads
    inactiveFollowerThreads = []
    for th in followers_threads:
        if not th.is_alive():
            inactiveFollowerThreads.append(th)
    for th in inactiveFollowerThreads:
        followers_threads.remove(th)
    if debug:
        print('DEBUG: ' + str(len(followers_threads)) +
              ' followers threads active')
    # retain up to 200 threads
    if len(followers_threads) > 200:
        # kill the thread if it is still alive
        if followers_threads[0].is_alive():
            followers_threads[0].kill()
        # remove it from the list
        followers_threads.pop(0)
    # create a thread to send the post to followers
    followersThread = \
        sendToFollowersThread(server.session,
                              base_dir,
                              postToNickname,
                              domain, onion_domain, i2p_domain,
                              port, http_prefix,
                              federation_list,
                              send_threads,
                              postLog,
                              cached_webfingers,
                              person_cache,
                              message_json, debug,
                              version,
                              shared_items_federated_domains,
                              sharedItemFederationTokens,
                              signing_priv_key_pem)
    followers_threads.append(followersThread)

    if debug:
        print('DEBUG: handle any unfollow requests')
    outboxUndoFollow(base_dir, message_json, debug)

    if debug:
        print('DEBUG: handle skills changes requests')
    outboxSkills(base_dir, postToNickname, message_json, debug)

    if debug:
        print('DEBUG: handle availability changes requests')
    outboxAvailability(base_dir, postToNickname, message_json, debug)

    if debug:
        print('DEBUG: handle any like requests')
    outboxLike(recent_posts_cache,
               base_dir, http_prefix,
               postToNickname, domain, port,
               message_json, debug)
    if debug:
        print('DEBUG: handle any undo like requests')
    outboxUndoLike(recent_posts_cache,
                   base_dir, http_prefix,
                   postToNickname, domain, port,
                   message_json, debug)

    if debug:
        print('DEBUG: handle any emoji reaction requests')
    outboxReaction(recent_posts_cache,
                   base_dir, http_prefix,
                   postToNickname, domain, port,
                   message_json, debug)
    if debug:
        print('DEBUG: handle any undo emoji reaction requests')
    outboxUndoReaction(recent_posts_cache,
                       base_dir, http_prefix,
                       postToNickname, domain, port,
                       message_json, debug)

    if debug:
        print('DEBUG: handle any undo announce requests')
    outboxUndoAnnounce(recent_posts_cache,
                       base_dir, http_prefix,
                       postToNickname, domain, port,
                       message_json, debug)

    if debug:
        print('DEBUG: handle any bookmark requests')
    outboxBookmark(recent_posts_cache,
                   base_dir, http_prefix,
                   postToNickname, domain, port,
                   message_json, debug)
    if debug:
        print('DEBUG: handle any undo bookmark requests')
    outboxUndoBookmark(recent_posts_cache,
                       base_dir, http_prefix,
                       postToNickname, domain, port,
                       message_json, debug)

    if debug:
        print('DEBUG: handle delete requests')
    outboxDelete(base_dir, http_prefix,
                 postToNickname, domain,
                 message_json, debug,
                 allow_deletion,
                 recent_posts_cache)

    if debug:
        print('DEBUG: handle block requests')
    outboxBlock(base_dir, http_prefix,
                postToNickname, domain,
                port,
                message_json, debug)

    if debug:
        print('DEBUG: handle undo block requests')
    outboxUndoBlock(base_dir, http_prefix,
                    postToNickname, domain,
                    port, message_json, debug)

    if debug:
        print('DEBUG: handle mute requests')
    outboxMute(base_dir, http_prefix,
               postToNickname, domain,
               port,
               message_json, debug,
               recent_posts_cache)

    if debug:
        print('DEBUG: handle undo mute requests')
    outboxUndoMute(base_dir, http_prefix,
                   postToNickname, domain,
                   port,
                   message_json, debug,
                   recent_posts_cache)

    if debug:
        print('DEBUG: handle share uploads')
    outboxShareUpload(base_dir, http_prefix, postToNickname, domain,
                      port, message_json, debug, city,
                      system_language, translate, low_bandwidth,
                      content_license_url)

    if debug:
        print('DEBUG: handle undo share uploads')
    outboxUndoShareUpload(base_dir, http_prefix,
                          postToNickname, domain,
                          port, message_json, debug)

    if debug:
        print('DEBUG: handle actor updates from c2s')
    _outboxPersonReceiveUpdate(recent_posts_cache,
                               base_dir, http_prefix,
                               postToNickname, domain, port,
                               message_json, debug)

    if debug:
        print('DEBUG: sending c2s post to named addresses')
        if message_json.get('to'):
            print('c2s sender: ' +
                  postToNickname + '@' + domain + ':' + str(port) +
                  ' recipient: ' + str(message_json['to']))
        else:
            print('c2s sender: ' +
                  postToNickname + '@' + domain + ':' + str(port))
    namedAddressesThread = \
        sendToNamedAddressesThread(server.session, base_dir,
                                   postToNickname,
                                   domain, onion_domain, i2p_domain, port,
                                   http_prefix,
                                   federation_list,
                                   send_threads,
                                   postLog,
                                   cached_webfingers,
                                   person_cache,
                                   message_json, debug,
                                   version,
                                   shared_items_federated_domains,
                                   sharedItemFederationTokens,
                                   signing_priv_key_pem)
    followers_threads.append(namedAddressesThread)
    return True
