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
from session import createSession
from auth import createPassword
from posts import isImageMedia
from posts import outboxMessageCreateWrap
from posts import savePostToBox
from posts import sendToFollowersThread
from posts import sendToNamedAddressesThread
from utils import hasObjectStringType
from utils import getBaseContentFromPost
from utils import hasObjectDict
from utils import getLocalNetworkAddresses
from utils import getFullDomain
from utils import removeIdEnding
from utils import getDomainFromActor
from utils import dangerousMarkup
from utils import isFeaturedWriter
from utils import loadJson
from utils import saveJson
from utils import acctDir
from utils import localActorUrl
from utils import hasActor
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
from follow import followerApprovalActive
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


def _outboxPersonReceiveUpdate(recentPostsCache: {},
                               base_dir: str, http_prefix: str,
                               nickname: str, domain: str, port: int,
                               messageJson: {}, debug: bool) -> None:
    """ Receive an actor update from c2s
    For example, setting the PGP key from the desktop client
    """
    # these attachments are updatable via c2s
    updatableAttachments = ('PGP', 'OpenPGP', 'Email')

    if not messageJson.get('type'):
        return
    if not isinstance(messageJson['type'], str):
        if debug:
            print('DEBUG: c2s actor update type is not a string')
        return
    if messageJson['type'] != 'Update':
        return
    if not hasObjectStringType(messageJson, debug):
        return
    if not isinstance(messageJson['object']['type'], str):
        if debug:
            print('DEBUG: c2s actor update object type is not a string')
        return
    if messageJson['object']['type'] != 'Person':
        if debug:
            print('DEBUG: not a c2s actor update')
        return
    if not messageJson.get('to'):
        if debug:
            print('DEBUG: c2s actor update has no "to" field')
        return
    if not hasActor(messageJson, debug):
        return
    if not messageJson.get('id'):
        if debug:
            print('DEBUG: c2s actor update has no id field')
        return
    if not isinstance(messageJson['id'], str):
        if debug:
            print('DEBUG: c2s actor update id is not a string')
        return
    domainFull = getFullDomain(domain, port)
    actor = localActorUrl(http_prefix, nickname, domainFull)
    if len(messageJson['to']) != 1:
        if debug:
            print('DEBUG: c2s actor update - to does not contain one actor ' +
                  str(messageJson['to']))
        return
    if messageJson['to'][0] != actor:
        if debug:
            print('DEBUG: c2s actor update - to does not contain actor ' +
                  str(messageJson['to']) + ' ' + actor)
        return
    if not messageJson['id'].startswith(actor + '#updates/'):
        if debug:
            print('DEBUG: c2s actor update - unexpected id ' +
                  messageJson['id'])
        return
    updatedActorJson = messageJson['object']
    # load actor from file
    actorFilename = acctDir(base_dir, nickname, domain) + '.json'
    if not os.path.isfile(actorFilename):
        print('actorFilename not found: ' + actorFilename)
        return
    actorJson = loadJson(actorFilename)
    if not actorJson:
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
            if 'attachment' not in actorJson:
                continue
            found = False
            for attachIdx in range(len(actorJson['attachment'])):
                if actorJson['attachment'][attachIdx]['type'] != \
                   'PropertyValue':
                    continue
                if actorJson['attachment'][attachIdx]['name'] != \
                   newPropertyValue['name']:
                    continue
                else:
                    if actorJson['attachment'][attachIdx]['value'] != \
                       newPropertyValue['value']:
                        actorJson['attachment'][attachIdx]['value'] = \
                            newPropertyValue['value']
                        actorChanged = True
                    found = True
                    break
            if not found:
                actorJson['attachment'].append({
                    "name": newPropertyValue['name'],
                    "type": "PropertyValue",
                    "value": newPropertyValue['value']
                })
                actorChanged = True
    # save actor to file
    if actorChanged:
        saveJson(actorJson, actorFilename)
        if debug:
            print('actor saved: ' + actorFilename)
    if debug:
        print('New attachment: ' + str(actorJson['attachment']))
    messageJson['object'] = actorJson
    if debug:
        print('DEBUG: actor update via c2s - ' + nickname + '@' + domain)


