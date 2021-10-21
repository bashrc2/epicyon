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
from bookmarks import outboxBookmark
from bookmarks import outboxUndoBookmark
from delete import outboxDelete
from shares import outboxShareUpload
from shares import outboxUndoShareUpload
from webapp_post import individualPostAsHtml


def _outboxPersonReceiveUpdate(recentPostsCache: {},
                               baseDir: str, httpPrefix: str,
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
    actor = localActorUrl(httpPrefix, nickname, domainFull)
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
    actorFilename = acctDir(baseDir, nickname, domain) + '.json'
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
                        server, baseDir: str, httpPrefix: str,
                        domain: str, domainFull: str,
                        onionDomain: str, i2pDomain: str, port: int,
                        recentPostsCache: {}, followersThreads: [],
                        federationList: [], sendThreads: [],
                        postLog: [], cachedWebfingers: {},
                        personCache: {}, allowDeletion: bool,
                        proxyType: str, version: str, debug: bool,
                        YTReplacementDomain: str,
                        twitterReplacementDomain: str,
                        showPublishedDateOnly: bool,
                        allowLocalNetworkAccess: bool,
                        city: str, systemLanguage: str,
                        sharedItemsFederatedDomains: [],
                        sharedItemFederationTokens: {},
                        lowBandwidth: bool,
                        signingPrivateKeyPem: str,
                        peertubeInstances: str, theme: str,
                        maxLikeCount: int,
                        maxRecentPosts: int, CWlists: {},
                        listsEnabled: str) -> bool:
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
                outboxMessageCreateWrap(httpPrefix,
                                        postToNickname,
                                        domain, port,
                                        messageJson)

    # check that the outgoing post doesn't contain any markup
    # which can be used to implement exploits
    if hasObjectDict(messageJson):
        contentStr = getBaseContentFromPost(messageJson, systemLanguage)
        if contentStr:
            if dangerousMarkup(contentStr, allowLocalNetworkAccess):
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
        if not allowLocalNetworkAccess:
            localNetworkPatternList = getLocalNetworkAddresses()
            for localNetworkPattern in localNetworkPatternList:
                if localNetworkPattern in messageJson['actor']:
                    return False

        testDomain, testPort = getDomainFromActor(messageJson['actor'])
        testDomain = getFullDomain(testDomain, testPort)
        if isBlockedDomain(baseDir, testDomain):
            if debug:
                print('DEBUG: domain is blocked: ' + messageJson['actor'])
            return False
        # replace youtube, so that google gets less tracking data
        replaceYouTube(messageJson, YTReplacementDomain, systemLanguage)
        # replace twitter, so that twitter posts can be shown without
        # having a twitter account
        replaceTwitter(messageJson, twitterReplacementDomain, systemLanguage)
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
                    baseDir + '/accounts/' + \
                    postToNickname + '@' + domain
                uploadMediaFilename = mediaDir + '/upload.' + fileExtension
                if not os.path.isfile(uploadMediaFilename):
                    del messageJson['object']['attachment']
                else:
                    # generate a path for the uploaded image
                    mPath = getMediaPath()
                    mediaPath = mPath + '/' + \
                        createPassword(16).lower() + '.' + fileExtension
                    createMediaDirs(baseDir, mPath)
                    mediaFilename = baseDir + '/' + mediaPath
                    # move the uploaded image to its new path
                    os.rename(uploadMediaFilename, mediaFilename)
                    # change the url of the attachment
                    attach['url'] = \
                        httpPrefix + '://' + domainFull + '/' + mediaPath
                    attach['url'] = \
                        attach['url'].replace('/media/',
                                              '/system/' +
                                              'media_attachments/files/')

    permittedOutboxTypes = ('Create', 'Announce', 'Like', 'Follow', 'Undo',
                            'Update', 'Add', 'Remove', 'Block', 'Delete',
                            'Skill', 'Ignore')
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
            savePostToBox(baseDir,
                          httpPrefix,
                          postId,
                          postToNickname, domainFull,
                          messageJson, outboxName)
        if not savedFilename:
            print('WARN: post not saved to outbox ' + outboxName)
            return False

        # save all instance blogs to the news actor
        if postToNickname != 'news' and outboxName == 'tlblogs':
            if '/' in savedFilename:
                if isFeaturedWriter(baseDir, postToNickname, domain):
                    savedPostId = savedFilename.split('/')[-1]
                    blogsDir = \
                        baseDir + '/accounts/news@' + domain + '/tlblogs'
                    if not os.path.isdir(blogsDir):
                        os.mkdir(blogsDir)
                    copyfile(savedFilename, blogsDir + '/' + savedPostId)
                    inboxUpdateIndex('tlblogs', baseDir,
                                     'news@' + domain,
                                     savedFilename, debug)

                # clear the citations file if it exists
                citationsFilename = \
                    baseDir + '/accounts/' + \
                    postToNickname + '@' + domain + '/.citations.txt'
                if os.path.isfile(citationsFilename):
                    try:
                        os.remove(citationsFilename)
                    except BaseException:
                        pass

        # The following activity types get added to the index files
        indexedActivities = (
            'Create', 'Question', 'Note', 'EncryptedMessage', 'Article',
            'Patch', 'Announce'
        )
        if messageJson['type'] in indexedActivities:
            indexes = [outboxName, "inbox"]
            selfActor = \
                localActorUrl(httpPrefix, postToNickname, domainFull)
            for boxNameIndex in indexes:
                if not boxNameIndex:
                    continue

                # should this also go to the media timeline?
                if boxNameIndex == 'inbox':
                    if isImageMedia(session, baseDir, httpPrefix,
                                    postToNickname, domain,
                                    messageJson,
                                    translate,
                                    YTReplacementDomain,
                                    twitterReplacementDomain,
                                    allowLocalNetworkAccess,
                                    recentPostsCache, debug, systemLanguage,
                                    domainFull, personCache,
                                    signingPrivateKeyPem):
                        inboxUpdateIndex('tlmedia', baseDir,
                                         postToNickname + '@' + domain,
                                         savedFilename, debug)

                if boxNameIndex == 'inbox' and outboxName == 'tlblogs':
                    continue

                # avoid duplicates of the message if already going
                # back to the inbox of the same account
                if selfActor not in messageJson['to']:
                    # show sent post within the inbox,
                    # as is the typical convention
                    inboxUpdateIndex(boxNameIndex, baseDir,
                                     postToNickname + '@' + domain,
                                     savedFilename, debug)

                    # regenerate the html
                    useCacheOnly = False
                    pageNumber = 1
                    showIndividualPostIcons = True
                    manuallyApproveFollowers = \
                        followerApprovalActive(baseDir, postToNickname, domain)
                    individualPostAsHtml(signingPrivateKeyPem,
                                         False, recentPostsCache,
                                         maxRecentPosts,
                                         translate, pageNumber,
                                         baseDir, session,
                                         cachedWebfingers,
                                         personCache,
                                         postToNickname, domain, port,
                                         messageJson, None, True,
                                         allowDeletion,
                                         httpPrefix, __version__,
                                         boxNameIndex,
                                         YTReplacementDomain,
                                         twitterReplacementDomain,
                                         showPublishedDateOnly,
                                         peertubeInstances,
                                         allowLocalNetworkAccess,
                                         theme, systemLanguage,
                                         maxLikeCount,
                                         boxNameIndex != 'dm',
                                         showIndividualPostIcons,
                                         manuallyApproveFollowers,
                                         False, True, useCacheOnly,
                                         CWlists, listsEnabled)

    if outboxAnnounce(recentPostsCache,
                      baseDir, messageJson, debug):
        if debug:
            print('DEBUG: Updated announcements (shares) collection ' +
                  'for the post associated with the Announce activity')
    if not server.session:
        print('DEBUG: creating new session for c2s')
        server.session = createSession(proxyType)
        if not server.session:
            print('ERROR: Failed to create session for postMessageToOutbox')
            return False
    if debug:
        print('DEBUG: sending c2s post to followers')
    # remove inactive threads
    inactiveFollowerThreads = []
    for th in followersThreads:
        if not th.is_alive():
            inactiveFollowerThreads.append(th)
    for th in inactiveFollowerThreads:
        followersThreads.remove(th)
    if debug:
        print('DEBUG: ' + str(len(followersThreads)) +
              ' followers threads active')
    # retain up to 200 threads
    if len(followersThreads) > 200:
        # kill the thread if it is still alive
        if followersThreads[0].is_alive():
            followersThreads[0].kill()
        # remove it from the list
        followersThreads.pop(0)
    # create a thread to send the post to followers
    followersThread = \
        sendToFollowersThread(server.session,
                              baseDir,
                              postToNickname,
                              domain, onionDomain, i2pDomain,
                              port, httpPrefix,
                              federationList,
                              sendThreads,
                              postLog,
                              cachedWebfingers,
                              personCache,
                              messageJson, debug,
                              version,
                              sharedItemsFederatedDomains,
                              sharedItemFederationTokens,
                              signingPrivateKeyPem)
    followersThreads.append(followersThread)

    if debug:
        print('DEBUG: handle any unfollow requests')
    outboxUndoFollow(baseDir, messageJson, debug)

    if debug:
        print('DEBUG: handle skills changes requests')
    outboxSkills(baseDir, postToNickname, messageJson, debug)

    if debug:
        print('DEBUG: handle availability changes requests')
    outboxAvailability(baseDir, postToNickname, messageJson, debug)

    if debug:
        print('DEBUG: handle any like requests')
    outboxLike(recentPostsCache,
               baseDir, httpPrefix,
               postToNickname, domain, port,
               messageJson, debug)
    if debug:
        print('DEBUG: handle any undo like requests')
    outboxUndoLike(recentPostsCache,
                   baseDir, httpPrefix,
                   postToNickname, domain, port,
                   messageJson, debug)
    if debug:
        print('DEBUG: handle any undo announce requests')
    outboxUndoAnnounce(recentPostsCache,
                       baseDir, httpPrefix,
                       postToNickname, domain, port,
                       messageJson, debug)

    if debug:
        print('DEBUG: handle any bookmark requests')
    outboxBookmark(recentPostsCache,
                   baseDir, httpPrefix,
                   postToNickname, domain, port,
                   messageJson, debug)
    if debug:
        print('DEBUG: handle any undo bookmark requests')
    outboxUndoBookmark(recentPostsCache,
                       baseDir, httpPrefix,
                       postToNickname, domain, port,
                       messageJson, debug)

    if debug:
        print('DEBUG: handle delete requests')
    outboxDelete(baseDir, httpPrefix,
                 postToNickname, domain,
                 messageJson, debug,
                 allowDeletion,
                 recentPostsCache)

    if debug:
        print('DEBUG: handle block requests')
    outboxBlock(baseDir, httpPrefix,
                postToNickname, domain,
                port,
                messageJson, debug)

    if debug:
        print('DEBUG: handle undo block requests')
    outboxUndoBlock(baseDir, httpPrefix,
                    postToNickname, domain,
                    port, messageJson, debug)

    if debug:
        print('DEBUG: handle mute requests')
    outboxMute(baseDir, httpPrefix,
               postToNickname, domain,
               port,
               messageJson, debug,
               recentPostsCache)

    if debug:
        print('DEBUG: handle undo mute requests')
    outboxUndoMute(baseDir, httpPrefix,
                   postToNickname, domain,
                   port,
                   messageJson, debug,
                   recentPostsCache)

    if debug:
        print('DEBUG: handle share uploads')
    outboxShareUpload(baseDir, httpPrefix, postToNickname, domain,
                      port, messageJson, debug, city,
                      systemLanguage, translate, lowBandwidth)

    if debug:
        print('DEBUG: handle undo share uploads')
    outboxUndoShareUpload(baseDir, httpPrefix,
                          postToNickname, domain,
                          port, messageJson, debug)

    if debug:
        print('DEBUG: handle actor updates from c2s')
    _outboxPersonReceiveUpdate(recentPostsCache,
                               baseDir, httpPrefix,
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
        sendToNamedAddressesThread(server.session, baseDir,
                                   postToNickname,
                                   domain, onionDomain, i2pDomain, port,
                                   httpPrefix,
                                   federationList,
                                   sendThreads,
                                   postLog,
                                   cachedWebfingers,
                                   personCache,
                                   messageJson, debug,
                                   version,
                                   sharedItemsFederatedDomains,
                                   sharedItemFederationTokens,
                                   signingPrivateKeyPem)
    followersThreads.append(namedAddressesThread)
    return True