def postMessageToOutbox(session, translate: {},
                        messageJson: {}, postToNickname: str,
                        server, base_dir: str, http_prefix: str,
                        domain: str, domainFull: str,
                        onion_domain: str, i2p_domain: str, port: int,
                        recentPostsCache: {}, followers_threads: [],
                        federationList: [], send_threads: [],
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
                        peertubeInstances: str, theme: str,
                        max_like_count: int,
                        max_recent_posts: int, cw_lists: {},
                        lists_enabled: str,
                        content_license_url: str) -> bool:
    """post is received by the outbox
    Client to server message post
    https://www.w3.org/TR/activitypub/#client-to-server-outbox-delivery
    """
    if not messageJson.get('type'):
        if debug:
            print('DEBUG: POST to outbox has no "type" parameter')
        return False
    if not messageJson.get('object') and messageJson.get('content'):
        if messageJson['type'] != 'Create':
            # https://www.w3.org/TR/activitypub/#object-without-create
            if debug:
                print('DEBUG: POST to outbox - adding Create wrapper')
            messageJson = \
                outboxMessageCreateWrap(http_prefix,
                                        postToNickname,
                                        domain, port,
                                        messageJson)

    # check that the outgoing post doesn't contain any markup
    # which can be used to implement exploits
    if hasObjectDict(messageJson):
        contentStr = getBaseContentFromPost(messageJson, system_language)
        if contentStr:
            if dangerousMarkup(contentStr, allow_local_network_access):
                print('POST to outbox contains dangerous markup: ' +
                      str(messageJson))
                return False

    if messageJson['type'] == 'Create':
        if not (messageJson.get('id') and
                messageJson.get('type') and
                messageJson.get('actor') and
                messageJson.get('object') and
                messageJson.get('to')):
            if not messageJson.get('id'):
                if debug:
                    print('DEBUG: POST to outbox - ' +
                          'Create does not have the id parameter ' +
                          str(messageJson))
            elif not messageJson.get('id'):
                if debug:
                    print('DEBUG: POST to outbox - ' +
                          'Create does not have the type parameter ' +
                          str(messageJson))
            elif not messageJson.get('id'):
                if debug:
                    print('DEBUG: POST to outbox - ' +
                          'Create does not have the actor parameter ' +
                          str(messageJson))
            elif not messageJson.get('id'):
                if debug:
                    print('DEBUG: POST to outbox - ' +
                          'Create does not have the object parameter ' +
                          str(messageJson))
            else:
                if debug:
                    print('DEBUG: POST to outbox - ' +
                          'Create does not have the "to" parameter ' +
                          str(messageJson))
            return False

        # actor should be a string
        if not isinstance(messageJson['actor'], str):
            return False

        # actor should look like a url
        if '://' not in messageJson['actor'] or \
           '.' not in messageJson['actor']:
            return False

        # sent by an actor on a local network address?
        if not allow_local_network_access:
            localNetworkPatternList = getLocalNetworkAddresses()
            for localNetworkPattern in localNetworkPatternList:
                if localNetworkPattern in messageJson['actor']:
                    return False

        testDomain, testPort = getDomainFromActor(messageJson['actor'])
        testDomain = getFullDomain(testDomain, testPort)
        if isBlockedDomain(base_dir, testDomain):
            if debug:
                print('DEBUG: domain is blocked: ' + messageJson['actor'])
            return False
        # replace youtube, so that google gets less tracking data
        replaceYouTube(messageJson, yt_replace_domain, system_language)
        # replace twitter, so that twitter posts can be shown without
        # having a twitter account
        replaceTwitter(messageJson, twitter_replacement_domain,
                       system_language)
        # https://www.w3.org/TR/activitypub/#create-activity-outbox
        messageJson['object']['attributedTo'] = messageJson['actor']
        if messageJson['object'].get('attachment'):
            attachmentIndex = 0
            attach = messageJson['object']['attachment'][attachmentIndex]
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
                    del messageJson['object']['attachment']
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
                        http_prefix + '://' + domainFull + '/' + mediaPath
                    attach['url'] = \
                        attach['url'].replace('/media/',
                                              '/system/' +
                                              'media_attachments/files/')

    permittedOutboxTypes = (
        'Create', 'Announce', 'Like', 'EmojiReact', 'Follow', 'Undo',
        'Update', 'Add', 'Remove', 'Block', 'Delete', 'Skill', 'Ignore'
    )
    if messageJson['type'] not in permittedOutboxTypes:
        if debug:
            print('DEBUG: POST to outbox - ' + messageJson['type'] +
                  ' is not a permitted activity type')
        return False
    if messageJson.get('id'):
        postId = removeIdEnding(messageJson['id'])
        if debug:
            print('DEBUG: id attribute exists within POST to outbox')
    else:
        if debug:
            print('DEBUG: No id attribute within POST to outbox')
        postId = None
    if debug:
        print('DEBUG: savePostToBox')
    if messageJson['type'] != 'Upgrade':
        outboxName = 'outbox'

        # if this is a blog post or an event then save to its own box
        if messageJson['type'] == 'Create':
            if hasObjectDict(messageJson):
                if messageJson['object'].get('type'):
                    if messageJson['object']['type'] == 'Article':
                        outboxName = 'tlblogs'

        savedFilename = \
            savePostToBox(base_dir,
                          http_prefix,
                          postId,
                          postToNickname, domainFull,
                          messageJson, outboxName)
        if not savedFilename:
            print('WARN: post not saved to outbox ' + outboxName)
            return False

        # save all instance blogs to the news actor
        if postToNickname != 'news' and outboxName == 'tlblogs':
            if '/' in savedFilename:
                if isFeaturedWriter(base_dir, postToNickname, domain):
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
        if messageJson['type'] in indexedActivities:
            indexes = [outboxName, "inbox"]
            selfActor = \
                localActorUrl(http_prefix, postToNickname, domainFull)
            for boxNameIndex in indexes:
                if not boxNameIndex:
                    continue

                # should this also go to the media timeline?
                if boxNameIndex == 'inbox':
                    if isImageMedia(session, base_dir, http_prefix,
                                    postToNickname, domain,
                                    messageJson,
                                    translate,
                                    yt_replace_domain,
                                    twitter_replacement_domain,
                                    allow_local_network_access,
                                    recentPostsCache, debug, system_language,
                                    domainFull, person_cache,
                                    signing_priv_key_pem):
                        inboxUpdateIndex('tlmedia', base_dir,
                                         postToNickname + '@' + domain,
                                         savedFilename, debug)

                if boxNameIndex == 'inbox' and outboxName == 'tlblogs':
                    continue

                # avoid duplicates of the message if already going
                # back to the inbox of the same account
                if selfActor not in messageJson['to']:
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
                        followerApprovalActive(base_dir,
                                               postToNickname, domain)
                    individualPostAsHtml(signing_priv_key_pem,
                                         False, recentPostsCache,
                                         max_recent_posts,
                                         translate, pageNumber,
                                         base_dir, session,
                                         cached_webfingers,
                                         person_cache,
                                         postToNickname, domain, port,
                                         messageJson, None, True,
                                         allow_deletion,
                                         http_prefix, __version__,
                                         boxNameIndex,
                                         yt_replace_domain,
                                         twitter_replacement_domain,
                                         show_published_date_only,
                                         peertubeInstances,
                                         allow_local_network_access,
                                         theme, system_language,
                                         max_like_count,
                                         boxNameIndex != 'dm',
                                         showIndividualPostIcons,
                                         manuallyApproveFollowers,
                                         False, True, useCacheOnly,
                                         cw_lists, lists_enabled)

    if outboxAnnounce(recentPostsCache,
                      base_dir, messageJson, debug):
        if debug:
            print('DEBUG: Updated announcements (shares) collection ' +
                  'for the post associated with the Announce activity')
    if not server.session:
        print('DEBUG: creating new session for c2s')
        server.session = createSession(proxy_type)
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
                              federationList,
                              send_threads,
                              postLog,
                              cached_webfingers,
                              person_cache,
                              messageJson, debug,
                              version,
                              shared_items_federated_domains,
                              sharedItemFederationTokens,
                              signing_priv_key_pem)
    followers_threads.append(followersThread)

    if debug:
        print('DEBUG: handle any unfollow requests')
    outboxUndoFollow(base_dir, messageJson, debug)

    if debug:
        print('DEBUG: handle skills changes requests')
    outboxSkills(base_dir, postToNickname, messageJson, debug)

    if debug:
        print('DEBUG: handle availability changes requests')
    outboxAvailability(base_dir, postToNickname, messageJson, debug)

    if debug:
        print('DEBUG: handle any like requests')
    outboxLike(recentPostsCache,
               base_dir, http_prefix,
               postToNickname, domain, port,
               messageJson, debug)
    if debug:
        print('DEBUG: handle any undo like requests')
    outboxUndoLike(recentPostsCache,
                   base_dir, http_prefix,
                   postToNickname, domain, port,
                   messageJson, debug)

    if debug:
        print('DEBUG: handle any emoji reaction requests')
    outboxReaction(recentPostsCache,
                   base_dir, http_prefix,
                   postToNickname, domain, port,
                   messageJson, debug)
    if debug:
        print('DEBUG: handle any undo emoji reaction requests')
    outboxUndoReaction(recentPostsCache,
                       base_dir, http_prefix,
                       postToNickname, domain, port,
                       messageJson, debug)

    if debug:
        print('DEBUG: handle any undo announce requests')
    outboxUndoAnnounce(recentPostsCache,
                       base_dir, http_prefix,
                       postToNickname, domain, port,
                       messageJson, debug)

    if debug:
        print('DEBUG: handle any bookmark requests')
    outboxBookmark(recentPostsCache,
                   base_dir, http_prefix,
                   postToNickname, domain, port,
                   messageJson, debug)
    if debug:
        print('DEBUG: handle any undo bookmark requests')
    outboxUndoBookmark(recentPostsCache,
                       base_dir, http_prefix,
                       postToNickname, domain, port,
                       messageJson, debug)

    if debug:
        print('DEBUG: handle delete requests')
    outboxDelete(base_dir, http_prefix,
                 postToNickname, domain,
                 messageJson, debug,
                 allow_deletion,
                 recentPostsCache)

    if debug:
        print('DEBUG: handle block requests')
    outboxBlock(base_dir, http_prefix,
                postToNickname, domain,
                port,
                messageJson, debug)

    if debug:
        print('DEBUG: handle undo block requests')
    outboxUndoBlock(base_dir, http_prefix,
                    postToNickname, domain,
                    port, messageJson, debug)

    if debug:
        print('DEBUG: handle mute requests')
    outboxMute(base_dir, http_prefix,
               postToNickname, domain,
               port,
               messageJson, debug,
               recentPostsCache)

    if debug:
        print('DEBUG: handle undo mute requests')
    outboxUndoMute(base_dir, http_prefix,
                   postToNickname, domain,
                   port,
                   messageJson, debug,
                   recentPostsCache)

    if debug:
        print('DEBUG: handle share uploads')
    outboxShareUpload(base_dir, http_prefix, postToNickname, domain,
                      port, messageJson, debug, city,
                      system_language, translate, low_bandwidth,
                      content_license_url)

    if debug:
        print('DEBUG: handle undo share uploads')
    outboxUndoShareUpload(base_dir, http_prefix,
                          postToNickname, domain,
                          port, messageJson, debug)

    if debug:
        print('DEBUG: handle actor updates from c2s')
    _outboxPersonReceiveUpdate(recentPostsCache,
                               base_dir, http_prefix,
                               postToNickname, domain, port,
                               messageJson, debug)

    if debug:
        print('DEBUG: sending c2s post to named addresses')
        if messageJson.get('to'):
            print('c2s sender: ' +
                  postToNickname + '@' + domain + ':' + str(port) +
                  ' recipient: ' + str(messageJson['to']))
        else:
            print('c2s sender: ' +
                  postToNickname + '@' + domain + ':' + str(port))
    namedAddressesThread = \
        sendToNamedAddressesThread(server.session, base_dir,
                                   postToNickname,
                                   domain, onion_domain, i2p_domain, port,
                                   http_prefix,
                                   federationList,
                                   send_threads,
                                   postLog,
                                   cached_webfingers,
                                   person_cache,
                                   messageJson, debug,
                                   version,
                                   shared_items_federated_domains,
                                   sharedItemFederationTokens,
                                   signing_priv_key_pem)
    followers_threads.append(namedAddressesThread)
    return True
