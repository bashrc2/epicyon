__filename__ = "daemon.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Core"

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer, HTTPServer
import sys
import json
import time
import urllib.parse
import datetime
from socket import error as SocketError
import errno
from functools import partial
import pyqrcode
# for saving images
from hashlib import sha256
from hashlib import md5
from shutil import copyfile
from session import createSession
from webfinger import webfingerMeta
from webfinger import webfingerNodeInfo
from webfinger import webfingerLookup
from webfinger import webfingerUpdate
from mastoapiv1 import mastoApiV1Response
from metadata import metaDataNodeInfo
from metadata import metadataCustomEmoji
from enigma import getEnigmaPubKey
from enigma import setEnigmaPubKey
from pgp import getEmailAddress
from pgp import setEmailAddress
from pgp import getPGPpubKey
from pgp import getPGPfingerprint
from pgp import setPGPpubKey
from pgp import setPGPfingerprint
from xmpp import getXmppAddress
from xmpp import setXmppAddress
from ssb import getSSBAddress
from ssb import setSSBAddress
from tox import getToxAddress
from tox import setToxAddress
from briar import getBriarAddress
from briar import setBriarAddress
from jami import getJamiAddress
from jami import setJamiAddress
from cwtch import getCwtchAddress
from cwtch import setCwtchAddress
from matrix import getMatrixAddress
from matrix import setMatrixAddress
from donate import getDonationUrl
from donate import setDonationUrl
from donate import getWebsite
from donate import setWebsite
from person import addActorUpdateTimestamp
from person import setPersonNotes
from person import getDefaultPersonContext
from person import getActorUpdateJson
from person import savePersonQrcode
from person import randomizeActorImages
from person import personUpgradeActor
from person import activateAccount
from person import deactivateAccount
from person import registerAccount
from person import personLookup
from person import personBoxJson
from person import createSharedInbox
from person import createNewsInbox
from person import suspendAccount
from person import reenableAccount
from person import removeAccount
from person import canRemovePost
from person import personSnooze
from person import personUnsnooze
from posts import getOriginalPostFromAnnounceUrl
from posts import savePostToBox
from posts import getInstanceActorKey
from posts import removePostInteractions
from posts import outboxMessageCreateWrap
from posts import getPinnedPostAsJson
from posts import pinPost
from posts import jsonPinPost
from posts import undoPinnedPost
from posts import isModerator
from posts import createQuestionPost
from posts import createPublicPost
from posts import createBlogPost
from posts import createReportPost
from posts import createUnlistedPost
from posts import createFollowersOnlyPost
from posts import createDirectMessagePost
from posts import populateRepliesJson
from posts import addToField
from posts import expireCache
from inbox import clearQueueItems
from inbox import inboxPermittedMessage
from inbox import inboxMessageHasParams
from inbox import runInboxQueue
from inbox import runInboxQueueWatchdog
from inbox import savePostToInboxQueue
from inbox import populateReplies
from follow import followerApprovalActive
from follow import isFollowingActor
from follow import getFollowingFeed
from follow import sendFollowRequest
from follow import unfollowAccount
from follow import createInitialLastSeen
from skills import getSkillsFromList
from skills import noOfActorSkills
from skills import actorHasSkill
from skills import actorSkillValue
from skills import setActorSkillLevel
from auth import recordLoginFailure
from auth import authorize
from auth import createPassword
from auth import createBasicAuthHeader
from auth import authorizeBasic
from auth import storeBasicCredentials
from threads import threadWithTrace
from threads import removeDormantThreads
from media import processMetaData
from media import convertImageToLowBandwidth
from media import replaceYouTube
from media import replaceTwitter
from media import attachMedia
from media import pathIsVideo
from media import pathIsAudio
from blocking import getCWlistVariable
from blocking import loadCWLists
from blocking import updateBlockedCache
from blocking import mutePost
from blocking import unmutePost
from blocking import setBrochMode
from blocking import broch_modeIsActive
from blocking import addBlock
from blocking import removeBlock
from blocking import addGlobalBlock
from blocking import removeGlobalBlock
from blocking import isBlockedHashtag
from blocking import isBlockedDomain
from blocking import getDomainBlocklist
from roles import getActorRolesList
from roles import setRole
from roles import clearModeratorStatus
from roles import clearEditorStatus
from roles import clearCounselorStatus
from roles import clearArtistStatus
from blog import pathContainsBlogLink
from blog import htmlBlogPageRSS2
from blog import htmlBlogPageRSS3
from blog import htmlBlogView
from blog import htmlBlogPage
from blog import htmlBlogPost
from blog import htmlEditBlog
from blog import getBlogAddress
from webapp_themeDesigner import htmlThemeDesigner
from webapp_minimalbutton import setMinimal
from webapp_minimalbutton import isMinimal
from webapp_utils import getAvatarImageUrl
from webapp_utils import htmlHashtagBlocked
from webapp_utils import htmlFollowingList
from webapp_utils import setBlogAddress
from webapp_utils import htmlShowShare
from webapp_calendar import htmlCalendarDeleteConfirm
from webapp_calendar import htmlCalendar
from webapp_about import htmlAbout
from webapp_accesskeys import htmlAccessKeys
from webapp_accesskeys import loadAccessKeysForAccounts
from webapp_confirm import htmlConfirmDelete
from webapp_confirm import htmlConfirmRemoveSharedItem
from webapp_confirm import htmlConfirmUnblock
from webapp_person_options import htmlPersonOptions
from webapp_timeline import htmlShares
from webapp_timeline import htmlWanted
from webapp_timeline import htmlInbox
from webapp_timeline import htmlBookmarks
from webapp_timeline import htmlInboxDMs
from webapp_timeline import htmlInboxReplies
from webapp_timeline import htmlInboxMedia
from webapp_timeline import htmlInboxBlogs
from webapp_timeline import htmlInboxNews
from webapp_timeline import htmlInboxFeatures
from webapp_timeline import htmlOutbox
from webapp_media import loadPeertubeInstances
from webapp_moderation import htmlAccountInfo
from webapp_moderation import htmlModeration
from webapp_moderation import htmlModerationInfo
from webapp_create_post import htmlNewPost
from webapp_login import htmlLogin
from webapp_login import htmlGetLoginCredentials
from webapp_suspended import htmlSuspended
from webapp_tos import htmlTermsOfService
from webapp_confirm import htmlConfirmFollow
from webapp_confirm import htmlConfirmUnfollow
from webapp_post import htmlEmojiReactionPicker
from webapp_post import htmlPostReplies
from webapp_post import htmlIndividualPost
from webapp_post import individualPostAsHtml
from webapp_profile import htmlEditProfile
from webapp_profile import htmlProfileAfterSearch
from webapp_profile import htmlProfile
from webapp_column_left import htmlLinksMobile
from webapp_column_left import htmlEditLinks
from webapp_column_right import htmlNewswireMobile
from webapp_column_right import htmlEditNewswire
from webapp_column_right import htmlCitations
from webapp_column_right import htmlEditNewsPost
from webapp_search import htmlSkillsSearch
from webapp_search import htmlHistorySearch
from webapp_search import htmlHashtagSearch
from webapp_search import rssHashtagSearch
from webapp_search import htmlSearchEmoji
from webapp_search import htmlSearchSharedItems
from webapp_search import htmlSearchEmojiTextEntry
from webapp_search import htmlSearch
from webapp_hashtagswarm import getHashtagCategoriesFeed
from webapp_hashtagswarm import htmlSearchHashtagCategory
from webapp_welcome import welcomeScreenIsComplete
from webapp_welcome import htmlWelcomeScreen
from webapp_welcome import isWelcomeScreenComplete
from webapp_welcome_profile import htmlWelcomeProfile
from webapp_welcome_final import htmlWelcomeFinal
from shares import mergeSharedItemTokens
from shares import runFederatedSharesDaemon
from shares import runFederatedSharesWatchdog
from shares import updateSharedItemFederationToken
from shares import createSharedItemFederationToken
from shares import authorizeSharedItems
from shares import generateSharedItemFederationTokens
from shares import getSharesFeedForPerson
from shares import addShare
from shares import removeSharedItem
from shares import expireShares
from shares import sharesCatalogEndpoint
from shares import sharesCatalogAccountEndpoint
from shares import sharesCatalogCSVEndpoint
from categories import setHashtagCategory
from categories import updateHashtagCategories
from languages import getActorLanguages
from languages import setActorLanguages
from like import updateLikesCollection
from reaction import updateReactionCollection
from utils import undoReactionCollectionEntry
from utils import getNewPostEndpoints
from utils import hasActor
from utils import setReplyIntervalHours
from utils import canReplyTo
from utils import isDM
from utils import replaceUsersWithAt
from utils import localActorUrl
from utils import isfloat
from utils import validPassword
from utils import removeLineEndings
from utils import getBaseContentFromPost
from utils import acctDir
from utils import getImageExtensionFromMimeType
from utils import getImageMimeType
from utils import hasObjectDict
from utils import userAgentDomain
from utils import isLocalNetworkAddress
from utils import permittedDir
from utils import isAccountDir
from utils import getOccupationSkills
from utils import getOccupationName
from utils import setOccupationName
from utils import loadTranslationsFromFile
from utils import getLocalNetworkAddresses
from utils import decodedHost
from utils import isPublicPost
from utils import getLockedAccount
from utils import hasUsersPath
from utils import getFullDomain
from utils import removeHtml
from utils import isEditor
from utils import isArtist
from utils import getImageExtensions
from utils import mediaFileMimeType
from utils import getCSS
from utils import firstParagraphFromString
from utils import clearFromPostCaches
from utils import containsInvalidChars
from utils import isSystemAccount
from utils import setConfigParam
from utils import getConfigParam
from utils import removeIdEnding
from utils import undoLikesCollectionEntry
from utils import deletePost
from utils import isBlogPost
from utils import removeAvatarFromCache
from utils import locatePost
from utils import getCachedPostFilename
from utils import removePostFromCache
from utils import getNicknameFromActor
from utils import getDomainFromActor
from utils import getStatusNumber
from utils import urlPermitted
from utils import loadJson
from utils import saveJson
from utils import isSuspended
from utils import dangerousMarkup
from utils import refreshNewswire
from utils import isImageFile
from utils import hasGroupType
from manualapprove import manualDenyFollowRequestThread
from manualapprove import manualApproveFollowRequestThread
from announce import createAnnounce
from content import containsInvalidLocalLinks
from content import getPriceFromString
from content import replaceEmojiFromTags
from content import addHtmlTags
from content import extractMediaInFormPOST
from content import saveMediaInFormPOST
from content import extractTextFieldsInPOST
from cache import checkForChangedActor
from cache import storePersonInCache
from cache import getPersonFromCache
from cache import getPersonPubKey
from httpsig import verifyPostHeaders
from theme import resetThemeDesignerSettings
from theme import setThemeFromDesigner
from theme import scanThemesForScripts
from theme import importTheme
from theme import exportTheme
from theme import isNewsThemeName
from theme import getTextModeBanner
from theme import setNewsAvatar
from theme import setTheme
from theme import getTheme
from theme import enableGrayscale
from theme import disableGrayscale
from schedule import runPostSchedule
from schedule import runPostScheduleWatchdog
from schedule import removeScheduledPosts
from outbox import postMessageToOutbox
from happening import removeCalendarEvent
from bookmarks import bookmark
from bookmarks import undoBookmark
from petnames import setPetName
from followingCalendar import addPersonToCalendar
from followingCalendar import removePersonFromCalendar
from notifyOnPost import addNotifyOnPost
from notifyOnPost import removeNotifyOnPost
from devices import E2EEdevicesCollection
from devices import E2EEvalidDevice
from devices import E2EEaddDevice
from newswire import getRSSfromDict
from newswire import rss2Header
from newswire import rss2Footer
from newswire import loadHashtagCategories
from newsdaemon import runNewswireWatchdog
from newsdaemon import runNewswireDaemon
from filters import isFiltered
from filters import addGlobalFilter
from filters import removeGlobalFilter
from context import hasValidContext
from context import getIndividualPostContext
from speaker import getSSMLbox
from city import getSpoofedCity
from fitnessFunctions import fitnessPerformance
from fitnessFunctions import fitnessThread
from fitnessFunctions import sortedWatchPoints
from fitnessFunctions import htmlWatchPointsGraph
import os


# maximum number of posts to list in outbox feed
maxPostsInFeed = 12

# maximum number of posts in a hashtag feed
maxPostsInHashtagFeed = 6

# reduced posts for media feed because it can take a while
maxPostsInMediaFeed = 6

# Blogs can be longer, so don't show many per page
maxPostsInBlogsFeed = 4

maxPostsInNewsFeed = 10

# Maximum number of entries in returned rss.xml
maxPostsInRSSFeed = 10

# number of follows/followers per page
followsPerPage = 6

# number of item shares per page
sharesPerPage = 12


def saveDomainQrcode(base_dir: str, http_prefix: str,
                     domainFull: str, scale=6) -> None:
    """Saves a qrcode image for the domain name
    This helps to transfer onion or i2p domains to a mobile device
    """
    qrcodeFilename = base_dir + '/accounts/qrcode.png'
    url = pyqrcode.create(http_prefix + '://' + domainFull)
    url.png(qrcodeFilename, scale)


class PubServer(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def _updateKnownCrawlers(self, uaStr: str) -> None:
        """Updates a dictionary of known crawlers accessing nodeinfo
        or the masto API
        """
        if not uaStr:
            return

        currTime = int(time.time())
        if self.server.knownCrawlers.get(uaStr):
            self.server.knownCrawlers[uaStr]['hits'] += 1
            self.server.knownCrawlers[uaStr]['lastseen'] = currTime
        else:
            self.server.knownCrawlers[uaStr] = {
                "lastseen": currTime,
                "hits": 1
            }

        if currTime - self.server.lastKnownCrawler >= 30:
            # remove any old observations
            removeCrawlers = []
            for ua, item in self.server.knownCrawlers.items():
                if currTime - item['lastseen'] >= 60 * 60 * 24 * 30:
                    removeCrawlers.append(ua)
            for ua in removeCrawlers:
                del self.server.knownCrawlers[ua]
            # save the list of crawlers
            saveJson(self.server.knownCrawlers,
                     self.server.base_dir + '/accounts/knownCrawlers.json')
        self.server.lastKnownCrawler = currTime

    def _getInstanceUrl(self, callingDomain: str) -> str:
        """Returns the URL for this instance
        """
        if callingDomain.endswith('.onion') and \
           self.server.onion_domain:
            instanceUrl = 'http://' + self.server.onion_domain
        elif (callingDomain.endswith('.i2p') and
              self.server.i2p_domain):
            instanceUrl = 'http://' + self.server.i2p_domain
        else:
            instanceUrl = \
                self.server.http_prefix + '://' + self.server.domainFull
        return instanceUrl

    def _getheaderSignatureInput(self):
        """There are different versions of http signatures with
        different header styles
        """
        if self.headers.get('Signature-Input'):
            # https://tools.ietf.org/html/
            # draft-ietf-httpbis-message-signatures-01
            return self.headers['Signature-Input']
        elif self.headers.get('signature-input'):
            return self.headers['signature-input']
        elif self.headers.get('signature'):
            # Ye olde Masto http sig
            return self.headers['signature']
        return None

    def handle_error(self, request, client_address):
        print('ERROR: http server error: ' + str(request) + ', ' +
              str(client_address))
        pass

    def _sendReplyToQuestion(self, nickname: str, messageId: str,
                             answer: str) -> None:
        """Sends a reply to a question
        """
        votesFilename = \
            acctDir(self.server.base_dir, nickname, self.server.domain) + \
            '/questions.txt'

        if os.path.isfile(votesFilename):
            # have we already voted on this?
            if messageId in open(votesFilename).read():
                print('Already voted on message ' + messageId)
                return

        print('Voting on message ' + messageId)
        print('Vote for: ' + answer)
        commentsEnabled = True
        attachImageFilename = None
        mediaType = None
        imageDescription = None
        inReplyTo = messageId
        inReplyToAtomUri = messageId
        subject = None
        schedulePost = False
        eventDate = None
        eventTime = None
        location = None
        conversationId = None
        city = getSpoofedCity(self.server.city,
                              self.server.base_dir,
                              nickname, self.server.domain)

        messageJson = \
            createPublicPost(self.server.base_dir,
                             nickname,
                             self.server.domain, self.server.port,
                             self.server.http_prefix,
                             answer, False, False, False,
                             commentsEnabled,
                             attachImageFilename, mediaType,
                             imageDescription, city,
                             inReplyTo,
                             inReplyToAtomUri,
                             subject,
                             schedulePost,
                             eventDate,
                             eventTime,
                             location, False,
                             self.server.systemLanguage,
                             conversationId,
                             self.server.low_bandwidth,
                             self.server.content_license_url)
        if messageJson:
            # name field contains the answer
            messageJson['object']['name'] = answer
            if self._postToOutbox(messageJson,
                                  self.server.project_version, nickname):
                postFilename = \
                    locatePost(self.server.base_dir, nickname,
                               self.server.domain, messageId)
                if postFilename:
                    postJsonObject = loadJson(postFilename)
                    if postJsonObject:
                        populateReplies(self.server.base_dir,
                                        self.server.http_prefix,
                                        self.server.domainFull,
                                        postJsonObject,
                                        self.server.max_replies,
                                        self.server.debug)
                        # record the vote
                        try:
                            with open(votesFilename, 'a+') as votesFile:
                                votesFile.write(messageId + '\n')
                        except OSError:
                            print('EX: unable to write vote ' +
                                  votesFilename)

                        # ensure that the cached post is removed if it exists,
                        # so that it then will be recreated
                        cachedPostFilename = \
                            getCachedPostFilename(self.server.base_dir,
                                                  nickname,
                                                  self.server.domain,
                                                  postJsonObject)
                        if cachedPostFilename:
                            if os.path.isfile(cachedPostFilename):
                                try:
                                    os.remove(cachedPostFilename)
                                except OSError:
                                    print('EX: _sendReplyToQuestion ' +
                                          'unable to delete ' +
                                          cachedPostFilename)
                        # remove from memory cache
                        removePostFromCache(postJsonObject,
                                            self.server.recentPostsCache)
            else:
                print('ERROR: unable to post vote to outbox')
        else:
            print('ERROR: unable to create vote')

    def _blockedUserAgent(self, callingDomain: str, agentStr: str) -> bool:
        """Should a GET or POST be blocked based upon its user agent?
        """
        if not agentStr:
            return False

        agentStrLower = agentStr.lower()
        defaultAgentBlocks = [
            'fedilist'
        ]
        for uaBlock in defaultAgentBlocks:
            if uaBlock in agentStrLower:
                print('Blocked User agent: ' + uaBlock)
                return True

        agentDomain = None

        if agentStr:
            # is this a web crawler? If so the block it
            if 'bot/' in agentStrLower or 'bot-' in agentStrLower:
                if self.server.news_instance:
                    return False
                print('Blocked Crawler: ' + agentStr)
                return True
            # get domain name from User-Agent
            agentDomain = userAgentDomain(agentStr, self.server.debug)
        else:
            # no User-Agent header is present
            return True

        # is the User-Agent type blocked? eg. "Mastodon"
        if self.server.user_agents_blocked:
            blockedUA = False
            for agentName in self.server.user_agents_blocked:
                if agentName in agentStr:
                    blockedUA = True
                    break
            if blockedUA:
                return True

        if not agentDomain:
            return False

        # is the User-Agent domain blocked
        blockedUA = False
        if not agentDomain.startswith(callingDomain):
            self.server.blockedCacheLastUpdated = \
                updateBlockedCache(self.server.base_dir,
                                   self.server.blockedCache,
                                   self.server.blockedCacheLastUpdated,
                                   self.server.blockedCacheUpdateSecs)

            blockedUA = isBlockedDomain(self.server.base_dir, agentDomain,
                                        self.server.blockedCache)
            # if self.server.debug:
            if blockedUA:
                print('Blocked User agent: ' + agentDomain)
        return blockedUA

    def _requestCSV(self) -> bool:
        """Should a csv response be given?
        """
        if not self.headers.get('Accept'):
            return False
        acceptStr = self.headers['Accept']
        if 'text/csv' in acceptStr:
            return True
        return False

    def _requestHTTP(self) -> bool:
        """Should a http response be given?
        """
        if not self.headers.get('Accept'):
            return False
        acceptStr = self.headers['Accept']
        if self.server.debug:
            print('ACCEPT: ' + acceptStr)
        if 'application/ssml' in acceptStr:
            if 'text/html' not in acceptStr:
                return False
        if 'image/' in acceptStr:
            if 'text/html' not in acceptStr:
                return False
        if 'video/' in acceptStr:
            if 'text/html' not in acceptStr:
                return False
        if 'audio/' in acceptStr:
            if 'text/html' not in acceptStr:
                return False
        if acceptStr.startswith('*'):
            if self.headers.get('User-Agent'):
                if 'ELinks' in self.headers['User-Agent'] or \
                   'Lynx' in self.headers['User-Agent']:
                    return True
            return False
        if 'json' in acceptStr:
            return False
        return True

    def _signedGETkeyId(self) -> str:
        """Returns the actor from the signed GET keyId
        """
        signature = None
        if self.headers.get('signature'):
            signature = self.headers['signature']
        elif self.headers.get('Signature'):
            signature = self.headers['Signature']

        # check that the headers are signed
        if not signature:
            if self.server.debug:
                print('AUTH: secure mode actor, ' +
                      'GET has no signature in headers')
            return None

        # get the keyId, which is typically the instance actor
        keyId = None
        signatureParams = signature.split(',')
        for signatureItem in signatureParams:
            if signatureItem.startswith('keyId='):
                if '"' in signatureItem:
                    keyId = signatureItem.split('"')[1]
                    # remove #main-key
                    if '#' in keyId:
                        keyId = keyId.split('#')[0]
                    return keyId
        return None

    def _establishSession(self, callingFunction: str) -> bool:
        """Recreates session if needed
        """
        if self.server.session:
            return True
        print('DEBUG: creating new session during ' + callingFunction)
        self.server.session = createSession(self.server.proxy_type)
        if self.server.session:
            return True
        print('ERROR: GET failed to create session during ' +
              callingFunction)
        return False

    def _secure_mode(self, force: bool = False) -> bool:
        """http authentication of GET requests for json
        """
        if not self.server.secure_mode and not force:
            return True

        keyId = self._signedGETkeyId()
        if not keyId:
            if self.server.debug:
                print('AUTH: secure mode, ' +
                      'failed to obtain keyId from signature')
            return False

        # is the keyId (actor) valid?
        if not urlPermitted(keyId, self.server.federationList):
            if self.server.debug:
                print('AUTH: Secure mode GET request not permitted: ' + keyId)
            return False

        if not self._establishSession("secure mode"):
            return False

        # obtain the public key
        pubKey = \
            getPersonPubKey(self.server.base_dir,
                            self.server.session, keyId,
                            self.server.personCache, self.server.debug,
                            self.server.project_version,
                            self.server.http_prefix,
                            self.server.domain, self.server.onion_domain,
                            self.server.signingPrivateKeyPem)
        if not pubKey:
            if self.server.debug:
                print('AUTH: secure mode failed to ' +
                      'obtain public key for ' + keyId)
            return False

        # verify the GET request without any digest
        if verifyPostHeaders(self.server.http_prefix,
                             self.server.domainFull,
                             pubKey, self.headers,
                             self.path, True, None, '', self.server.debug):
            return True

        if self.server.debug:
            print('AUTH: secure mode authorization failed for ' + keyId)
        return False

    def _login_headers(self, fileFormat: str, length: int,
                       callingDomain: str) -> None:
        self.send_response(200)
        self.send_header('Content-type', fileFormat)
        self.send_header('Content-Length', str(length))
        self.send_header('Host', callingDomain)
        self.send_header('WWW-Authenticate',
                         'title="Login to Epicyon", Basic realm="epicyon"')
        self.end_headers()

    def _logout_headers(self, fileFormat: str, length: int,
                        callingDomain: str) -> None:
        self.send_response(200)
        self.send_header('Content-type', fileFormat)
        self.send_header('Content-Length', str(length))
        self.send_header('Set-Cookie', 'epicyon=; SameSite=Strict')
        self.send_header('Host', callingDomain)
        self.send_header('WWW-Authenticate',
                         'title="Login to Epicyon", Basic realm="epicyon"')
        self.end_headers()

    def _quoted_redirect(self, redirect: str) -> str:
        """hashtag screen urls sometimes contain non-ascii characters which
        need to be url encoded
        """
        if '/tags/' not in redirect:
            return redirect
        lastStr = redirect.split('/')[-1]
        return redirect.replace('/' + lastStr, '/' +
                                urllib.parse.quote_plus(lastStr))

    def _logout_redirect(self, redirect: str, cookie: str,
                         callingDomain: str) -> None:
        if '://' not in redirect:
            print('REDIRECT ERROR: redirect is not an absolute url ' +
                  redirect)

        self.send_response(303)
        self.send_header('Set-Cookie', 'epicyon=; SameSite=Strict')
        self.send_header('Location', self._quoted_redirect(redirect))
        self.send_header('Host', callingDomain)
        self.send_header('X-AP-Instance-ID', self.server.instance_id)
        self.send_header('Content-Length', '0')
        self.end_headers()

    def _set_headers_base(self, fileFormat: str, length: int, cookie: str,
                          callingDomain: str, permissive: bool) -> None:
        self.send_response(200)
        self.send_header('Content-type', fileFormat)
        if 'image/' in fileFormat or \
           'audio/' in fileFormat or \
           'video/' in fileFormat:
            cache_control = 'public, max-age=84600, immutable'
            self.send_header('Cache-Control', cache_control)
        else:
            self.send_header('Cache-Control', 'public')
        self.send_header('Origin', self.server.domainFull)
        if length > -1:
            self.send_header('Content-Length', str(length))
        if callingDomain:
            self.send_header('Host', callingDomain)
        if permissive:
            self.send_header('Access-Control-Allow-Origin', '*')
            return
        self.send_header('X-AP-Instance-ID', self.server.instance_id)
        self.send_header('X-Clacks-Overhead', 'GNU Natalie Nguyen')
        if cookie:
            cookieStr = cookie
            if 'HttpOnly;' not in cookieStr:
                if self.server.http_prefix == 'https':
                    cookieStr += '; Secure'
                cookieStr += '; HttpOnly; SameSite=Strict'
            self.send_header('Cookie', cookieStr)

    def _set_headers(self, fileFormat: str, length: int, cookie: str,
                     callingDomain: str, permissive: bool) -> None:
        self._set_headers_base(fileFormat, length, cookie, callingDomain,
                               permissive)
        self.end_headers()

    def _set_headers_head(self, fileFormat: str, length: int, etag: str,
                          callingDomain: str, permissive: bool) -> None:
        self._set_headers_base(fileFormat, length, None, callingDomain,
                               permissive)
        if etag:
            self.send_header('ETag', '"' + etag + '"')
        self.end_headers()

    def _set_headers_etag(self, mediaFilename: str, fileFormat: str,
                          data, cookie: str, callingDomain: str,
                          permissive: bool, lastModified: str) -> None:
        datalen = len(data)
        self._set_headers_base(fileFormat, datalen, cookie, callingDomain,
                               permissive)
        etag = None
        if os.path.isfile(mediaFilename + '.etag'):
            try:
                with open(mediaFilename + '.etag', 'r') as etagFile:
                    etag = etagFile.read()
            except OSError:
                print('EX: _set_headers_etag ' +
                      'unable to read ' + mediaFilename + '.etag')
        if not etag:
            etag = md5(data).hexdigest()  # nosec
            try:
                with open(mediaFilename + '.etag', 'w+') as etagFile:
                    etagFile.write(etag)
            except OSError:
                print('EX: _set_headers_etag ' +
                      'unable to write ' + mediaFilename + '.etag')
        # if etag:
        #     self.send_header('ETag', '"' + etag + '"')
        if lastModified:
            self.send_header('last-modified', lastModified)
        self.end_headers()

    def _etag_exists(self, mediaFilename: str) -> bool:
        """Does an etag header exist for the given file?
        """
        etagHeader = 'If-None-Match'
        if not self.headers.get(etagHeader):
            etagHeader = 'if-none-match'
            if not self.headers.get(etagHeader):
                etagHeader = 'If-none-match'

        if self.headers.get(etagHeader):
            oldEtag = self.headers[etagHeader].replace('"', '')
            if os.path.isfile(mediaFilename + '.etag'):
                # load the etag from file
                currEtag = ''
                try:
                    with open(mediaFilename + '.etag', 'r') as etagFile:
                        currEtag = etagFile.read()
                except OSError:
                    print('EX: _etag_exists unable to read ' +
                          str(mediaFilename))
                if currEtag and oldEtag == currEtag:
                    # The file has not changed
                    return True
        return False

    def _redirect_headers(self, redirect: str, cookie: str,
                          callingDomain: str) -> None:
        if '://' not in redirect:
            print('REDIRECT ERROR: redirect is not an absolute url ' +
                  redirect)

        self.send_response(303)

        if cookie:
            cookieStr = cookie.replace('SET:', '').strip()
            if 'HttpOnly;' not in cookieStr:
                if self.server.http_prefix == 'https':
                    cookieStr += '; Secure'
                cookieStr += '; HttpOnly; SameSite=Strict'
            if not cookie.startswith('SET:'):
                self.send_header('Cookie', cookieStr)
            else:
                self.send_header('Set-Cookie', cookieStr)
        self.send_header('Location', self._quoted_redirect(redirect))
        self.send_header('Host', callingDomain)
        self.send_header('X-AP-Instance-ID', self.server.instance_id)
        self.send_header('Content-Length', '0')
        self.end_headers()

    def _httpReturnCode(self, httpCode: int, httpDescription: str,
                        longDescription: str) -> None:
        msg = \
            '<html><head><title>' + str(httpCode) + '</title></head>' \
            '<body bgcolor="linen" text="black">' \
            '<div style="font-size: 400px; ' \
            'text-align: center;">' + str(httpCode) + '</div>' \
            '<div style="font-size: 128px; ' \
            'text-align: center; font-variant: ' \
            'small-caps;"><p role="alert">' + httpDescription + '</p></div>' \
            '<div style="text-align: center;">' + longDescription + '</div>' \
            '</body></html>'
        msg = msg.encode('utf-8')
        self.send_response(httpCode)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        msgLenStr = str(len(msg))
        self.send_header('Content-Length', msgLenStr)
        self.end_headers()
        if not self._write(msg):
            print('Error when showing ' + str(httpCode))

    def _200(self) -> None:
        if self.server.translate:
            self._httpReturnCode(200, self.server.translate['Ok'],
                                 self.server.translate['This is nothing ' +
                                                       'less than an utter ' +
                                                       'triumph'])
        else:
            self._httpReturnCode(200, 'Ok',
                                 'This is nothing less ' +
                                 'than an utter triumph')

    def _403(self) -> None:
        if self.server.translate:
            self._httpReturnCode(403, self.server.translate['Forbidden'],
                                 self.server.translate["You're not allowed"])
        else:
            self._httpReturnCode(403, 'Forbidden',
                                 "You're not allowed")

    def _404(self) -> None:
        if self.server.translate:
            self._httpReturnCode(404, self.server.translate['Not Found'],
                                 self.server.translate['These are not the ' +
                                                       'droids you are ' +
                                                       'looking for'])
        else:
            self._httpReturnCode(404, 'Not Found',
                                 'These are not the ' +
                                 'droids you are ' +
                                 'looking for')

    def _304(self) -> None:
        if self.server.translate:
            self._httpReturnCode(304, self.server.translate['Not changed'],
                                 self.server.translate['The contents of ' +
                                                       'your local cache ' +
                                                       'are up to date'])
        else:
            self._httpReturnCode(304, 'Not changed',
                                 'The contents of ' +
                                 'your local cache ' +
                                 'are up to date')

    def _400(self) -> None:
        if self.server.translate:
            self._httpReturnCode(400, self.server.translate['Bad Request'],
                                 self.server.translate['Better luck ' +
                                                       'next time'])
        else:
            self._httpReturnCode(400, 'Bad Request',
                                 'Better luck next time')

    def _503(self) -> None:
        if self.server.translate:
            self._httpReturnCode(503, self.server.translate['Unavailable'],
                                 self.server.translate['The server is busy. ' +
                                                       'Please try again ' +
                                                       'later'])
        else:
            self._httpReturnCode(503, 'Unavailable',
                                 'The server is busy. Please try again ' +
                                 'later')

    def _write(self, msg) -> bool:
        tries = 0
        while tries < 5:
            try:
                self.wfile.write(msg)
                return True
            except BrokenPipeError as ex:
                if self.server.debug:
                    print('ERROR: _write error ' + str(tries) + ' ' + str(ex))
                break
            except Exception as ex:
                print('ERROR: _write error ' + str(tries) + ' ' + str(ex))
                time.sleep(0.5)
            tries += 1
        return False

    def _hasAccept(self, callingDomain: str) -> bool:
        """Do the http headers have an Accept field?
        """
        if not self.headers.get('Accept'):
            if self.headers.get('accept'):
                print('Upper case Accept')
                self.headers['Accept'] = self.headers['accept']

        if self.headers.get('Accept') or callingDomain.endswith('.b32.i2p'):
            if not self.headers.get('Accept'):
                self.headers['Accept'] = \
                    'text/html,application/xhtml+xml,' \
                    'application/xml;q=0.9,image/webp,*/*;q=0.8'
            return True
        return False

    def _mastoApiV1(self, path: str, callingDomain: str,
                    uaStr: str,
                    authorized: bool,
                    http_prefix: str,
                    base_dir: str, nickname: str, domain: str,
                    domainFull: str,
                    onion_domain: str, i2p_domain: str,
                    translate: {},
                    registration: bool,
                    systemLanguage: str,
                    project_version: str,
                    customEmoji: [],
                    show_node_info_accounts: bool) -> bool:
        """This is a vestigil mastodon API for the purpose
        of returning an empty result to sites like
        https://mastopeek.app-dist.eu
        """
        if not path.startswith('/api/v1/'):
            return False
        print('mastodon api v1: ' + path)
        print('mastodon api v1: authorized ' + str(authorized))
        print('mastodon api v1: nickname ' + str(nickname))
        self._updateKnownCrawlers(uaStr)

        broch_mode = broch_modeIsActive(base_dir)
        sendJson, sendJsonStr = mastoApiV1Response(path,
                                                   callingDomain,
                                                   uaStr,
                                                   authorized,
                                                   http_prefix,
                                                   base_dir,
                                                   nickname, domain,
                                                   domainFull,
                                                   onion_domain,
                                                   i2p_domain,
                                                   translate,
                                                   registration,
                                                   systemLanguage,
                                                   project_version,
                                                   customEmoji,
                                                   show_node_info_accounts,
                                                   broch_mode)

        if sendJson is not None:
            msg = json.dumps(sendJson).encode('utf-8')
            msglen = len(msg)
            if self._hasAccept(callingDomain):
                if 'application/ld+json' in self.headers['Accept']:
                    self._set_headers('application/ld+json', msglen,
                                      None, callingDomain, True)
                else:
                    self._set_headers('application/json', msglen,
                                      None, callingDomain, True)
            else:
                self._set_headers('application/ld+json', msglen,
                                  None, callingDomain, True)
            self._write(msg)
            if sendJsonStr:
                print(sendJsonStr)
            return True

        # no api endpoints were matched
        self._404()
        return True

    def _mastoApi(self, path: str, callingDomain: str,
                  uaStr: str,
                  authorized: bool, http_prefix: str,
                  base_dir: str, nickname: str, domain: str,
                  domainFull: str,
                  onion_domain: str, i2p_domain: str,
                  translate: {},
                  registration: bool,
                  systemLanguage: str,
                  project_version: str,
                  customEmoji: [],
                  show_node_info_accounts: bool) -> bool:
        return self._mastoApiV1(path, callingDomain, uaStr, authorized,
                                http_prefix, base_dir, nickname, domain,
                                domainFull, onion_domain, i2p_domain,
                                translate, registration, systemLanguage,
                                project_version, customEmoji,
                                show_node_info_accounts)

    def _nodeinfo(self, uaStr: str, callingDomain: str) -> bool:
        if not self.path.startswith('/nodeinfo/2.0'):
            return False
        if self.server.debug:
            print('DEBUG: nodeinfo ' + self.path)
        self._updateKnownCrawlers(uaStr)

        # If we are in broch mode then don't show potentially
        # sensitive metadata.
        # For example, if this or allied instances are being attacked
        # then numbers of accounts may be changing as people
        # migrate, and that information may be useful to an adversary
        broch_mode = broch_modeIsActive(self.server.base_dir)

        nodeInfoVersion = self.server.project_version
        if not self.server.show_node_info_version or broch_mode:
            nodeInfoVersion = '0.0.0'

        show_node_info_accounts = self.server.show_node_info_accounts
        if broch_mode:
            show_node_info_accounts = False

        instanceUrl = self._getInstanceUrl(callingDomain)
        aboutUrl = instanceUrl + '/about'
        termsOfServiceUrl = instanceUrl + '/terms'
        info = metaDataNodeInfo(self.server.base_dir,
                                aboutUrl, termsOfServiceUrl,
                                self.server.registration,
                                nodeInfoVersion,
                                show_node_info_accounts)
        if info:
            msg = json.dumps(info).encode('utf-8')
            msglen = len(msg)
            if self._hasAccept(callingDomain):
                if 'application/ld+json' in self.headers['Accept']:
                    self._set_headers('application/ld+json', msglen,
                                      None, callingDomain, True)
                else:
                    self._set_headers('application/json', msglen,
                                      None, callingDomain, True)
            else:
                self._set_headers('application/ld+json', msglen,
                                  None, callingDomain, True)
            self._write(msg)
            print('nodeinfo sent to ' + callingDomain)
            return True
        self._404()
        return True

    def _webfinger(self, callingDomain: str) -> bool:
        if not self.path.startswith('/.well-known'):
            return False
        if self.server.debug:
            print('DEBUG: WEBFINGER well-known')

        if self.server.debug:
            print('DEBUG: WEBFINGER host-meta')
        if self.path.startswith('/.well-known/host-meta'):
            if callingDomain.endswith('.onion') and \
               self.server.onion_domain:
                wfResult = \
                    webfingerMeta('http', self.server.onion_domain)
            elif (callingDomain.endswith('.i2p') and
                  self.server.i2p_domain):
                wfResult = \
                    webfingerMeta('http', self.server.i2p_domain)
            else:
                wfResult = \
                    webfingerMeta(self.server.http_prefix,
                                  self.server.domainFull)
            if wfResult:
                msg = wfResult.encode('utf-8')
                msglen = len(msg)
                self._set_headers('application/xrd+xml', msglen,
                                  None, callingDomain, True)
                self._write(msg)
                return True
            self._404()
            return True
        if self.path.startswith('/api/statusnet') or \
           self.path.startswith('/api/gnusocial') or \
           self.path.startswith('/siteinfo') or \
           self.path.startswith('/poco') or \
           self.path.startswith('/friendi'):
            self._404()
            return True
        if self.path.startswith('/.well-known/nodeinfo') or \
           self.path.startswith('/.well-known/x-nodeinfo'):
            if callingDomain.endswith('.onion') and \
               self.server.onion_domain:
                wfResult = \
                    webfingerNodeInfo('http', self.server.onion_domain)
            elif (callingDomain.endswith('.i2p') and
                  self.server.i2p_domain):
                wfResult = \
                    webfingerNodeInfo('http', self.server.i2p_domain)
            else:
                wfResult = \
                    webfingerNodeInfo(self.server.http_prefix,
                                      self.server.domainFull)
            if wfResult:
                msg = json.dumps(wfResult).encode('utf-8')
                msglen = len(msg)
                if self._hasAccept(callingDomain):
                    if 'application/ld+json' in self.headers['Accept']:
                        self._set_headers('application/ld+json', msglen,
                                          None, callingDomain, True)
                    else:
                        self._set_headers('application/json', msglen,
                                          None, callingDomain, True)
                else:
                    self._set_headers('application/ld+json', msglen,
                                      None, callingDomain, True)
                self._write(msg)
                return True
            self._404()
            return True

        if self.server.debug:
            print('DEBUG: WEBFINGER lookup ' + self.path + ' ' +
                  str(self.server.base_dir))
        wfResult = \
            webfingerLookup(self.path, self.server.base_dir,
                            self.server.domain, self.server.onion_domain,
                            self.server.port, self.server.debug)
        if wfResult:
            msg = json.dumps(wfResult).encode('utf-8')
            msglen = len(msg)
            self._set_headers('application/jrd+json', msglen,
                              None, callingDomain, True)
            self._write(msg)
        else:
            if self.server.debug:
                print('DEBUG: WEBFINGER lookup 404 ' + self.path)
            self._404()
        return True

    def _postToOutbox(self, messageJson: {}, version: str,
                      postToNickname: str) -> bool:
        """post is received by the outbox
        Client to server message post
        https://www.w3.org/TR/activitypub/#client-to-server-outbox-delivery
        """
        city = self.server.city

        if postToNickname:
            print('Posting to nickname ' + postToNickname)
            self.postToNickname = postToNickname
            city = getSpoofedCity(self.server.city,
                                  self.server.base_dir,
                                  postToNickname, self.server.domain)

        return postMessageToOutbox(self.server.session,
                                   self.server.translate,
                                   messageJson, self.postToNickname,
                                   self.server, self.server.base_dir,
                                   self.server.http_prefix,
                                   self.server.domain,
                                   self.server.domainFull,
                                   self.server.onion_domain,
                                   self.server.i2p_domain,
                                   self.server.port,
                                   self.server.recentPostsCache,
                                   self.server.followersThreads,
                                   self.server.federationList,
                                   self.server.sendThreads,
                                   self.server.postLog,
                                   self.server.cachedWebfingers,
                                   self.server.personCache,
                                   self.server.allowDeletion,
                                   self.server.proxy_type, version,
                                   self.server.debug,
                                   self.server.yt_replace_domain,
                                   self.server.twitter_replacement_domain,
                                   self.server.show_published_date_only,
                                   self.server.allow_local_network_access,
                                   city, self.server.systemLanguage,
                                   self.server.shared_items_federated_domains,
                                   self.server.sharedItemFederationTokens,
                                   self.server.low_bandwidth,
                                   self.server.signingPrivateKeyPem,
                                   self.server.peertubeInstances,
                                   self.server.themeName,
                                   self.server.max_like_count,
                                   self.server.max_recent_posts,
                                   self.server.CWlists,
                                   self.server.lists_enabled,
                                   self.server.content_license_url)

    def _getOutboxThreadIndex(self, nickname: str,
                              maxOutboxThreadsPerAccount: int) -> int:
        """Returns the outbox thread index for the given account
        This is a ring buffer used to store the thread objects which
        are sending out posts
        """
        accountOutboxThreadName = nickname
        if not accountOutboxThreadName:
            accountOutboxThreadName = '*'

        # create the buffer for the given account
        if not self.server.outboxThread.get(accountOutboxThreadName):
            self.server.outboxThread[accountOutboxThreadName] = \
                [None] * maxOutboxThreadsPerAccount
            self.server.outboxThreadIndex[accountOutboxThreadName] = 0
            return 0

        # increment the ring buffer index
        index = self.server.outboxThreadIndex[accountOutboxThreadName] + 1
        if index >= maxOutboxThreadsPerAccount:
            index = 0

        self.server.outboxThreadIndex[accountOutboxThreadName] = index

        # remove any existing thread from the current index in the buffer
        if self.server.outboxThread.get(accountOutboxThreadName):
            acct = accountOutboxThreadName
            if self.server.outboxThread[acct][index].is_alive():
                self.server.outboxThread[acct][index].kill()
        return index

    def _postToOutboxThread(self, messageJson: {}) -> bool:
        """Creates a thread to send a post
        """
        accountOutboxThreadName = self.postToNickname
        if not accountOutboxThreadName:
            accountOutboxThreadName = '*'

        index = self._getOutboxThreadIndex(accountOutboxThreadName, 8)

        print('Creating outbox thread ' +
              accountOutboxThreadName + '/' +
              str(self.server.outboxThreadIndex[accountOutboxThreadName]))
        self.server.outboxThread[accountOutboxThreadName][index] = \
            threadWithTrace(target=self._postToOutbox,
                            args=(messageJson.copy(),
                                  self.server.project_version, None),
                            daemon=True)
        print('Starting outbox thread')
        self.server.outboxThread[accountOutboxThreadName][index].start()
        return True

    def _updateInboxQueue(self, nickname: str, messageJson: {},
                          messageBytes: str) -> int:
        """Update the inbox queue
        """
        if self.server.restartInboxQueueInProgress:
            self._503()
            print('Message arrived but currently restarting inbox queue')
            self.server.POSTbusy = False
            return 2

        # check that the incoming message has a fully recognized
        # linked data context
        if not hasValidContext(messageJson):
            print('Message arriving at inbox queue has no valid context')
            self._400()
            self.server.POSTbusy = False
            return 3

        # check for blocked domains so that they can be rejected early
        messageDomain = None
        if not hasActor(messageJson, self.server.debug):
            print('Message arriving at inbox queue has no actor')
            self._400()
            self.server.POSTbusy = False
            return 3

        # actor should be a string
        if not isinstance(messageJson['actor'], str):
            self._400()
            self.server.POSTbusy = False
            return 3

        # check that some additional fields are strings
        stringFields = ('id', 'type', 'published')
        for checkField in stringFields:
            if not messageJson.get(checkField):
                continue
            if not isinstance(messageJson[checkField], str):
                self._400()
                self.server.POSTbusy = False
                return 3

        # check that to/cc fields are lists
        listFields = ('to', 'cc')
        for checkField in listFields:
            if not messageJson.get(checkField):
                continue
            if not isinstance(messageJson[checkField], list):
                self._400()
                self.server.POSTbusy = False
                return 3

        if hasObjectDict(messageJson):
            stringFields = (
                'id', 'actor', 'type', 'content', 'published',
                'summary', 'url', 'attributedTo'
            )
            for checkField in stringFields:
                if not messageJson['object'].get(checkField):
                    continue
                if not isinstance(messageJson['object'][checkField], str):
                    self._400()
                    self.server.POSTbusy = False
                    return 3
            # check that some fields are lists
            listFields = ('to', 'cc', 'attachment')
            for checkField in listFields:
                if not messageJson['object'].get(checkField):
                    continue
                if not isinstance(messageJson['object'][checkField], list):
                    self._400()
                    self.server.POSTbusy = False
                    return 3

        # actor should look like a url
        if '://' not in messageJson['actor'] or \
           '.' not in messageJson['actor']:
            print('POST actor does not look like a url ' +
                  messageJson['actor'])
            self._400()
            self.server.POSTbusy = False
            return 3

        # sent by an actor on a local network address?
        if not self.server.allow_local_network_access:
            localNetworkPatternList = getLocalNetworkAddresses()
            for localNetworkPattern in localNetworkPatternList:
                if localNetworkPattern in messageJson['actor']:
                    print('POST actor contains local network address ' +
                          messageJson['actor'])
                    self._400()
                    self.server.POSTbusy = False
                    return 3

        messageDomain, messagePort = \
            getDomainFromActor(messageJson['actor'])

        self.server.blockedCacheLastUpdated = \
            updateBlockedCache(self.server.base_dir,
                               self.server.blockedCache,
                               self.server.blockedCacheLastUpdated,
                               self.server.blockedCacheUpdateSecs)

        if isBlockedDomain(self.server.base_dir, messageDomain,
                           self.server.blockedCache):
            print('POST from blocked domain ' + messageDomain)
            self._400()
            self.server.POSTbusy = False
            return 3

        # if the inbox queue is full then return a busy code
        if len(self.server.inboxQueue) >= self.server.maxQueueLength:
            if messageDomain:
                print('Queue: Inbox queue is full. Incoming post from ' +
                      messageJson['actor'])
            else:
                print('Queue: Inbox queue is full')
            self._503()
            clearQueueItems(self.server.base_dir, self.server.inboxQueue)
            if not self.server.restartInboxQueueInProgress:
                self.server.restartInboxQueue = True
            self.server.POSTbusy = False
            return 2

        # Convert the headers needed for signature verification to dict
        headersDict = {}
        headersDict['host'] = self.headers['host']
        headersDict['signature'] = self.headers['signature']
        if self.headers.get('Date'):
            headersDict['Date'] = self.headers['Date']
        elif self.headers.get('date'):
            headersDict['Date'] = self.headers['date']
        if self.headers.get('digest'):
            headersDict['digest'] = self.headers['digest']
        if self.headers.get('Collection-Synchronization'):
            headersDict['Collection-Synchronization'] = \
                self.headers['Collection-Synchronization']
        if self.headers.get('Content-type'):
            headersDict['Content-type'] = self.headers['Content-type']
        if self.headers.get('Content-Length'):
            headersDict['Content-Length'] = self.headers['Content-Length']
        elif self.headers.get('content-length'):
            headersDict['content-length'] = self.headers['content-length']

        originalMessageJson = messageJson.copy()

        # whether to add a 'to' field to the message
        addToFieldTypes = (
            'Follow', 'Like', 'EmojiReact', 'Add', 'Remove', 'Ignore'
        )
        for addToType in addToFieldTypes:
            messageJson, toFieldExists = \
                addToField(addToType, messageJson, self.server.debug)

        beginSaveTime = time.time()
        # save the json for later queue processing
        messageBytesDecoded = messageBytes.decode('utf-8')

        if containsInvalidLocalLinks(messageBytesDecoded):
            print('WARN: post contains invalid local links ' +
                  str(originalMessageJson))
            return 5

        self.server.blockedCacheLastUpdated = \
            updateBlockedCache(self.server.base_dir,
                               self.server.blockedCache,
                               self.server.blockedCacheLastUpdated,
                               self.server.blockedCacheUpdateSecs)

        queueFilename = \
            savePostToInboxQueue(self.server.base_dir,
                                 self.server.http_prefix,
                                 nickname,
                                 self.server.domainFull,
                                 messageJson, originalMessageJson,
                                 messageBytesDecoded,
                                 headersDict,
                                 self.path,
                                 self.server.debug,
                                 self.server.blockedCache,
                                 self.server.systemLanguage)
        if queueFilename:
            # add json to the queue
            if queueFilename not in self.server.inboxQueue:
                self.server.inboxQueue.append(queueFilename)
            if self.server.debug:
                timeDiff = int((time.time() - beginSaveTime) * 1000)
                if timeDiff > 200:
                    print('SLOW: slow save of inbox queue item ' +
                          queueFilename + ' took ' + str(timeDiff) + ' mS')
            self.send_response(201)
            self.end_headers()
            self.server.POSTbusy = False
            return 0
        self._503()
        self.server.POSTbusy = False
        return 1

    def _isAuthorized(self) -> bool:
        self.authorizedNickname = None

        notAuthPaths = (
            '/icons/', '/avatars/', '/favicons/',
            '/system/accounts/avatars/',
            '/system/accounts/headers/',
            '/system/media_attachments/files/',
            '/accounts/avatars/', '/accounts/headers/',
            '/favicon.ico', '/newswire.xml',
            '/newswire_favicon.ico', '/categories.xml'
        )
        for notAuthStr in notAuthPaths:
            if self.path.startswith(notAuthStr):
                return False

        # token based authenticated used by the web interface
        if self.headers.get('Cookie'):
            if self.headers['Cookie'].startswith('epicyon='):
                tokenStr = self.headers['Cookie'].split('=', 1)[1].strip()
                if ';' in tokenStr:
                    tokenStr = tokenStr.split(';')[0].strip()
                if self.server.tokensLookup.get(tokenStr):
                    nickname = self.server.tokensLookup[tokenStr]
                    if not isSystemAccount(nickname):
                        self.authorizedNickname = nickname
                        # default to the inbox of the person
                        if self.path == '/':
                            self.path = '/users/' + nickname + '/inbox'
                        # check that the path contains the same nickname
                        # as the cookie otherwise it would be possible
                        # to be authorized to use an account you don't own
                        if '/' + nickname + '/' in self.path:
                            return True
                        elif '/' + nickname + '?' in self.path:
                            return True
                        elif self.path.endswith('/' + nickname):
                            return True
                        if self.server.debug:
                            print('AUTH: nickname ' + nickname +
                                  ' was not found in path ' + self.path)
                    return False
                print('AUTH: epicyon cookie ' +
                      'authorization failed, header=' +
                      self.headers['Cookie'].replace('epicyon=', '') +
                      ' tokenStr=' + tokenStr + ' tokens=' +
                      str(self.server.tokensLookup))
                return False
            print('AUTH: Header cookie was not authorized')
            return False
        # basic auth for c2s
        if self.headers.get('Authorization'):
            if authorize(self.server.base_dir, self.path,
                         self.headers['Authorization'],
                         self.server.debug):
                return True
            print('AUTH: C2S Basic auth did not authorize ' +
                  self.headers['Authorization'])
        return False

    def _clearLoginDetails(self, nickname: str, callingDomain: str) -> None:
        """Clears login details for the given account
        """
        # remove any token
        if self.server.tokens.get(nickname):
            del self.server.tokensLookup[self.server.tokens[nickname]]
            del self.server.tokens[nickname]
        self._redirect_headers(self.server.http_prefix + '://' +
                               self.server.domainFull + '/login',
                               'epicyon=; SameSite=Strict',
                               callingDomain)

    def _loginScreen(self, path: str, callingDomain: str, cookie: str,
                     base_dir: str, http_prefix: str,
                     domain: str, domainFull: str, port: int,
                     onion_domain: str, i2p_domain: str,
                     debug: bool) -> None:
        """Shows the login screen
        """
        # ensure that there is a minimum delay between failed login
        # attempts, to mitigate brute force
        if int(time.time()) - self.server.lastLoginFailure < 5:
            self._503()
            self.server.POSTbusy = False
            return

        # get the contents of POST containing login credentials
        length = int(self.headers['Content-length'])
        if length > 512:
            print('Login failed - credentials too long')
            self.send_response(401)
            self.end_headers()
            self.server.POSTbusy = False
            return

        try:
            loginParams = self.rfile.read(length).decode('utf-8')
        except SocketError as ex:
            if ex.errno == errno.ECONNRESET:
                print('WARN: POST login read ' +
                      'connection reset by peer')
            else:
                print('WARN: POST login read socket error')
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy = False
            return
        except ValueError as ex:
            print('ERROR: POST login read failed, ' + str(ex))
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy = False
            return

        loginNickname, loginPassword, register = \
            htmlGetLoginCredentials(loginParams,
                                    self.server.lastLoginTime,
                                    self.server.domain)
        if loginNickname:
            if isSystemAccount(loginNickname):
                print('Invalid username login: ' + loginNickname +
                      ' (system account)')
                self._clearLoginDetails(loginNickname, callingDomain)
                self.server.POSTbusy = False
                return
            self.server.lastLoginTime = int(time.time())
            if register:
                if not validPassword(loginPassword):
                    self.server.POSTbusy = False
                    if callingDomain.endswith('.onion') and onion_domain:
                        self._redirect_headers('http://' + onion_domain +
                                               '/login', cookie,
                                               callingDomain)
                    elif (callingDomain.endswith('.i2p') and i2p_domain):
                        self._redirect_headers('http://' + i2p_domain +
                                               '/login', cookie,
                                               callingDomain)
                    else:
                        self._redirect_headers(http_prefix + '://' +
                                               domainFull + '/login',
                                               cookie, callingDomain)
                    return

                if not registerAccount(base_dir, http_prefix, domain, port,
                                       loginNickname, loginPassword,
                                       self.server.manualFollowerApproval):
                    self.server.POSTbusy = False
                    if callingDomain.endswith('.onion') and onion_domain:
                        self._redirect_headers('http://' + onion_domain +
                                               '/login', cookie,
                                               callingDomain)
                    elif (callingDomain.endswith('.i2p') and i2p_domain):
                        self._redirect_headers('http://' + i2p_domain +
                                               '/login', cookie,
                                               callingDomain)
                    else:
                        self._redirect_headers(http_prefix + '://' +
                                               domainFull + '/login',
                                               cookie, callingDomain)
                    return
            authHeader = \
                createBasicAuthHeader(loginNickname, loginPassword)
            if self.headers.get('X-Forward-For'):
                ipAddress = self.headers['X-Forward-For']
            elif self.headers.get('X-Forwarded-For'):
                ipAddress = self.headers['X-Forwarded-For']
            else:
                ipAddress = self.client_address[0]
            if not domain.endswith('.onion'):
                if not isLocalNetworkAddress(ipAddress):
                    print('Login attempt from IP: ' + str(ipAddress))
            if not authorizeBasic(base_dir, '/users/' +
                                  loginNickname + '/outbox',
                                  authHeader, False):
                print('Login failed: ' + loginNickname)
                self._clearLoginDetails(loginNickname, callingDomain)
                failTime = int(time.time())
                self.server.lastLoginFailure = failTime
                if not domain.endswith('.onion'):
                    if not isLocalNetworkAddress(ipAddress):
                        recordLoginFailure(base_dir, ipAddress,
                                           self.server.loginFailureCount,
                                           failTime,
                                           self.server.log_login_failures)
                self.server.POSTbusy = False
                return
            else:
                if self.server.loginFailureCount.get(ipAddress):
                    del self.server.loginFailureCount[ipAddress]
                if isSuspended(base_dir, loginNickname):
                    msg = \
                        htmlSuspended(self.server.cssCache,
                                      base_dir).encode('utf-8')
                    msglen = len(msg)
                    self._login_headers('text/html',
                                        msglen, callingDomain)
                    self._write(msg)
                    self.server.POSTbusy = False
                    return
                # login success - redirect with authorization
                print('Login success: ' + loginNickname)
                # re-activate account if needed
                activateAccount(base_dir, loginNickname, domain)
                # This produces a deterministic token based
                # on nick+password+salt
                saltFilename = \
                    acctDir(base_dir, loginNickname, domain) + '/.salt'
                salt = createPassword(32)
                if os.path.isfile(saltFilename):
                    try:
                        with open(saltFilename, 'r') as fp:
                            salt = fp.read()
                    except OSError as ex:
                        print('EX: Unable to read salt for ' +
                              loginNickname + ' ' + str(ex))
                else:
                    try:
                        with open(saltFilename, 'w+') as fp:
                            fp.write(salt)
                    except OSError as ex:
                        print('EX: Unable to save salt for ' +
                              loginNickname + ' ' + str(ex))

                tokenText = loginNickname + loginPassword + salt
                token = sha256(tokenText.encode('utf-8')).hexdigest()
                self.server.tokens[loginNickname] = token
                loginHandle = loginNickname + '@' + domain
                tokenFilename = \
                    base_dir + '/accounts/' + \
                    loginHandle + '/.token'
                try:
                    with open(tokenFilename, 'w+') as fp:
                        fp.write(token)
                except OSError as ex:
                    print('EX: Unable to save token for ' +
                          loginNickname + ' ' + str(ex))

                personUpgradeActor(base_dir, None, loginHandle,
                                   base_dir + '/accounts/' +
                                   loginHandle + '.json')

                index = self.server.tokens[loginNickname]
                self.server.tokensLookup[index] = loginNickname
                cookieStr = 'SET:epicyon=' + \
                    self.server.tokens[loginNickname] + '; SameSite=Strict'
                if callingDomain.endswith('.onion') and onion_domain:
                    self._redirect_headers('http://' +
                                           onion_domain +
                                           '/users/' +
                                           loginNickname + '/' +
                                           self.server.defaultTimeline,
                                           cookieStr, callingDomain)
                elif (callingDomain.endswith('.i2p') and i2p_domain):
                    self._redirect_headers('http://' +
                                           i2p_domain +
                                           '/users/' +
                                           loginNickname + '/' +
                                           self.server.defaultTimeline,
                                           cookieStr, callingDomain)
                else:
                    self._redirect_headers(http_prefix + '://' +
                                           domainFull + '/users/' +
                                           loginNickname + '/' +
                                           self.server.defaultTimeline,
                                           cookieStr, callingDomain)
                self.server.POSTbusy = False
                return
        self._200()
        self.server.POSTbusy = False

    def _moderatorActions(self, path: str, callingDomain: str, cookie: str,
                          base_dir: str, http_prefix: str,
                          domain: str, domainFull: str, port: int,
                          onion_domain: str, i2p_domain: str,
                          debug: bool) -> None:
        """Actions on the moderator screen
        """
        usersPath = path.replace('/moderationaction', '')
        nickname = usersPath.replace('/users/', '')
        actorStr = self._getInstanceUrl(callingDomain) + usersPath
        if not isModerator(self.server.base_dir, nickname):
            self._redirect_headers(actorStr + '/moderation',
                                   cookie, callingDomain)
            self.server.POSTbusy = False
            return

        length = int(self.headers['Content-length'])

        try:
            moderationParams = self.rfile.read(length).decode('utf-8')
        except SocketError as ex:
            if ex.errno == errno.ECONNRESET:
                print('WARN: POST moderationParams connection was reset')
            else:
                print('WARN: POST moderationParams ' +
                      'rfile.read socket error')
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy = False
            return
        except ValueError as ex:
            print('ERROR: POST moderationParams rfile.read failed, ' + str(ex))
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy = False
            return

        if '&' in moderationParams:
            moderationText = None
            moderationButton = None
            for moderationStr in moderationParams.split('&'):
                if moderationStr.startswith('moderationAction'):
                    if '=' in moderationStr:
                        moderationText = \
                            moderationStr.split('=')[1].strip()
                        modText = moderationText.replace('+', ' ')
                        moderationText = \
                            urllib.parse.unquote_plus(modText.strip())
                elif moderationStr.startswith('submitInfo'):
                    searchHandle = moderationText
                    if searchHandle:
                        if '/@' in searchHandle:
                            searchNickname = \
                                getNicknameFromActor(searchHandle)
                            searchDomain, searchPort = \
                                getDomainFromActor(searchHandle)
                            searchHandle = \
                                searchNickname + '@' + searchDomain
                        if '@' not in searchHandle:
                            if searchHandle.startswith('http'):
                                searchNickname = \
                                    getNicknameFromActor(searchHandle)
                                searchDomain, searchPort = \
                                    getDomainFromActor(searchHandle)
                                searchHandle = \
                                    searchNickname + '@' + searchDomain
                        if '@' not in searchHandle:
                            # is this a local nickname on this instance?
                            localHandle = \
                                searchHandle + '@' + self.server.domain
                            if os.path.isdir(self.server.base_dir +
                                             '/accounts/' + localHandle):
                                searchHandle = localHandle
                            else:
                                searchHandle = None
                    if searchHandle:
                        msg = \
                            htmlAccountInfo(self.server.cssCache,
                                            self.server.translate,
                                            base_dir, http_prefix,
                                            nickname,
                                            self.server.domain,
                                            self.server.port,
                                            searchHandle,
                                            self.server.debug,
                                            self.server.systemLanguage,
                                            self.server.signingPrivateKeyPem)
                    else:
                        msg = \
                            htmlModerationInfo(self.server.cssCache,
                                               self.server.translate,
                                               base_dir, http_prefix,
                                               nickname)
                    msg = msg.encode('utf-8')
                    msglen = len(msg)
                    self._login_headers('text/html',
                                        msglen, callingDomain)
                    self._write(msg)
                    self.server.POSTbusy = False
                    return
                elif moderationStr.startswith('submitBlock'):
                    moderationButton = 'block'
                elif moderationStr.startswith('submitUnblock'):
                    moderationButton = 'unblock'
                elif moderationStr.startswith('submitFilter'):
                    moderationButton = 'filter'
                elif moderationStr.startswith('submitUnfilter'):
                    moderationButton = 'unfilter'
                elif moderationStr.startswith('submitSuspend'):
                    moderationButton = 'suspend'
                elif moderationStr.startswith('submitUnsuspend'):
                    moderationButton = 'unsuspend'
                elif moderationStr.startswith('submitRemove'):
                    moderationButton = 'remove'
            if moderationButton and moderationText:
                if debug:
                    print('moderationButton: ' + moderationButton)
                    print('moderationText: ' + moderationText)
                nickname = moderationText
                if nickname.startswith('http') or \
                   nickname.startswith('hyper'):
                    nickname = getNicknameFromActor(nickname)
                if '@' in nickname:
                    nickname = nickname.split('@')[0]
                if moderationButton == 'suspend':
                    suspendAccount(base_dir, nickname, domain)
                if moderationButton == 'unsuspend':
                    reenableAccount(base_dir, nickname)
                if moderationButton == 'filter':
                    addGlobalFilter(base_dir, moderationText)
                if moderationButton == 'unfilter':
                    removeGlobalFilter(base_dir, moderationText)
                if moderationButton == 'block':
                    fullBlockDomain = None
                    if moderationText.startswith('http') or \
                       moderationText.startswith('hyper'):
                        # https://domain
                        blockDomain, blockPort = \
                            getDomainFromActor(moderationText)
                        fullBlockDomain = getFullDomain(blockDomain, blockPort)
                    if '@' in moderationText:
                        # nick@domain or *@domain
                        fullBlockDomain = moderationText.split('@')[1]
                    else:
                        # assume the text is a domain name
                        if not fullBlockDomain and '.' in moderationText:
                            nickname = '*'
                            fullBlockDomain = moderationText.strip()
                    if fullBlockDomain or nickname.startswith('#'):
                        addGlobalBlock(base_dir, nickname, fullBlockDomain)
                if moderationButton == 'unblock':
                    fullBlockDomain = None
                    if moderationText.startswith('http') or \
                       moderationText.startswith('hyper'):
                        # https://domain
                        blockDomain, blockPort = \
                            getDomainFromActor(moderationText)
                        fullBlockDomain = getFullDomain(blockDomain, blockPort)
                    if '@' in moderationText:
                        # nick@domain or *@domain
                        fullBlockDomain = moderationText.split('@')[1]
                    else:
                        # assume the text is a domain name
                        if not fullBlockDomain and '.' in moderationText:
                            nickname = '*'
                            fullBlockDomain = moderationText.strip()
                    if fullBlockDomain or nickname.startswith('#'):
                        removeGlobalBlock(base_dir, nickname, fullBlockDomain)
                if moderationButton == 'remove':
                    if '/statuses/' not in moderationText:
                        removeAccount(base_dir, nickname, domain, port)
                    else:
                        # remove a post or thread
                        postFilename = \
                            locatePost(base_dir, nickname, domain,
                                       moderationText)
                        if postFilename:
                            if canRemovePost(base_dir,
                                             nickname, domain, port,
                                             moderationText):
                                deletePost(base_dir,
                                           http_prefix,
                                           nickname, domain,
                                           postFilename,
                                           debug,
                                           self.server.recentPostsCache)
                        if nickname != 'news':
                            # if this is a local blog post then also remove it
                            # from the news actor
                            postFilename = \
                                locatePost(base_dir, 'news', domain,
                                           moderationText)
                            if postFilename:
                                if canRemovePost(base_dir,
                                                 'news', domain, port,
                                                 moderationText):
                                    deletePost(base_dir,
                                               http_prefix,
                                               'news', domain,
                                               postFilename,
                                               debug,
                                               self.server.recentPostsCache)

        self._redirect_headers(actorStr + '/moderation',
                               cookie, callingDomain)
        self.server.POSTbusy = False
        return

    def _keyShortcuts(self, path: str,
                      callingDomain: str, cookie: str,
                      base_dir: str, http_prefix: str, nickname: str,
                      domain: str, domainFull: str, port: int,
                      onion_domain: str, i2p_domain: str,
                      debug: bool, accessKeys: {},
                      defaultTimeline: str) -> None:
        """Receive POST from webapp_accesskeys
        """
        usersPath = '/users/' + nickname
        originPathStr = \
            http_prefix + '://' + domainFull + usersPath + '/' + \
            defaultTimeline
        length = int(self.headers['Content-length'])

        try:
            accessKeysParams = self.rfile.read(length).decode('utf-8')
        except SocketError as ex:
            if ex.errno == errno.ECONNRESET:
                print('WARN: POST accessKeysParams ' +
                      'connection reset by peer')
            else:
                print('WARN: POST accessKeysParams socket error')
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy = False
            return
        except ValueError as ex:
            print('ERROR: POST accessKeysParams rfile.read failed, ' + str(ex))
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy = False
            return
        accessKeysParams = \
            urllib.parse.unquote_plus(accessKeysParams)

        # key shortcuts screen, back button
        # See htmlAccessKeys
        if 'submitAccessKeysCancel=' in accessKeysParams or \
           'submitAccessKeys=' not in accessKeysParams:
            if callingDomain.endswith('.onion') and onion_domain:
                originPathStr = \
                    'http://' + onion_domain + usersPath + '/' + \
                    defaultTimeline
            elif callingDomain.endswith('.i2p') and i2p_domain:
                originPathStr = \
                    'http://' + i2p_domain + usersPath + '/' + defaultTimeline
            self._redirect_headers(originPathStr, cookie, callingDomain)
            self.server.POSTbusy = False
            return

        saveKeys = False
        accessKeysTemplate = self.server.accessKeys
        for variableName, key in accessKeysTemplate.items():
            if not accessKeys.get(variableName):
                accessKeys[variableName] = accessKeysTemplate[variableName]

            variableName2 = variableName.replace(' ', '_')
            if variableName2 + '=' in accessKeysParams:
                newKey = accessKeysParams.split(variableName2 + '=')[1]
                if '&' in newKey:
                    newKey = newKey.split('&')[0]
                if newKey:
                    if len(newKey) > 1:
                        newKey = newKey[0]
                    if newKey != accessKeys[variableName]:
                        accessKeys[variableName] = newKey
                        saveKeys = True

        if saveKeys:
            accessKeysFilename = \
                acctDir(base_dir, nickname, domain) + '/accessKeys.json'
            saveJson(accessKeys, accessKeysFilename)
            if not self.server.keyShortcuts.get(nickname):
                self.server.keyShortcuts[nickname] = accessKeys.copy()

        # redirect back from key shortcuts screen
        if callingDomain.endswith('.onion') and onion_domain:
            originPathStr = \
                'http://' + onion_domain + usersPath + '/' + defaultTimeline
        elif callingDomain.endswith('.i2p') and i2p_domain:
            originPathStr = \
                'http://' + i2p_domain + usersPath + '/' + defaultTimeline
        self._redirect_headers(originPathStr, cookie, callingDomain)
        self.server.POSTbusy = False
        return

    def _themeDesigner(self, path: str,
                       callingDomain: str, cookie: str,
                       base_dir: str, http_prefix: str, nickname: str,
                       domain: str, domainFull: str, port: int,
                       onion_domain: str, i2p_domain: str,
                       debug: bool, accessKeys: {},
                       defaultTimeline: str, themeName: str,
                       allow_local_network_access: bool,
                       systemLanguage: str) -> None:
        """Receive POST from webapp_themeDesigner
        """
        usersPath = '/users/' + nickname
        originPathStr = \
            http_prefix + '://' + domainFull + usersPath + '/' + \
            defaultTimeline
        length = int(self.headers['Content-length'])

        try:
            themeParams = self.rfile.read(length).decode('utf-8')
        except SocketError as ex:
            if ex.errno == errno.ECONNRESET:
                print('WARN: POST themeParams ' +
                      'connection reset by peer')
            else:
                print('WARN: POST themeParams socket error')
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy = False
            return
        except ValueError as ex:
            print('ERROR: POST themeParams rfile.read failed, ' + str(ex))
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy = False
            return
        themeParams = \
            urllib.parse.unquote_plus(themeParams)

        # theme designer screen, reset button
        # See htmlThemeDesigner
        if 'submitThemeDesignerReset=' in themeParams or \
           'submitThemeDesigner=' not in themeParams:
            if 'submitThemeDesignerReset=' in themeParams:
                resetThemeDesignerSettings(base_dir, themeName, domain,
                                           allow_local_network_access,
                                           systemLanguage)
                setTheme(base_dir, themeName, domain,
                         allow_local_network_access, systemLanguage)

            if callingDomain.endswith('.onion') and onion_domain:
                originPathStr = \
                    'http://' + onion_domain + usersPath + '/' + \
                    defaultTimeline
            elif callingDomain.endswith('.i2p') and i2p_domain:
                originPathStr = \
                    'http://' + i2p_domain + usersPath + '/' + defaultTimeline
            self._redirect_headers(originPathStr, cookie, callingDomain)
            self.server.POSTbusy = False
            return

        fields = {}
        fieldsList = themeParams.split('&')
        for fieldStr in fieldsList:
            if '=' not in fieldStr:
                continue
            fieldValue = fieldStr.split('=')[1].strip()
            if not fieldValue:
                continue
            if fieldValue == 'on':
                fieldValue = 'True'
            fields[fieldStr.split('=')[0]] = fieldValue

        # Check for boolean values which are False.
        # These don't come through via themeParams,
        # so need to be checked separately
        themeFilename = base_dir + '/theme/' + themeName + '/theme.json'
        themeJson = loadJson(themeFilename)
        if themeJson:
            for variableName, value in themeJson.items():
                variableName = 'themeSetting_' + variableName
                if value.lower() == 'false' or value.lower() == 'true':
                    if variableName not in fields:
                        fields[variableName] = 'False'

        # get the parameters from the theme designer screen
        themeDesignerParams = {}
        for variableName, key in fields.items():
            if variableName.startswith('themeSetting_'):
                variableName = variableName.replace('themeSetting_', '')
                themeDesignerParams[variableName] = key

        setThemeFromDesigner(base_dir, themeName, domain,
                             themeDesignerParams,
                             allow_local_network_access,
                             systemLanguage)

        # set boolean values
        if 'rss-icon-at-top' in themeDesignerParams:
            if themeDesignerParams['rss-icon-at-top'].lower() == 'true':
                self.server.rss_icon_at_top = True
            else:
                self.server.rss_icon_at_top = False
        if 'publish-button-at-top' in themeDesignerParams:
            if themeDesignerParams['publish-button-at-top'].lower() == 'true':
                self.server.publish_button_at_top = True
            else:
                self.server.publish_button_at_top = False
        if 'newswire-publish-icon' in themeDesignerParams:
            if themeDesignerParams['newswire-publish-icon'].lower() == 'true':
                self.server.show_publish_as_icon = True
            else:
                self.server.show_publish_as_icon = False
        if 'icons-as-buttons' in themeDesignerParams:
            if themeDesignerParams['icons-as-buttons'].lower() == 'true':
                self.server.icons_as_buttons = True
            else:
                self.server.icons_as_buttons = False
        if 'full-width-timeline-buttons' in themeDesignerParams:
            themeValue = themeDesignerParams['full-width-timeline-buttons']
            if themeValue.lower() == 'true':
                self.server.full_width_tl_button_header = True
            else:
                self.server.full_width_tl_button_header = False

        # redirect back from theme designer screen
        if callingDomain.endswith('.onion') and onion_domain:
            originPathStr = \
                'http://' + onion_domain + usersPath + '/' + defaultTimeline
        elif callingDomain.endswith('.i2p') and i2p_domain:
            originPathStr = \
                'http://' + i2p_domain + usersPath + '/' + defaultTimeline
        self._redirect_headers(originPathStr, cookie, callingDomain)
        self.server.POSTbusy = False
        return

    def _personOptions(self, path: str,
                       callingDomain: str, cookie: str,
                       base_dir: str, http_prefix: str,
                       domain: str, domainFull: str, port: int,
                       onion_domain: str, i2p_domain: str,
                       debug: bool) -> None:
        """Receive POST from person options screen
        """
        pageNumber = 1
        usersPath = path.split('/personoptions')[0]
        originPathStr = http_prefix + '://' + domainFull + usersPath

        chooserNickname = getNicknameFromActor(originPathStr)
        if not chooserNickname:
            if callingDomain.endswith('.onion') and onion_domain:
                originPathStr = 'http://' + onion_domain + usersPath
            elif (callingDomain.endswith('.i2p') and i2p_domain):
                originPathStr = 'http://' + i2p_domain + usersPath
            print('WARN: unable to find nickname in ' + originPathStr)
            self._redirect_headers(originPathStr, cookie, callingDomain)
            self.server.POSTbusy = False
            return

        length = int(self.headers['Content-length'])

        try:
            optionsConfirmParams = self.rfile.read(length).decode('utf-8')
        except SocketError as ex:
            if ex.errno == errno.ECONNRESET:
                print('WARN: POST optionsConfirmParams ' +
                      'connection reset by peer')
            else:
                print('WARN: POST optionsConfirmParams socket error')
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy = False
            return
        except ValueError as ex:
            print('ERROR: ' +
                  'POST optionsConfirmParams rfile.read failed, ' + str(ex))
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy = False
            return
        optionsConfirmParams = \
            urllib.parse.unquote_plus(optionsConfirmParams)

        # page number to return to
        if 'pageNumber=' in optionsConfirmParams:
            pageNumberStr = optionsConfirmParams.split('pageNumber=')[1]
            if '&' in pageNumberStr:
                pageNumberStr = pageNumberStr.split('&')[0]
            if pageNumberStr.isdigit():
                pageNumber = int(pageNumberStr)

        # actor for the person
        optionsActor = optionsConfirmParams.split('actor=')[1]
        if '&' in optionsActor:
            optionsActor = optionsActor.split('&')[0]

        # url of the avatar
        optionsAvatarUrl = optionsConfirmParams.split('avatarUrl=')[1]
        if '&' in optionsAvatarUrl:
            optionsAvatarUrl = optionsAvatarUrl.split('&')[0]

        # link to a post, which can then be included in reports
        postUrl = None
        if 'postUrl' in optionsConfirmParams:
            postUrl = optionsConfirmParams.split('postUrl=')[1]
            if '&' in postUrl:
                postUrl = postUrl.split('&')[0]

        # petname for this person
        petname = None
        if 'optionpetname' in optionsConfirmParams:
            petname = optionsConfirmParams.split('optionpetname=')[1]
            if '&' in petname:
                petname = petname.split('&')[0]
            # Limit the length of the petname
            if len(petname) > 20 or \
               ' ' in petname or '/' in petname or \
               '?' in petname or '#' in petname:
                petname = None

        # notes about this person
        personNotes = None
        if 'optionnotes' in optionsConfirmParams:
            personNotes = optionsConfirmParams.split('optionnotes=')[1]
            if '&' in personNotes:
                personNotes = personNotes.split('&')[0]
            personNotes = urllib.parse.unquote_plus(personNotes.strip())
            # Limit the length of the notes
            if len(personNotes) > 64000:
                personNotes = None

        # get the nickname
        optionsNickname = getNicknameFromActor(optionsActor)
        if not optionsNickname:
            if callingDomain.endswith('.onion') and onion_domain:
                originPathStr = 'http://' + onion_domain + usersPath
            elif (callingDomain.endswith('.i2p') and i2p_domain):
                originPathStr = 'http://' + i2p_domain + usersPath
            print('WARN: unable to find nickname in ' + optionsActor)
            self._redirect_headers(originPathStr, cookie, callingDomain)
            self.server.POSTbusy = False
            return

        optionsDomain, optionsPort = getDomainFromActor(optionsActor)
        optionsDomainFull = getFullDomain(optionsDomain, optionsPort)
        if chooserNickname == optionsNickname and \
           optionsDomain == domain and \
           optionsPort == port:
            if debug:
                print('You cannot perform an option action on yourself')

        # person options screen, view button
        # See htmlPersonOptions
        if '&submitView=' in optionsConfirmParams:
            if debug:
                print('Viewing ' + optionsActor)
            self._redirect_headers(optionsActor,
                                   cookie, callingDomain)
            self.server.POSTbusy = False
            return

        # person options screen, petname submit button
        # See htmlPersonOptions
        if '&submitPetname=' in optionsConfirmParams and petname:
            if debug:
                print('Change petname to ' + petname)
            handle = optionsNickname + '@' + optionsDomainFull
            setPetName(base_dir,
                       chooserNickname,
                       domain,
                       handle, petname)
            usersPathStr = \
                usersPath + '/' + self.server.defaultTimeline + \
                '?page=' + str(pageNumber)
            self._redirect_headers(usersPathStr, cookie,
                                   callingDomain)
            self.server.POSTbusy = False
            return

        # person options screen, person notes submit button
        # See htmlPersonOptions
        if '&submitPersonNotes=' in optionsConfirmParams:
            if debug:
                print('Change person notes')
            handle = optionsNickname + '@' + optionsDomainFull
            if not personNotes:
                personNotes = ''
            setPersonNotes(base_dir,
                           chooserNickname,
                           domain,
                           handle, personNotes)
            usersPathStr = \
                usersPath + '/' + self.server.defaultTimeline + \
                '?page=' + str(pageNumber)
            self._redirect_headers(usersPathStr, cookie,
                                   callingDomain)
            self.server.POSTbusy = False
            return

        # person options screen, on calendar checkbox
        # See htmlPersonOptions
        if '&submitOnCalendar=' in optionsConfirmParams:
            onCalendar = None
            if 'onCalendar=' in optionsConfirmParams:
                onCalendar = optionsConfirmParams.split('onCalendar=')[1]
                if '&' in onCalendar:
                    onCalendar = onCalendar.split('&')[0]
            if onCalendar == 'on':
                addPersonToCalendar(base_dir,
                                    chooserNickname,
                                    domain,
                                    optionsNickname,
                                    optionsDomainFull)
            else:
                removePersonFromCalendar(base_dir,
                                         chooserNickname,
                                         domain,
                                         optionsNickname,
                                         optionsDomainFull)
            usersPathStr = \
                usersPath + '/' + self.server.defaultTimeline + \
                '?page=' + str(pageNumber)
            self._redirect_headers(usersPathStr, cookie,
                                   callingDomain)
            self.server.POSTbusy = False
            return

        # person options screen, on notify checkbox
        # See htmlPersonOptions
        if '&submitNotifyOnPost=' in optionsConfirmParams:
            notify = None
            if 'notifyOnPost=' in optionsConfirmParams:
                notify = optionsConfirmParams.split('notifyOnPost=')[1]
                if '&' in notify:
                    notify = notify.split('&')[0]
            if notify == 'on':
                addNotifyOnPost(base_dir,
                                chooserNickname,
                                domain,
                                optionsNickname,
                                optionsDomainFull)
            else:
                removeNotifyOnPost(base_dir,
                                   chooserNickname,
                                   domain,
                                   optionsNickname,
                                   optionsDomainFull)
            usersPathStr = \
                usersPath + '/' + self.server.defaultTimeline + \
                '?page=' + str(pageNumber)
            self._redirect_headers(usersPathStr, cookie,
                                   callingDomain)
            self.server.POSTbusy = False
            return

        # person options screen, permission to post to newswire
        # See htmlPersonOptions
        if '&submitPostToNews=' in optionsConfirmParams:
            adminNickname = getConfigParam(self.server.base_dir, 'admin')
            if (chooserNickname != optionsNickname and
                (chooserNickname == adminNickname or
                 (isModerator(self.server.base_dir, chooserNickname) and
                  not isModerator(self.server.base_dir, optionsNickname)))):
                postsToNews = None
                if 'postsToNews=' in optionsConfirmParams:
                    postsToNews = optionsConfirmParams.split('postsToNews=')[1]
                    if '&' in postsToNews:
                        postsToNews = postsToNews.split('&')[0]
                accountDir = acctDir(self.server.base_dir,
                                     optionsNickname, optionsDomain)
                newswireBlockedFilename = accountDir + '/.nonewswire'
                if postsToNews == 'on':
                    if os.path.isfile(newswireBlockedFilename):
                        try:
                            os.remove(newswireBlockedFilename)
                        except OSError:
                            print('EX: _personOptions unable to delete ' +
                                  newswireBlockedFilename)
                        refreshNewswire(self.server.base_dir)
                else:
                    if os.path.isdir(accountDir):
                        nwFilename = newswireBlockedFilename
                        nwWritten = False
                        try:
                            with open(nwFilename, 'w+') as noNewswireFile:
                                noNewswireFile.write('\n')
                                nwWritten = True
                        except OSError as ex:
                            print('EX: unable to write ' + nwFilename +
                                  ' ' + str(ex))
                        if nwWritten:
                            refreshNewswire(self.server.base_dir)
            usersPathStr = \
                usersPath + '/' + self.server.defaultTimeline + \
                '?page=' + str(pageNumber)
            self._redirect_headers(usersPathStr, cookie,
                                   callingDomain)
            self.server.POSTbusy = False
            return

        # person options screen, permission to post to featured articles
        # See htmlPersonOptions
        if '&submitPostToFeatures=' in optionsConfirmParams:
            adminNickname = getConfigParam(self.server.base_dir, 'admin')
            if (chooserNickname != optionsNickname and
                (chooserNickname == adminNickname or
                 (isModerator(self.server.base_dir, chooserNickname) and
                  not isModerator(self.server.base_dir, optionsNickname)))):
                postsToFeatures = None
                if 'postsToFeatures=' in optionsConfirmParams:
                    postsToFeatures = \
                        optionsConfirmParams.split('postsToFeatures=')[1]
                    if '&' in postsToFeatures:
                        postsToFeatures = postsToFeatures.split('&')[0]
                accountDir = acctDir(self.server.base_dir,
                                     optionsNickname, optionsDomain)
                featuresBlockedFilename = accountDir + '/.nofeatures'
                if postsToFeatures == 'on':
                    if os.path.isfile(featuresBlockedFilename):
                        try:
                            os.remove(featuresBlockedFilename)
                        except OSError:
                            print('EX: _personOptions unable to delete ' +
                                  featuresBlockedFilename)
                        refreshNewswire(self.server.base_dir)
                else:
                    if os.path.isdir(accountDir):
                        featFilename = featuresBlockedFilename
                        featWritten = False
                        try:
                            with open(featFilename, 'w+') as noFeaturesFile:
                                noFeaturesFile.write('\n')
                                featWritten = True
                        except OSError as ex:
                            print('EX: unable to write ' + featFilename +
                                  ' ' + str(ex))
                        if featWritten:
                            refreshNewswire(self.server.base_dir)
            usersPathStr = \
                usersPath + '/' + self.server.defaultTimeline + \
                '?page=' + str(pageNumber)
            self._redirect_headers(usersPathStr, cookie,
                                   callingDomain)
            self.server.POSTbusy = False
            return

        # person options screen, permission to post to newswire
        # See htmlPersonOptions
        if '&submitModNewsPosts=' in optionsConfirmParams:
            adminNickname = getConfigParam(self.server.base_dir, 'admin')
            if (chooserNickname != optionsNickname and
                (chooserNickname == adminNickname or
                 (isModerator(self.server.base_dir, chooserNickname) and
                  not isModerator(self.server.base_dir, optionsNickname)))):
                modPostsToNews = None
                if 'modNewsPosts=' in optionsConfirmParams:
                    modPostsToNews = \
                        optionsConfirmParams.split('modNewsPosts=')[1]
                    if '&' in modPostsToNews:
                        modPostsToNews = modPostsToNews.split('&')[0]
                accountDir = acctDir(self.server.base_dir,
                                     optionsNickname, optionsDomain)
                newswireModFilename = accountDir + '/.newswiremoderated'
                if modPostsToNews != 'on':
                    if os.path.isfile(newswireModFilename):
                        try:
                            os.remove(newswireModFilename)
                        except OSError:
                            print('EX: _personOptions unable to delete ' +
                                  newswireModFilename)
                else:
                    if os.path.isdir(accountDir):
                        nwFilename = newswireModFilename
                        try:
                            with open(nwFilename, 'w+') as modNewswireFile:
                                modNewswireFile.write('\n')
                        except OSError:
                            print('EX: unable to write ' + nwFilename)
            usersPathStr = \
                usersPath + '/' + self.server.defaultTimeline + \
                '?page=' + str(pageNumber)
            self._redirect_headers(usersPathStr, cookie,
                                   callingDomain)
            self.server.POSTbusy = False
            return

        # person options screen, block button
        # See htmlPersonOptions
        if '&submitBlock=' in optionsConfirmParams:
            print('Adding block by ' + chooserNickname +
                  ' of ' + optionsActor)
            if addBlock(base_dir, chooserNickname,
                        domain,
                        optionsNickname, optionsDomainFull):
                # send block activity
                self._sendBlock(http_prefix,
                                chooserNickname, domainFull,
                                optionsNickname, optionsDomainFull)

        # person options screen, unblock button
        # See htmlPersonOptions
        if '&submitUnblock=' in optionsConfirmParams:
            if debug:
                print('Unblocking ' + optionsActor)
            msg = \
                htmlConfirmUnblock(self.server.cssCache,
                                   self.server.translate,
                                   base_dir,
                                   usersPath,
                                   optionsActor,
                                   optionsAvatarUrl).encode('utf-8')
            msglen = len(msg)
            self._set_headers('text/html', msglen,
                              cookie, callingDomain, False)
            self._write(msg)
            self.server.POSTbusy = False
            return

        # person options screen, follow button
        # See htmlPersonOptions followStr
        if '&submitFollow=' in optionsConfirmParams or \
           '&submitJoin=' in optionsConfirmParams:
            if debug:
                print('Following ' + optionsActor)
            msg = \
                htmlConfirmFollow(self.server.cssCache,
                                  self.server.translate,
                                  base_dir,
                                  usersPath,
                                  optionsActor,
                                  optionsAvatarUrl).encode('utf-8')
            msglen = len(msg)
            self._set_headers('text/html', msglen,
                              cookie, callingDomain, False)
            self._write(msg)
            self.server.POSTbusy = False
            return

        # person options screen, unfollow button
        # See htmlPersonOptions followStr
        if '&submitUnfollow=' in optionsConfirmParams or \
           '&submitLeave=' in optionsConfirmParams:
            print('Unfollowing ' + optionsActor)
            msg = \
                htmlConfirmUnfollow(self.server.cssCache,
                                    self.server.translate,
                                    base_dir,
                                    usersPath,
                                    optionsActor,
                                    optionsAvatarUrl).encode('utf-8')
            msglen = len(msg)
            self._set_headers('text/html', msglen,
                              cookie, callingDomain, False)
            self._write(msg)
            self.server.POSTbusy = False
            return

        # person options screen, DM button
        # See htmlPersonOptions
        if '&submitDM=' in optionsConfirmParams:
            if debug:
                print('Sending DM to ' + optionsActor)
            reportPath = path.replace('/personoptions', '') + '/newdm'

            accessKeys = self.server.accessKeys
            if '/users/' in path:
                nickname = path.split('/users/')[1]
                if '/' in nickname:
                    nickname = nickname.split('/')[0]
                if self.server.keyShortcuts.get(nickname):
                    accessKeys = self.server.keyShortcuts[nickname]

            customSubmitText = getConfigParam(base_dir, 'customSubmitText')
            conversationId = None
            msg = htmlNewPost(self.server.cssCache,
                              False, self.server.translate,
                              base_dir,
                              http_prefix,
                              reportPath, None,
                              [optionsActor], None, None,
                              pageNumber, '',
                              chooserNickname,
                              domain,
                              domainFull,
                              self.server.defaultTimeline,
                              self.server.newswire,
                              self.server.themeName,
                              True, accessKeys,
                              customSubmitText,
                              conversationId,
                              self.server.recentPostsCache,
                              self.server.max_recent_posts,
                              self.server.session,
                              self.server.cachedWebfingers,
                              self.server.personCache,
                              self.server.port,
                              None,
                              self.server.project_version,
                              self.server.yt_replace_domain,
                              self.server.twitter_replacement_domain,
                              self.server.show_published_date_only,
                              self.server.peertubeInstances,
                              self.server.allow_local_network_access,
                              self.server.systemLanguage,
                              self.server.max_like_count,
                              self.server.signingPrivateKeyPem,
                              self.server.CWlists,
                              self.server.lists_enabled,
                              self.server.defaultTimeline).encode('utf-8')
            msglen = len(msg)
            self._set_headers('text/html', msglen,
                              cookie, callingDomain, False)
            self._write(msg)
            self.server.POSTbusy = False
            return

        # person options screen, Info button
        # See htmlPersonOptions
        if '&submitPersonInfo=' in optionsConfirmParams:
            if isModerator(self.server.base_dir, chooserNickname):
                if debug:
                    print('Showing info for ' + optionsActor)
                signingPrivateKeyPem = self.server.signingPrivateKeyPem
                msg = \
                    htmlAccountInfo(self.server.cssCache,
                                    self.server.translate,
                                    base_dir,
                                    http_prefix,
                                    chooserNickname,
                                    domain,
                                    self.server.port,
                                    optionsActor,
                                    self.server.debug,
                                    self.server.systemLanguage,
                                    signingPrivateKeyPem).encode('utf-8')
                msglen = len(msg)
                self._set_headers('text/html', msglen,
                                  cookie, callingDomain, False)
                self._write(msg)
                self.server.POSTbusy = False
                return
            else:
                self._404()
                return

        # person options screen, snooze button
        # See htmlPersonOptions
        if '&submitSnooze=' in optionsConfirmParams:
            usersPath = path.split('/personoptions')[0]
            thisActor = http_prefix + '://' + domainFull + usersPath
            if debug:
                print('Snoozing ' + optionsActor + ' ' + thisActor)
            if '/users/' in thisActor:
                nickname = thisActor.split('/users/')[1]
                personSnooze(base_dir, nickname,
                             domain, optionsActor)
                if callingDomain.endswith('.onion') and onion_domain:
                    thisActor = 'http://' + onion_domain + usersPath
                elif (callingDomain.endswith('.i2p') and i2p_domain):
                    thisActor = 'http://' + i2p_domain + usersPath
                actorPathStr = \
                    thisActor + '/' + self.server.defaultTimeline + \
                    '?page=' + str(pageNumber)
                self._redirect_headers(actorPathStr, cookie,
                                       callingDomain)
                self.server.POSTbusy = False
                return

        # person options screen, unsnooze button
        # See htmlPersonOptions
        if '&submitUnSnooze=' in optionsConfirmParams:
            usersPath = path.split('/personoptions')[0]
            thisActor = http_prefix + '://' + domainFull + usersPath
            if debug:
                print('Unsnoozing ' + optionsActor + ' ' + thisActor)
            if '/users/' in thisActor:
                nickname = thisActor.split('/users/')[1]
                personUnsnooze(base_dir, nickname,
                               domain, optionsActor)
                if callingDomain.endswith('.onion') and onion_domain:
                    thisActor = 'http://' + onion_domain + usersPath
                elif (callingDomain.endswith('.i2p') and i2p_domain):
                    thisActor = 'http://' + i2p_domain + usersPath
                actorPathStr = \
                    thisActor + '/' + self.server.defaultTimeline + \
                    '?page=' + str(pageNumber)
                self._redirect_headers(actorPathStr, cookie,
                                       callingDomain)
                self.server.POSTbusy = False
                return

        # person options screen, report button
        # See htmlPersonOptions
        if '&submitReport=' in optionsConfirmParams:
            if debug:
                print('Reporting ' + optionsActor)
            reportPath = \
                path.replace('/personoptions', '') + '/newreport'

            accessKeys = self.server.accessKeys
            if '/users/' in path:
                nickname = path.split('/users/')[1]
                if '/' in nickname:
                    nickname = nickname.split('/')[0]
                if self.server.keyShortcuts.get(nickname):
                    accessKeys = self.server.keyShortcuts[nickname]

            customSubmitText = getConfigParam(base_dir, 'customSubmitText')
            conversationId = None
            msg = htmlNewPost(self.server.cssCache,
                              False, self.server.translate,
                              base_dir,
                              http_prefix,
                              reportPath, None, [],
                              None, postUrl, pageNumber, '',
                              chooserNickname,
                              domain,
                              domainFull,
                              self.server.defaultTimeline,
                              self.server.newswire,
                              self.server.themeName,
                              True, accessKeys,
                              customSubmitText,
                              conversationId,
                              self.server.recentPostsCache,
                              self.server.max_recent_posts,
                              self.server.session,
                              self.server.cachedWebfingers,
                              self.server.personCache,
                              self.server.port,
                              None,
                              self.server.project_version,
                              self.server.yt_replace_domain,
                              self.server.twitter_replacement_domain,
                              self.server.show_published_date_only,
                              self.server.peertubeInstances,
                              self.server.allow_local_network_access,
                              self.server.systemLanguage,
                              self.server.max_like_count,
                              self.server.signingPrivateKeyPem,
                              self.server.CWlists,
                              self.server.lists_enabled,
                              self.server.defaultTimeline).encode('utf-8')
            msglen = len(msg)
            self._set_headers('text/html', msglen,
                              cookie, callingDomain, False)
            self._write(msg)
            self.server.POSTbusy = False
            return

        # redirect back from person options screen
        if callingDomain.endswith('.onion') and onion_domain:
            originPathStr = 'http://' + onion_domain + usersPath
        elif callingDomain.endswith('.i2p') and i2p_domain:
            originPathStr = 'http://' + i2p_domain + usersPath
        self._redirect_headers(originPathStr, cookie, callingDomain)
        self.server.POSTbusy = False
        return

    def _unfollowConfirm(self, callingDomain: str, cookie: str,
                         authorized: bool, path: str,
                         base_dir: str, http_prefix: str,
                         domain: str, domainFull: str, port: int,
                         onion_domain: str, i2p_domain: str,
                         debug: bool) -> None:
        """Confirm to unfollow
        """
        usersPath = path.split('/unfollowconfirm')[0]
        originPathStr = http_prefix + '://' + domainFull + usersPath
        followerNickname = getNicknameFromActor(originPathStr)

        length = int(self.headers['Content-length'])

        try:
            followConfirmParams = self.rfile.read(length).decode('utf-8')
        except SocketError as ex:
            if ex.errno == errno.ECONNRESET:
                print('WARN: POST followConfirmParams ' +
                      'connection was reset')
            else:
                print('WARN: POST followConfirmParams socket error')
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy = False
            return
        except ValueError as ex:
            print('ERROR: POST followConfirmParams rfile.read failed, ' +
                  str(ex))
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy = False
            return

        if '&submitYes=' in followConfirmParams:
            followingActor = \
                urllib.parse.unquote_plus(followConfirmParams)
            followingActor = followingActor.split('actor=')[1]
            if '&' in followingActor:
                followingActor = followingActor.split('&')[0]
            followingNickname = getNicknameFromActor(followingActor)
            followingDomain, followingPort = \
                getDomainFromActor(followingActor)
            followingDomainFull = getFullDomain(followingDomain, followingPort)
            if followerNickname == followingNickname and \
               followingDomain == domain and \
               followingPort == port:
                if debug:
                    print('You cannot unfollow yourself!')
            else:
                if debug:
                    print(followerNickname + ' stops following ' +
                          followingActor)
                followActor = \
                    localActorUrl(http_prefix, followerNickname, domainFull)
                statusNumber, published = getStatusNumber()
                followId = followActor + '/statuses/' + str(statusNumber)
                unfollowJson = {
                    '@context': 'https://www.w3.org/ns/activitystreams',
                    'id': followId + '/undo',
                    'type': 'Undo',
                    'actor': followActor,
                    'object': {
                        'id': followId,
                        'type': 'Follow',
                        'actor': followActor,
                        'object': followingActor
                    }
                }
                pathUsersSection = path.split('/users/')[1]
                self.postToNickname = pathUsersSection.split('/')[0]
                groupAccount = hasGroupType(self.server.base_dir,
                                            followingActor,
                                            self.server.personCache)
                unfollowAccount(self.server.base_dir, self.postToNickname,
                                self.server.domain,
                                followingNickname, followingDomainFull,
                                self.server.debug, groupAccount)
                self._postToOutboxThread(unfollowJson)

        if callingDomain.endswith('.onion') and onion_domain:
            originPathStr = 'http://' + onion_domain + usersPath
        elif (callingDomain.endswith('.i2p') and i2p_domain):
            originPathStr = 'http://' + i2p_domain + usersPath
        self._redirect_headers(originPathStr, cookie, callingDomain)
        self.server.POSTbusy = False

    def _followConfirm(self, callingDomain: str, cookie: str,
                       authorized: bool, path: str,
                       base_dir: str, http_prefix: str,
                       domain: str, domainFull: str, port: int,
                       onion_domain: str, i2p_domain: str,
                       debug: bool) -> None:
        """Confirm to follow
        """
        usersPath = path.split('/followconfirm')[0]
        originPathStr = http_prefix + '://' + domainFull + usersPath
        followerNickname = getNicknameFromActor(originPathStr)

        length = int(self.headers['Content-length'])

        try:
            followConfirmParams = self.rfile.read(length).decode('utf-8')
        except SocketError as ex:
            if ex.errno == errno.ECONNRESET:
                print('WARN: POST followConfirmParams ' +
                      'connection was reset')
            else:
                print('WARN: POST followConfirmParams socket error')
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy = False
            return
        except ValueError as ex:
            print('ERROR: POST followConfirmParams rfile.read failed, ' +
                  str(ex))
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy = False
            return

        if '&submitView=' in followConfirmParams:
            followingActor = \
                urllib.parse.unquote_plus(followConfirmParams)
            followingActor = followingActor.split('actor=')[1]
            if '&' in followingActor:
                followingActor = followingActor.split('&')[0]
            self._redirect_headers(followingActor, cookie, callingDomain)
            self.server.POSTbusy = False
            return

        if '&submitYes=' in followConfirmParams:
            followingActor = \
                urllib.parse.unquote_plus(followConfirmParams)
            followingActor = followingActor.split('actor=')[1]
            if '&' in followingActor:
                followingActor = followingActor.split('&')[0]
            followingNickname = getNicknameFromActor(followingActor)
            followingDomain, followingPort = \
                getDomainFromActor(followingActor)
            if followerNickname == followingNickname and \
               followingDomain == domain and \
               followingPort == port:
                if debug:
                    print('You cannot follow yourself!')
            elif (followingNickname == 'news' and
                  followingDomain == domain and
                  followingPort == port):
                if debug:
                    print('You cannot follow the news actor')
            else:
                print('Sending follow request from ' +
                      followerNickname + ' to ' + followingActor)
                if not self.server.signingPrivateKeyPem:
                    print('Sending follow request with no signing key')
                sendFollowRequest(self.server.session,
                                  base_dir, followerNickname,
                                  domain, port,
                                  http_prefix,
                                  followingNickname,
                                  followingDomain,
                                  followingActor,
                                  followingPort, http_prefix,
                                  False, self.server.federationList,
                                  self.server.sendThreads,
                                  self.server.postLog,
                                  self.server.cachedWebfingers,
                                  self.server.personCache, debug,
                                  self.server.project_version,
                                  self.server.signingPrivateKeyPem)
        if callingDomain.endswith('.onion') and onion_domain:
            originPathStr = 'http://' + onion_domain + usersPath
        elif (callingDomain.endswith('.i2p') and i2p_domain):
            originPathStr = 'http://' + i2p_domain + usersPath
        self._redirect_headers(originPathStr, cookie, callingDomain)
        self.server.POSTbusy = False

    def _blockConfirm(self, callingDomain: str, cookie: str,
                      authorized: bool, path: str,
                      base_dir: str, http_prefix: str,
                      domain: str, domainFull: str, port: int,
                      onion_domain: str, i2p_domain: str,
                      debug: bool) -> None:
        """Confirms a block
        """
        usersPath = path.split('/blockconfirm')[0]
        originPathStr = http_prefix + '://' + domainFull + usersPath
        blockerNickname = getNicknameFromActor(originPathStr)
        if not blockerNickname:
            if callingDomain.endswith('.onion') and onion_domain:
                originPathStr = 'http://' + onion_domain + usersPath
            elif (callingDomain.endswith('.i2p') and i2p_domain):
                originPathStr = 'http://' + i2p_domain + usersPath
            print('WARN: unable to find nickname in ' + originPathStr)
            self._redirect_headers(originPathStr,
                                   cookie, callingDomain)
            self.server.POSTbusy = False
            return

        length = int(self.headers['Content-length'])

        try:
            blockConfirmParams = self.rfile.read(length).decode('utf-8')
        except SocketError as ex:
            if ex.errno == errno.ECONNRESET:
                print('WARN: POST blockConfirmParams ' +
                      'connection was reset')
            else:
                print('WARN: POST blockConfirmParams socket error')
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy = False
            return
        except ValueError as ex:
            print('ERROR: POST blockConfirmParams rfile.read failed, ' +
                  str(ex))
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy = False
            return

        if '&submitYes=' in blockConfirmParams:
            blockingActor = \
                urllib.parse.unquote_plus(blockConfirmParams)
            blockingActor = blockingActor.split('actor=')[1]
            if '&' in blockingActor:
                blockingActor = blockingActor.split('&')[0]
            blockingNickname = getNicknameFromActor(blockingActor)
            if not blockingNickname:
                if callingDomain.endswith('.onion') and onion_domain:
                    originPathStr = 'http://' + onion_domain + usersPath
                elif (callingDomain.endswith('.i2p') and i2p_domain):
                    originPathStr = 'http://' + i2p_domain + usersPath
                print('WARN: unable to find nickname in ' + blockingActor)
                self._redirect_headers(originPathStr,
                                       cookie, callingDomain)
                self.server.POSTbusy = False
                return
            blockingDomain, blockingPort = \
                getDomainFromActor(blockingActor)
            blockingDomainFull = getFullDomain(blockingDomain, blockingPort)
            if blockerNickname == blockingNickname and \
               blockingDomain == domain and \
               blockingPort == port:
                if debug:
                    print('You cannot block yourself!')
            else:
                print('Adding block by ' + blockerNickname +
                      ' of ' + blockingActor)
                if addBlock(base_dir, blockerNickname,
                            domain,
                            blockingNickname,
                            blockingDomainFull):
                    # send block activity
                    self._sendBlock(http_prefix,
                                    blockerNickname, domainFull,
                                    blockingNickname, blockingDomainFull)
        if callingDomain.endswith('.onion') and onion_domain:
            originPathStr = 'http://' + onion_domain + usersPath
        elif (callingDomain.endswith('.i2p') and i2p_domain):
            originPathStr = 'http://' + i2p_domain + usersPath
        self._redirect_headers(originPathStr, cookie, callingDomain)
        self.server.POSTbusy = False

    def _unblockConfirm(self, callingDomain: str, cookie: str,
                        authorized: bool, path: str,
                        base_dir: str, http_prefix: str,
                        domain: str, domainFull: str, port: int,
                        onion_domain: str, i2p_domain: str,
                        debug: bool) -> None:
        """Confirms a unblock
        """
        usersPath = path.split('/unblockconfirm')[0]
        originPathStr = http_prefix + '://' + domainFull + usersPath
        blockerNickname = getNicknameFromActor(originPathStr)
        if not blockerNickname:
            if callingDomain.endswith('.onion') and onion_domain:
                originPathStr = 'http://' + onion_domain + usersPath
            elif (callingDomain.endswith('.i2p') and i2p_domain):
                originPathStr = 'http://' + i2p_domain + usersPath
            print('WARN: unable to find nickname in ' + originPathStr)
            self._redirect_headers(originPathStr,
                                   cookie, callingDomain)
            self.server.POSTbusy = False
            return

        length = int(self.headers['Content-length'])

        try:
            blockConfirmParams = self.rfile.read(length).decode('utf-8')
        except SocketError as ex:
            if ex.errno == errno.ECONNRESET:
                print('WARN: POST blockConfirmParams ' +
                      'connection was reset')
            else:
                print('WARN: POST blockConfirmParams socket error')
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy = False
            return
        except ValueError as ex:
            print('ERROR: POST blockConfirmParams rfile.read failed, ' +
                  str(ex))
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy = False
            return

        if '&submitYes=' in blockConfirmParams:
            blockingActor = \
                urllib.parse.unquote_plus(blockConfirmParams)
            blockingActor = blockingActor.split('actor=')[1]
            if '&' in blockingActor:
                blockingActor = blockingActor.split('&')[0]
            blockingNickname = getNicknameFromActor(blockingActor)
            if not blockingNickname:
                if callingDomain.endswith('.onion') and onion_domain:
                    originPathStr = 'http://' + onion_domain + usersPath
                elif (callingDomain.endswith('.i2p') and i2p_domain):
                    originPathStr = 'http://' + i2p_domain + usersPath
                print('WARN: unable to find nickname in ' + blockingActor)
                self._redirect_headers(originPathStr,
                                       cookie, callingDomain)
                self.server.POSTbusy = False
                return
            blockingDomain, blockingPort = \
                getDomainFromActor(blockingActor)
            blockingDomainFull = getFullDomain(blockingDomain, blockingPort)
            if blockerNickname == blockingNickname and \
               blockingDomain == domain and \
               blockingPort == port:
                if debug:
                    print('You cannot unblock yourself!')
            else:
                if debug:
                    print(blockerNickname + ' stops blocking ' +
                          blockingActor)
                removeBlock(base_dir,
                            blockerNickname, domain,
                            blockingNickname, blockingDomainFull)
        if callingDomain.endswith('.onion') and onion_domain:
            originPathStr = 'http://' + onion_domain + usersPath
        elif (callingDomain.endswith('.i2p') and i2p_domain):
            originPathStr = 'http://' + i2p_domain + usersPath
        self._redirect_headers(originPathStr,
                               cookie, callingDomain)
        self.server.POSTbusy = False

    def _receiveSearchQuery(self, callingDomain: str, cookie: str,
                            authorized: bool, path: str,
                            base_dir: str, http_prefix: str,
                            domain: str, domainFull: str,
                            port: int, searchForEmoji: bool,
                            onion_domain: str, i2p_domain: str,
                            GETstartTime, GETtimings: {},
                            debug: bool) -> None:
        """Receive a search query
        """
        # get the page number
        pageNumber = 1
        if '/searchhandle?page=' in path:
            pageNumberStr = path.split('/searchhandle?page=')[1]
            if '#' in pageNumberStr:
                pageNumberStr = pageNumberStr.split('#')[0]
            if pageNumberStr.isdigit():
                pageNumber = int(pageNumberStr)
            path = path.split('?page=')[0]

        usersPath = path.replace('/searchhandle', '')
        actorStr = self._getInstanceUrl(callingDomain) + usersPath
        length = int(self.headers['Content-length'])
        try:
            searchParams = self.rfile.read(length).decode('utf-8')
        except SocketError as ex:
            if ex.errno == errno.ECONNRESET:
                print('WARN: POST searchParams connection was reset')
            else:
                print('WARN: POST searchParams socket error')
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy = False
            return
        except ValueError as ex:
            print('ERROR: POST searchParams rfile.read failed, ' + str(ex))
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy = False
            return
        if 'submitBack=' in searchParams:
            # go back on search screen
            self._redirect_headers(actorStr + '/' +
                                   self.server.defaultTimeline,
                                   cookie, callingDomain)
            self.server.POSTbusy = False
            return
        if 'searchtext=' in searchParams:
            searchStr = searchParams.split('searchtext=')[1]
            if '&' in searchStr:
                searchStr = searchStr.split('&')[0]
            searchStr = \
                urllib.parse.unquote_plus(searchStr.strip())
            searchStr = searchStr.lower().strip()
            print('searchStr: ' + searchStr)
            if searchForEmoji:
                searchStr = ':' + searchStr + ':'
            if searchStr.startswith('#'):
                nickname = getNicknameFromActor(actorStr)
                # hashtag search
                hashtagStr = \
                    htmlHashtagSearch(self.server.cssCache,
                                      nickname, domain, port,
                                      self.server.recentPostsCache,
                                      self.server.max_recent_posts,
                                      self.server.translate,
                                      base_dir,
                                      searchStr[1:], 1,
                                      maxPostsInHashtagFeed,
                                      self.server.session,
                                      self.server.cachedWebfingers,
                                      self.server.personCache,
                                      http_prefix,
                                      self.server.project_version,
                                      self.server.yt_replace_domain,
                                      self.server.twitter_replacement_domain,
                                      self.server.show_published_date_only,
                                      self.server.peertubeInstances,
                                      self.server.allow_local_network_access,
                                      self.server.themeName,
                                      self.server.systemLanguage,
                                      self.server.max_like_count,
                                      self.server.signingPrivateKeyPem,
                                      self.server.CWlists,
                                      self.server.lists_enabled)
                if hashtagStr:
                    msg = hashtagStr.encode('utf-8')
                    msglen = len(msg)
                    self._login_headers('text/html',
                                        msglen, callingDomain)
                    self._write(msg)
                    self.server.POSTbusy = False
                    return
            elif (searchStr.startswith('*') or
                  searchStr.endswith(' skill')):
                possibleEndings = (
                    ' skill'
                )
                for possEnding in possibleEndings:
                    if searchStr.endswith(possEnding):
                        searchStr = searchStr.replace(possEnding, '')
                        break
                # skill search
                searchStr = searchStr.replace('*', '').strip()
                skillStr = \
                    htmlSkillsSearch(actorStr,
                                     self.server.cssCache,
                                     self.server.translate,
                                     base_dir,
                                     http_prefix,
                                     searchStr,
                                     self.server.instanceOnlySkillsSearch,
                                     64)
                if skillStr:
                    msg = skillStr.encode('utf-8')
                    msglen = len(msg)
                    self._login_headers('text/html',
                                        msglen, callingDomain)
                    self._write(msg)
                    self.server.POSTbusy = False
                    return
            elif (searchStr.startswith("'") or
                  searchStr.endswith(' history') or
                  searchStr.endswith(' in sent') or
                  searchStr.endswith(' in outbox') or
                  searchStr.endswith(' in outgoing') or
                  searchStr.endswith(' in sent items') or
                  searchStr.endswith(' in sent posts') or
                  searchStr.endswith(' in outgoing posts') or
                  searchStr.endswith(' in my history') or
                  searchStr.endswith(' in my outbox') or
                  searchStr.endswith(' in my posts')):
                possibleEndings = (
                    ' in my posts',
                    ' in my history',
                    ' in my outbox',
                    ' in sent posts',
                    ' in outgoing posts',
                    ' in sent items',
                    ' in history',
                    ' in outbox',
                    ' in outgoing',
                    ' in sent',
                    ' history'
                )
                for possEnding in possibleEndings:
                    if searchStr.endswith(possEnding):
                        searchStr = searchStr.replace(possEnding, '')
                        break
                # your post history search
                nickname = getNicknameFromActor(actorStr)
                searchStr = searchStr.replace("'", '', 1).strip()
                historyStr = \
                    htmlHistorySearch(self.server.cssCache,
                                      self.server.translate,
                                      base_dir,
                                      http_prefix,
                                      nickname,
                                      domain,
                                      searchStr,
                                      maxPostsInFeed,
                                      pageNumber,
                                      self.server.project_version,
                                      self.server.recentPostsCache,
                                      self.server.max_recent_posts,
                                      self.server.session,
                                      self.server.cachedWebfingers,
                                      self.server.personCache,
                                      port,
                                      self.server.yt_replace_domain,
                                      self.server.twitter_replacement_domain,
                                      self.server.show_published_date_only,
                                      self.server.peertubeInstances,
                                      self.server.allow_local_network_access,
                                      self.server.themeName, 'outbox',
                                      self.server.systemLanguage,
                                      self.server.max_like_count,
                                      self.server.signingPrivateKeyPem,
                                      self.server.CWlists,
                                      self.server.lists_enabled)
                if historyStr:
                    msg = historyStr.encode('utf-8')
                    msglen = len(msg)
                    self._login_headers('text/html',
                                        msglen, callingDomain)
                    self._write(msg)
                    self.server.POSTbusy = False
                    return
            elif (searchStr.startswith('-') or
                  searchStr.endswith(' in my saved items') or
                  searchStr.endswith(' in my saved posts') or
                  searchStr.endswith(' in my bookmarks') or
                  searchStr.endswith(' in my saved') or
                  searchStr.endswith(' in my saves') or
                  searchStr.endswith(' in saved posts') or
                  searchStr.endswith(' in saved items') or
                  searchStr.endswith(' in bookmarks') or
                  searchStr.endswith(' in saved') or
                  searchStr.endswith(' in saves') or
                  searchStr.endswith(' bookmark')):
                possibleEndings = (
                    ' in my bookmarks'
                    ' in my saved posts'
                    ' in my saved items'
                    ' in my saved'
                    ' in my saves'
                    ' in saved posts'
                    ' in saved items'
                    ' in saved'
                    ' in saves'
                    ' in bookmarks'
                    ' bookmark'
                )
                for possEnding in possibleEndings:
                    if searchStr.endswith(possEnding):
                        searchStr = searchStr.replace(possEnding, '')
                        break
                # bookmark search
                nickname = getNicknameFromActor(actorStr)
                searchStr = searchStr.replace('-', '', 1).strip()
                bookmarksStr = \
                    htmlHistorySearch(self.server.cssCache,
                                      self.server.translate,
                                      base_dir,
                                      http_prefix,
                                      nickname,
                                      domain,
                                      searchStr,
                                      maxPostsInFeed,
                                      pageNumber,
                                      self.server.project_version,
                                      self.server.recentPostsCache,
                                      self.server.max_recent_posts,
                                      self.server.session,
                                      self.server.cachedWebfingers,
                                      self.server.personCache,
                                      port,
                                      self.server.yt_replace_domain,
                                      self.server.twitter_replacement_domain,
                                      self.server.show_published_date_only,
                                      self.server.peertubeInstances,
                                      self.server.allow_local_network_access,
                                      self.server.themeName, 'bookmarks',
                                      self.server.systemLanguage,
                                      self.server.max_like_count,
                                      self.server.signingPrivateKeyPem,
                                      self.server.CWlists,
                                      self.server.lists_enabled)
                if bookmarksStr:
                    msg = bookmarksStr.encode('utf-8')
                    msglen = len(msg)
                    self._login_headers('text/html',
                                        msglen, callingDomain)
                    self._write(msg)
                    self.server.POSTbusy = False
                    return
            elif ('@' in searchStr or
                  ('://' in searchStr and
                   hasUsersPath(searchStr))):
                if searchStr.endswith(':') or \
                   searchStr.endswith(';') or \
                   searchStr.endswith('.'):
                    actorStr = self._getInstanceUrl(callingDomain) + usersPath
                    self._redirect_headers(actorStr + '/search',
                                           cookie, callingDomain)
                    self.server.POSTbusy = False
                    return
                # profile search
                nickname = getNicknameFromActor(actorStr)
                if not self._establishSession("handle search"):
                    self.server.POSTbusy = False
                    return
                profilePathStr = path.replace('/searchhandle', '')

                # are we already following the searched for handle?
                if isFollowingActor(base_dir, nickname, domain, searchStr):
                    if not hasUsersPath(searchStr):
                        searchNickname = getNicknameFromActor(searchStr)
                        searchDomain, searchPort = \
                            getDomainFromActor(searchStr)
                        searchDomainFull = \
                            getFullDomain(searchDomain, searchPort)
                        actor = \
                            localActorUrl(http_prefix, searchNickname,
                                          searchDomainFull)
                    else:
                        actor = searchStr
                    avatarUrl = \
                        getAvatarImageUrl(self.server.session,
                                          base_dir, http_prefix,
                                          actor,
                                          self.server.personCache,
                                          None, True,
                                          self.server.signingPrivateKeyPem)
                    profilePathStr += \
                        '?options=' + actor + ';1;' + avatarUrl

                    self._showPersonOptions(callingDomain, profilePathStr,
                                            base_dir, http_prefix,
                                            domain, domainFull,
                                            GETstartTime,
                                            onion_domain, i2p_domain,
                                            cookie, debug, authorized)
                    return
                else:
                    show_published_date_only = \
                        self.server.show_published_date_only
                    allow_local_network_access = \
                        self.server.allow_local_network_access

                    accessKeys = self.server.accessKeys
                    if self.server.keyShortcuts.get(nickname):
                        accessKeys = self.server.keyShortcuts[nickname]

                    signingPrivateKeyPem = \
                        self.server.signingPrivateKeyPem
                    twitter_replacement_domain = \
                        self.server.twitter_replacement_domain
                    profileStr = \
                        htmlProfileAfterSearch(self.server.cssCache,
                                               self.server.recentPostsCache,
                                               self.server.max_recent_posts,
                                               self.server.translate,
                                               base_dir,
                                               profilePathStr,
                                               http_prefix,
                                               nickname,
                                               domain,
                                               port,
                                               searchStr,
                                               self.server.session,
                                               self.server.cachedWebfingers,
                                               self.server.personCache,
                                               self.server.debug,
                                               self.server.project_version,
                                               self.server.yt_replace_domain,
                                               twitter_replacement_domain,
                                               show_published_date_only,
                                               self.server.defaultTimeline,
                                               self.server.peertubeInstances,
                                               allow_local_network_access,
                                               self.server.themeName,
                                               accessKeys,
                                               self.server.systemLanguage,
                                               self.server.max_like_count,
                                               signingPrivateKeyPem,
                                               self.server.CWlists,
                                               self.server.lists_enabled)
                if profileStr:
                    msg = profileStr.encode('utf-8')
                    msglen = len(msg)
                    self._login_headers('text/html',
                                        msglen, callingDomain)
                    self._write(msg)
                    self.server.POSTbusy = False
                    return
                else:
                    actorStr = self._getInstanceUrl(callingDomain) + usersPath
                    self._redirect_headers(actorStr + '/search',
                                           cookie, callingDomain)
                    self.server.POSTbusy = False
                    return
            elif (searchStr.startswith(':') or
                  searchStr.endswith(' emoji')):
                # eg. "cat emoji"
                if searchStr.endswith(' emoji'):
                    searchStr = \
                        searchStr.replace(' emoji', '')
                # emoji search
                emojiStr = \
                    htmlSearchEmoji(self.server.cssCache,
                                    self.server.translate,
                                    base_dir,
                                    http_prefix,
                                    searchStr)
                if emojiStr:
                    msg = emojiStr.encode('utf-8')
                    msglen = len(msg)
                    self._login_headers('text/html',
                                        msglen, callingDomain)
                    self._write(msg)
                    self.server.POSTbusy = False
                    return
            elif searchStr.startswith('.'):
                # wanted items search
                shared_items_federated_domains = \
                    self.server.shared_items_federated_domains
                wantedItemsStr = \
                    htmlSearchSharedItems(self.server.cssCache,
                                          self.server.translate,
                                          base_dir,
                                          searchStr[1:], pageNumber,
                                          maxPostsInFeed,
                                          http_prefix,
                                          domainFull,
                                          actorStr, callingDomain,
                                          shared_items_federated_domains,
                                          'wanted')
                if wantedItemsStr:
                    msg = wantedItemsStr.encode('utf-8')
                    msglen = len(msg)
                    self._login_headers('text/html',
                                        msglen, callingDomain)
                    self._write(msg)
                    self.server.POSTbusy = False
                    return
            else:
                # shared items search
                shared_items_federated_domains = \
                    self.server.shared_items_federated_domains
                sharedItemsStr = \
                    htmlSearchSharedItems(self.server.cssCache,
                                          self.server.translate,
                                          base_dir,
                                          searchStr, pageNumber,
                                          maxPostsInFeed,
                                          http_prefix,
                                          domainFull,
                                          actorStr, callingDomain,
                                          shared_items_federated_domains,
                                          'shares')
                if sharedItemsStr:
                    msg = sharedItemsStr.encode('utf-8')
                    msglen = len(msg)
                    self._login_headers('text/html',
                                        msglen, callingDomain)
                    self._write(msg)
                    self.server.POSTbusy = False
                    return
        actorStr = self._getInstanceUrl(callingDomain) + usersPath
        self._redirect_headers(actorStr + '/' +
                               self.server.defaultTimeline,
                               cookie, callingDomain)
        self.server.POSTbusy = False

    def _receiveVote(self, callingDomain: str, cookie: str,
                     authorized: bool, path: str,
                     base_dir: str, http_prefix: str,
                     domain: str, domainFull: str,
                     onion_domain: str, i2p_domain: str,
                     debug: bool) -> None:
        """Receive a vote via POST
        """
        pageNumber = 1
        if '?page=' in path:
            pageNumberStr = path.split('?page=')[1]
            if '#' in pageNumberStr:
                pageNumberStr = pageNumberStr.split('#')[0]
            if pageNumberStr.isdigit():
                pageNumber = int(pageNumberStr)
            path = path.split('?page=')[0]

        # the actor who votes
        usersPath = path.replace('/question', '')
        actor = http_prefix + '://' + domainFull + usersPath
        nickname = getNicknameFromActor(actor)
        if not nickname:
            if callingDomain.endswith('.onion') and onion_domain:
                actor = 'http://' + onion_domain + usersPath
            elif (callingDomain.endswith('.i2p') and i2p_domain):
                actor = 'http://' + i2p_domain + usersPath
            actorPathStr = \
                actor + '/' + self.server.defaultTimeline + \
                '?page=' + str(pageNumber)
            self._redirect_headers(actorPathStr,
                                   cookie, callingDomain)
            self.server.POSTbusy = False
            return

        # get the parameters
        length = int(self.headers['Content-length'])

        try:
            questionParams = self.rfile.read(length).decode('utf-8')
        except SocketError as ex:
            if ex.errno == errno.ECONNRESET:
                print('WARN: POST questionParams connection was reset')
            else:
                print('WARN: POST questionParams socket error')
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy = False
            return
        except ValueError as ex:
            print('ERROR: POST questionParams rfile.read failed, ' + str(ex))
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy = False
            return

        questionParams = questionParams.replace('+', ' ')
        questionParams = questionParams.replace('%3F', '')
        questionParams = \
            urllib.parse.unquote_plus(questionParams.strip())

        # post being voted on
        messageId = None
        if 'messageId=' in questionParams:
            messageId = questionParams.split('messageId=')[1]
            if '&' in messageId:
                messageId = messageId.split('&')[0]

        answer = None
        if 'answer=' in questionParams:
            answer = questionParams.split('answer=')[1]
            if '&' in answer:
                answer = answer.split('&')[0]

        self._sendReplyToQuestion(nickname, messageId, answer)
        if callingDomain.endswith('.onion') and onion_domain:
            actor = 'http://' + onion_domain + usersPath
        elif (callingDomain.endswith('.i2p') and i2p_domain):
            actor = 'http://' + i2p_domain + usersPath
        actorPathStr = \
            actor + '/' + self.server.defaultTimeline + \
            '?page=' + str(pageNumber)
        self._redirect_headers(actorPathStr, cookie,
                               callingDomain)
        self.server.POSTbusy = False
        return

    def _receiveImage(self, length: int,
                      callingDomain: str, cookie: str,
                      authorized: bool, path: str,
                      base_dir: str, http_prefix: str,
                      domain: str, domainFull: str,
                      onion_domain: str, i2p_domain: str,
                      debug: bool) -> None:
        """Receives an image via POST
        """
        if not self.outboxAuthenticated:
            if debug:
                print('DEBUG: unauthenticated attempt to ' +
                      'post image to outbox')
            self.send_response(403)
            self.end_headers()
            self.server.POSTbusy = False
            return
        pathUsersSection = path.split('/users/')[1]
        if '/' not in pathUsersSection:
            self._404()
            self.server.POSTbusy = False
            return
        self.postFromNickname = pathUsersSection.split('/')[0]
        accountsDir = acctDir(base_dir, self.postFromNickname, domain)
        if not os.path.isdir(accountsDir):
            self._404()
            self.server.POSTbusy = False
            return

        try:
            mediaBytes = self.rfile.read(length)
        except SocketError as ex:
            if ex.errno == errno.ECONNRESET:
                print('WARN: POST mediaBytes ' +
                      'connection reset by peer')
            else:
                print('WARN: POST mediaBytes socket error')
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy = False
            return
        except ValueError as ex:
            print('ERROR: POST mediaBytes rfile.read failed, ' + str(ex))
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy = False
            return

        mediaFilenameBase = accountsDir + '/upload'
        mediaFilename = \
            mediaFilenameBase + '.' + \
            getImageExtensionFromMimeType(self.headers['Content-type'])
        try:
            with open(mediaFilename, 'wb') as avFile:
                avFile.write(mediaBytes)
        except OSError:
            print('EX: unable to write ' + mediaFilename)
        if debug:
            print('DEBUG: image saved to ' + mediaFilename)
        self.send_response(201)
        self.end_headers()
        self.server.POSTbusy = False

    def _removeShare(self, callingDomain: str, cookie: str,
                     authorized: bool, path: str,
                     base_dir: str, http_prefix: str,
                     domain: str, domainFull: str,
                     onion_domain: str, i2p_domain: str,
                     debug: bool) -> None:
        """Removes a shared item
        """
        usersPath = path.split('/rmshare')[0]
        originPathStr = http_prefix + '://' + domainFull + usersPath

        length = int(self.headers['Content-length'])

        try:
            removeShareConfirmParams = \
                self.rfile.read(length).decode('utf-8')
        except SocketError as ex:
            if ex.errno == errno.ECONNRESET:
                print('WARN: POST removeShareConfirmParams ' +
                      'connection was reset')
            else:
                print('WARN: POST removeShareConfirmParams socket error')
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy = False
            return
        except ValueError as ex:
            print('ERROR: POST removeShareConfirmParams rfile.read failed, ' +
                  str(ex))
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy = False
            return

        if '&submitYes=' in removeShareConfirmParams and authorized:
            removeShareConfirmParams = \
                removeShareConfirmParams.replace('+', ' ').strip()
            removeShareConfirmParams = \
                urllib.parse.unquote_plus(removeShareConfirmParams)
            shareActor = removeShareConfirmParams.split('actor=')[1]
            if '&' in shareActor:
                shareActor = shareActor.split('&')[0]
            adminNickname = getConfigParam(base_dir, 'admin')
            adminActor = \
                localActorUrl(http_prefix, adminNickname, domainFull)
            actor = originPathStr
            actorNickname = getNicknameFromActor(actor)
            if actor == shareActor or actor == adminActor or \
               isModerator(base_dir, actorNickname):
                itemID = removeShareConfirmParams.split('itemID=')[1]
                if '&' in itemID:
                    itemID = itemID.split('&')[0]
                shareNickname = getNicknameFromActor(shareActor)
                if shareNickname:
                    shareDomain, sharePort = getDomainFromActor(shareActor)
                    removeSharedItem(base_dir,
                                     shareNickname, shareDomain, itemID,
                                     http_prefix, domainFull, 'shares')

        if callingDomain.endswith('.onion') and onion_domain:
            originPathStr = 'http://' + onion_domain + usersPath
        elif (callingDomain.endswith('.i2p') and i2p_domain):
            originPathStr = 'http://' + i2p_domain + usersPath
        self._redirect_headers(originPathStr + '/tlshares',
                               cookie, callingDomain)
        self.server.POSTbusy = False

    def _removeWanted(self, callingDomain: str, cookie: str,
                      authorized: bool, path: str,
                      base_dir: str, http_prefix: str,
                      domain: str, domainFull: str,
                      onion_domain: str, i2p_domain: str,
                      debug: bool) -> None:
        """Removes a wanted item
        """
        usersPath = path.split('/rmwanted')[0]
        originPathStr = http_prefix + '://' + domainFull + usersPath

        length = int(self.headers['Content-length'])

        try:
            removeShareConfirmParams = \
                self.rfile.read(length).decode('utf-8')
        except SocketError as ex:
            if ex.errno == errno.ECONNRESET:
                print('WARN: POST removeShareConfirmParams ' +
                      'connection was reset')
            else:
                print('WARN: POST removeShareConfirmParams socket error')
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy = False
            return
        except ValueError as ex:
            print('ERROR: POST removeShareConfirmParams rfile.read failed, ' +
                  str(ex))
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy = False
            return

        if '&submitYes=' in removeShareConfirmParams and authorized:
            removeShareConfirmParams = \
                removeShareConfirmParams.replace('+', ' ').strip()
            removeShareConfirmParams = \
                urllib.parse.unquote_plus(removeShareConfirmParams)
            shareActor = removeShareConfirmParams.split('actor=')[1]
            if '&' in shareActor:
                shareActor = shareActor.split('&')[0]
            adminNickname = getConfigParam(base_dir, 'admin')
            adminActor = \
                localActorUrl(http_prefix, adminNickname, domainFull)
            actor = originPathStr
            actorNickname = getNicknameFromActor(actor)
            if actor == shareActor or actor == adminActor or \
               isModerator(base_dir, actorNickname):
                itemID = removeShareConfirmParams.split('itemID=')[1]
                if '&' in itemID:
                    itemID = itemID.split('&')[0]
                shareNickname = getNicknameFromActor(shareActor)
                if shareNickname:
                    shareDomain, sharePort = getDomainFromActor(shareActor)
                    removeSharedItem(base_dir,
                                     shareNickname, shareDomain, itemID,
                                     http_prefix, domainFull, 'wanted')

        if callingDomain.endswith('.onion') and onion_domain:
            originPathStr = 'http://' + onion_domain + usersPath
        elif (callingDomain.endswith('.i2p') and i2p_domain):
            originPathStr = 'http://' + i2p_domain + usersPath
        self._redirect_headers(originPathStr + '/tlwanted',
                               cookie, callingDomain)
        self.server.POSTbusy = False

    def _removePost(self, callingDomain: str, cookie: str,
                    authorized: bool, path: str,
                    base_dir: str, http_prefix: str,
                    domain: str, domainFull: str,
                    onion_domain: str, i2p_domain: str,
                    debug: bool) -> None:
        """Endpoint for removing posts after confirmation
        """
        pageNumber = 1
        usersPath = path.split('/rmpost')[0]
        originPathStr = \
            http_prefix + '://' + \
            domainFull + usersPath

        length = int(self.headers['Content-length'])

        try:
            removePostConfirmParams = \
                self.rfile.read(length).decode('utf-8')
        except SocketError as ex:
            if ex.errno == errno.ECONNRESET:
                print('WARN: POST removePostConfirmParams ' +
                      'connection was reset')
            else:
                print('WARN: POST removePostConfirmParams socket error')
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy = False
            return
        except ValueError as ex:
            print('ERROR: POST removePostConfirmParams rfile.read failed, ' +
                  str(ex))
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy = False
            return
        if '&submitYes=' in removePostConfirmParams:
            removePostConfirmParams = \
                urllib.parse.unquote_plus(removePostConfirmParams)
            removeMessageId = \
                removePostConfirmParams.split('messageId=')[1]
            if '&' in removeMessageId:
                removeMessageId = removeMessageId.split('&')[0]
            if 'pageNumber=' in removePostConfirmParams:
                pageNumberStr = \
                    removePostConfirmParams.split('pageNumber=')[1]
                if '&' in pageNumberStr:
                    pageNumberStr = pageNumberStr.split('&')[0]
                if pageNumberStr.isdigit():
                    pageNumber = int(pageNumberStr)
            yearStr = None
            if 'year=' in removePostConfirmParams:
                yearStr = removePostConfirmParams.split('year=')[1]
                if '&' in yearStr:
                    yearStr = yearStr.split('&')[0]
            monthStr = None
            if 'month=' in removePostConfirmParams:
                monthStr = removePostConfirmParams.split('month=')[1]
                if '&' in monthStr:
                    monthStr = monthStr.split('&')[0]
            if '/statuses/' in removeMessageId:
                removePostActor = removeMessageId.split('/statuses/')[0]
            if originPathStr in removePostActor:
                toList = ['https://www.w3.org/ns/activitystreams#Public',
                          removePostActor]
                deleteJson = {
                    "@context": "https://www.w3.org/ns/activitystreams",
                    'actor': removePostActor,
                    'object': removeMessageId,
                    'to': toList,
                    'cc': [removePostActor + '/followers'],
                    'type': 'Delete'
                }
                self.postToNickname = getNicknameFromActor(removePostActor)
                if self.postToNickname:
                    if monthStr and yearStr:
                        if monthStr.isdigit() and yearStr.isdigit():
                            yearInt = int(yearStr)
                            monthInt = int(monthStr)
                            removeCalendarEvent(base_dir,
                                                self.postToNickname,
                                                domain,
                                                yearInt,
                                                monthInt,
                                                removeMessageId)
                    self._postToOutboxThread(deleteJson)
        if callingDomain.endswith('.onion') and onion_domain:
            originPathStr = 'http://' + onion_domain + usersPath
        elif (callingDomain.endswith('.i2p') and i2p_domain):
            originPathStr = 'http://' + i2p_domain + usersPath
        if pageNumber == 1:
            self._redirect_headers(originPathStr + '/outbox', cookie,
                                   callingDomain)
        else:
            pageNumberStr = str(pageNumber)
            actorPathStr = originPathStr + '/outbox?page=' + pageNumberStr
            self._redirect_headers(actorPathStr,
                                   cookie, callingDomain)
        self.server.POSTbusy = False

    def _linksUpdate(self, callingDomain: str, cookie: str,
                     authorized: bool, path: str,
                     base_dir: str, http_prefix: str,
                     domain: str, domainFull: str,
                     onion_domain: str, i2p_domain: str, debug: bool,
                     defaultTimeline: str,
                     allow_local_network_access: bool) -> None:
        """Updates the left links column of the timeline
        """
        usersPath = path.replace('/linksdata', '')
        usersPath = usersPath.replace('/editlinks', '')
        actorStr = self._getInstanceUrl(callingDomain) + usersPath
        if ' boundary=' in self.headers['Content-type']:
            boundary = self.headers['Content-type'].split('boundary=')[1]
            if ';' in boundary:
                boundary = boundary.split(';')[0]

            # get the nickname
            nickname = getNicknameFromActor(actorStr)
            editor = None
            if nickname:
                editor = isEditor(base_dir, nickname)
            if not nickname or not editor:
                if not nickname:
                    print('WARN: nickname not found in ' + actorStr)
                else:
                    print('WARN: nickname is not a moderator' + actorStr)
                self._redirect_headers(actorStr, cookie, callingDomain)
                self.server.POSTbusy = False
                return

            length = int(self.headers['Content-length'])

            # check that the POST isn't too large
            if length > self.server.maxPostLength:
                print('Maximum links data length exceeded ' + str(length))
                self._redirect_headers(actorStr, cookie, callingDomain)
                self.server.POSTbusy = False
                return

            try:
                # read the bytes of the http form POST
                postBytes = self.rfile.read(length)
            except SocketError as ex:
                if ex.errno == errno.ECONNRESET:
                    print('WARN: connection was reset while ' +
                          'reading bytes from http form POST')
                else:
                    print('WARN: error while reading bytes ' +
                          'from http form POST')
                self.send_response(400)
                self.end_headers()
                self.server.POSTbusy = False
                return
            except ValueError as ex:
                print('ERROR: failed to read bytes for POST, ' + str(ex))
                self.send_response(400)
                self.end_headers()
                self.server.POSTbusy = False
                return

            linksFilename = base_dir + '/accounts/links.txt'
            aboutFilename = base_dir + '/accounts/about.md'
            TOSFilename = base_dir + '/accounts/tos.md'

            # extract all of the text fields into a dict
            fields = \
                extractTextFieldsInPOST(postBytes, boundary, debug)

            if fields.get('editedLinks'):
                linksStr = fields['editedLinks']
                if fields.get('newColLink'):
                    if linksStr:
                        if not linksStr.endswith('\n'):
                            linksStr += '\n'
                    linksStr += fields['newColLink'] + '\n'
                try:
                    with open(linksFilename, 'w+') as linksFile:
                        linksFile.write(linksStr)
                except OSError:
                    print('EX: _linksUpdate unable to write ' + linksFilename)
            else:
                if fields.get('newColLink'):
                    # the text area is empty but there is a new link added
                    linksStr = fields['newColLink'] + '\n'
                    try:
                        with open(linksFilename, 'w+') as linksFile:
                            linksFile.write(linksStr)
                    except OSError:
                        print('EX: _linksUpdate unable to write ' +
                              linksFilename)
                else:
                    if os.path.isfile(linksFilename):
                        try:
                            os.remove(linksFilename)
                        except OSError:
                            print('EX: _linksUpdate unable to delete ' +
                                  linksFilename)

            adminNickname = \
                getConfigParam(base_dir, 'admin')
            if nickname == adminNickname:
                if fields.get('editedAbout'):
                    aboutStr = fields['editedAbout']
                    if not dangerousMarkup(aboutStr,
                                           allow_local_network_access):
                        try:
                            with open(aboutFilename, 'w+') as aboutFile:
                                aboutFile.write(aboutStr)
                        except OSError:
                            print('EX: unable to write about ' + aboutFilename)
                else:
                    if os.path.isfile(aboutFilename):
                        try:
                            os.remove(aboutFilename)
                        except OSError:
                            print('EX: _linksUpdate unable to delete ' +
                                  aboutFilename)

                if fields.get('editedTOS'):
                    TOSStr = fields['editedTOS']
                    if not dangerousMarkup(TOSStr,
                                           allow_local_network_access):
                        try:
                            with open(TOSFilename, 'w+') as TOSFile:
                                TOSFile.write(TOSStr)
                        except OSError:
                            print('EX: unable to write TOS ' + TOSFilename)
                else:
                    if os.path.isfile(TOSFilename):
                        try:
                            os.remove(TOSFilename)
                        except OSError:
                            print('EX: _linksUpdate unable to delete ' +
                                  TOSFilename)

        # redirect back to the default timeline
        self._redirect_headers(actorStr + '/' + defaultTimeline,
                               cookie, callingDomain)
        self.server.POSTbusy = False

    def _setHashtagCategory(self, callingDomain: str, cookie: str,
                            authorized: bool, path: str,
                            base_dir: str, http_prefix: str,
                            domain: str, domainFull: str,
                            onion_domain: str, i2p_domain: str, debug: bool,
                            defaultTimeline: str,
                            allow_local_network_access: bool) -> None:
        """On the screen after selecting a hashtag from the swarm, this sets
        the category for that tag
        """
        usersPath = path.replace('/sethashtagcategory', '')
        hashtag = ''
        if '/tags/' not in usersPath:
            # no hashtag is specified within the path
            self._404()
            return
        hashtag = usersPath.split('/tags/')[1].strip()
        hashtag = urllib.parse.unquote_plus(hashtag)
        if not hashtag:
            # no hashtag was given in the path
            self._404()
            return
        hashtagFilename = base_dir + '/tags/' + hashtag + '.txt'
        if not os.path.isfile(hashtagFilename):
            # the hashtag does not exist
            self._404()
            return
        usersPath = usersPath.split('/tags/')[0]
        actorStr = self._getInstanceUrl(callingDomain) + usersPath
        tagScreenStr = actorStr + '/tags/' + hashtag
        if ' boundary=' in self.headers['Content-type']:
            boundary = self.headers['Content-type'].split('boundary=')[1]
            if ';' in boundary:
                boundary = boundary.split(';')[0]

            # get the nickname
            nickname = getNicknameFromActor(actorStr)
            editor = None
            if nickname:
                editor = isEditor(base_dir, nickname)
            if not hashtag or not editor:
                if not nickname:
                    print('WARN: nickname not found in ' + actorStr)
                else:
                    print('WARN: nickname is not a moderator' + actorStr)
                self._redirect_headers(tagScreenStr, cookie, callingDomain)
                self.server.POSTbusy = False
                return

            length = int(self.headers['Content-length'])

            # check that the POST isn't too large
            if length > self.server.maxPostLength:
                print('Maximum links data length exceeded ' + str(length))
                self._redirect_headers(tagScreenStr, cookie, callingDomain)
                self.server.POSTbusy = False
                return

            try:
                # read the bytes of the http form POST
                postBytes = self.rfile.read(length)
            except SocketError as ex:
                if ex.errno == errno.ECONNRESET:
                    print('WARN: connection was reset while ' +
                          'reading bytes from http form POST')
                else:
                    print('WARN: error while reading bytes ' +
                          'from http form POST')
                self.send_response(400)
                self.end_headers()
                self.server.POSTbusy = False
                return
            except ValueError as ex:
                print('ERROR: failed to read bytes for POST, ' + str(ex))
                self.send_response(400)
                self.end_headers()
                self.server.POSTbusy = False
                return

            # extract all of the text fields into a dict
            fields = \
                extractTextFieldsInPOST(postBytes, boundary, debug)

            if fields.get('hashtagCategory'):
                categoryStr = fields['hashtagCategory'].lower()
                if not isBlockedHashtag(base_dir, categoryStr) and \
                   not isFiltered(base_dir, nickname, domain, categoryStr):
                    setHashtagCategory(base_dir, hashtag, categoryStr, False)
            else:
                categoryFilename = base_dir + '/tags/' + hashtag + '.category'
                if os.path.isfile(categoryFilename):
                    try:
                        os.remove(categoryFilename)
                    except OSError:
                        print('EX: _setHashtagCategory unable to delete ' +
                              categoryFilename)

        # redirect back to the default timeline
        self._redirect_headers(tagScreenStr,
                               cookie, callingDomain)
        self.server.POSTbusy = False

    def _newswireUpdate(self, callingDomain: str, cookie: str,
                        authorized: bool, path: str,
                        base_dir: str, http_prefix: str,
                        domain: str, domainFull: str,
                        onion_domain: str, i2p_domain: str, debug: bool,
                        defaultTimeline: str) -> None:
        """Updates the right newswire column of the timeline
        """
        usersPath = path.replace('/newswiredata', '')
        usersPath = usersPath.replace('/editnewswire', '')
        actorStr = self._getInstanceUrl(callingDomain) + usersPath
        if ' boundary=' in self.headers['Content-type']:
            boundary = self.headers['Content-type'].split('boundary=')[1]
            if ';' in boundary:
                boundary = boundary.split(';')[0]

            # get the nickname
            nickname = getNicknameFromActor(actorStr)
            moderator = None
            if nickname:
                moderator = isModerator(base_dir, nickname)
            if not nickname or not moderator:
                if not nickname:
                    print('WARN: nickname not found in ' + actorStr)
                else:
                    print('WARN: nickname is not a moderator' + actorStr)
                self._redirect_headers(actorStr, cookie, callingDomain)
                self.server.POSTbusy = False
                return

            length = int(self.headers['Content-length'])

            # check that the POST isn't too large
            if length > self.server.maxPostLength:
                print('Maximum newswire data length exceeded ' + str(length))
                self._redirect_headers(actorStr, cookie, callingDomain)
                self.server.POSTbusy = False
                return

            try:
                # read the bytes of the http form POST
                postBytes = self.rfile.read(length)
            except SocketError as ex:
                if ex.errno == errno.ECONNRESET:
                    print('WARN: connection was reset while ' +
                          'reading bytes from http form POST')
                else:
                    print('WARN: error while reading bytes ' +
                          'from http form POST')
                self.send_response(400)
                self.end_headers()
                self.server.POSTbusy = False
                return
            except ValueError as ex:
                print('ERROR: failed to read bytes for POST, ' + str(ex))
                self.send_response(400)
                self.end_headers()
                self.server.POSTbusy = False
                return

            newswireFilename = base_dir + '/accounts/newswire.txt'

            # extract all of the text fields into a dict
            fields = \
                extractTextFieldsInPOST(postBytes, boundary, debug)
            if fields.get('editedNewswire'):
                newswireStr = fields['editedNewswire']
                # append a new newswire entry
                if fields.get('newNewswireFeed'):
                    if newswireStr:
                        if not newswireStr.endswith('\n'):
                            newswireStr += '\n'
                    newswireStr += fields['newNewswireFeed'] + '\n'
                try:
                    with open(newswireFilename, 'w+') as newswireFile:
                        newswireFile.write(newswireStr)
                except OSError:
                    print('EX: unable to write ' + newswireFilename)
            else:
                if fields.get('newNewswireFeed'):
                    # the text area is empty but there is a new feed added
                    newswireStr = fields['newNewswireFeed'] + '\n'
                    try:
                        with open(newswireFilename, 'w+') as newswireFile:
                            newswireFile.write(newswireStr)
                    except OSError:
                        print('EX: unable to write ' + newswireFilename)
                else:
                    # text area has been cleared and there is no new feed
                    if os.path.isfile(newswireFilename):
                        try:
                            os.remove(newswireFilename)
                        except OSError:
                            print('EX: _newswireUpdate unable to delete ' +
                                  newswireFilename)

            # save filtered words list for the newswire
            filterNewswireFilename = \
                base_dir + '/accounts/' + \
                'news@' + domain + '/filters.txt'
            if fields.get('filteredWordsNewswire'):
                try:
                    with open(filterNewswireFilename, 'w+') as filterfile:
                        filterfile.write(fields['filteredWordsNewswire'])
                except OSError:
                    print('EX: unable to write ' + filterNewswireFilename)
            else:
                if os.path.isfile(filterNewswireFilename):
                    try:
                        os.remove(filterNewswireFilename)
                    except OSError:
                        print('EX: _newswireUpdate unable to delete ' +
                              filterNewswireFilename)

            # save news tagging rules
            hashtagRulesFilename = \
                base_dir + '/accounts/hashtagrules.txt'
            if fields.get('hashtagRulesList'):
                try:
                    with open(hashtagRulesFilename, 'w+') as rulesfile:
                        rulesfile.write(fields['hashtagRulesList'])
                except OSError:
                    print('EX: unable to write ' + hashtagRulesFilename)
            else:
                if os.path.isfile(hashtagRulesFilename):
                    try:
                        os.remove(hashtagRulesFilename)
                    except OSError:
                        print('EX: _newswireUpdate unable to delete ' +
                              hashtagRulesFilename)

            newswireTrustedFilename = \
                base_dir + '/accounts/newswiretrusted.txt'
            if fields.get('trustedNewswire'):
                newswireTrusted = fields['trustedNewswire']
                if not newswireTrusted.endswith('\n'):
                    newswireTrusted += '\n'
                try:
                    with open(newswireTrustedFilename, 'w+') as trustFile:
                        trustFile.write(newswireTrusted)
                except OSError:
                    print('EX: unable to write ' + newswireTrustedFilename)
            else:
                if os.path.isfile(newswireTrustedFilename):
                    try:
                        os.remove(newswireTrustedFilename)
                    except OSError:
                        print('EX: _newswireUpdate unable to delete ' +
                              newswireTrustedFilename)

        # redirect back to the default timeline
        self._redirect_headers(actorStr + '/' + defaultTimeline,
                               cookie, callingDomain)
        self.server.POSTbusy = False

    def _citationsUpdate(self, callingDomain: str, cookie: str,
                         authorized: bool, path: str,
                         base_dir: str, http_prefix: str,
                         domain: str, domainFull: str,
                         onion_domain: str, i2p_domain: str, debug: bool,
                         defaultTimeline: str,
                         newswire: {}) -> None:
        """Updates the citations for a blog post after hitting
        update button on the citations screen
        """
        usersPath = path.replace('/citationsdata', '')
        actorStr = self._getInstanceUrl(callingDomain) + usersPath
        nickname = getNicknameFromActor(actorStr)

        citationsFilename = \
            acctDir(base_dir, nickname, domain) + '/.citations.txt'
        # remove any existing citations file
        if os.path.isfile(citationsFilename):
            try:
                os.remove(citationsFilename)
            except OSError:
                print('EX: _citationsUpdate unable to delete ' +
                      citationsFilename)

        if newswire and \
           ' boundary=' in self.headers['Content-type']:
            boundary = self.headers['Content-type'].split('boundary=')[1]
            if ';' in boundary:
                boundary = boundary.split(';')[0]

            length = int(self.headers['Content-length'])

            # check that the POST isn't too large
            if length > self.server.maxPostLength:
                print('Maximum citations data length exceeded ' + str(length))
                self._redirect_headers(actorStr, cookie, callingDomain)
                self.server.POSTbusy = False
                return

            try:
                # read the bytes of the http form POST
                postBytes = self.rfile.read(length)
            except SocketError as ex:
                if ex.errno == errno.ECONNRESET:
                    print('WARN: connection was reset while ' +
                          'reading bytes from http form ' +
                          'citation screen POST')
                else:
                    print('WARN: error while reading bytes ' +
                          'from http form citations screen POST')
                self.send_response(400)
                self.end_headers()
                self.server.POSTbusy = False
                return
            except ValueError as ex:
                print('ERROR: failed to read bytes for ' +
                      'citations screen POST, ' + str(ex))
                self.send_response(400)
                self.end_headers()
                self.server.POSTbusy = False
                return

            # extract all of the text fields into a dict
            fields = \
                extractTextFieldsInPOST(postBytes, boundary, debug)
            print('citationstest: ' + str(fields))
            citations = []
            for ctr in range(0, 128):
                fieldName = 'newswire' + str(ctr)
                if not fields.get(fieldName):
                    continue
                citations.append(fields[fieldName])

            if citations:
                citationsStr = ''
                for citationDate in citations:
                    citationsStr += citationDate + '\n'
                # save citations dates, so that they can be added when
                # reloading the newblog screen
                try:
                    with open(citationsFilename, 'w+') as citationsFile:
                        citationsFile.write(citationsStr)
                except OSError:
                    print('EX: unable to write ' + citationsFilename)

        # redirect back to the default timeline
        self._redirect_headers(actorStr + '/newblog',
                               cookie, callingDomain)
        self.server.POSTbusy = False

    def _newsPostEdit(self, callingDomain: str, cookie: str,
                      authorized: bool, path: str,
                      base_dir: str, http_prefix: str,
                      domain: str, domainFull: str,
                      onion_domain: str, i2p_domain: str, debug: bool,
                      defaultTimeline: str) -> None:
        """edits a news post after receiving POST
        """
        usersPath = path.replace('/newseditdata', '')
        usersPath = usersPath.replace('/editnewspost', '')
        actorStr = self._getInstanceUrl(callingDomain) + usersPath
        if ' boundary=' in self.headers['Content-type']:
            boundary = self.headers['Content-type'].split('boundary=')[1]
            if ';' in boundary:
                boundary = boundary.split(';')[0]

            # get the nickname
            nickname = getNicknameFromActor(actorStr)
            editorRole = None
            if nickname:
                editorRole = isEditor(base_dir, nickname)
            if not nickname or not editorRole:
                if not nickname:
                    print('WARN: nickname not found in ' + actorStr)
                else:
                    print('WARN: nickname is not an editor' + actorStr)
                if self.server.news_instance:
                    self._redirect_headers(actorStr + '/tlfeatures',
                                           cookie, callingDomain)
                else:
                    self._redirect_headers(actorStr + '/tlnews',
                                           cookie, callingDomain)
                self.server.POSTbusy = False
                return

            length = int(self.headers['Content-length'])

            # check that the POST isn't too large
            if length > self.server.maxPostLength:
                print('Maximum news data length exceeded ' + str(length))
                if self.server.news_instance:
                    self._redirect_headers(actorStr + '/tlfeatures',
                                           cookie, callingDomain)
                else:
                    self._redirect_headers(actorStr + '/tlnews',
                                           cookie, callingDomain)
                self.server.POSTbusy = False
                return

            try:
                # read the bytes of the http form POST
                postBytes = self.rfile.read(length)
            except SocketError as ex:
                if ex.errno == errno.ECONNRESET:
                    print('WARN: connection was reset while ' +
                          'reading bytes from http form POST')
                else:
                    print('WARN: error while reading bytes ' +
                          'from http form POST')
                self.send_response(400)
                self.end_headers()
                self.server.POSTbusy = False
                return
            except ValueError as ex:
                print('ERROR: failed to read bytes for POST, ' + str(ex))
                self.send_response(400)
                self.end_headers()
                self.server.POSTbusy = False
                return

            # extract all of the text fields into a dict
            fields = \
                extractTextFieldsInPOST(postBytes, boundary, debug)
            newsPostUrl = None
            newsPostTitle = None
            newsPostContent = None
            if fields.get('newsPostUrl'):
                newsPostUrl = fields['newsPostUrl']
            if fields.get('newsPostTitle'):
                newsPostTitle = fields['newsPostTitle']
            if fields.get('editedNewsPost'):
                newsPostContent = fields['editedNewsPost']

            if newsPostUrl and newsPostContent and newsPostTitle:
                # load the post
                postFilename = \
                    locatePost(base_dir, nickname, domain,
                               newsPostUrl)
                if postFilename:
                    postJsonObject = loadJson(postFilename)
                    # update the content and title
                    postJsonObject['object']['summary'] = \
                        newsPostTitle
                    postJsonObject['object']['content'] = \
                        newsPostContent
                    contentMap = postJsonObject['object']['contentMap']
                    contentMap[self.server.systemLanguage] = newsPostContent
                    # update newswire
                    pubDate = postJsonObject['object']['published']
                    publishedDate = \
                        datetime.datetime.strptime(pubDate,
                                                   "%Y-%m-%dT%H:%M:%SZ")
                    if self.server.newswire.get(str(publishedDate)):
                        self.server.newswire[publishedDate][0] = \
                            newsPostTitle
                        self.server.newswire[publishedDate][4] = \
                            firstParagraphFromString(newsPostContent)
                        # save newswire
                        newswireStateFilename = \
                            base_dir + '/accounts/.newswirestate.json'
                        try:
                            saveJson(self.server.newswire,
                                     newswireStateFilename)
                        except Exception as ex:
                            print('ERROR: saving newswire state, ' + str(ex))

                    # remove any previous cached news posts
                    newsId = removeIdEnding(postJsonObject['object']['id'])
                    newsId = newsId.replace('/', '#')
                    clearFromPostCaches(base_dir, self.server.recentPostsCache,
                                        newsId)

                    # save the news post
                    saveJson(postJsonObject, postFilename)

        # redirect back to the default timeline
        if self.server.news_instance:
            self._redirect_headers(actorStr + '/tlfeatures',
                                   cookie, callingDomain)
        else:
            self._redirect_headers(actorStr + '/tlnews',
                                   cookie, callingDomain)
        self.server.POSTbusy = False

    def _profileUpdate(self, callingDomain: str, cookie: str,
                       authorized: bool, path: str,
                       base_dir: str, http_prefix: str,
                       domain: str, domainFull: str,
                       onion_domain: str, i2p_domain: str,
                       debug: bool, allow_local_network_access: bool,
                       systemLanguage: str, content_license_url: str) -> None:
        """Updates your user profile after editing via the Edit button
        on the profile screen
        """
        usersPath = path.replace('/profiledata', '')
        usersPath = usersPath.replace('/editprofile', '')
        actorStr = self._getInstanceUrl(callingDomain) + usersPath
        if ' boundary=' in self.headers['Content-type']:
            boundary = self.headers['Content-type'].split('boundary=')[1]
            if ';' in boundary:
                boundary = boundary.split(';')[0]

            # get the nickname
            nickname = getNicknameFromActor(actorStr)
            if not nickname:
                print('WARN: nickname not found in ' + actorStr)
                self._redirect_headers(actorStr, cookie, callingDomain)
                self.server.POSTbusy = False
                return

            length = int(self.headers['Content-length'])

            # check that the POST isn't too large
            if length > self.server.maxPostLength:
                print('Maximum profile data length exceeded ' +
                      str(length))
                self._redirect_headers(actorStr, cookie, callingDomain)
                self.server.POSTbusy = False
                return

            try:
                # read the bytes of the http form POST
                postBytes = self.rfile.read(length)
            except SocketError as ex:
                if ex.errno == errno.ECONNRESET:
                    print('WARN: connection was reset while ' +
                          'reading bytes from http form POST')
                else:
                    print('WARN: error while reading bytes ' +
                          'from http form POST')
                self.send_response(400)
                self.end_headers()
                self.server.POSTbusy = False
                return
            except ValueError as ex:
                print('ERROR: failed to read bytes for POST, ' + str(ex))
                self.send_response(400)
                self.end_headers()
                self.server.POSTbusy = False
                return

            adminNickname = getConfigParam(self.server.base_dir, 'admin')

            # get the various avatar, banner and background images
            actorChanged = True
            profileMediaTypes = ('avatar', 'image',
                                 'banner', 'search_banner',
                                 'instanceLogo',
                                 'left_col_image', 'right_col_image',
                                 'submitImportTheme')
            profileMediaTypesUploaded = {}
            for mType in profileMediaTypes:
                # some images can only be changed by the admin
                if mType == 'instanceLogo':
                    if nickname != adminNickname:
                        print('WARN: only the admin can change ' +
                              'instance logo')
                        continue

                if debug:
                    print('DEBUG: profile update extracting ' + mType +
                          ' image, zip or font from POST')
                mediaBytes, postBytes = \
                    extractMediaInFormPOST(postBytes, boundary, mType)
                if mediaBytes:
                    if debug:
                        print('DEBUG: profile update ' + mType +
                              ' image, zip or font was found. ' +
                              str(len(mediaBytes)) + ' bytes')
                else:
                    if debug:
                        print('DEBUG: profile update, no ' + mType +
                              ' image, zip or font was found in POST')
                    continue

                # Note: a .temp extension is used here so that at no
                # time is an image with metadata publicly exposed,
                # even for a few mS
                if mType == 'instanceLogo':
                    filenameBase = \
                        base_dir + '/accounts/login.temp'
                elif mType == 'submitImportTheme':
                    if not os.path.isdir(base_dir + '/imports'):
                        os.mkdir(base_dir + '/imports')
                    filenameBase = \
                        base_dir + '/imports/newtheme.zip'
                    if os.path.isfile(filenameBase):
                        try:
                            os.remove(filenameBase)
                        except OSError:
                            print('EX: _profileUpdate unable to delete ' +
                                  filenameBase)
                else:
                    filenameBase = \
                        acctDir(base_dir, nickname, domain) + \
                        '/' + mType + '.temp'

                filename, attachmentMediaType = \
                    saveMediaInFormPOST(mediaBytes, debug,
                                        filenameBase)
                if filename:
                    print('Profile update POST ' + mType +
                          ' media, zip or font filename is ' + filename)
                else:
                    print('Profile update, no ' + mType +
                          ' media, zip or font filename in POST')
                    continue

                if mType == 'submitImportTheme':
                    if nickname == adminNickname or \
                       isArtist(base_dir, nickname):
                        if importTheme(base_dir, filename):
                            print(nickname + ' uploaded a theme')
                    else:
                        print('Only admin or artist can import a theme')
                    continue

                postImageFilename = filename.replace('.temp', '')
                if debug:
                    print('DEBUG: POST ' + mType +
                          ' media removing metadata')
                # remove existing etag
                if os.path.isfile(postImageFilename + '.etag'):
                    try:
                        os.remove(postImageFilename + '.etag')
                    except OSError:
                        print('EX: _profileUpdate unable to delete ' +
                              postImageFilename + '.etag')

                city = getSpoofedCity(self.server.city,
                                      base_dir, nickname, domain)

                if self.server.low_bandwidth:
                    convertImageToLowBandwidth(filename)
                processMetaData(base_dir, nickname, domain,
                                filename, postImageFilename, city,
                                content_license_url)
                if os.path.isfile(postImageFilename):
                    print('profile update POST ' + mType +
                          ' image, zip or font saved to ' +
                          postImageFilename)
                    if mType != 'instanceLogo':
                        lastPartOfImageFilename = \
                            postImageFilename.split('/')[-1]
                        profileMediaTypesUploaded[mType] = \
                            lastPartOfImageFilename
                        actorChanged = True
                else:
                    print('ERROR: profile update POST ' + mType +
                          ' image or font could not be saved to ' +
                          postImageFilename)

            postBytesStr = postBytes.decode('utf-8')
            redirectPath = ''
            checkNameAndBio = False
            onFinalWelcomeScreen = False
            if 'name="previewAvatar"' in postBytesStr:
                redirectPath = '/welcome_profile'
            elif 'name="initialWelcomeScreen"' in postBytesStr:
                redirectPath = '/welcome'
            elif 'name="finalWelcomeScreen"' in postBytesStr:
                checkNameAndBio = True
                redirectPath = '/welcome_final'
            elif 'name="welcomeCompleteButton"' in postBytesStr:
                redirectPath = '/' + self.server.defaultTimeline
                welcomeScreenIsComplete(self.server.base_dir, nickname,
                                        self.server.domain)
                onFinalWelcomeScreen = True
            elif 'name="submitExportTheme"' in postBytesStr:
                print('submitExportTheme')
                themeDownloadPath = actorStr
                if exportTheme(self.server.base_dir,
                               self.server.themeName):
                    themeDownloadPath += \
                        '/exports/' + self.server.themeName + '.zip'
                print('submitExportTheme path=' + themeDownloadPath)
                self._redirect_headers(themeDownloadPath,
                                       cookie, callingDomain)
                self.server.POSTbusy = False
                return

            # extract all of the text fields into a dict
            fields = \
                extractTextFieldsInPOST(postBytes, boundary, debug)
            if debug:
                if fields:
                    print('DEBUG: profile update text ' +
                          'field extracted from POST ' + str(fields))
                else:
                    print('WARN: profile update, no text ' +
                          'fields could be extracted from POST')

            # load the json for the actor for this user
            actorFilename = \
                acctDir(base_dir, nickname, domain) + '.json'
            if os.path.isfile(actorFilename):
                actorJson = loadJson(actorFilename)
                if actorJson:
                    if not actorJson.get('discoverable'):
                        # discoverable in profile directory
                        # which isn't implemented in Epicyon
                        actorJson['discoverable'] = True
                        actorChanged = True
                    if actorJson.get('capabilityAcquisitionEndpoint'):
                        del actorJson['capabilityAcquisitionEndpoint']
                        actorChanged = True
                    # update the avatar/image url file extension
                    uploads = profileMediaTypesUploaded.items()
                    for mType, lastPart in uploads:
                        repStr = '/' + lastPart
                        if mType == 'avatar':
                            actorUrl = actorJson['icon']['url']
                            lastPartOfUrl = actorUrl.split('/')[-1]
                            srchStr = '/' + lastPartOfUrl
                            actorUrl = actorUrl.replace(srchStr, repStr)
                            actorJson['icon']['url'] = actorUrl
                            print('actorUrl: ' + actorUrl)
                            if '.' in actorUrl:
                                imgExt = actorUrl.split('.')[-1]
                                if imgExt == 'jpg':
                                    imgExt = 'jpeg'
                                actorJson['icon']['mediaType'] = \
                                    'image/' + imgExt
                        elif mType == 'image':
                            lastPartOfUrl = \
                                actorJson['image']['url'].split('/')[-1]
                            srchStr = '/' + lastPartOfUrl
                            actorJson['image']['url'] = \
                                actorJson['image']['url'].replace(srchStr,
                                                                  repStr)
                            if '.' in actorJson['image']['url']:
                                imgExt = \
                                    actorJson['image']['url'].split('.')[-1]
                                if imgExt == 'jpg':
                                    imgExt = 'jpeg'
                                actorJson['image']['mediaType'] = \
                                    'image/' + imgExt

                    # set skill levels
                    skillCtr = 1
                    actorSkillsCtr = noOfActorSkills(actorJson)
                    while skillCtr < 10:
                        skillName = \
                            fields.get('skillName' + str(skillCtr))
                        if not skillName:
                            skillCtr += 1
                            continue
                        if isFiltered(base_dir, nickname, domain, skillName):
                            skillCtr += 1
                            continue
                        skillValue = \
                            fields.get('skillValue' + str(skillCtr))
                        if not skillValue:
                            skillCtr += 1
                            continue
                        if not actorHasSkill(actorJson, skillName):
                            actorChanged = True
                        else:
                            if actorSkillValue(actorJson, skillName) != \
                               int(skillValue):
                                actorChanged = True
                        setActorSkillLevel(actorJson,
                                           skillName, int(skillValue))
                        skillsStr = self.server.translate['Skills']
                        skillsStr = skillsStr.lower()
                        setHashtagCategory(base_dir, skillName,
                                           skillsStr, False)
                        skillCtr += 1
                    if noOfActorSkills(actorJson) != \
                       actorSkillsCtr:
                        actorChanged = True

                    # change password
                    if fields.get('password') and \
                       fields.get('passwordconfirm'):
                        fields['password'] = \
                            removeLineEndings(fields['password'])
                        fields['passwordconfirm'] = \
                            removeLineEndings(fields['passwordconfirm'])
                        if validPassword(fields['password']) and \
                           fields['password'] == fields['passwordconfirm']:
                            # set password
                            storeBasicCredentials(base_dir, nickname,
                                                  fields['password'])

                    # reply interval in hours
                    if fields.get('replyhours'):
                        if fields['replyhours'].isdigit():
                            setReplyIntervalHours(base_dir, nickname, domain,
                                                  fields['replyhours'])

                    # change city
                    if fields.get('cityDropdown'):
                        cityFilename = \
                            acctDir(base_dir, nickname, domain) + '/city.txt'
                        try:
                            with open(cityFilename, 'w+') as fp:
                                fp.write(fields['cityDropdown'])
                        except OSError:
                            print('EX: unable to write city ' + cityFilename)

                    # change displayed name
                    if fields.get('displayNickname'):
                        if fields['displayNickname'] != actorJson['name']:
                            displayName = \
                                removeHtml(fields['displayNickname'])
                            if not isFiltered(base_dir,
                                              nickname, domain,
                                              displayName):
                                actorJson['name'] = displayName
                            else:
                                actorJson['name'] = nickname
                                if checkNameAndBio:
                                    redirectPath = 'previewAvatar'
                            actorChanged = True
                    else:
                        if checkNameAndBio:
                            redirectPath = 'previewAvatar'

                    if nickname == adminNickname or \
                       isArtist(base_dir, nickname):
                        # change theme
                        if fields.get('themeDropdown'):
                            self.server.themeName = fields['themeDropdown']
                            setTheme(base_dir, self.server.themeName, domain,
                                     allow_local_network_access,
                                     systemLanguage)
                            self.server.textModeBanner = \
                                getTextModeBanner(self.server.base_dir)
                            self.server.iconsCache = {}
                            self.server.fontsCache = {}
                            self.server.show_publish_as_icon = \
                                getConfigParam(self.server.base_dir,
                                               'show_publish_as_icon')
                            self.server.full_width_tl_button_header = \
                                getConfigParam(self.server.base_dir,
                                               'full_width_tl_button_header')
                            self.server.icons_as_buttons = \
                                getConfigParam(self.server.base_dir,
                                               'icons_as_buttons')
                            self.server.rss_icon_at_top = \
                                getConfigParam(self.server.base_dir,
                                               'rss_icon_at_top')
                            self.server.publish_button_at_top = \
                                getConfigParam(self.server.base_dir,
                                               'publish_button_at_top')
                            setNewsAvatar(base_dir,
                                          fields['themeDropdown'],
                                          http_prefix,
                                          domain,
                                          domainFull)

                    if nickname == adminNickname:
                        # change media instance status
                        if fields.get('media_instance'):
                            self.server.media_instance = False
                            self.server.defaultTimeline = 'inbox'
                            if fields['media_instance'] == 'on':
                                self.server.media_instance = True
                                self.server.blogs_instance = False
                                self.server.news_instance = False
                                self.server.defaultTimeline = 'tlmedia'
                            setConfigParam(base_dir,
                                           "media_instance",
                                           self.server.media_instance)
                            setConfigParam(base_dir,
                                           "blogs_instance",
                                           self.server.blogs_instance)
                            setConfigParam(base_dir,
                                           "news_instance",
                                           self.server.news_instance)
                        else:
                            if self.server.media_instance:
                                self.server.media_instance = False
                                self.server.defaultTimeline = 'inbox'
                                setConfigParam(base_dir,
                                               "media_instance",
                                               self.server.media_instance)

                        # is this a news theme?
                        if isNewsThemeName(self.server.base_dir,
                                           self.server.themeName):
                            fields['news_instance'] = 'on'

                        # change news instance status
                        if fields.get('news_instance'):
                            self.server.news_instance = False
                            self.server.defaultTimeline = 'inbox'
                            if fields['news_instance'] == 'on':
                                self.server.news_instance = True
                                self.server.blogs_instance = False
                                self.server.media_instance = False
                                self.server.defaultTimeline = 'tlfeatures'
                            setConfigParam(base_dir,
                                           "media_instance",
                                           self.server.media_instance)
                            setConfigParam(base_dir,
                                           "blogs_instance",
                                           self.server.blogs_instance)
                            setConfigParam(base_dir,
                                           "news_instance",
                                           self.server.news_instance)
                        else:
                            if self.server.news_instance:
                                self.server.news_instance = False
                                self.server.defaultTimeline = 'inbox'
                                setConfigParam(base_dir,
                                               "news_instance",
                                               self.server.media_instance)

                        # change blog instance status
                        if fields.get('blogs_instance'):
                            self.server.blogs_instance = False
                            self.server.defaultTimeline = 'inbox'
                            if fields['blogs_instance'] == 'on':
                                self.server.blogs_instance = True
                                self.server.media_instance = False
                                self.server.news_instance = False
                                self.server.defaultTimeline = 'tlblogs'
                            setConfigParam(base_dir,
                                           "blogs_instance",
                                           self.server.blogs_instance)
                            setConfigParam(base_dir,
                                           "media_instance",
                                           self.server.media_instance)
                            setConfigParam(base_dir,
                                           "news_instance",
                                           self.server.news_instance)
                        else:
                            if self.server.blogs_instance:
                                self.server.blogs_instance = False
                                self.server.defaultTimeline = 'inbox'
                                setConfigParam(base_dir,
                                               "blogs_instance",
                                               self.server.blogs_instance)

                        # change instance title
                        if fields.get('instanceTitle'):
                            currInstanceTitle = \
                                getConfigParam(base_dir, 'instanceTitle')
                            if fields['instanceTitle'] != currInstanceTitle:
                                setConfigParam(base_dir, 'instanceTitle',
                                               fields['instanceTitle'])

                        # change YouTube alternate domain
                        if fields.get('ytdomain'):
                            currYTDomain = self.server.yt_replace_domain
                            if fields['ytdomain'] != currYTDomain:
                                newYTDomain = fields['ytdomain']
                                if '://' in newYTDomain:
                                    newYTDomain = newYTDomain.split('://')[1]
                                if '/' in newYTDomain:
                                    newYTDomain = newYTDomain.split('/')[0]
                                if '.' in newYTDomain:
                                    setConfigParam(base_dir,
                                                   'youtubedomain',
                                                   newYTDomain)
                                    self.server.yt_replace_domain = \
                                        newYTDomain
                        else:
                            setConfigParam(base_dir,
                                           'youtubedomain', '')
                            self.server.yt_replace_domain = None

                        # change twitter alternate domain
                        if fields.get('twitterdomain'):
                            currTwitterDomain = \
                                self.server.twitter_replacement_domain
                            if fields['twitterdomain'] != currTwitterDomain:
                                newTwitterDomain = fields['twitterdomain']
                                if '://' in newTwitterDomain:
                                    newTwitterDomain = \
                                        newTwitterDomain.split('://')[1]
                                if '/' in newTwitterDomain:
                                    newTwitterDomain = \
                                        newTwitterDomain.split('/')[0]
                                if '.' in newTwitterDomain:
                                    setConfigParam(base_dir,
                                                   'twitterdomain',
                                                   newTwitterDomain)
                                    self.server.twitter_replacement_domain = \
                                        newTwitterDomain
                        else:
                            setConfigParam(base_dir,
                                           'twitterdomain', '')
                            self.server.twitter_replacement_domain = None

                        # change custom post submit button text
                        currCustomSubmitText = \
                            getConfigParam(base_dir, 'customSubmitText')
                        if fields.get('customSubmitText'):
                            if fields['customSubmitText'] != \
                               currCustomSubmitText:
                                customText = fields['customSubmitText']
                                setConfigParam(base_dir,
                                               'customSubmitText',
                                               customText)
                        else:
                            if currCustomSubmitText:
                                setConfigParam(base_dir,
                                               'customSubmitText', '')

                        # libretranslate URL
                        currLibretranslateUrl = \
                            getConfigParam(base_dir,
                                           'libretranslateUrl')
                        if fields.get('libretranslateUrl'):
                            if fields['libretranslateUrl'] != \
                               currLibretranslateUrl:
                                ltUrl = fields['libretranslateUrl']
                                if '://' in ltUrl and \
                                   '.' in ltUrl:
                                    setConfigParam(base_dir,
                                                   'libretranslateUrl',
                                                   ltUrl)
                        else:
                            if currLibretranslateUrl:
                                setConfigParam(base_dir,
                                               'libretranslateUrl', '')

                        # libretranslate API Key
                        currLibretranslateApiKey = \
                            getConfigParam(base_dir,
                                           'libretranslateApiKey')
                        if fields.get('libretranslateApiKey'):
                            if fields['libretranslateApiKey'] != \
                               currLibretranslateApiKey:
                                ltApiKey = fields['libretranslateApiKey']
                                setConfigParam(base_dir,
                                               'libretranslateApiKey',
                                               ltApiKey)
                        else:
                            if currLibretranslateApiKey:
                                setConfigParam(base_dir,
                                               'libretranslateApiKey', '')

                        # change instance short description
                        if fields.get('content_license_url'):
                            if fields['content_license_url'] != \
                               self.server.content_license_url:
                                licenseStr = fields['content_license_url']
                                setConfigParam(base_dir,
                                               'content_license_url',
                                               licenseStr)
                                self.server.content_license_url = \
                                    licenseStr
                        else:
                            licenseStr = \
                                'https://creativecommons.org/licenses/by/4.0'
                            setConfigParam(base_dir,
                                           'content_license_url',
                                           licenseStr)
                            self.server.content_license_url = licenseStr

                        # change instance short description
                        currInstanceDescriptionShort = \
                            getConfigParam(base_dir,
                                           'instanceDescriptionShort')
                        if fields.get('instanceDescriptionShort'):
                            if fields['instanceDescriptionShort'] != \
                               currInstanceDescriptionShort:
                                iDesc = fields['instanceDescriptionShort']
                                setConfigParam(base_dir,
                                               'instanceDescriptionShort',
                                               iDesc)
                        else:
                            if currInstanceDescriptionShort:
                                setConfigParam(base_dir,
                                               'instanceDescriptionShort', '')

                        # change instance description
                        currInstanceDescription = \
                            getConfigParam(base_dir, 'instanceDescription')
                        if fields.get('instanceDescription'):
                            if fields['instanceDescription'] != \
                               currInstanceDescription:
                                setConfigParam(base_dir,
                                               'instanceDescription',
                                               fields['instanceDescription'])
                        else:
                            if currInstanceDescription:
                                setConfigParam(base_dir,
                                               'instanceDescription', '')

                    # change email address
                    currentEmailAddress = getEmailAddress(actorJson)
                    if fields.get('email'):
                        if fields['email'] != currentEmailAddress:
                            setEmailAddress(actorJson, fields['email'])
                            actorChanged = True
                    else:
                        if currentEmailAddress:
                            setEmailAddress(actorJson, '')
                            actorChanged = True

                    # change xmpp address
                    currentXmppAddress = getXmppAddress(actorJson)
                    if fields.get('xmppAddress'):
                        if fields['xmppAddress'] != currentXmppAddress:
                            setXmppAddress(actorJson,
                                           fields['xmppAddress'])
                            actorChanged = True
                    else:
                        if currentXmppAddress:
                            setXmppAddress(actorJson, '')
                            actorChanged = True

                    # change matrix address
                    currentMatrixAddress = getMatrixAddress(actorJson)
                    if fields.get('matrixAddress'):
                        if fields['matrixAddress'] != currentMatrixAddress:
                            setMatrixAddress(actorJson,
                                             fields['matrixAddress'])
                            actorChanged = True
                    else:
                        if currentMatrixAddress:
                            setMatrixAddress(actorJson, '')
                            actorChanged = True

                    # change SSB address
                    currentSSBAddress = getSSBAddress(actorJson)
                    if fields.get('ssbAddress'):
                        if fields['ssbAddress'] != currentSSBAddress:
                            setSSBAddress(actorJson,
                                          fields['ssbAddress'])
                            actorChanged = True
                    else:
                        if currentSSBAddress:
                            setSSBAddress(actorJson, '')
                            actorChanged = True

                    # change blog address
                    currentBlogAddress = getBlogAddress(actorJson)
                    if fields.get('blogAddress'):
                        if fields['blogAddress'] != currentBlogAddress:
                            setBlogAddress(actorJson,
                                           fields['blogAddress'])
                            actorChanged = True
                    else:
                        if currentBlogAddress:
                            setBlogAddress(actorJson, '')
                            actorChanged = True

                    # change Languages address
                    currentShowLanguages = getActorLanguages(actorJson)
                    if fields.get('showLanguages'):
                        if fields['showLanguages'] != currentShowLanguages:
                            setActorLanguages(base_dir, actorJson,
                                              fields['showLanguages'])
                            actorChanged = True
                    else:
                        if currentShowLanguages:
                            setActorLanguages(base_dir, actorJson, '')
                            actorChanged = True

                    # change tox address
                    currentToxAddress = getToxAddress(actorJson)
                    if fields.get('toxAddress'):
                        if fields['toxAddress'] != currentToxAddress:
                            setToxAddress(actorJson,
                                          fields['toxAddress'])
                            actorChanged = True
                    else:
                        if currentToxAddress:
                            setToxAddress(actorJson, '')
                            actorChanged = True

                    # change briar address
                    currentBriarAddress = getBriarAddress(actorJson)
                    if fields.get('briarAddress'):
                        if fields['briarAddress'] != currentBriarAddress:
                            setBriarAddress(actorJson,
                                            fields['briarAddress'])
                            actorChanged = True
                    else:
                        if currentBriarAddress:
                            setBriarAddress(actorJson, '')
                            actorChanged = True

                    # change jami address
                    currentJamiAddress = getJamiAddress(actorJson)
                    if fields.get('jamiAddress'):
                        if fields['jamiAddress'] != currentJamiAddress:
                            setJamiAddress(actorJson,
                                           fields['jamiAddress'])
                            actorChanged = True
                    else:
                        if currentJamiAddress:
                            setJamiAddress(actorJson, '')
                            actorChanged = True

                    # change cwtch address
                    currentCwtchAddress = getCwtchAddress(actorJson)
                    if fields.get('cwtchAddress'):
                        if fields['cwtchAddress'] != currentCwtchAddress:
                            setCwtchAddress(actorJson,
                                            fields['cwtchAddress'])
                            actorChanged = True
                    else:
                        if currentCwtchAddress:
                            setCwtchAddress(actorJson, '')
                            actorChanged = True

                    # change Enigma public key
                    currentEnigmaPubKey = getEnigmaPubKey(actorJson)
                    if fields.get('enigmapubkey'):
                        if fields['enigmapubkey'] != currentEnigmaPubKey:
                            setEnigmaPubKey(actorJson,
                                            fields['enigmapubkey'])
                            actorChanged = True
                    else:
                        if currentEnigmaPubKey:
                            setEnigmaPubKey(actorJson, '')
                            actorChanged = True

                    # change PGP public key
                    currentPGPpubKey = getPGPpubKey(actorJson)
                    if fields.get('pgp'):
                        if fields['pgp'] != currentPGPpubKey:
                            setPGPpubKey(actorJson,
                                         fields['pgp'])
                            actorChanged = True
                    else:
                        if currentPGPpubKey:
                            setPGPpubKey(actorJson, '')
                            actorChanged = True

                    # change PGP fingerprint
                    currentPGPfingerprint = getPGPfingerprint(actorJson)
                    if fields.get('openpgp'):
                        if fields['openpgp'] != currentPGPfingerprint:
                            setPGPfingerprint(actorJson,
                                              fields['openpgp'])
                            actorChanged = True
                    else:
                        if currentPGPfingerprint:
                            setPGPfingerprint(actorJson, '')
                            actorChanged = True

                    # change donation link
                    currentDonateUrl = getDonationUrl(actorJson)
                    if fields.get('donateUrl'):
                        if fields['donateUrl'] != currentDonateUrl:
                            setDonationUrl(actorJson,
                                           fields['donateUrl'])
                            actorChanged = True
                    else:
                        if currentDonateUrl:
                            setDonationUrl(actorJson, '')
                            actorChanged = True

                    # change website
                    currentWebsite = \
                        getWebsite(actorJson, self.server.translate)
                    if fields.get('websiteUrl'):
                        if fields['websiteUrl'] != currentWebsite:
                            setWebsite(actorJson,
                                       fields['websiteUrl'],
                                       self.server.translate)
                            actorChanged = True
                    else:
                        if currentWebsite:
                            setWebsite(actorJson, '', self.server.translate)
                            actorChanged = True

                    # account moved to new address
                    movedTo = ''
                    if actorJson.get('movedTo'):
                        movedTo = actorJson['movedTo']
                    if fields.get('movedTo'):
                        if fields['movedTo'] != movedTo and \
                           '://' in fields['movedTo'] and \
                           '.' in fields['movedTo']:
                            actorJson['movedTo'] = movedTo
                            actorChanged = True
                    else:
                        if movedTo:
                            del actorJson['movedTo']
                            actorChanged = True

                    # Other accounts (alsoKnownAs)
                    occupationName = getOccupationName(actorJson)
                    if fields.get('occupationName'):
                        fields['occupationName'] = \
                            removeHtml(fields['occupationName'])
                        if occupationName != \
                           fields['occupationName']:
                            setOccupationName(actorJson,
                                              fields['occupationName'])
                            actorChanged = True
                    else:
                        if occupationName:
                            setOccupationName(actorJson, '')
                            actorChanged = True

                    # Other accounts (alsoKnownAs)
                    alsoKnownAs = []
                    if actorJson.get('alsoKnownAs'):
                        alsoKnownAs = actorJson['alsoKnownAs']
                    if fields.get('alsoKnownAs'):
                        alsoKnownAsStr = ''
                        alsoKnownAsCtr = 0
                        for altActor in alsoKnownAs:
                            if alsoKnownAsCtr > 0:
                                alsoKnownAsStr += ', '
                            alsoKnownAsStr += altActor
                            alsoKnownAsCtr += 1
                        if fields['alsoKnownAs'] != alsoKnownAsStr and \
                           '://' in fields['alsoKnownAs'] and \
                           '@' not in fields['alsoKnownAs'] and \
                           '.' in fields['alsoKnownAs']:
                            if ';' in fields['alsoKnownAs']:
                                fields['alsoKnownAs'] = \
                                    fields['alsoKnownAs'].replace(';', ',')
                            newAlsoKnownAs = fields['alsoKnownAs'].split(',')
                            alsoKnownAs = []
                            for altActor in newAlsoKnownAs:
                                altActor = altActor.strip()
                                if '://' in altActor and '.' in altActor:
                                    if altActor not in alsoKnownAs:
                                        alsoKnownAs.append(altActor)
                            actorJson['alsoKnownAs'] = alsoKnownAs
                            actorChanged = True
                    else:
                        if alsoKnownAs:
                            del actorJson['alsoKnownAs']
                            actorChanged = True

                    # change user bio
                    if fields.get('bio'):
                        if fields['bio'] != actorJson['summary']:
                            bioStr = removeHtml(fields['bio'])
                            if not isFiltered(base_dir,
                                              nickname, domain, bioStr):
                                actorTags = {}
                                actorJson['summary'] = \
                                    addHtmlTags(base_dir,
                                                http_prefix,
                                                nickname,
                                                domainFull,
                                                bioStr, [], actorTags)
                                if actorTags:
                                    actorJson['tag'] = []
                                    for tagName, tag in actorTags.items():
                                        actorJson['tag'].append(tag)
                                actorChanged = True
                            else:
                                if checkNameAndBio:
                                    redirectPath = 'previewAvatar'
                    else:
                        if checkNameAndBio:
                            redirectPath = 'previewAvatar'

                    adminNickname = \
                        getConfigParam(base_dir, 'admin')

                    if adminNickname:
                        # whether to require jsonld signatures
                        # on all incoming posts
                        if path.startswith('/users/' +
                                           adminNickname + '/'):
                            show_node_info_accounts = False
                            if fields.get('show_node_info_accounts'):
                                if fields['show_node_info_accounts'] == 'on':
                                    show_node_info_accounts = True
                            self.server.show_node_info_accounts = \
                                show_node_info_accounts
                            setConfigParam(base_dir, "show_node_info_accounts",
                                           show_node_info_accounts)

                            show_node_info_version = False
                            if fields.get('show_node_info_version'):
                                if fields['show_node_info_version'] == 'on':
                                    show_node_info_version = True
                            self.server.show_node_info_version = \
                                show_node_info_version
                            setConfigParam(base_dir, "show_node_info_version",
                                           show_node_info_version)

                            verify_all_signatures = False
                            if fields.get('verifyallsignatures'):
                                if fields['verifyallsignatures'] == 'on':
                                    verify_all_signatures = True
                            self.server.verify_all_signatures = \
                                verify_all_signatures
                            setConfigParam(base_dir, "verify_all_signatures",
                                           verify_all_signatures)

                            broch_mode = False
                            if fields.get('broch_mode'):
                                if fields['broch_mode'] == 'on':
                                    broch_mode = True
                            currBrochMode = \
                                getConfigParam(base_dir, "broch_mode")
                            if broch_mode != currBrochMode:
                                setBrochMode(self.server.base_dir,
                                             self.server.domainFull,
                                             broch_mode)
                                setConfigParam(base_dir, "broch_mode",
                                               broch_mode)

                            # shared item federation domains
                            siDomainUpdated = False
                            fed_domains_variable = \
                                "shared_items_federated_domains"
                            fed_domains_str = \
                                getConfigParam(base_dir,
                                               fed_domains_variable)
                            if not fed_domains_str:
                                fed_domains_str = ''
                            sharedItemsFormStr = ''
                            if fields.get('shareDomainList'):
                                sharedItemsList = \
                                    fed_domains_str.split(',')
                                for sharedFederatedDomain in sharedItemsList:
                                    sharedItemsFormStr += \
                                        sharedFederatedDomain.strip() + '\n'

                                shareDomainList = fields['shareDomainList']
                                if shareDomainList != \
                                   sharedItemsFormStr:
                                    sharedItemsFormStr2 = \
                                        shareDomainList.replace('\n', ',')
                                    sharedItemsField = \
                                        "shared_items_federated_domains"
                                    setConfigParam(base_dir, sharedItemsField,
                                                   sharedItemsFormStr2)
                                    siDomainUpdated = True
                            else:
                                if fed_domains_str:
                                    sharedItemsField = \
                                        "shared_items_federated_domains"
                                    setConfigParam(base_dir, sharedItemsField,
                                                   '')
                                    siDomainUpdated = True
                            if siDomainUpdated:
                                siDomains = sharedItemsFormStr.split('\n')
                                siTokens = \
                                    self.server.sharedItemFederationTokens
                                self.server.shared_items_federated_domains = \
                                    siDomains
                                domainFull = self.server.domainFull
                                self.server.sharedItemFederationTokens = \
                                    mergeSharedItemTokens(self.server.base_dir,
                                                          domainFull,
                                                          siDomains,
                                                          siTokens)

                        # change moderators list
                        if fields.get('moderators'):
                            if path.startswith('/users/' +
                                               adminNickname + '/'):
                                moderatorsFile = \
                                    base_dir + \
                                    '/accounts/moderators.txt'
                                clearModeratorStatus(base_dir)
                                if ',' in fields['moderators']:
                                    # if the list was given as comma separated
                                    mods = fields['moderators'].split(',')
                                    try:
                                        with open(moderatorsFile,
                                                  'w+') as modFile:
                                            for modNick in mods:
                                                modNick = modNick.strip()
                                                modDir = base_dir + \
                                                    '/accounts/' + modNick + \
                                                    '@' + domain
                                                if os.path.isdir(modDir):
                                                    modFile.write(modNick +
                                                                  '\n')
                                    except OSError:
                                        print('EX: ' +
                                              'unable to write moderators ' +
                                              moderatorsFile)

                                    for modNick in mods:
                                        modNick = modNick.strip()
                                        modDir = base_dir + \
                                            '/accounts/' + modNick + \
                                            '@' + domain
                                        if os.path.isdir(modDir):
                                            setRole(base_dir,
                                                    modNick, domain,
                                                    'moderator')
                                else:
                                    # nicknames on separate lines
                                    mods = fields['moderators'].split('\n')
                                    try:
                                        with open(moderatorsFile,
                                                  'w+') as modFile:
                                            for modNick in mods:
                                                modNick = modNick.strip()
                                                modDir = \
                                                    base_dir + \
                                                    '/accounts/' + modNick + \
                                                    '@' + domain
                                                if os.path.isdir(modDir):
                                                    modFile.write(modNick +
                                                                  '\n')
                                    except OSError:
                                        print('EX: ' +
                                              'unable to write moderators 2 ' +
                                              moderatorsFile)

                                    for modNick in mods:
                                        modNick = modNick.strip()
                                        modDir = \
                                            base_dir + \
                                            '/accounts/' + \
                                            modNick + '@' + \
                                            domain
                                        if os.path.isdir(modDir):
                                            setRole(base_dir,
                                                    modNick, domain,
                                                    'moderator')

                        # change site editors list
                        if fields.get('editors'):
                            if path.startswith('/users/' +
                                               adminNickname + '/'):
                                editorsFile = \
                                    base_dir + \
                                    '/accounts/editors.txt'
                                clearEditorStatus(base_dir)
                                if ',' in fields['editors']:
                                    # if the list was given as comma separated
                                    eds = fields['editors'].split(',')
                                    try:
                                        with open(editorsFile, 'w+') as edFile:
                                            for edNick in eds:
                                                edNick = edNick.strip()
                                                edDir = base_dir + \
                                                    '/accounts/' + edNick + \
                                                    '@' + domain
                                                if os.path.isdir(edDir):
                                                    edFile.write(edNick + '\n')
                                    except OSError as ex:
                                        print('EX: unable to write editors ' +
                                              editorsFile + ' ' + str(ex))

                                    for edNick in eds:
                                        edNick = edNick.strip()
                                        edDir = base_dir + \
                                            '/accounts/' + edNick + \
                                            '@' + domain
                                        if os.path.isdir(edDir):
                                            setRole(base_dir,
                                                    edNick, domain,
                                                    'editor')
                                else:
                                    # nicknames on separate lines
                                    eds = fields['editors'].split('\n')
                                    try:
                                        with open(editorsFile,
                                                  'w+') as edFile:
                                            for edNick in eds:
                                                edNick = edNick.strip()
                                                edDir = \
                                                    base_dir + \
                                                    '/accounts/' + edNick + \
                                                    '@' + domain
                                                if os.path.isdir(edDir):
                                                    edFile.write(edNick + '\n')
                                    except OSError as ex:
                                        print('EX: unable to write editors ' +
                                              editorsFile + ' ' + str(ex))

                                    for edNick in eds:
                                        edNick = edNick.strip()
                                        edDir = \
                                            base_dir + \
                                            '/accounts/' + \
                                            edNick + '@' + \
                                            domain
                                        if os.path.isdir(edDir):
                                            setRole(base_dir,
                                                    edNick, domain,
                                                    'editor')

                        # change site counselors list
                        if fields.get('counselors'):
                            if path.startswith('/users/' +
                                               adminNickname + '/'):
                                counselorsFile = \
                                    base_dir + \
                                    '/accounts/counselors.txt'
                                clearCounselorStatus(base_dir)
                                if ',' in fields['counselors']:
                                    # if the list was given as comma separated
                                    eds = fields['counselors'].split(',')
                                    try:
                                        with open(counselorsFile,
                                                  'w+') as edFile:
                                            for edNick in eds:
                                                edNick = edNick.strip()
                                                edDir = base_dir + \
                                                    '/accounts/' + edNick + \
                                                    '@' + domain
                                                if os.path.isdir(edDir):
                                                    edFile.write(edNick + '\n')
                                    except OSError as ex:
                                        print('EX: ' +
                                              'unable to write counselors ' +
                                              counselorsFile + ' ' + str(ex))

                                    for edNick in eds:
                                        edNick = edNick.strip()
                                        edDir = base_dir + \
                                            '/accounts/' + edNick + \
                                            '@' + domain
                                        if os.path.isdir(edDir):
                                            setRole(base_dir,
                                                    edNick, domain,
                                                    'counselor')
                                else:
                                    # nicknames on separate lines
                                    eds = fields['counselors'].split('\n')
                                    try:
                                        with open(counselorsFile,
                                                  'w+') as edFile:
                                            for edNick in eds:
                                                edNick = edNick.strip()
                                                edDir = \
                                                    base_dir + \
                                                    '/accounts/' + edNick + \
                                                    '@' + domain
                                                if os.path.isdir(edDir):
                                                    edFile.write(edNick + '\n')
                                    except OSError as ex:
                                        print('EX: ' +
                                              'unable to write counselors ' +
                                              counselorsFile + ' ' + str(ex))

                                    for edNick in eds:
                                        edNick = edNick.strip()
                                        edDir = \
                                            base_dir + \
                                            '/accounts/' + \
                                            edNick + '@' + \
                                            domain
                                        if os.path.isdir(edDir):
                                            setRole(base_dir,
                                                    edNick, domain,
                                                    'counselor')

                        # change site artists list
                        if fields.get('artists'):
                            if path.startswith('/users/' +
                                               adminNickname + '/'):
                                artistsFile = \
                                    base_dir + \
                                    '/accounts/artists.txt'
                                clearArtistStatus(base_dir)
                                if ',' in fields['artists']:
                                    # if the list was given as comma separated
                                    eds = fields['artists'].split(',')
                                    try:
                                        with open(artistsFile, 'w+') as edFile:
                                            for edNick in eds:
                                                edNick = edNick.strip()
                                                edDir = base_dir + \
                                                    '/accounts/' + edNick + \
                                                    '@' + domain
                                                if os.path.isdir(edDir):
                                                    edFile.write(edNick + '\n')
                                    except OSError as ex:
                                        print('EX: unable to write artists ' +
                                              artistsFile + ' ' + str(ex))

                                    for edNick in eds:
                                        edNick = edNick.strip()
                                        edDir = base_dir + \
                                            '/accounts/' + edNick + \
                                            '@' + domain
                                        if os.path.isdir(edDir):
                                            setRole(base_dir,
                                                    edNick, domain,
                                                    'artist')
                                else:
                                    # nicknames on separate lines
                                    eds = fields['artists'].split('\n')
                                    try:
                                        with open(artistsFile, 'w+') as edFile:
                                            for edNick in eds:
                                                edNick = edNick.strip()
                                                edDir = \
                                                    base_dir + \
                                                    '/accounts/' + edNick + \
                                                    '@' + domain
                                                if os.path.isdir(edDir):
                                                    edFile.write(edNick + '\n')
                                    except OSError as ex:
                                        print('EX: unable to write artists ' +
                                              artistsFile + ' ' + str(ex))

                                    for edNick in eds:
                                        edNick = edNick.strip()
                                        edDir = \
                                            base_dir + \
                                            '/accounts/' + \
                                            edNick + '@' + \
                                            domain
                                        if os.path.isdir(edDir):
                                            setRole(base_dir,
                                                    edNick, domain,
                                                    'artist')

                    # remove scheduled posts
                    if fields.get('removeScheduledPosts'):
                        if fields['removeScheduledPosts'] == 'on':
                            removeScheduledPosts(base_dir,
                                                 nickname, domain)

                    # approve followers
                    if onFinalWelcomeScreen:
                        # Default setting created via the welcome screen
                        actorJson['manuallyApprovesFollowers'] = True
                        actorChanged = True
                    else:
                        approveFollowers = False
                        if fields.get('approveFollowers'):
                            if fields['approveFollowers'] == 'on':
                                approveFollowers = True
                        if approveFollowers != \
                           actorJson['manuallyApprovesFollowers']:
                            actorJson['manuallyApprovesFollowers'] = \
                                approveFollowers
                            actorChanged = True

                    # remove a custom font
                    if fields.get('removeCustomFont'):
                        if (fields['removeCustomFont'] == 'on' and
                            (isArtist(base_dir, nickname) or
                             path.startswith('/users/' +
                                             adminNickname + '/'))):
                            fontExt = ('woff', 'woff2', 'otf', 'ttf')
                            for ext in fontExt:
                                if os.path.isfile(base_dir +
                                                  '/fonts/custom.' + ext):
                                    try:
                                        os.remove(base_dir +
                                                  '/fonts/custom.' + ext)
                                    except OSError:
                                        print('EX: _profileUpdate ' +
                                              'unable to delete ' +
                                              base_dir +
                                              '/fonts/custom.' + ext)
                                if os.path.isfile(base_dir +
                                                  '/fonts/custom.' + ext +
                                                  '.etag'):
                                    try:
                                        os.remove(base_dir +
                                                  '/fonts/custom.' + ext +
                                                  '.etag')
                                    except OSError:
                                        print('EX: _profileUpdate ' +
                                              'unable to delete ' +
                                              base_dir + '/fonts/custom.' +
                                              ext + '.etag')
                            currTheme = getTheme(base_dir)
                            if currTheme:
                                self.server.themeName = currTheme
                                allow_local_network_access = \
                                    self.server.allow_local_network_access
                                setTheme(base_dir, currTheme, domain,
                                         allow_local_network_access,
                                         systemLanguage)
                                self.server.textModeBanner = \
                                    getTextModeBanner(base_dir)
                                self.server.iconsCache = {}
                                self.server.fontsCache = {}
                                self.server.show_publish_as_icon = \
                                    getConfigParam(base_dir,
                                                   'show_publish_as_icon')
                                self.server.full_width_tl_button_header = \
                                    getConfigParam(base_dir,
                                                   'fullWidthTimeline' +
                                                   'ButtonHeader')
                                self.server.icons_as_buttons = \
                                    getConfigParam(base_dir,
                                                   'icons_as_buttons')
                                self.server.rss_icon_at_top = \
                                    getConfigParam(base_dir,
                                                   'rss_icon_at_top')
                                self.server.publish_button_at_top = \
                                    getConfigParam(base_dir,
                                                   'publish_button_at_top')

                    # only receive DMs from accounts you follow
                    followDMsFilename = \
                        acctDir(base_dir, nickname, domain) + '/.followDMs'
                    if onFinalWelcomeScreen:
                        # initial default setting created via
                        # the welcome screen
                        try:
                            with open(followDMsFilename, 'w+') as fFile:
                                fFile.write('\n')
                        except OSError:
                            print('EX: unable to write follow DMs ' +
                                  followDMsFilename)
                        actorChanged = True
                    else:
                        followDMsActive = False
                        if fields.get('followDMs'):
                            if fields['followDMs'] == 'on':
                                followDMsActive = True
                                try:
                                    with open(followDMsFilename,
                                              'w+') as fFile:
                                        fFile.write('\n')
                                except OSError:
                                    print('EX: unable to write follow DMs 2 ' +
                                          followDMsFilename)
                        if not followDMsActive:
                            if os.path.isfile(followDMsFilename):
                                try:
                                    os.remove(followDMsFilename)
                                except OSError:
                                    print('EX: _profileUpdate ' +
                                          'unable to delete ' +
                                          followDMsFilename)

                    # remove Twitter retweets
                    removeTwitterFilename = \
                        acctDir(base_dir, nickname, domain) + \
                        '/.removeTwitter'
                    removeTwitterActive = False
                    if fields.get('removeTwitter'):
                        if fields['removeTwitter'] == 'on':
                            removeTwitterActive = True
                            try:
                                with open(removeTwitterFilename,
                                          'w+') as rFile:
                                    rFile.write('\n')
                            except OSError:
                                print('EX: unable to write remove twitter ' +
                                      removeTwitterFilename)
                    if not removeTwitterActive:
                        if os.path.isfile(removeTwitterFilename):
                            try:
                                os.remove(removeTwitterFilename)
                            except OSError:
                                print('EX: _profileUpdate ' +
                                      'unable to delete ' +
                                      removeTwitterFilename)

                    # hide Like button
                    hideLikeButtonFile = \
                        acctDir(base_dir, nickname, domain) + \
                        '/.hideLikeButton'
                    notifyLikesFilename = \
                        acctDir(base_dir, nickname, domain) + \
                        '/.notifyLikes'
                    hideLikeButtonActive = False
                    if fields.get('hideLikeButton'):
                        if fields['hideLikeButton'] == 'on':
                            hideLikeButtonActive = True
                            try:
                                with open(hideLikeButtonFile, 'w+') as rFile:
                                    rFile.write('\n')
                            except OSError:
                                print('EX: unable to write hide like ' +
                                      hideLikeButtonFile)
                            # remove notify likes selection
                            if os.path.isfile(notifyLikesFilename):
                                try:
                                    os.remove(notifyLikesFilename)
                                except OSError:
                                    print('EX: _profileUpdate ' +
                                          'unable to delete ' +
                                          notifyLikesFilename)
                    if not hideLikeButtonActive:
                        if os.path.isfile(hideLikeButtonFile):
                            try:
                                os.remove(hideLikeButtonFile)
                            except OSError:
                                print('EX: _profileUpdate ' +
                                      'unable to delete ' +
                                      hideLikeButtonFile)

                    # hide Reaction button
                    hideReactionButtonFile = \
                        acctDir(base_dir, nickname, domain) + \
                        '/.hideReactionButton'
                    notifyReactionsFilename = \
                        acctDir(base_dir, nickname, domain) + \
                        '/.notifyReactions'
                    hideReactionButtonActive = False
                    if fields.get('hideReactionButton'):
                        if fields['hideReactionButton'] == 'on':
                            hideReactionButtonActive = True
                            try:
                                with open(hideReactionButtonFile,
                                          'w+') as rFile:
                                    rFile.write('\n')
                            except OSError:
                                print('EX: unable to write hide reaction ' +
                                      hideReactionButtonFile)
                            # remove notify Reaction selection
                            if os.path.isfile(notifyReactionsFilename):
                                try:
                                    os.remove(notifyReactionsFilename)
                                except OSError:
                                    print('EX: _profileUpdate ' +
                                          'unable to delete ' +
                                          notifyReactionsFilename)
                    if not hideReactionButtonActive:
                        if os.path.isfile(hideReactionButtonFile):
                            try:
                                os.remove(hideReactionButtonFile)
                            except OSError:
                                print('EX: _profileUpdate ' +
                                      'unable to delete ' +
                                      hideReactionButtonFile)

                    # notify about new Likes
                    if onFinalWelcomeScreen:
                        # default setting from welcome screen
                        try:
                            with open(notifyLikesFilename, 'w+') as rFile:
                                rFile.write('\n')
                        except OSError:
                            print('EX: unable to write notify likes ' +
                                  notifyLikesFilename)
                        actorChanged = True
                    else:
                        notifyLikesActive = False
                        if fields.get('notifyLikes'):
                            if fields['notifyLikes'] == 'on' and \
                               not hideLikeButtonActive:
                                notifyLikesActive = True
                                try:
                                    with open(notifyLikesFilename,
                                              'w+') as rFile:
                                        rFile.write('\n')
                                except OSError:
                                    print('EX: unable to write notify likes ' +
                                          notifyLikesFilename)
                        if not notifyLikesActive:
                            if os.path.isfile(notifyLikesFilename):
                                try:
                                    os.remove(notifyLikesFilename)
                                except OSError:
                                    print('EX: _profileUpdate ' +
                                          'unable to delete ' +
                                          notifyLikesFilename)

                    notifyReactionsFilename = \
                        acctDir(base_dir, nickname, domain) + \
                        '/.notifyReactions'
                    if onFinalWelcomeScreen:
                        # default setting from welcome screen
                        try:
                            with open(notifyReactionsFilename, 'w+') as rFile:
                                rFile.write('\n')
                        except OSError:
                            print('EX: unable to write notify reactions ' +
                                  notifyReactionsFilename)
                        actorChanged = True
                    else:
                        notifyReactionsActive = False
                        if fields.get('notifyReactions'):
                            if fields['notifyReactions'] == 'on' and \
                               not hideReactionButtonActive:
                                notifyReactionsActive = True
                                try:
                                    with open(notifyReactionsFilename,
                                              'w+') as rFile:
                                        rFile.write('\n')
                                except OSError:
                                    print('EX: unable to write ' +
                                          'notify reactions ' +
                                          notifyReactionsFilename)
                        if not notifyReactionsActive:
                            if os.path.isfile(notifyReactionsFilename):
                                try:
                                    os.remove(notifyReactionsFilename)
                                except OSError:
                                    print('EX: _profileUpdate ' +
                                          'unable to delete ' +
                                          notifyReactionsFilename)

                    # this account is a bot
                    if fields.get('isBot'):
                        if fields['isBot'] == 'on':
                            if actorJson['type'] != 'Service':
                                actorJson['type'] = 'Service'
                                actorChanged = True
                    else:
                        # this account is a group
                        if fields.get('isGroup'):
                            if fields['isGroup'] == 'on':
                                if actorJson['type'] != 'Group':
                                    # only allow admin to create groups
                                    if path.startswith('/users/' +
                                                       adminNickname + '/'):
                                        actorJson['type'] = 'Group'
                                        actorChanged = True
                        else:
                            # this account is a person (default)
                            if actorJson['type'] != 'Person':
                                actorJson['type'] = 'Person'
                                actorChanged = True

                    # grayscale theme
                    if path.startswith('/users/' + adminNickname + '/') or \
                       isArtist(base_dir, nickname):
                        grayscale = False
                        if fields.get('grayscale'):
                            if fields['grayscale'] == 'on':
                                grayscale = True
                        if grayscale:
                            enableGrayscale(base_dir)
                        else:
                            disableGrayscale(base_dir)

                    # low bandwidth images checkbox
                    if path.startswith('/users/' + adminNickname + '/') or \
                       isArtist(base_dir, nickname):
                        currLowBandwidth = \
                            getConfigParam(base_dir, 'low_bandwidth')
                        low_bandwidth = False
                        if fields.get('low_bandwidth'):
                            if fields['low_bandwidth'] == 'on':
                                low_bandwidth = True
                        if currLowBandwidth != low_bandwidth:
                            setConfigParam(base_dir, 'low_bandwidth',
                                           low_bandwidth)
                            self.server.low_bandwidth = low_bandwidth

                    # save filtered words list
                    filterFilename = \
                        acctDir(base_dir, nickname, domain) + \
                        '/filters.txt'
                    if fields.get('filteredWords'):
                        try:
                            with open(filterFilename, 'w+') as filterfile:
                                filterfile.write(fields['filteredWords'])
                        except OSError:
                            print('EX: unable to write filter ' +
                                  filterFilename)
                    else:
                        if os.path.isfile(filterFilename):
                            try:
                                os.remove(filterFilename)
                            except OSError:
                                print('EX: _profileUpdate ' +
                                      'unable to delete filter ' +
                                      filterFilename)

                    # save filtered words within bio list
                    filterBioFilename = \
                        acctDir(base_dir, nickname, domain) + \
                        '/filters_bio.txt'
                    if fields.get('filteredWordsBio'):
                        try:
                            with open(filterBioFilename, 'w+') as filterfile:
                                filterfile.write(fields['filteredWordsBio'])
                        except OSError:
                            print('EX: unable to write bio filter ' +
                                  filterBioFilename)
                    else:
                        if os.path.isfile(filterBioFilename):
                            try:
                                os.remove(filterBioFilename)
                            except OSError:
                                print('EX: _profileUpdate ' +
                                      'unable to delete bio filter ' +
                                      filterBioFilename)

                    # word replacements
                    switchFilename = \
                        acctDir(base_dir, nickname, domain) + \
                        '/replacewords.txt'
                    if fields.get('switchWords'):
                        try:
                            with open(switchFilename, 'w+') as switchfile:
                                switchfile.write(fields['switchWords'])
                        except OSError:
                            print('EX: unable to write switches ' +
                                  switchFilename)
                    else:
                        if os.path.isfile(switchFilename):
                            try:
                                os.remove(switchFilename)
                            except OSError:
                                print('EX: _profileUpdate ' +
                                      'unable to delete ' +
                                      switchFilename)

                    # autogenerated tags
                    autoTagsFilename = \
                        acctDir(base_dir, nickname, domain) + \
                        '/autotags.txt'
                    if fields.get('autoTags'):
                        try:
                            with open(autoTagsFilename, 'w+') as autoTagsFile:
                                autoTagsFile.write(fields['autoTags'])
                        except OSError:
                            print('EX: unable to write auto tags ' +
                                  autoTagsFilename)
                    else:
                        if os.path.isfile(autoTagsFilename):
                            try:
                                os.remove(autoTagsFilename)
                            except OSError:
                                print('EX: _profileUpdate ' +
                                      'unable to delete ' +
                                      autoTagsFilename)

                    # autogenerated content warnings
                    autoCWFilename = \
                        acctDir(base_dir, nickname, domain) + \
                        '/autocw.txt'
                    if fields.get('autoCW'):
                        try:
                            with open(autoCWFilename, 'w+') as autoCWFile:
                                autoCWFile.write(fields['autoCW'])
                        except OSError:
                            print('EX: unable to write auto CW ' +
                                  autoCWFilename)
                    else:
                        if os.path.isfile(autoCWFilename):
                            try:
                                os.remove(autoCWFilename)
                            except OSError:
                                print('EX: _profileUpdate ' +
                                      'unable to delete ' +
                                      autoCWFilename)

                    # save blocked accounts list
                    blockedFilename = \
                        acctDir(base_dir, nickname, domain) + \
                        '/blocking.txt'
                    if fields.get('blocked'):
                        try:
                            with open(blockedFilename, 'w+') as blockedfile:
                                blockedfile.write(fields['blocked'])
                        except OSError:
                            print('EX: unable to write blocked accounts ' +
                                  blockedFilename)
                    else:
                        if os.path.isfile(blockedFilename):
                            try:
                                os.remove(blockedFilename)
                            except OSError:
                                print('EX: _profileUpdate ' +
                                      'unable to delete ' +
                                      blockedFilename)

                    # Save DM allowed instances list.
                    # The allow list for incoming DMs,
                    # if the .followDMs flag file exists
                    dmAllowedInstancesFilename = \
                        acctDir(base_dir, nickname, domain) + \
                        '/dmAllowedinstances.txt'
                    if fields.get('dmAllowedInstances'):
                        try:
                            with open(dmAllowedInstancesFilename,
                                      'w+') as aFile:
                                aFile.write(fields['dmAllowedInstances'])
                        except OSError:
                            print('EX: unable to write allowed DM instances ' +
                                  dmAllowedInstancesFilename)
                    else:
                        if os.path.isfile(dmAllowedInstancesFilename):
                            try:
                                os.remove(dmAllowedInstancesFilename)
                            except OSError:
                                print('EX: _profileUpdate ' +
                                      'unable to delete ' +
                                      dmAllowedInstancesFilename)

                    # save allowed instances list
                    # This is the account level allow list
                    allowedInstancesFilename = \
                        acctDir(base_dir, nickname, domain) + \
                        '/allowedinstances.txt'
                    if fields.get('allowedInstances'):
                        try:
                            with open(allowedInstancesFilename, 'w+') as aFile:
                                aFile.write(fields['allowedInstances'])
                        except OSError:
                            print('EX: unable to write allowed instances ' +
                                  allowedInstancesFilename)
                    else:
                        if os.path.isfile(allowedInstancesFilename):
                            try:
                                os.remove(allowedInstancesFilename)
                            except OSError:
                                print('EX: _profileUpdate ' +
                                      'unable to delete ' +
                                      allowedInstancesFilename)

                    if isModerator(self.server.base_dir, nickname):
                        # set selected content warning lists
                        newListsEnabled = ''
                        for name, item in self.server.CWlists.items():
                            listVarName = getCWlistVariable(name)
                            if fields.get(listVarName):
                                if fields[listVarName] == 'on':
                                    if newListsEnabled:
                                        newListsEnabled += ', ' + name
                                    else:
                                        newListsEnabled += name
                        if newListsEnabled != self.server.lists_enabled:
                            self.server.lists_enabled = newListsEnabled
                            setConfigParam(self.server.base_dir,
                                           "lists_enabled",
                                           newListsEnabled)

                        # save blocked user agents
                        user_agents_blocked = []
                        if fields.get('user_agents_blockedStr'):
                            user_agents_blockedStr = \
                                fields['user_agents_blockedStr']
                            user_agents_blockedList = \
                                user_agents_blockedStr.split('\n')
                            for ua in user_agents_blockedList:
                                if ua in user_agents_blocked:
                                    continue
                                user_agents_blocked.append(ua.strip())
                        if str(self.server.user_agents_blocked) != \
                           str(user_agents_blocked):
                            self.server.user_agents_blocked = \
                                user_agents_blocked
                            user_agents_blockedStr = ''
                            for ua in user_agents_blocked:
                                if user_agents_blockedStr:
                                    user_agents_blockedStr += ','
                                user_agents_blockedStr += ua
                            setConfigParam(base_dir, 'user_agents_blocked',
                                           user_agents_blockedStr)

                        # save peertube instances list
                        peertubeInstancesFile = \
                            base_dir + '/accounts/peertube.txt'
                        if fields.get('ptInstances'):
                            self.server.peertubeInstances.clear()
                            try:
                                with open(peertubeInstancesFile,
                                          'w+') as aFile:
                                    aFile.write(fields['ptInstances'])
                            except OSError:
                                print('EX: unable to write peertube ' +
                                      peertubeInstancesFile)
                            ptInstancesList = \
                                fields['ptInstances'].split('\n')
                            if ptInstancesList:
                                for url in ptInstancesList:
                                    url = url.strip()
                                    if not url:
                                        continue
                                    if url in self.server.peertubeInstances:
                                        continue
                                    self.server.peertubeInstances.append(url)
                        else:
                            if os.path.isfile(peertubeInstancesFile):
                                try:
                                    os.remove(peertubeInstancesFile)
                                except OSError:
                                    print('EX: _profileUpdate ' +
                                          'unable to delete ' +
                                          peertubeInstancesFile)
                            self.server.peertubeInstances.clear()

                    # save git project names list
                    gitProjectsFilename = \
                        acctDir(base_dir, nickname, domain) + \
                        '/gitprojects.txt'
                    if fields.get('gitProjects'):
                        try:
                            with open(gitProjectsFilename, 'w+') as aFile:
                                aFile.write(fields['gitProjects'].lower())
                        except OSError:
                            print('EX: unable to write git ' +
                                  gitProjectsFilename)
                    else:
                        if os.path.isfile(gitProjectsFilename):
                            try:
                                os.remove(gitProjectsFilename)
                            except OSError:
                                print('EX: _profileUpdate ' +
                                      'unable to delete ' +
                                      gitProjectsFilename)

                    # save actor json file within accounts
                    if actorChanged:
                        # update the context for the actor
                        actorJson['@context'] = [
                            'https://www.w3.org/ns/activitystreams',
                            'https://w3id.org/security/v1',
                            getDefaultPersonContext()
                        ]
                        if actorJson.get('nomadicLocations'):
                            del actorJson['nomadicLocations']
                        if not actorJson.get('featured'):
                            actorJson['featured'] = \
                                actorJson['id'] + '/collections/featured'
                        if not actorJson.get('featuredTags'):
                            actorJson['featuredTags'] = \
                                actorJson['id'] + '/collections/tags'
                        randomizeActorImages(actorJson)
                        addActorUpdateTimestamp(actorJson)
                        # save the actor
                        saveJson(actorJson, actorFilename)
                        webfingerUpdate(base_dir,
                                        nickname, domain,
                                        onion_domain,
                                        self.server.cachedWebfingers)
                        # also copy to the actors cache and
                        # personCache in memory
                        storePersonInCache(base_dir,
                                           actorJson['id'], actorJson,
                                           self.server.personCache,
                                           True)
                        # clear any cached images for this actor
                        idStr = actorJson['id'].replace('/', '-')
                        removeAvatarFromCache(base_dir, idStr)
                        # save the actor to the cache
                        actorCacheFilename = \
                            base_dir + '/cache/actors/' + \
                            actorJson['id'].replace('/', '#') + '.json'
                        saveJson(actorJson, actorCacheFilename)
                        # send profile update to followers
                        pubNumber, pubDate = getStatusNumber()
                        updateActorJson = getActorUpdateJson(actorJson)
                        print('Sending actor update: ' + str(updateActorJson))
                        self._postToOutbox(updateActorJson,
                                           self.server.project_version,
                                           nickname)

                    # deactivate the account
                    if fields.get('deactivateThisAccount'):
                        if fields['deactivateThisAccount'] == 'on':
                            deactivateAccount(base_dir,
                                              nickname, domain)
                            self._clearLoginDetails(nickname,
                                                    callingDomain)
                            self.server.POSTbusy = False
                            return

        # redirect back to the profile screen
        self._redirect_headers(actorStr + redirectPath,
                               cookie, callingDomain)
        self.server.POSTbusy = False

    def _progressiveWebAppManifest(self, callingDomain: str,
                                   GETstartTime) -> None:
        """gets the PWA manifest
        """
        app1 = "https://f-droid.org/en/packages/eu.siacs.conversations"
        app2 = "https://staging.f-droid.org/en/packages/im.vector.app"
        manifest = {
            "name": "Epicyon",
            "short_name": "Epicyon",
            "start_url": "/index.html",
            "display": "standalone",
            "background_color": "black",
            "theme_color": "grey",
            "orientation": "portrait-primary",
            "categories": ["microblog", "fediverse", "activitypub"],
            "screenshots": [
                {
                    "src": "/mobile.jpg",
                    "sizes": "418x851",
                    "type": "image/jpeg"
                },
                {
                    "src": "/mobile_person.jpg",
                    "sizes": "429x860",
                    "type": "image/jpeg"
                },
                {
                    "src": "/mobile_search.jpg",
                    "sizes": "422x861",
                    "type": "image/jpeg"
                }
            ],
            "icons": [
                {
                    "src": "/logo72.png",
                    "type": "image/png",
                    "sizes": "72x72"
                },
                {
                    "src": "/logo96.png",
                    "type": "image/png",
                    "sizes": "96x96"
                },
                {
                    "src": "/logo128.png",
                    "type": "image/png",
                    "sizes": "128x128"
                },
                {
                    "src": "/logo144.png",
                    "type": "image/png",
                    "sizes": "144x144"
                },
                {
                    "src": "/logo150.png",
                    "type": "image/png",
                    "sizes": "150x150"
                },
                {
                    "src": "/apple-touch-icon.png",
                    "type": "image/png",
                    "sizes": "180x180"
                },
                {
                    "src": "/logo192.png",
                    "type": "image/png",
                    "sizes": "192x192"
                },
                {
                    "src": "/logo256.png",
                    "type": "image/png",
                    "sizes": "256x256"
                },
                {
                    "src": "/logo512.png",
                    "type": "image/png",
                    "sizes": "512x512"
                }
            ],
            "related_applications": [
                {
                    "platform": "fdroid",
                    "url": app1
                },
                {
                    "platform": "fdroid",
                    "url": app2
                }
            ]
        }
        msg = json.dumps(manifest,
                         ensure_ascii=False).encode('utf-8')
        msglen = len(msg)
        self._set_headers('application/json', msglen,
                          None, callingDomain, False)
        self._write(msg)
        if self.server.debug:
            print('Sent manifest: ' + callingDomain)
        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', '_progressiveWebAppManifest',
                           self.server.debug)

    def _browserConfig(self, callingDomain: str, GETstartTime) -> None:
        """Used by MS Windows to put an icon on the desktop if you
        link to a website
        """
        xmlStr = \
            '<?xml version="1.0" encoding="utf-8"?>\n' + \
            '<browserconfig>\n' + \
            '  <msapplication>\n' + \
            '    <tile>\n' + \
            '      <square150x150logo src="/logo150.png"/>\n' + \
            '      <TileColor>#eeeeee</TileColor>\n' + \
            '    </tile>\n' + \
            '  </msapplication>\n' + \
            '</browserconfig>'

        msg = json.dumps(xmlStr,
                         ensure_ascii=False).encode('utf-8')
        msglen = len(msg)
        self._set_headers('application/xrd+xml', msglen,
                          None, callingDomain, False)
        self._write(msg)
        if self.server.debug:
            print('Sent browserconfig: ' + callingDomain)
        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', '_browserConfig',
                           self.server.debug)

    def _getFavicon(self, callingDomain: str,
                    base_dir: str, debug: bool,
                    favFilename: str) -> None:
        """Return the site favicon or default newswire favicon
        """
        favType = 'image/x-icon'
        if self._hasAccept(callingDomain):
            if 'image/webp' in self.headers['Accept']:
                favType = 'image/webp'
                favFilename = favFilename.split('.')[0] + '.webp'
            if 'image/avif' in self.headers['Accept']:
                favType = 'image/avif'
                favFilename = favFilename.split('.')[0] + '.avif'
        if not self.server.themeName:
            self.themeName = getConfigParam(base_dir, 'theme')
        if not self.server.themeName:
            self.server.themeName = 'default'
        # custom favicon
        faviconFilename = \
            base_dir + '/theme/' + self.server.themeName + \
            '/icons/' + favFilename
        if not favFilename.endswith('.ico'):
            if not os.path.isfile(faviconFilename):
                if favFilename.endswith('.webp'):
                    favFilename = favFilename.replace('.webp', '.ico')
                elif favFilename.endswith('.avif'):
                    favFilename = favFilename.replace('.avif', '.ico')
        if not os.path.isfile(faviconFilename):
            # default favicon
            faviconFilename = \
                base_dir + '/theme/default/icons/' + favFilename
        if self._etag_exists(faviconFilename):
            # The file has not changed
            if debug:
                print('favicon icon has not changed: ' + callingDomain)
            self._304()
            return
        if self.server.iconsCache.get(favFilename):
            favBinary = self.server.iconsCache[favFilename]
            self._set_headers_etag(faviconFilename,
                                   favType,
                                   favBinary, None,
                                   self.server.domainFull,
                                   False, None)
            self._write(favBinary)
            if debug:
                print('Sent favicon from cache: ' + callingDomain)
            return
        else:
            if os.path.isfile(faviconFilename):
                favBinary = None
                try:
                    with open(faviconFilename, 'rb') as favFile:
                        favBinary = favFile.read()
                except OSError:
                    print('EX: unable to read favicon ' + faviconFilename)
                if favBinary:
                    self._set_headers_etag(faviconFilename,
                                           favType,
                                           favBinary, None,
                                           self.server.domainFull,
                                           False, None)
                    self._write(favBinary)
                    self.server.iconsCache[favFilename] = favBinary
                    if self.server.debug:
                        print('Sent favicon from file: ' + callingDomain)
                    return
        if debug:
            print('favicon not sent: ' + callingDomain)
        self._404()

    def _getSpeaker(self, callingDomain: str, path: str,
                    base_dir: str, domain: str, debug: bool) -> None:
        """Returns the speaker file used for TTS and
        accessed via c2s
        """
        nickname = path.split('/users/')[1]
        if '/' in nickname:
            nickname = nickname.split('/')[0]
        speakerFilename = \
            acctDir(base_dir, nickname, domain) + '/speaker.json'
        if not os.path.isfile(speakerFilename):
            self._404()
            return

        speakerJson = loadJson(speakerFilename)
        msg = json.dumps(speakerJson,
                         ensure_ascii=False).encode('utf-8')
        msglen = len(msg)
        self._set_headers('application/json', msglen,
                          None, callingDomain, False)
        self._write(msg)

    def _getExportedTheme(self, callingDomain: str, path: str,
                          base_dir: str, domainFull: str,
                          debug: bool) -> None:
        """Returns an exported theme zip file
        """
        filename = path.split('/exports/', 1)[1]
        filename = base_dir + '/exports/' + filename
        if os.path.isfile(filename):
            exportBinary = None
            try:
                with open(filename, 'rb') as fp:
                    exportBinary = fp.read()
            except OSError:
                print('EX: unable to read theme export ' + filename)
            if exportBinary:
                exportType = 'application/zip'
                self._set_headers_etag(filename, exportType,
                                       exportBinary, None,
                                       domainFull, False, None)
                self._write(exportBinary)
        self._404()

    def _getFonts(self, callingDomain: str, path: str,
                  base_dir: str, debug: bool,
                  GETstartTime) -> None:
        """Returns a font
        """
        fontStr = path.split('/fonts/')[1]
        if fontStr.endswith('.otf') or \
           fontStr.endswith('.ttf') or \
           fontStr.endswith('.woff') or \
           fontStr.endswith('.woff2'):
            if fontStr.endswith('.otf'):
                fontType = 'font/otf'
            elif fontStr.endswith('.ttf'):
                fontType = 'font/ttf'
            elif fontStr.endswith('.woff'):
                fontType = 'font/woff'
            else:
                fontType = 'font/woff2'
            fontFilename = \
                base_dir + '/fonts/' + fontStr
            if self._etag_exists(fontFilename):
                # The file has not changed
                self._304()
                return
            if self.server.fontsCache.get(fontStr):
                fontBinary = self.server.fontsCache[fontStr]
                self._set_headers_etag(fontFilename,
                                       fontType,
                                       fontBinary, None,
                                       self.server.domainFull, False, None)
                self._write(fontBinary)
                if debug:
                    print('font sent from cache: ' +
                          path + ' ' + callingDomain)
                fitnessPerformance(GETstartTime, self.server.fitness,
                                   '_GET', '_getFonts cache',
                                   self.server.debug)
                return
            else:
                if os.path.isfile(fontFilename):
                    fontBinary = None
                    try:
                        with open(fontFilename, 'rb') as fontFile:
                            fontBinary = fontFile.read()
                    except OSError:
                        print('EX: unable to load font ' + fontFilename)
                    if fontBinary:
                        self._set_headers_etag(fontFilename,
                                               fontType,
                                               fontBinary, None,
                                               self.server.domainFull,
                                               False, None)
                        self._write(fontBinary)
                        self.server.fontsCache[fontStr] = fontBinary
                    if debug:
                        print('font sent from file: ' +
                              path + ' ' + callingDomain)
                    fitnessPerformance(GETstartTime, self.server.fitness,
                                       '_GET', '_getFonts',
                                       self.server.debug)
                    return
        if debug:
            print('font not found: ' + path + ' ' + callingDomain)
        self._404()

    def _getRSS2feed(self, authorized: bool,
                     callingDomain: str, path: str,
                     base_dir: str, http_prefix: str,
                     domain: str, port: int, proxy_type: str,
                     GETstartTime,
                     debug: bool) -> None:
        """Returns an RSS2 feed for the blog
        """
        nickname = path.split('/blog/')[1]
        if '/' in nickname:
            nickname = nickname.split('/')[0]
        if not nickname.startswith('rss.'):
            accountDir = acctDir(self.server.base_dir, nickname, domain)
            if os.path.isdir(accountDir):
                if not self._establishSession("RSS request"):
                    return

                msg = \
                    htmlBlogPageRSS2(authorized,
                                     self.server.session,
                                     base_dir,
                                     http_prefix,
                                     self.server.translate,
                                     nickname,
                                     domain,
                                     port,
                                     maxPostsInRSSFeed, 1,
                                     True,
                                     self.server.systemLanguage)
                if msg is not None:
                    msg = msg.encode('utf-8')
                    msglen = len(msg)
                    self._set_headers('text/xml', msglen,
                                      None, callingDomain, True)
                    self._write(msg)
                    if debug:
                        print('Sent rss2 feed: ' +
                              path + ' ' + callingDomain)
                    fitnessPerformance(GETstartTime, self.server.fitness,
                                       '_GET', '_getRSS2feed',
                                       debug)
                    return
        if debug:
            print('Failed to get rss2 feed: ' +
                  path + ' ' + callingDomain)
        self._404()

    def _getRSS2site(self, authorized: bool,
                     callingDomain: str, path: str,
                     base_dir: str, http_prefix: str,
                     domainFull: str, port: int, proxy_type: str,
                     translate: {},
                     GETstartTime,
                     debug: bool) -> None:
        """Returns an RSS2 feed for all blogs on this instance
        """
        if not self._establishSession("getRSS2site"):
            self._404()
            return

        msg = ''
        for subdir, dirs, files in os.walk(base_dir + '/accounts'):
            for acct in dirs:
                if not isAccountDir(acct):
                    continue
                nickname = acct.split('@')[0]
                domain = acct.split('@')[1]
                msg += \
                    htmlBlogPageRSS2(authorized,
                                     self.server.session,
                                     base_dir,
                                     http_prefix,
                                     self.server.translate,
                                     nickname,
                                     domain,
                                     port,
                                     maxPostsInRSSFeed, 1,
                                     False,
                                     self.server.systemLanguage)
            break
        if msg:
            msg = rss2Header(http_prefix,
                             'news', domainFull,
                             'Site', translate) + msg + rss2Footer()

            msg = msg.encode('utf-8')
            msglen = len(msg)
            self._set_headers('text/xml', msglen,
                              None, callingDomain, True)
            self._write(msg)
            if debug:
                print('Sent rss2 feed: ' +
                      path + ' ' + callingDomain)
            fitnessPerformance(GETstartTime, self.server.fitness,
                               '_GET', '_getRSS2site',
                               debug)
            return
        if debug:
            print('Failed to get rss2 feed: ' +
                  path + ' ' + callingDomain)
        self._404()

    def _getNewswireFeed(self, authorized: bool,
                         callingDomain: str, path: str,
                         base_dir: str, http_prefix: str,
                         domain: str, port: int, proxy_type: str,
                         GETstartTime,
                         debug: bool) -> None:
        """Returns the newswire feed
        """
        if not self._establishSession("getNewswireFeed"):
            self._404()
            return

        msg = getRSSfromDict(self.server.base_dir, self.server.newswire,
                             self.server.http_prefix,
                             self.server.domainFull,
                             'Newswire', self.server.translate)
        if msg:
            msg = msg.encode('utf-8')
            msglen = len(msg)
            self._set_headers('text/xml', msglen,
                              None, callingDomain, True)
            self._write(msg)
            if debug:
                print('Sent rss2 newswire feed: ' +
                      path + ' ' + callingDomain)
            fitnessPerformance(GETstartTime, self.server.fitness,
                               '_GET', '_getNewswireFeed',
                               debug)
            return
        if debug:
            print('Failed to get rss2 newswire feed: ' +
                  path + ' ' + callingDomain)
        self._404()

    def _getHashtagCategoriesFeed(self, authorized: bool,
                                  callingDomain: str, path: str,
                                  base_dir: str, http_prefix: str,
                                  domain: str, port: int, proxy_type: str,
                                  GETstartTime,
                                  debug: bool) -> None:
        """Returns the hashtag categories feed
        """
        if not self._establishSession("getHashtagCategoriesFeed"):
            self._404()
            return

        hashtagCategories = None
        msg = \
            getHashtagCategoriesFeed(base_dir, hashtagCategories)
        if msg:
            msg = msg.encode('utf-8')
            msglen = len(msg)
            self._set_headers('text/xml', msglen,
                              None, callingDomain, True)
            self._write(msg)
            if debug:
                print('Sent rss2 categories feed: ' +
                      path + ' ' + callingDomain)
            fitnessPerformance(GETstartTime, self.server.fitness,
                               '_GET', '_getHashtagCategoriesFeed', debug)
            return
        if debug:
            print('Failed to get rss2 categories feed: ' +
                  path + ' ' + callingDomain)
        self._404()

    def _getRSS3feed(self, authorized: bool,
                     callingDomain: str, path: str,
                     base_dir: str, http_prefix: str,
                     domain: str, port: int, proxy_type: str,
                     GETstartTime,
                     debug: bool, systemLanguage: str) -> None:
        """Returns an RSS3 feed
        """
        nickname = path.split('/blog/')[1]
        if '/' in nickname:
            nickname = nickname.split('/')[0]
        if not nickname.startswith('rss.'):
            accountDir = acctDir(base_dir, nickname, domain)
            if os.path.isdir(accountDir):
                if not self._establishSession("getRSS3Feed"):
                    self._404()
                    return
                msg = \
                    htmlBlogPageRSS3(authorized,
                                     self.server.session,
                                     base_dir, http_prefix,
                                     self.server.translate,
                                     nickname, domain, port,
                                     maxPostsInRSSFeed, 1,
                                     systemLanguage)
                if msg is not None:
                    msg = msg.encode('utf-8')
                    msglen = len(msg)
                    self._set_headers('text/plain; charset=utf-8',
                                      msglen, None, callingDomain, True)
                    self._write(msg)
                    if self.server.debug:
                        print('Sent rss3 feed: ' +
                              path + ' ' + callingDomain)
                    fitnessPerformance(GETstartTime, self.server.fitness,
                                       '_GET', '_getRSS3feed', debug)
                    return
        if debug:
            print('Failed to get rss3 feed: ' +
                  path + ' ' + callingDomain)
        self._404()

    def _showPersonOptions(self, callingDomain: str, path: str,
                           base_dir: str, http_prefix: str,
                           domain: str, domainFull: str,
                           GETstartTime,
                           onion_domain: str, i2p_domain: str,
                           cookie: str, debug: bool,
                           authorized: bool) -> None:
        """Show person options screen
        """
        backToPath = ''
        optionsStr = path.split('?options=')[1]
        originPathStr = path.split('?options=')[0]
        if ';' in optionsStr and '/users/news/' not in path:
            pageNumber = 1
            optionsList = optionsStr.split(';')
            optionsActor = optionsList[0]
            optionsPageNumber = optionsList[1]
            optionsProfileUrl = optionsList[2]
            if '.' in optionsProfileUrl and \
               optionsProfileUrl.startswith('/members/'):
                ext = optionsProfileUrl.split('.')[-1]
                optionsProfileUrl = optionsProfileUrl.split('/members/')[1]
                optionsProfileUrl = optionsProfileUrl.replace('.' + ext, '')
                optionsProfileUrl = \
                    '/users/' + optionsProfileUrl + '/avatar.' + ext
                backToPath = 'moderation'
            if optionsPageNumber.isdigit():
                pageNumber = int(optionsPageNumber)
            optionsLink = None
            if len(optionsList) > 3:
                optionsLink = optionsList[3]
            isGroup = False
            donateUrl = None
            websiteUrl = None
            EnigmaPubKey = None
            PGPpubKey = None
            PGPfingerprint = None
            xmppAddress = None
            matrixAddress = None
            blogAddress = None
            toxAddress = None
            briarAddress = None
            jamiAddress = None
            cwtchAddress = None
            ssbAddress = None
            emailAddress = None
            lockedAccount = False
            alsoKnownAs = None
            movedTo = ''
            actorJson = getPersonFromCache(base_dir,
                                           optionsActor,
                                           self.server.personCache,
                                           True)
            if actorJson:
                if actorJson.get('movedTo'):
                    movedTo = actorJson['movedTo']
                    if '"' in movedTo:
                        movedTo = movedTo.split('"')[1]
                if actorJson['type'] == 'Group':
                    isGroup = True
                lockedAccount = getLockedAccount(actorJson)
                donateUrl = getDonationUrl(actorJson)
                websiteUrl = getWebsite(actorJson, self.server.translate)
                xmppAddress = getXmppAddress(actorJson)
                matrixAddress = getMatrixAddress(actorJson)
                ssbAddress = getSSBAddress(actorJson)
                blogAddress = getBlogAddress(actorJson)
                toxAddress = getToxAddress(actorJson)
                briarAddress = getBriarAddress(actorJson)
                jamiAddress = getJamiAddress(actorJson)
                cwtchAddress = getCwtchAddress(actorJson)
                emailAddress = getEmailAddress(actorJson)
                EnigmaPubKey = getEnigmaPubKey(actorJson)
                PGPpubKey = getPGPpubKey(actorJson)
                PGPfingerprint = getPGPfingerprint(actorJson)
                if actorJson.get('alsoKnownAs'):
                    alsoKnownAs = actorJson['alsoKnownAs']

            if self.server.session:
                checkForChangedActor(self.server.session,
                                     self.server.base_dir,
                                     self.server.http_prefix,
                                     self.server.domainFull,
                                     optionsActor, optionsProfileUrl,
                                     self.server.personCache, 5)

            accessKeys = self.server.accessKeys
            if '/users/' in path:
                nickname = path.split('/users/')[1]
                if '/' in nickname:
                    nickname = nickname.split('/')[0]
                if self.server.keyShortcuts.get(nickname):
                    accessKeys = self.server.keyShortcuts[nickname]
            msg = htmlPersonOptions(self.server.defaultTimeline,
                                    self.server.cssCache,
                                    self.server.translate,
                                    base_dir, domain,
                                    domainFull,
                                    originPathStr,
                                    optionsActor,
                                    optionsProfileUrl,
                                    optionsLink,
                                    pageNumber, donateUrl, websiteUrl,
                                    xmppAddress, matrixAddress,
                                    ssbAddress, blogAddress,
                                    toxAddress, briarAddress,
                                    jamiAddress, cwtchAddress,
                                    EnigmaPubKey,
                                    PGPpubKey, PGPfingerprint,
                                    emailAddress,
                                    self.server.dormant_months,
                                    backToPath,
                                    lockedAccount,
                                    movedTo, alsoKnownAs,
                                    self.server.textModeBanner,
                                    self.server.news_instance,
                                    authorized,
                                    accessKeys, isGroup).encode('utf-8')
            msglen = len(msg)
            self._set_headers('text/html', msglen,
                              cookie, callingDomain, False)
            self._write(msg)
            fitnessPerformance(GETstartTime, self.server.fitness,
                               '_GET', '_showPersonOptions', debug)
            return

        if '/users/news/' in path:
            self._redirect_headers(originPathStr + '/tlfeatures',
                                   cookie, callingDomain)
            return

        if callingDomain.endswith('.onion') and onion_domain:
            originPathStrAbsolute = \
                'http://' + onion_domain + originPathStr
        elif callingDomain.endswith('.i2p') and i2p_domain:
            originPathStrAbsolute = \
                'http://' + i2p_domain + originPathStr
        else:
            originPathStrAbsolute = \
                http_prefix + '://' + domainFull + originPathStr
        self._redirect_headers(originPathStrAbsolute, cookie,
                               callingDomain)

    def _showMedia(self, callingDomain: str,
                   path: str, base_dir: str,
                   GETstartTime) -> None:
        """Returns a media file
        """
        if isImageFile(path) or \
           pathIsVideo(path) or \
           pathIsAudio(path):
            mediaStr = path.split('/media/')[1]
            mediaFilename = base_dir + '/media/' + mediaStr
            if os.path.isfile(mediaFilename):
                if self._etag_exists(mediaFilename):
                    # The file has not changed
                    self._304()
                    return

                mediaFileType = mediaFileMimeType(mediaFilename)

                t = os.path.getmtime(mediaFilename)
                lastModifiedTime = datetime.datetime.fromtimestamp(t)
                lastModifiedTimeStr = \
                    lastModifiedTime.strftime('%a, %d %b %Y %H:%M:%S GMT')

                mediaBinary = None
                try:
                    with open(mediaFilename, 'rb') as avFile:
                        mediaBinary = avFile.read()
                except OSError:
                    print('EX: unable to read media binary ' + mediaFilename)
                if mediaBinary:
                    self._set_headers_etag(mediaFilename, mediaFileType,
                                           mediaBinary, None,
                                           None, True,
                                           lastModifiedTimeStr)
                    self._write(mediaBinary)
                fitnessPerformance(GETstartTime, self.server.fitness,
                                   '_GET', '_showMedia', self.server.debug)
                return
        self._404()

    def _getOntology(self, callingDomain: str,
                     path: str, base_dir: str,
                     GETstartTime) -> None:
        """Returns an ontology file
        """
        if '.owl' in path or '.rdf' in path or '.json' in path:
            if '/ontologies/' in path:
                ontologyStr = path.split('/ontologies/')[1].replace('#', '')
            else:
                ontologyStr = path.split('/data/')[1].replace('#', '')
            ontologyFilename = None
            ontologyFileType = 'application/rdf+xml'
            if ontologyStr.startswith('DFC_'):
                ontologyFilename = base_dir + '/ontology/DFC/' + ontologyStr
            else:
                ontologyStr = ontologyStr.replace('/data/', '')
                ontologyFilename = base_dir + '/ontology/' + ontologyStr
            if ontologyStr.endswith('.json'):
                ontologyFileType = 'application/ld+json'
            if os.path.isfile(ontologyFilename):
                ontologyFile = None
                try:
                    with open(ontologyFilename, 'r') as fp:
                        ontologyFile = fp.read()
                except OSError:
                    print('EX: unable to read ontology ' + ontologyFilename)
                if ontologyFile:
                    ontologyFile = \
                        ontologyFile.replace('static.datafoodconsortium.org',
                                             callingDomain)
                    if not callingDomain.endswith('.i2p') and \
                       not callingDomain.endswith('.onion'):
                        ontologyFile = \
                            ontologyFile.replace('http://' +
                                                 callingDomain,
                                                 'https://' +
                                                 callingDomain)
                    msg = ontologyFile.encode('utf-8')
                    msglen = len(msg)
                    self._set_headers(ontologyFileType, msglen,
                                      None, callingDomain, False)
                    self._write(msg)
                fitnessPerformance(GETstartTime, self.server.fitness,
                                   '_GET', '_getOntology', self.server.debug)
                return
        self._404()

    def _showEmoji(self, callingDomain: str, path: str,
                   base_dir: str, GETstartTime) -> None:
        """Returns an emoji image
        """
        if isImageFile(path):
            emojiStr = path.split('/emoji/')[1]
            emojiFilename = base_dir + '/emoji/' + emojiStr
            if not os.path.isfile(emojiFilename):
                emojiFilename = base_dir + '/emojicustom/' + emojiStr
            if os.path.isfile(emojiFilename):
                if self._etag_exists(emojiFilename):
                    # The file has not changed
                    self._304()
                    return

                mediaImageType = getImageMimeType(emojiFilename)
                mediaBinary = None
                try:
                    with open(emojiFilename, 'rb') as avFile:
                        mediaBinary = avFile.read()
                except OSError:
                    print('EX: unable to read emoji image ' + emojiFilename)
                if mediaBinary:
                    self._set_headers_etag(emojiFilename,
                                           mediaImageType,
                                           mediaBinary, None,
                                           self.server.domainFull,
                                           False, None)
                    self._write(mediaBinary)
                fitnessPerformance(GETstartTime, self.server.fitness,
                                   '_GET', '_showEmoji', self.server.debug)
                return
        self._404()

    def _showIcon(self, callingDomain: str, path: str,
                  base_dir: str, GETstartTime) -> None:
        """Shows an icon
        """
        if not path.endswith('.png'):
            self._404()
            return
        mediaStr = path.split('/icons/')[1]
        if '/' not in mediaStr:
            if not self.server.themeName:
                theme = 'default'
            else:
                theme = self.server.themeName
            iconFilename = mediaStr
        else:
            theme = mediaStr.split('/')[0]
            iconFilename = mediaStr.split('/')[1]
        mediaFilename = \
            base_dir + '/theme/' + theme + '/icons/' + iconFilename
        if self._etag_exists(mediaFilename):
            # The file has not changed
            self._304()
            return
        if self.server.iconsCache.get(mediaStr):
            mediaBinary = self.server.iconsCache[mediaStr]
            mimeTypeStr = mediaFileMimeType(mediaFilename)
            self._set_headers_etag(mediaFilename,
                                   mimeTypeStr,
                                   mediaBinary, None,
                                   self.server.domainFull,
                                   False, None)
            self._write(mediaBinary)
            fitnessPerformance(GETstartTime, self.server.fitness,
                               '_GET', '_showIcon', self.server.debug)
            return
        else:
            if os.path.isfile(mediaFilename):
                mediaBinary = None
                try:
                    with open(mediaFilename, 'rb') as avFile:
                        mediaBinary = avFile.read()
                except OSError:
                    print('EX: unable to read icon image ' + mediaFilename)
                if mediaBinary:
                    mimeType = mediaFileMimeType(mediaFilename)
                    self._set_headers_etag(mediaFilename,
                                           mimeType,
                                           mediaBinary, None,
                                           self.server.domainFull,
                                           False, None)
                    self._write(mediaBinary)
                    self.server.iconsCache[mediaStr] = mediaBinary
                fitnessPerformance(GETstartTime, self.server.fitness,
                                   '_GET', '_showIcon', self.server.debug)
                return
        self._404()

    def _showHelpScreenImage(self, callingDomain: str, path: str,
                             base_dir: str, GETstartTime) -> None:
        """Shows a help screen image
        """
        if not isImageFile(path):
            return
        mediaStr = path.split('/helpimages/')[1]
        if '/' not in mediaStr:
            if not self.server.themeName:
                theme = 'default'
            else:
                theme = self.server.themeName
            iconFilename = mediaStr
        else:
            theme = mediaStr.split('/')[0]
            iconFilename = mediaStr.split('/')[1]
        mediaFilename = \
            base_dir + '/theme/' + theme + '/helpimages/' + iconFilename
        # if there is no theme-specific help image then use the default one
        if not os.path.isfile(mediaFilename):
            mediaFilename = \
                base_dir + '/theme/default/helpimages/' + iconFilename
        if self._etag_exists(mediaFilename):
            # The file has not changed
            self._304()
            return
        if os.path.isfile(mediaFilename):
            mediaBinary = None
            try:
                with open(mediaFilename, 'rb') as avFile:
                    mediaBinary = avFile.read()
            except OSError:
                print('EX: unable to read help image ' + mediaFilename)
            if mediaBinary:
                mimeType = mediaFileMimeType(mediaFilename)
                self._set_headers_etag(mediaFilename,
                                       mimeType,
                                       mediaBinary, None,
                                       self.server.domainFull,
                                       False, None)
                self._write(mediaBinary)
            fitnessPerformance(GETstartTime, self.server.fitness,
                               '_GET', '_showHelpScreenImage',
                               self.server.debug)
            return
        self._404()

    def _showCachedFavicon(self, refererDomain: str, path: str,
                           base_dir: str, GETstartTime) -> None:
        """Shows a favicon image obtained from the cache
        """
        favFile = path.replace('/favicons/', '')
        favFilename = base_dir + urllib.parse.unquote_plus(path)
        print('showCachedFavicon: ' + favFilename)
        if self.server.faviconsCache.get(favFile):
            mediaBinary = self.server.faviconsCache[favFile]
            mimeType = mediaFileMimeType(favFilename)
            self._set_headers_etag(favFilename,
                                   mimeType,
                                   mediaBinary, None,
                                   refererDomain,
                                   False, None)
            self._write(mediaBinary)
            fitnessPerformance(GETstartTime, self.server.fitness,
                               '_GET', '_showCachedFavicon2',
                               self.server.debug)
            return
        if not os.path.isfile(favFilename):
            self._404()
            return
        if self._etag_exists(favFilename):
            # The file has not changed
            self._304()
            return
        mediaBinary = None
        try:
            with open(favFilename, 'rb') as avFile:
                mediaBinary = avFile.read()
        except OSError:
            print('EX: unable to read cached favicon ' + favFilename)
        if mediaBinary:
            mimeType = mediaFileMimeType(favFilename)
            self._set_headers_etag(favFilename,
                                   mimeType,
                                   mediaBinary, None,
                                   refererDomain,
                                   False, None)
            self._write(mediaBinary)
            fitnessPerformance(GETstartTime, self.server.fitness,
                               '_GET', '_showCachedFavicon',
                               self.server.debug)
            self.server.faviconsCache[favFile] = mediaBinary
            return
        self._404()

    def _showCachedAvatar(self, refererDomain: str, path: str,
                          base_dir: str, GETstartTime) -> None:
        """Shows an avatar image obtained from the cache
        """
        mediaFilename = base_dir + '/cache' + path
        if os.path.isfile(mediaFilename):
            if self._etag_exists(mediaFilename):
                # The file has not changed
                self._304()
                return
            mediaBinary = None
            try:
                with open(mediaFilename, 'rb') as avFile:
                    mediaBinary = avFile.read()
            except OSError:
                print('EX: unable to read cached avatar ' + mediaFilename)
            if mediaBinary:
                mimeType = mediaFileMimeType(mediaFilename)
                self._set_headers_etag(mediaFilename,
                                       mimeType,
                                       mediaBinary, None,
                                       refererDomain,
                                       False, None)
                self._write(mediaBinary)
                fitnessPerformance(GETstartTime, self.server.fitness,
                                   '_GET', '_showCachedAvatar',
                                   self.server.debug)
                return
        self._404()

    def _hashtagSearch(self, callingDomain: str,
                       path: str, cookie: str,
                       base_dir: str, http_prefix: str,
                       domain: str, domainFull: str, port: int,
                       onion_domain: str, i2p_domain: str,
                       GETstartTime) -> None:
        """Return the result of a hashtag search
        """
        pageNumber = 1
        if '?page=' in path:
            pageNumberStr = path.split('?page=')[1]
            if '#' in pageNumberStr:
                pageNumberStr = pageNumberStr.split('#')[0]
            if pageNumberStr.isdigit():
                pageNumber = int(pageNumberStr)
        hashtag = path.split('/tags/')[1]
        if '?page=' in hashtag:
            hashtag = hashtag.split('?page=')[0]
        hashtag = urllib.parse.unquote_plus(hashtag)
        if isBlockedHashtag(base_dir, hashtag):
            print('BLOCK: hashtag #' + hashtag)
            msg = htmlHashtagBlocked(self.server.cssCache, base_dir,
                                     self.server.translate).encode('utf-8')
            msglen = len(msg)
            self._login_headers('text/html', msglen, callingDomain)
            self._write(msg)
            return
        nickname = None
        if '/users/' in path:
            nickname = path.split('/users/')[1]
            if '/' in nickname:
                nickname = nickname.split('/')[0]
            if '?' in nickname:
                nickname = nickname.split('?')[0]
        hashtagStr = \
            htmlHashtagSearch(self.server.cssCache,
                              nickname, domain, port,
                              self.server.recentPostsCache,
                              self.server.max_recent_posts,
                              self.server.translate,
                              base_dir, hashtag, pageNumber,
                              maxPostsInHashtagFeed, self.server.session,
                              self.server.cachedWebfingers,
                              self.server.personCache,
                              http_prefix,
                              self.server.project_version,
                              self.server.yt_replace_domain,
                              self.server.twitter_replacement_domain,
                              self.server.show_published_date_only,
                              self.server.peertubeInstances,
                              self.server.allow_local_network_access,
                              self.server.themeName,
                              self.server.systemLanguage,
                              self.server.max_like_count,
                              self.server.signingPrivateKeyPem,
                              self.server.CWlists,
                              self.server.lists_enabled)
        if hashtagStr:
            msg = hashtagStr.encode('utf-8')
            msglen = len(msg)
            self._set_headers('text/html', msglen,
                              cookie, callingDomain, False)
            self._write(msg)
        else:
            originPathStr = path.split('/tags/')[0]
            originPathStrAbsolute = \
                http_prefix + '://' + domainFull + originPathStr
            if callingDomain.endswith('.onion') and onion_domain:
                originPathStrAbsolute = \
                    'http://' + onion_domain + originPathStr
            elif (callingDomain.endswith('.i2p') and onion_domain):
                originPathStrAbsolute = \
                    'http://' + i2p_domain + originPathStr
            self._redirect_headers(originPathStrAbsolute + '/search',
                                   cookie, callingDomain)
        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', '_hashtagSearch',
                           self.server.debug)

    def _hashtagSearchRSS2(self, callingDomain: str,
                           path: str, cookie: str,
                           base_dir: str, http_prefix: str,
                           domain: str, domainFull: str, port: int,
                           onion_domain: str, i2p_domain: str,
                           GETstartTime) -> None:
        """Return an RSS 2 feed for a hashtag
        """
        hashtag = path.split('/tags/rss2/')[1]
        if isBlockedHashtag(base_dir, hashtag):
            self._400()
            return
        nickname = None
        if '/users/' in path:
            actor = \
                http_prefix + '://' + domainFull + path
            nickname = \
                getNicknameFromActor(actor)
        hashtagStr = \
            rssHashtagSearch(nickname,
                             domain, port,
                             self.server.recentPostsCache,
                             self.server.max_recent_posts,
                             self.server.translate,
                             base_dir, hashtag,
                             maxPostsInFeed, self.server.session,
                             self.server.cachedWebfingers,
                             self.server.personCache,
                             http_prefix,
                             self.server.project_version,
                             self.server.yt_replace_domain,
                             self.server.twitter_replacement_domain,
                             self.server.systemLanguage)
        if hashtagStr:
            msg = hashtagStr.encode('utf-8')
            msglen = len(msg)
            self._set_headers('text/xml', msglen,
                              cookie, callingDomain, False)
            self._write(msg)
        else:
            originPathStr = path.split('/tags/rss2/')[0]
            originPathStrAbsolute = \
                http_prefix + '://' + domainFull + originPathStr
            if callingDomain.endswith('.onion') and onion_domain:
                originPathStrAbsolute = \
                    'http://' + onion_domain + originPathStr
            elif (callingDomain.endswith('.i2p') and onion_domain):
                originPathStrAbsolute = \
                    'http://' + i2p_domain + originPathStr
            self._redirect_headers(originPathStrAbsolute + '/search',
                                   cookie, callingDomain)
        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', '_hashtagSearchRSS2',
                           self.server.debug)

    def _announceButton(self, callingDomain: str, path: str,
                        base_dir: str,
                        cookie: str, proxy_type: str,
                        http_prefix: str,
                        domain: str, domainFull: str, port: int,
                        onion_domain: str, i2p_domain: str,
                        GETstartTime,
                        repeatPrivate: bool,
                        debug: bool) -> None:
        """The announce/repeat button was pressed on a post
        """
        pageNumber = 1
        repeatUrl = path.split('?repeat=')[1]
        if '?' in repeatUrl:
            repeatUrl = repeatUrl.split('?')[0]
        timelineBookmark = ''
        if '?bm=' in path:
            timelineBookmark = path.split('?bm=')[1]
            if '?' in timelineBookmark:
                timelineBookmark = timelineBookmark.split('?')[0]
            timelineBookmark = '#' + timelineBookmark
        if '?page=' in path:
            pageNumberStr = path.split('?page=')[1]
            if '?' in pageNumberStr:
                pageNumberStr = pageNumberStr.split('?')[0]
            if '#' in pageNumberStr:
                pageNumberStr = pageNumberStr.split('#')[0]
            if pageNumberStr.isdigit():
                pageNumber = int(pageNumberStr)
        timelineStr = 'inbox'
        if '?tl=' in path:
            timelineStr = path.split('?tl=')[1]
            if '?' in timelineStr:
                timelineStr = timelineStr.split('?')[0]
        actor = path.split('?repeat=')[0]
        self.postToNickname = getNicknameFromActor(actor)
        if not self.postToNickname:
            print('WARN: unable to find nickname in ' + actor)
            actorAbsolute = self._getInstanceUrl(callingDomain) + actor
            actorPathStr = \
                actorAbsolute + '/' + timelineStr + \
                '?page=' + str(pageNumber)
            self._redirect_headers(actorPathStr, cookie,
                                   callingDomain)
            return
        if not self._establishSession("announceButton"):
            self._404()
            return
        self.server.actorRepeat = path.split('?actor=')[1]
        announceToStr = \
            localActorUrl(http_prefix, self.postToNickname, domainFull) + \
            '/followers'
        if not repeatPrivate:
            announceToStr = 'https://www.w3.org/ns/activitystreams#Public'
        announceJson = \
            createAnnounce(self.server.session,
                           base_dir,
                           self.server.federationList,
                           self.postToNickname,
                           domain, port,
                           announceToStr,
                           None, http_prefix,
                           repeatUrl, False, False,
                           self.server.sendThreads,
                           self.server.postLog,
                           self.server.personCache,
                           self.server.cachedWebfingers,
                           debug,
                           self.server.project_version,
                           self.server.signingPrivateKeyPem)
        announceFilename = None
        if announceJson:
            # save the announce straight to the outbox
            # This is because the subsequent send is within a separate thread
            # but the html still needs to be generated before this call ends
            announceId = removeIdEnding(announceJson['id'])
            announceFilename = \
                savePostToBox(base_dir, http_prefix, announceId,
                              self.postToNickname, domainFull,
                              announceJson, 'outbox')

            # clear the icon from the cache so that it gets updated
            if self.server.iconsCache.get('repeat.png'):
                del self.server.iconsCache['repeat.png']

            # send out the announce within a separate thread
            self._postToOutbox(announceJson,
                               self.server.project_version,
                               self.postToNickname)

            fitnessPerformance(GETstartTime, self.server.fitness,
                               '_GET', '_announceButton postToOutboxThread',
                               self.server.debug)

        # generate the html for the announce
        if announceJson and announceFilename:
            if debug:
                print('Generating html post for announce')
            cachedPostFilename = \
                getCachedPostFilename(base_dir, self.postToNickname,
                                      domain, announceJson)
            if debug:
                print('Announced post json: ' + str(announceJson))
                print('Announced post nickname: ' +
                      self.postToNickname + ' ' + domain)
                print('Announced post cache: ' + str(cachedPostFilename))
            showIndividualPostIcons = True
            manuallyApproveFollowers = \
                followerApprovalActive(base_dir,
                                       self.postToNickname, domain)
            showRepeats = not isDM(announceJson)
            individualPostAsHtml(self.server.signingPrivateKeyPem, False,
                                 self.server.recentPostsCache,
                                 self.server.max_recent_posts,
                                 self.server.translate,
                                 pageNumber, base_dir,
                                 self.server.session,
                                 self.server.cachedWebfingers,
                                 self.server.personCache,
                                 self.postToNickname, domain,
                                 self.server.port, announceJson,
                                 None, True,
                                 self.server.allowDeletion,
                                 http_prefix, self.server.project_version,
                                 timelineStr,
                                 self.server.yt_replace_domain,
                                 self.server.twitter_replacement_domain,
                                 self.server.show_published_date_only,
                                 self.server.peertubeInstances,
                                 self.server.allow_local_network_access,
                                 self.server.themeName,
                                 self.server.systemLanguage,
                                 self.server.max_like_count,
                                 showRepeats,
                                 showIndividualPostIcons,
                                 manuallyApproveFollowers,
                                 False, True, False,
                                 self.server.CWlists,
                                 self.server.lists_enabled)

        actorAbsolute = self._getInstanceUrl(callingDomain) + actor
        actorPathStr = \
            actorAbsolute + '/' + timelineStr + '?page=' + \
            str(pageNumber) + timelineBookmark
        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', '_announceButton',
                           self.server.debug)
        self._redirect_headers(actorPathStr, cookie, callingDomain)

    def _undoAnnounceButton(self, callingDomain: str, path: str,
                            base_dir: str,
                            cookie: str, proxy_type: str,
                            http_prefix: str,
                            domain: str, domainFull: str, port: int,
                            onion_domain: str, i2p_domain: str,
                            GETstartTime,
                            repeatPrivate: bool, debug: bool,
                            recentPostsCache: {}) -> None:
        """Undo announce/repeat button was pressed
        """
        pageNumber = 1

        # the post which was referenced by the announce post
        repeatUrl = path.split('?unrepeat=')[1]
        if '?' in repeatUrl:
            repeatUrl = repeatUrl.split('?')[0]

        timelineBookmark = ''
        if '?bm=' in path:
            timelineBookmark = path.split('?bm=')[1]
            if '?' in timelineBookmark:
                timelineBookmark = timelineBookmark.split('?')[0]
            timelineBookmark = '#' + timelineBookmark
        if '?page=' in path:
            pageNumberStr = path.split('?page=')[1]
            if '?' in pageNumberStr:
                pageNumberStr = pageNumberStr.split('?')[0]
            if '#' in pageNumberStr:
                pageNumberStr = pageNumberStr.split('#')[0]
            if pageNumberStr.isdigit():
                pageNumber = int(pageNumberStr)
        timelineStr = 'inbox'
        if '?tl=' in path:
            timelineStr = path.split('?tl=')[1]
            if '?' in timelineStr:
                timelineStr = timelineStr.split('?')[0]
        actor = path.split('?unrepeat=')[0]
        self.postToNickname = getNicknameFromActor(actor)
        if not self.postToNickname:
            print('WARN: unable to find nickname in ' + actor)
            actorAbsolute = self._getInstanceUrl(callingDomain) + actor
            actorPathStr = \
                actorAbsolute + '/' + timelineStr + '?page=' + \
                str(pageNumber)
            self._redirect_headers(actorPathStr, cookie,
                                   callingDomain)
            return
        if not self._establishSession("undoAnnounceButton"):
            self._404()
            return
        undoAnnounceActor = \
            http_prefix + '://' + domainFull + \
            '/users/' + self.postToNickname
        unRepeatToStr = 'https://www.w3.org/ns/activitystreams#Public'
        newUndoAnnounce = {
            "@context": "https://www.w3.org/ns/activitystreams",
            'actor': undoAnnounceActor,
            'type': 'Undo',
            'cc': [undoAnnounceActor + '/followers'],
            'to': [unRepeatToStr],
            'object': {
                'actor': undoAnnounceActor,
                'cc': [undoAnnounceActor + '/followers'],
                'object': repeatUrl,
                'to': [unRepeatToStr],
                'type': 'Announce'
            }
        }
        # clear the icon from the cache so that it gets updated
        if self.server.iconsCache.get('repeat_inactive.png'):
            del self.server.iconsCache['repeat_inactive.png']

        # delete  the announce post
        if '?unannounce=' in path:
            announceUrl = path.split('?unannounce=')[1]
            if '?' in announceUrl:
                announceUrl = announceUrl.split('?')[0]
            postFilename = None
            nickname = getNicknameFromActor(announceUrl)
            if nickname:
                if domainFull + '/users/' + nickname + '/' in announceUrl:
                    postFilename = \
                        locatePost(base_dir, nickname, domain, announceUrl)
            if postFilename:
                deletePost(base_dir, http_prefix,
                           nickname, domain, postFilename,
                           debug, recentPostsCache)

        self._postToOutbox(newUndoAnnounce,
                           self.server.project_version, self.postToNickname)

        actorAbsolute = self._getInstanceUrl(callingDomain) + actor
        actorPathStr = \
            actorAbsolute + '/' + timelineStr + '?page=' + \
            str(pageNumber) + timelineBookmark
        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', '_undoAnnounceButton',
                           self.server.debug)
        self._redirect_headers(actorPathStr, cookie, callingDomain)

    def _followApproveButton(self, callingDomain: str, path: str,
                             cookie: str,
                             base_dir: str, http_prefix: str,
                             domain: str, domainFull: str, port: int,
                             onion_domain: str, i2p_domain: str,
                             GETstartTime,
                             proxy_type: str, debug: bool) -> None:
        """Follow approve button was pressed
        """
        originPathStr = path.split('/followapprove=')[0]
        followerNickname = originPathStr.replace('/users/', '')
        followingHandle = path.split('/followapprove=')[1]
        if '://' in followingHandle:
            handleNickname = getNicknameFromActor(followingHandle)
            handleDomain, handlePort = getDomainFromActor(followingHandle)
            followingHandle = \
                handleNickname + '@' + getFullDomain(handleDomain, handlePort)
        if '@' in followingHandle:
            if not self._establishSession("followApproveButton"):
                self._404()
                return
            manualApproveFollowRequestThread(self.server.session,
                                             base_dir, http_prefix,
                                             followerNickname,
                                             domain, port,
                                             followingHandle,
                                             self.server.federationList,
                                             self.server.sendThreads,
                                             self.server.postLog,
                                             self.server.cachedWebfingers,
                                             self.server.personCache,
                                             debug,
                                             self.server.project_version,
                                             self.server.signingPrivateKeyPem)
        originPathStrAbsolute = \
            http_prefix + '://' + domainFull + originPathStr
        if callingDomain.endswith('.onion') and onion_domain:
            originPathStrAbsolute = \
                'http://' + onion_domain + originPathStr
        elif (callingDomain.endswith('.i2p') and i2p_domain):
            originPathStrAbsolute = \
                'http://' + i2p_domain + originPathStr
        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', '_followApproveButton',
                           self.server.debug)
        self._redirect_headers(originPathStrAbsolute,
                               cookie, callingDomain)

    def _newswireVote(self, callingDomain: str, path: str,
                      cookie: str,
                      base_dir: str, http_prefix: str,
                      domain: str, domainFull: str, port: int,
                      onion_domain: str, i2p_domain: str,
                      GETstartTime,
                      proxy_type: str, debug: bool,
                      newswire: {}):
        """Vote for a newswire item
        """
        originPathStr = path.split('/newswirevote=')[0]
        dateStr = \
            path.split('/newswirevote=')[1].replace('T', ' ')
        dateStr = dateStr.replace(' 00:00', '').replace('+00:00', '')
        dateStr = urllib.parse.unquote_plus(dateStr) + '+00:00'
        nickname = urllib.parse.unquote_plus(originPathStr.split('/users/')[1])
        if '/' in nickname:
            nickname = nickname.split('/')[0]
        print('Newswire item date: ' + dateStr)
        if newswire.get(dateStr):
            if isModerator(base_dir, nickname):
                newswireItem = newswire[dateStr]
                print('Voting on newswire item: ' + str(newswireItem))
                votesIndex = 2
                filenameIndex = 3
                if 'vote:' + nickname not in newswireItem[votesIndex]:
                    newswireItem[votesIndex].append('vote:' + nickname)
                    filename = newswireItem[filenameIndex]
                    newswireStateFilename = \
                        base_dir + '/accounts/.newswirestate.json'
                    try:
                        saveJson(newswire, newswireStateFilename)
                    except Exception as ex:
                        print('ERROR: saving newswire state, ' + str(ex))
                    if filename:
                        saveJson(newswireItem[votesIndex],
                                 filename + '.votes')
        else:
            print('No newswire item with date: ' + dateStr + ' ' +
                  str(newswire))

        originPathStrAbsolute = \
            http_prefix + '://' + domainFull + originPathStr + '/' + \
            self.server.defaultTimeline
        if callingDomain.endswith('.onion') and onion_domain:
            originPathStrAbsolute = \
                'http://' + onion_domain + originPathStr
        elif (callingDomain.endswith('.i2p') and i2p_domain):
            originPathStrAbsolute = \
                'http://' + i2p_domain + originPathStr
        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', '_newswireVote',
                           self.server.debug)
        self._redirect_headers(originPathStrAbsolute,
                               cookie, callingDomain)

    def _newswireUnvote(self, callingDomain: str, path: str,
                        cookie: str,
                        base_dir: str, http_prefix: str,
                        domain: str, domainFull: str, port: int,
                        onion_domain: str, i2p_domain: str,
                        GETstartTime,
                        proxy_type: str, debug: bool,
                        newswire: {}):
        """Remove vote for a newswire item
        """
        originPathStr = path.split('/newswireunvote=')[0]
        dateStr = \
            path.split('/newswireunvote=')[1].replace('T', ' ')
        dateStr = dateStr.replace(' 00:00', '').replace('+00:00', '')
        dateStr = urllib.parse.unquote_plus(dateStr) + '+00:00'
        nickname = urllib.parse.unquote_plus(originPathStr.split('/users/')[1])
        if '/' in nickname:
            nickname = nickname.split('/')[0]
        if newswire.get(dateStr):
            if isModerator(base_dir, nickname):
                votesIndex = 2
                filenameIndex = 3
                newswireItem = newswire[dateStr]
                if 'vote:' + nickname in newswireItem[votesIndex]:
                    newswireItem[votesIndex].remove('vote:' + nickname)
                    filename = newswireItem[filenameIndex]
                    newswireStateFilename = \
                        base_dir + '/accounts/.newswirestate.json'
                    try:
                        saveJson(newswire, newswireStateFilename)
                    except Exception as ex:
                        print('ERROR: saving newswire state, ' + str(ex))
                    if filename:
                        saveJson(newswireItem[votesIndex],
                                 filename + '.votes')
        else:
            print('No newswire item with date: ' + dateStr + ' ' +
                  str(newswire))

        originPathStrAbsolute = \
            http_prefix + '://' + domainFull + originPathStr + '/' + \
            self.server.defaultTimeline
        if callingDomain.endswith('.onion') and onion_domain:
            originPathStrAbsolute = \
                'http://' + onion_domain + originPathStr
        elif (callingDomain.endswith('.i2p') and i2p_domain):
            originPathStrAbsolute = \
                'http://' + i2p_domain + originPathStr
        self._redirect_headers(originPathStrAbsolute,
                               cookie, callingDomain)
        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', '_newswireUnvote',
                           self.server.debug)

    def _followDenyButton(self, callingDomain: str, path: str,
                          cookie: str,
                          base_dir: str, http_prefix: str,
                          domain: str, domainFull: str, port: int,
                          onion_domain: str, i2p_domain: str,
                          GETstartTime,
                          proxy_type: str, debug: bool) -> None:
        """Follow deny button was pressed
        """
        originPathStr = path.split('/followdeny=')[0]
        followerNickname = originPathStr.replace('/users/', '')
        followingHandle = path.split('/followdeny=')[1]
        if '://' in followingHandle:
            handleNickname = getNicknameFromActor(followingHandle)
            handleDomain, handlePort = getDomainFromActor(followingHandle)
            followingHandle = \
                handleNickname + '@' + getFullDomain(handleDomain, handlePort)
        if '@' in followingHandle:
            manualDenyFollowRequestThread(self.server.session,
                                          base_dir, http_prefix,
                                          followerNickname,
                                          domain, port,
                                          followingHandle,
                                          self.server.federationList,
                                          self.server.sendThreads,
                                          self.server.postLog,
                                          self.server.cachedWebfingers,
                                          self.server.personCache,
                                          debug,
                                          self.server.project_version,
                                          self.server.signingPrivateKeyPem)
        originPathStrAbsolute = \
            http_prefix + '://' + domainFull + originPathStr
        if callingDomain.endswith('.onion') and onion_domain:
            originPathStrAbsolute = \
                'http://' + onion_domain + originPathStr
        elif callingDomain.endswith('.i2p') and i2p_domain:
            originPathStrAbsolute = \
                'http://' + i2p_domain + originPathStr
        self._redirect_headers(originPathStrAbsolute,
                               cookie, callingDomain)
        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', '_followDenyButton',
                           self.server.debug)

    def _likeButton(self, callingDomain: str, path: str,
                    base_dir: str, http_prefix: str,
                    domain: str, domainFull: str,
                    onion_domain: str, i2p_domain: str,
                    GETstartTime,
                    proxy_type: str, cookie: str,
                    debug: str) -> None:
        """Press the like button
        """
        pageNumber = 1
        likeUrl = path.split('?like=')[1]
        if '?' in likeUrl:
            likeUrl = likeUrl.split('?')[0]
        timelineBookmark = ''
        if '?bm=' in path:
            timelineBookmark = path.split('?bm=')[1]
            if '?' in timelineBookmark:
                timelineBookmark = timelineBookmark.split('?')[0]
            timelineBookmark = '#' + timelineBookmark
        actor = path.split('?like=')[0]
        if '?page=' in path:
            pageNumberStr = path.split('?page=')[1]
            if '?' in pageNumberStr:
                pageNumberStr = pageNumberStr.split('?')[0]
            if '#' in pageNumberStr:
                pageNumberStr = pageNumberStr.split('#')[0]
            if pageNumberStr.isdigit():
                pageNumber = int(pageNumberStr)
        timelineStr = 'inbox'
        if '?tl=' in path:
            timelineStr = path.split('?tl=')[1]
            if '?' in timelineStr:
                timelineStr = timelineStr.split('?')[0]

        self.postToNickname = getNicknameFromActor(actor)
        if not self.postToNickname:
            print('WARN: unable to find nickname in ' + actor)
            actorAbsolute = self._getInstanceUrl(callingDomain) + actor
            actorPathStr = \
                actorAbsolute + '/' + timelineStr + \
                '?page=' + str(pageNumber) + timelineBookmark
            self._redirect_headers(actorPathStr, cookie,
                                   callingDomain)
            return
        if not self._establishSession("likeButton"):
            self._404()
            return
        likeActor = \
            localActorUrl(http_prefix, self.postToNickname, domainFull)
        actorLiked = path.split('?actor=')[1]
        if '?' in actorLiked:
            actorLiked = actorLiked.split('?')[0]

        # if this is an announce then send the like to the original post
        origActor, origPostUrl, origFilename = \
            getOriginalPostFromAnnounceUrl(likeUrl, base_dir,
                                           self.postToNickname, domain)
        likeUrl2 = likeUrl
        likedPostFilename = origFilename
        if origActor and origPostUrl:
            actorLiked = origActor
            likeUrl2 = origPostUrl
            likedPostFilename = None

        likeJson = {
            "@context": "https://www.w3.org/ns/activitystreams",
            'type': 'Like',
            'actor': likeActor,
            'to': [actorLiked],
            'object': likeUrl2
        }

        # send out the like to followers
        self._postToOutbox(likeJson, self.server.project_version, None)

        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', '_likeButton postToOutbox',
                           self.server.debug)

        print('Locating liked post ' + likeUrl)
        # directly like the post file
        if not likedPostFilename:
            likedPostFilename = \
                locatePost(base_dir, self.postToNickname, domain, likeUrl)
        if likedPostFilename:
            recentPostsCache = self.server.recentPostsCache
            likedPostJson = loadJson(likedPostFilename, 0, 1)
            if origFilename and origPostUrl:
                updateLikesCollection(recentPostsCache,
                                      base_dir, likedPostFilename,
                                      likeUrl, likeActor, self.postToNickname,
                                      domain, debug, likedPostJson)
                likeUrl = origPostUrl
                likedPostFilename = origFilename
            if debug:
                print('Updating likes for ' + likedPostFilename)
            updateLikesCollection(recentPostsCache,
                                  base_dir, likedPostFilename, likeUrl,
                                  likeActor, self.postToNickname, domain,
                                  debug, None)
            if debug:
                print('Regenerating html post for changed likes collection')
            # clear the icon from the cache so that it gets updated
            if likedPostJson:
                cachedPostFilename = \
                    getCachedPostFilename(base_dir, self.postToNickname,
                                          domain, likedPostJson)
                if debug:
                    print('Liked post json: ' + str(likedPostJson))
                    print('Liked post nickname: ' +
                          self.postToNickname + ' ' + domain)
                    print('Liked post cache: ' + str(cachedPostFilename))
                showIndividualPostIcons = True
                manuallyApproveFollowers = \
                    followerApprovalActive(base_dir,
                                           self.postToNickname, domain)
                showRepeats = not isDM(likedPostJson)
                individualPostAsHtml(self.server.signingPrivateKeyPem, False,
                                     self.server.recentPostsCache,
                                     self.server.max_recent_posts,
                                     self.server.translate,
                                     pageNumber, base_dir,
                                     self.server.session,
                                     self.server.cachedWebfingers,
                                     self.server.personCache,
                                     self.postToNickname, domain,
                                     self.server.port, likedPostJson,
                                     None, True,
                                     self.server.allowDeletion,
                                     http_prefix,
                                     self.server.project_version,
                                     timelineStr,
                                     self.server.yt_replace_domain,
                                     self.server.twitter_replacement_domain,
                                     self.server.show_published_date_only,
                                     self.server.peertubeInstances,
                                     self.server.allow_local_network_access,
                                     self.server.themeName,
                                     self.server.systemLanguage,
                                     self.server.max_like_count,
                                     showRepeats,
                                     showIndividualPostIcons,
                                     manuallyApproveFollowers,
                                     False, True, False,
                                     self.server.CWlists,
                                     self.server.lists_enabled)
            else:
                print('WARN: Liked post not found: ' + likedPostFilename)
            # clear the icon from the cache so that it gets updated
            if self.server.iconsCache.get('like.png'):
                del self.server.iconsCache['like.png']
        else:
            print('WARN: unable to locate file for liked post ' +
                  likeUrl)

        actorAbsolute = self._getInstanceUrl(callingDomain) + actor
        actorPathStr = \
            actorAbsolute + '/' + timelineStr + \
            '?page=' + str(pageNumber) + timelineBookmark
        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', '_likeButton',
                           self.server.debug)
        self._redirect_headers(actorPathStr, cookie,
                               callingDomain)

    def _undoLikeButton(self, callingDomain: str, path: str,
                        base_dir: str, http_prefix: str,
                        domain: str, domainFull: str,
                        onion_domain: str, i2p_domain: str,
                        GETstartTime,
                        proxy_type: str, cookie: str,
                        debug: str) -> None:
        """A button is pressed to undo
        """
        pageNumber = 1
        likeUrl = path.split('?unlike=')[1]
        if '?' in likeUrl:
            likeUrl = likeUrl.split('?')[0]
        timelineBookmark = ''
        if '?bm=' in path:
            timelineBookmark = path.split('?bm=')[1]
            if '?' in timelineBookmark:
                timelineBookmark = timelineBookmark.split('?')[0]
            timelineBookmark = '#' + timelineBookmark
        if '?page=' in path:
            pageNumberStr = path.split('?page=')[1]
            if '?' in pageNumberStr:
                pageNumberStr = pageNumberStr.split('?')[0]
            if '#' in pageNumberStr:
                pageNumberStr = pageNumberStr.split('#')[0]
            if pageNumberStr.isdigit():
                pageNumber = int(pageNumberStr)
        timelineStr = 'inbox'
        if '?tl=' in path:
            timelineStr = path.split('?tl=')[1]
            if '?' in timelineStr:
                timelineStr = timelineStr.split('?')[0]
        actor = path.split('?unlike=')[0]
        self.postToNickname = getNicknameFromActor(actor)
        if not self.postToNickname:
            print('WARN: unable to find nickname in ' + actor)
            actorAbsolute = self._getInstanceUrl(callingDomain) + actor
            actorPathStr = \
                actorAbsolute + '/' + timelineStr + \
                '?page=' + str(pageNumber)
            self._redirect_headers(actorPathStr, cookie,
                                   callingDomain)
            return
        if not self._establishSession("undoLikeButton"):
            self._404()
            return
        undoActor = \
            localActorUrl(http_prefix, self.postToNickname, domainFull)
        actorLiked = path.split('?actor=')[1]
        if '?' in actorLiked:
            actorLiked = actorLiked.split('?')[0]

        # if this is an announce then send the like to the original post
        origActor, origPostUrl, origFilename = \
            getOriginalPostFromAnnounceUrl(likeUrl, base_dir,
                                           self.postToNickname, domain)
        likeUrl2 = likeUrl
        likedPostFilename = origFilename
        if origActor and origPostUrl:
            actorLiked = origActor
            likeUrl2 = origPostUrl
            likedPostFilename = None

        undoLikeJson = {
            "@context": "https://www.w3.org/ns/activitystreams",
            'type': 'Undo',
            'actor': undoActor,
            'to': [actorLiked],
            'object': {
                'type': 'Like',
                'actor': undoActor,
                'to': [actorLiked],
                'object': likeUrl2
            }
        }

        # send out the undo like to followers
        self._postToOutbox(undoLikeJson, self.server.project_version, None)

        # directly undo the like within the post file
        if not likedPostFilename:
            likedPostFilename = locatePost(base_dir, self.postToNickname,
                                           domain, likeUrl)
        if likedPostFilename:
            recentPostsCache = self.server.recentPostsCache
            likedPostJson = loadJson(likedPostFilename, 0, 1)
            if origFilename and origPostUrl:
                undoLikesCollectionEntry(recentPostsCache,
                                         base_dir, likedPostFilename,
                                         likeUrl, undoActor, domain, debug,
                                         likedPostJson)
                likeUrl = origPostUrl
                likedPostFilename = origFilename
            if debug:
                print('Removing likes for ' + likedPostFilename)
            undoLikesCollectionEntry(recentPostsCache,
                                     base_dir,
                                     likedPostFilename, likeUrl,
                                     undoActor, domain, debug, None)
            if debug:
                print('Regenerating html post for changed likes collection')
            if likedPostJson:
                showIndividualPostIcons = True
                manuallyApproveFollowers = \
                    followerApprovalActive(base_dir,
                                           self.postToNickname, domain)
                showRepeats = not isDM(likedPostJson)
                individualPostAsHtml(self.server.signingPrivateKeyPem, False,
                                     self.server.recentPostsCache,
                                     self.server.max_recent_posts,
                                     self.server.translate,
                                     pageNumber, base_dir,
                                     self.server.session,
                                     self.server.cachedWebfingers,
                                     self.server.personCache,
                                     self.postToNickname, domain,
                                     self.server.port, likedPostJson,
                                     None, True,
                                     self.server.allowDeletion,
                                     http_prefix,
                                     self.server.project_version, timelineStr,
                                     self.server.yt_replace_domain,
                                     self.server.twitter_replacement_domain,
                                     self.server.show_published_date_only,
                                     self.server.peertubeInstances,
                                     self.server.allow_local_network_access,
                                     self.server.themeName,
                                     self.server.systemLanguage,
                                     self.server.max_like_count,
                                     showRepeats,
                                     showIndividualPostIcons,
                                     manuallyApproveFollowers,
                                     False, True, False,
                                     self.server.CWlists,
                                     self.server.lists_enabled)
            else:
                print('WARN: Unliked post not found: ' + likedPostFilename)
            # clear the icon from the cache so that it gets updated
            if self.server.iconsCache.get('like_inactive.png'):
                del self.server.iconsCache['like_inactive.png']
        actorAbsolute = self._getInstanceUrl(callingDomain) + actor
        actorPathStr = \
            actorAbsolute + '/' + timelineStr + \
            '?page=' + str(pageNumber) + timelineBookmark
        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', '_undoLikeButton',
                           self.server.debug)
        self._redirect_headers(actorPathStr, cookie,
                               callingDomain)

    def _reactionButton(self, callingDomain: str, path: str,
                        base_dir: str, http_prefix: str,
                        domain: str, domainFull: str,
                        onion_domain: str, i2p_domain: str,
                        GETstartTime,
                        proxy_type: str, cookie: str,
                        debug: str) -> None:
        """Press an emoji reaction button
        Note that this is not the emoji reaction selection icon at the
        bottom of the post
        """
        pageNumber = 1
        reactionUrl = path.split('?react=')[1]
        if '?' in reactionUrl:
            reactionUrl = reactionUrl.split('?')[0]
        timelineBookmark = ''
        if '?bm=' in path:
            timelineBookmark = path.split('?bm=')[1]
            if '?' in timelineBookmark:
                timelineBookmark = timelineBookmark.split('?')[0]
            timelineBookmark = '#' + timelineBookmark
        actor = path.split('?react=')[0]
        if '?page=' in path:
            pageNumberStr = path.split('?page=')[1]
            if '?' in pageNumberStr:
                pageNumberStr = pageNumberStr.split('?')[0]
            if '#' in pageNumberStr:
                pageNumberStr = pageNumberStr.split('#')[0]
            if pageNumberStr.isdigit():
                pageNumber = int(pageNumberStr)
        timelineStr = 'inbox'
        if '?tl=' in path:
            timelineStr = path.split('?tl=')[1]
            if '?' in timelineStr:
                timelineStr = timelineStr.split('?')[0]
        emojiContentEncoded = None
        if '?emojreact=' in path:
            emojiContentEncoded = path.split('?emojreact=')[1]
            if '?' in emojiContentEncoded:
                emojiContentEncoded = emojiContentEncoded.split('?')[0]
        if not emojiContentEncoded:
            print('WARN: no emoji reaction ' + actor)
            actorAbsolute = self._getInstanceUrl(callingDomain) + actor
            actorPathStr = \
                actorAbsolute + '/' + timelineStr + \
                '?page=' + str(pageNumber) + timelineBookmark
            self._redirect_headers(actorPathStr, cookie,
                                   callingDomain)
            return
        emojiContent = urllib.parse.unquote_plus(emojiContentEncoded)
        self.postToNickname = getNicknameFromActor(actor)
        if not self.postToNickname:
            print('WARN: unable to find nickname in ' + actor)
            actorAbsolute = self._getInstanceUrl(callingDomain) + actor
            actorPathStr = \
                actorAbsolute + '/' + timelineStr + \
                '?page=' + str(pageNumber) + timelineBookmark
            self._redirect_headers(actorPathStr, cookie,
                                   callingDomain)
            return
        if not self._establishSession("reactionButton"):
            self._404()
            return
        reactionActor = \
            localActorUrl(http_prefix, self.postToNickname, domainFull)
        actorReaction = path.split('?actor=')[1]
        if '?' in actorReaction:
            actorReaction = actorReaction.split('?')[0]

        # if this is an announce then send the emoji reaction
        # to the original post
        origActor, origPostUrl, origFilename = \
            getOriginalPostFromAnnounceUrl(reactionUrl, base_dir,
                                           self.postToNickname, domain)
        reactionUrl2 = reactionUrl
        reactionPostFilename = origFilename
        if origActor and origPostUrl:
            actorReaction = origActor
            reactionUrl2 = origPostUrl
            reactionPostFilename = None

        reactionJson = {
            "@context": "https://www.w3.org/ns/activitystreams",
            'type': 'EmojiReact',
            'actor': reactionActor,
            'to': [actorReaction],
            'object': reactionUrl2,
            'content': emojiContent
        }

        # send out the emoji reaction to followers
        self._postToOutbox(reactionJson, self.server.project_version, None)

        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', '_reactionButton postToOutbox',
                           self.server.debug)

        print('Locating emoji reaction post ' + reactionUrl)
        # directly emoji reaction the post file
        if not reactionPostFilename:
            reactionPostFilename = \
                locatePost(base_dir, self.postToNickname, domain, reactionUrl)
        if reactionPostFilename:
            recentPostsCache = self.server.recentPostsCache
            reactionPostJson = loadJson(reactionPostFilename, 0, 1)
            if origFilename and origPostUrl:
                updateReactionCollection(recentPostsCache,
                                         base_dir, reactionPostFilename,
                                         reactionUrl,
                                         reactionActor, self.postToNickname,
                                         domain, debug, reactionPostJson,
                                         emojiContent)
                reactionUrl = origPostUrl
                reactionPostFilename = origFilename
            if debug:
                print('Updating emoji reaction for ' + reactionPostFilename)
            updateReactionCollection(recentPostsCache,
                                     base_dir, reactionPostFilename,
                                     reactionUrl,
                                     reactionActor,
                                     self.postToNickname, domain,
                                     debug, None, emojiContent)
            if debug:
                print('Regenerating html post for changed ' +
                      'emoji reaction collection')
            # clear the icon from the cache so that it gets updated
            if reactionPostJson:
                cachedPostFilename = \
                    getCachedPostFilename(base_dir, self.postToNickname,
                                          domain, reactionPostJson)
                if debug:
                    print('Reaction post json: ' + str(reactionPostJson))
                    print('Reaction post nickname: ' +
                          self.postToNickname + ' ' + domain)
                    print('Reaction post cache: ' + str(cachedPostFilename))
                showIndividualPostIcons = True
                manuallyApproveFollowers = \
                    followerApprovalActive(base_dir,
                                           self.postToNickname, domain)
                showRepeats = not isDM(reactionPostJson)
                individualPostAsHtml(self.server.signingPrivateKeyPem, False,
                                     self.server.recentPostsCache,
                                     self.server.max_recent_posts,
                                     self.server.translate,
                                     pageNumber, base_dir,
                                     self.server.session,
                                     self.server.cachedWebfingers,
                                     self.server.personCache,
                                     self.postToNickname, domain,
                                     self.server.port, reactionPostJson,
                                     None, True,
                                     self.server.allowDeletion,
                                     http_prefix,
                                     self.server.project_version,
                                     timelineStr,
                                     self.server.yt_replace_domain,
                                     self.server.twitter_replacement_domain,
                                     self.server.show_published_date_only,
                                     self.server.peertubeInstances,
                                     self.server.allow_local_network_access,
                                     self.server.themeName,
                                     self.server.systemLanguage,
                                     self.server.max_like_count,
                                     showRepeats,
                                     showIndividualPostIcons,
                                     manuallyApproveFollowers,
                                     False, True, False,
                                     self.server.CWlists,
                                     self.server.lists_enabled)
            else:
                print('WARN: Emoji reaction post not found: ' +
                      reactionPostFilename)
        else:
            print('WARN: unable to locate file for emoji reaction post ' +
                  reactionUrl)

        actorAbsolute = self._getInstanceUrl(callingDomain) + actor
        actorPathStr = \
            actorAbsolute + '/' + timelineStr + \
            '?page=' + str(pageNumber) + timelineBookmark
        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', '_reactionButton',
                           self.server.debug)
        self._redirect_headers(actorPathStr, cookie,
                               callingDomain)

    def _undoReactionButton(self, callingDomain: str, path: str,
                            base_dir: str, http_prefix: str,
                            domain: str, domainFull: str,
                            onion_domain: str, i2p_domain: str,
                            GETstartTime,
                            proxy_type: str, cookie: str,
                            debug: str) -> None:
        """A button is pressed to undo emoji reaction
        """
        pageNumber = 1
        reactionUrl = path.split('?unreact=')[1]
        if '?' in reactionUrl:
            reactionUrl = reactionUrl.split('?')[0]
        timelineBookmark = ''
        if '?bm=' in path:
            timelineBookmark = path.split('?bm=')[1]
            if '?' in timelineBookmark:
                timelineBookmark = timelineBookmark.split('?')[0]
            timelineBookmark = '#' + timelineBookmark
        if '?page=' in path:
            pageNumberStr = path.split('?page=')[1]
            if '?' in pageNumberStr:
                pageNumberStr = pageNumberStr.split('?')[0]
            if '#' in pageNumberStr:
                pageNumberStr = pageNumberStr.split('#')[0]
            if pageNumberStr.isdigit():
                pageNumber = int(pageNumberStr)
        timelineStr = 'inbox'
        if '?tl=' in path:
            timelineStr = path.split('?tl=')[1]
            if '?' in timelineStr:
                timelineStr = timelineStr.split('?')[0]
        actor = path.split('?unreact=')[0]
        self.postToNickname = getNicknameFromActor(actor)
        if not self.postToNickname:
            print('WARN: unable to find nickname in ' + actor)
            actorAbsolute = self._getInstanceUrl(callingDomain) + actor
            actorPathStr = \
                actorAbsolute + '/' + timelineStr + \
                '?page=' + str(pageNumber)
            self._redirect_headers(actorPathStr, cookie,
                                   callingDomain)
            return
        emojiContentEncoded = None
        if '?emojreact=' in path:
            emojiContentEncoded = path.split('?emojreact=')[1]
            if '?' in emojiContentEncoded:
                emojiContentEncoded = emojiContentEncoded.split('?')[0]
        if not emojiContentEncoded:
            print('WARN: no emoji reaction ' + actor)
            actorAbsolute = self._getInstanceUrl(callingDomain) + actor
            actorPathStr = \
                actorAbsolute + '/' + timelineStr + \
                '?page=' + str(pageNumber) + timelineBookmark
            self._redirect_headers(actorPathStr, cookie,
                                   callingDomain)
            return
        emojiContent = urllib.parse.unquote_plus(emojiContentEncoded)
        if not self._establishSession("undoReactionButton"):
            self._404()
            return
        undoActor = \
            localActorUrl(http_prefix, self.postToNickname, domainFull)
        actorReaction = path.split('?actor=')[1]
        if '?' in actorReaction:
            actorReaction = actorReaction.split('?')[0]

        # if this is an announce then send the emoji reaction
        # to the original post
        origActor, origPostUrl, origFilename = \
            getOriginalPostFromAnnounceUrl(reactionUrl, base_dir,
                                           self.postToNickname, domain)
        reactionUrl2 = reactionUrl
        reactionPostFilename = origFilename
        if origActor and origPostUrl:
            actorReaction = origActor
            reactionUrl2 = origPostUrl
            reactionPostFilename = None

        undoReactionJson = {
            "@context": "https://www.w3.org/ns/activitystreams",
            'type': 'Undo',
            'actor': undoActor,
            'to': [actorReaction],
            'object': {
                'type': 'EmojiReact',
                'actor': undoActor,
                'to': [actorReaction],
                'object': reactionUrl2
            }
        }

        # send out the undo emoji reaction to followers
        self._postToOutbox(undoReactionJson, self.server.project_version, None)

        # directly undo the emoji reaction within the post file
        if not reactionPostFilename:
            reactionPostFilename = \
                locatePost(base_dir, self.postToNickname, domain, reactionUrl)
        if reactionPostFilename:
            recentPostsCache = self.server.recentPostsCache
            reactionPostJson = loadJson(reactionPostFilename, 0, 1)
            if origFilename and origPostUrl:
                undoReactionCollectionEntry(recentPostsCache,
                                            base_dir, reactionPostFilename,
                                            reactionUrl,
                                            undoActor, domain, debug,
                                            reactionPostJson,
                                            emojiContent)
                reactionUrl = origPostUrl
                reactionPostFilename = origFilename
            if debug:
                print('Removing emoji reaction for ' + reactionPostFilename)
            undoReactionCollectionEntry(recentPostsCache,
                                        base_dir,
                                        reactionPostFilename, reactionUrl,
                                        undoActor, domain, debug,
                                        reactionPostJson, emojiContent)
            if debug:
                print('Regenerating html post for changed ' +
                      'emoji reaction collection')
            if reactionPostJson:
                showIndividualPostIcons = True
                manuallyApproveFollowers = \
                    followerApprovalActive(base_dir,
                                           self.postToNickname, domain)
                showRepeats = not isDM(reactionPostJson)
                individualPostAsHtml(self.server.signingPrivateKeyPem, False,
                                     self.server.recentPostsCache,
                                     self.server.max_recent_posts,
                                     self.server.translate,
                                     pageNumber, base_dir,
                                     self.server.session,
                                     self.server.cachedWebfingers,
                                     self.server.personCache,
                                     self.postToNickname, domain,
                                     self.server.port, reactionPostJson,
                                     None, True,
                                     self.server.allowDeletion,
                                     http_prefix,
                                     self.server.project_version, timelineStr,
                                     self.server.yt_replace_domain,
                                     self.server.twitter_replacement_domain,
                                     self.server.show_published_date_only,
                                     self.server.peertubeInstances,
                                     self.server.allow_local_network_access,
                                     self.server.themeName,
                                     self.server.systemLanguage,
                                     self.server.max_like_count,
                                     showRepeats,
                                     showIndividualPostIcons,
                                     manuallyApproveFollowers,
                                     False, True, False,
                                     self.server.CWlists,
                                     self.server.lists_enabled)
            else:
                print('WARN: Unreaction post not found: ' +
                      reactionPostFilename)

        actorAbsolute = self._getInstanceUrl(callingDomain) + actor
        actorPathStr = \
            actorAbsolute + '/' + timelineStr + \
            '?page=' + str(pageNumber) + timelineBookmark
        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', '_undoReactionButton',
                           self.server.debug)
        self._redirect_headers(actorPathStr, cookie, callingDomain)

    def _reactionPicker(self, callingDomain: str, path: str,
                        base_dir: str, http_prefix: str,
                        domain: str, domainFull: str, port: int,
                        onion_domain: str, i2p_domain: str,
                        GETstartTime,
                        proxy_type: str, cookie: str,
                        debug: str) -> None:
        """Press the emoji reaction picker icon at the bottom of the post
        """
        pageNumber = 1
        reactionUrl = path.split('?selreact=')[1]
        if '?' in reactionUrl:
            reactionUrl = reactionUrl.split('?')[0]
        timelineBookmark = ''
        if '?bm=' in path:
            timelineBookmark = path.split('?bm=')[1]
            if '?' in timelineBookmark:
                timelineBookmark = timelineBookmark.split('?')[0]
            timelineBookmark = '#' + timelineBookmark
        actor = path.split('?selreact=')[0]
        if '?page=' in path:
            pageNumberStr = path.split('?page=')[1]
            if '?' in pageNumberStr:
                pageNumberStr = pageNumberStr.split('?')[0]
            if '#' in pageNumberStr:
                pageNumberStr = pageNumberStr.split('#')[0]
            if pageNumberStr.isdigit():
                pageNumber = int(pageNumberStr)
        timelineStr = 'inbox'
        if '?tl=' in path:
            timelineStr = path.split('?tl=')[1]
            if '?' in timelineStr:
                timelineStr = timelineStr.split('?')[0]
        self.postToNickname = getNicknameFromActor(actor)
        if not self.postToNickname:
            print('WARN: unable to find nickname in ' + actor)
            actorAbsolute = self._getInstanceUrl(callingDomain) + actor
            actorPathStr = \
                actorAbsolute + '/' + timelineStr + \
                '?page=' + str(pageNumber) + timelineBookmark
            self._redirect_headers(actorPathStr, cookie, callingDomain)
            return

        postJsonObject = None
        reactionPostFilename = \
            locatePost(self.server.base_dir,
                       self.postToNickname, domain, reactionUrl)
        if reactionPostFilename:
            postJsonObject = loadJson(reactionPostFilename)
        if not reactionPostFilename or not postJsonObject:
            print('WARN: unable to locate reaction post ' + reactionUrl)
            actorAbsolute = self._getInstanceUrl(callingDomain) + actor
            actorPathStr = \
                actorAbsolute + '/' + timelineStr + \
                '?page=' + str(pageNumber) + timelineBookmark
            self._redirect_headers(actorPathStr, cookie, callingDomain)
            return

        msg = \
            htmlEmojiReactionPicker(self.server.cssCache,
                                    self.server.recentPostsCache,
                                    self.server.max_recent_posts,
                                    self.server.translate,
                                    self.server.base_dir,
                                    self.server.session,
                                    self.server.cachedWebfingers,
                                    self.server.personCache,
                                    self.postToNickname,
                                    domain, port, postJsonObject,
                                    self.server.http_prefix,
                                    self.server.project_version,
                                    self.server.yt_replace_domain,
                                    self.server.twitter_replacement_domain,
                                    self.server.show_published_date_only,
                                    self.server.peertubeInstances,
                                    self.server.allow_local_network_access,
                                    self.server.themeName,
                                    self.server.systemLanguage,
                                    self.server.max_like_count,
                                    self.server.signingPrivateKeyPem,
                                    self.server.CWlists,
                                    self.server.lists_enabled,
                                    timelineStr, pageNumber)
        msg = msg.encode('utf-8')
        msglen = len(msg)
        self._set_headers('text/html', msglen,
                          cookie, callingDomain, False)
        self._write(msg)
        fitnessPerformance(GETstartTime,
                           self.server.fitness,
                           '_GET', '_reactionPicker',
                           self.server.debug)

    def _bookmarkButton(self, callingDomain: str, path: str,
                        base_dir: str, http_prefix: str,
                        domain: str, domainFull: str, port: int,
                        onion_domain: str, i2p_domain: str,
                        GETstartTime,
                        proxy_type: str, cookie: str,
                        debug: str) -> None:
        """Bookmark button was pressed
        """
        pageNumber = 1
        bookmarkUrl = path.split('?bookmark=')[1]
        if '?' in bookmarkUrl:
            bookmarkUrl = bookmarkUrl.split('?')[0]
        timelineBookmark = ''
        if '?bm=' in path:
            timelineBookmark = path.split('?bm=')[1]
            if '?' in timelineBookmark:
                timelineBookmark = timelineBookmark.split('?')[0]
            timelineBookmark = '#' + timelineBookmark
        actor = path.split('?bookmark=')[0]
        if '?page=' in path:
            pageNumberStr = path.split('?page=')[1]
            if '?' in pageNumberStr:
                pageNumberStr = pageNumberStr.split('?')[0]
            if '#' in pageNumberStr:
                pageNumberStr = pageNumberStr.split('#')[0]
            if pageNumberStr.isdigit():
                pageNumber = int(pageNumberStr)
        timelineStr = 'inbox'
        if '?tl=' in path:
            timelineStr = path.split('?tl=')[1]
            if '?' in timelineStr:
                timelineStr = timelineStr.split('?')[0]

        self.postToNickname = getNicknameFromActor(actor)
        if not self.postToNickname:
            print('WARN: unable to find nickname in ' + actor)
            actorAbsolute = self._getInstanceUrl(callingDomain) + actor
            actorPathStr = \
                actorAbsolute + '/' + timelineStr + \
                '?page=' + str(pageNumber)
            self._redirect_headers(actorPathStr, cookie,
                                   callingDomain)
            return
        if not self._establishSession("bookmarkButton"):
            self._404()
            return
        bookmarkActor = \
            localActorUrl(http_prefix, self.postToNickname, domainFull)
        ccList = []
        bookmark(self.server.recentPostsCache,
                 self.server.session,
                 base_dir,
                 self.server.federationList,
                 self.postToNickname,
                 domain, port,
                 ccList,
                 http_prefix,
                 bookmarkUrl, bookmarkActor, False,
                 self.server.sendThreads,
                 self.server.postLog,
                 self.server.personCache,
                 self.server.cachedWebfingers,
                 self.server.debug,
                 self.server.project_version)
        # clear the icon from the cache so that it gets updated
        if self.server.iconsCache.get('bookmark.png'):
            del self.server.iconsCache['bookmark.png']
        bookmarkFilename = \
            locatePost(base_dir, self.postToNickname, domain, bookmarkUrl)
        if bookmarkFilename:
            print('Regenerating html post for changed bookmark')
            bookmarkPostJson = loadJson(bookmarkFilename, 0, 1)
            if bookmarkPostJson:
                cachedPostFilename = \
                    getCachedPostFilename(base_dir, self.postToNickname,
                                          domain, bookmarkPostJson)
                print('Bookmarked post json: ' + str(bookmarkPostJson))
                print('Bookmarked post nickname: ' +
                      self.postToNickname + ' ' + domain)
                print('Bookmarked post cache: ' + str(cachedPostFilename))
                showIndividualPostIcons = True
                manuallyApproveFollowers = \
                    followerApprovalActive(base_dir,
                                           self.postToNickname, domain)
                showRepeats = not isDM(bookmarkPostJson)
                individualPostAsHtml(self.server.signingPrivateKeyPem, False,
                                     self.server.recentPostsCache,
                                     self.server.max_recent_posts,
                                     self.server.translate,
                                     pageNumber, base_dir,
                                     self.server.session,
                                     self.server.cachedWebfingers,
                                     self.server.personCache,
                                     self.postToNickname, domain,
                                     self.server.port, bookmarkPostJson,
                                     None, True,
                                     self.server.allowDeletion,
                                     http_prefix, self.server.project_version,
                                     timelineStr,
                                     self.server.yt_replace_domain,
                                     self.server.twitter_replacement_domain,
                                     self.server.show_published_date_only,
                                     self.server.peertubeInstances,
                                     self.server.allow_local_network_access,
                                     self.server.themeName,
                                     self.server.systemLanguage,
                                     self.server.max_like_count,
                                     showRepeats,
                                     showIndividualPostIcons,
                                     manuallyApproveFollowers,
                                     False, True, False,
                                     self.server.CWlists,
                                     self.server.lists_enabled)
            else:
                print('WARN: Bookmarked post not found: ' + bookmarkFilename)
        # self._postToOutbox(bookmarkJson, self.server.project_version, None)
        actorAbsolute = self._getInstanceUrl(callingDomain) + actor
        actorPathStr = \
            actorAbsolute + '/' + timelineStr + \
            '?page=' + str(pageNumber) + timelineBookmark
        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', '_bookmarkButton',
                           self.server.debug)
        self._redirect_headers(actorPathStr, cookie,
                               callingDomain)

    def _undoBookmarkButton(self, callingDomain: str, path: str,
                            base_dir: str, http_prefix: str,
                            domain: str, domainFull: str, port: int,
                            onion_domain: str, i2p_domain: str,
                            GETstartTime,
                            proxy_type: str, cookie: str,
                            debug: str) -> None:
        """Button pressed to undo a bookmark
        """
        pageNumber = 1
        bookmarkUrl = path.split('?unbookmark=')[1]
        if '?' in bookmarkUrl:
            bookmarkUrl = bookmarkUrl.split('?')[0]
        timelineBookmark = ''
        if '?bm=' in path:
            timelineBookmark = path.split('?bm=')[1]
            if '?' in timelineBookmark:
                timelineBookmark = timelineBookmark.split('?')[0]
            timelineBookmark = '#' + timelineBookmark
        if '?page=' in path:
            pageNumberStr = path.split('?page=')[1]
            if '?' in pageNumberStr:
                pageNumberStr = pageNumberStr.split('?')[0]
            if '#' in pageNumberStr:
                pageNumberStr = pageNumberStr.split('#')[0]
            if pageNumberStr.isdigit():
                pageNumber = int(pageNumberStr)
        timelineStr = 'inbox'
        if '?tl=' in path:
            timelineStr = path.split('?tl=')[1]
            if '?' in timelineStr:
                timelineStr = timelineStr.split('?')[0]
        actor = path.split('?unbookmark=')[0]
        self.postToNickname = getNicknameFromActor(actor)
        if not self.postToNickname:
            print('WARN: unable to find nickname in ' + actor)
            actorAbsolute = self._getInstanceUrl(callingDomain) + actor
            actorPathStr = \
                actorAbsolute + '/' + timelineStr + \
                '?page=' + str(pageNumber)
            self._redirect_headers(actorPathStr, cookie,
                                   callingDomain)
            return
        if not self._establishSession("undoBookmarkButton"):
            self._404()
            return
        undoActor = \
            localActorUrl(http_prefix, self.postToNickname, domainFull)
        ccList = []
        undoBookmark(self.server.recentPostsCache,
                     self.server.session,
                     base_dir,
                     self.server.federationList,
                     self.postToNickname,
                     domain, port,
                     ccList,
                     http_prefix,
                     bookmarkUrl, undoActor, False,
                     self.server.sendThreads,
                     self.server.postLog,
                     self.server.personCache,
                     self.server.cachedWebfingers,
                     debug,
                     self.server.project_version)
        # clear the icon from the cache so that it gets updated
        if self.server.iconsCache.get('bookmark_inactive.png'):
            del self.server.iconsCache['bookmark_inactive.png']
        # self._postToOutbox(undoBookmarkJson,
        #                    self.server.project_version, None)
        bookmarkFilename = \
            locatePost(base_dir, self.postToNickname, domain, bookmarkUrl)
        if bookmarkFilename:
            print('Regenerating html post for changed unbookmark')
            bookmarkPostJson = loadJson(bookmarkFilename, 0, 1)
            if bookmarkPostJson:
                cachedPostFilename = \
                    getCachedPostFilename(base_dir, self.postToNickname,
                                          domain, bookmarkPostJson)
                print('Unbookmarked post json: ' + str(bookmarkPostJson))
                print('Unbookmarked post nickname: ' +
                      self.postToNickname + ' ' + domain)
                print('Unbookmarked post cache: ' + str(cachedPostFilename))
                showIndividualPostIcons = True
                manuallyApproveFollowers = \
                    followerApprovalActive(base_dir,
                                           self.postToNickname, domain)
                showRepeats = not isDM(bookmarkPostJson)
                individualPostAsHtml(self.server.signingPrivateKeyPem, False,
                                     self.server.recentPostsCache,
                                     self.server.max_recent_posts,
                                     self.server.translate,
                                     pageNumber, base_dir,
                                     self.server.session,
                                     self.server.cachedWebfingers,
                                     self.server.personCache,
                                     self.postToNickname, domain,
                                     self.server.port, bookmarkPostJson,
                                     None, True,
                                     self.server.allowDeletion,
                                     http_prefix,
                                     self.server.project_version, timelineStr,
                                     self.server.yt_replace_domain,
                                     self.server.twitter_replacement_domain,
                                     self.server.show_published_date_only,
                                     self.server.peertubeInstances,
                                     self.server.allow_local_network_access,
                                     self.server.themeName,
                                     self.server.systemLanguage,
                                     self.server.max_like_count,
                                     showRepeats,
                                     showIndividualPostIcons,
                                     manuallyApproveFollowers,
                                     False, True, False,
                                     self.server.CWlists,
                                     self.server.lists_enabled)
            else:
                print('WARN: Unbookmarked post not found: ' + bookmarkFilename)
        actorAbsolute = self._getInstanceUrl(callingDomain) + actor
        actorPathStr = \
            actorAbsolute + '/' + timelineStr + \
            '?page=' + str(pageNumber) + timelineBookmark
        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', '_undoBookmarkButton',
                           self.server.debug)
        self._redirect_headers(actorPathStr, cookie,
                               callingDomain)

    def _deleteButton(self, callingDomain: str, path: str,
                      base_dir: str, http_prefix: str,
                      domain: str, domainFull: str, port: int,
                      onion_domain: str, i2p_domain: str,
                      GETstartTime,
                      proxy_type: str, cookie: str,
                      debug: str) -> None:
        """Delete button is pressed on a post
        """
        if not cookie:
            print('ERROR: no cookie given when deleting ' + path)
            self._400()
            return
        pageNumber = 1
        if '?page=' in path:
            pageNumberStr = path.split('?page=')[1]
            if '?' in pageNumberStr:
                pageNumberStr = pageNumberStr.split('?')[0]
            if '#' in pageNumberStr:
                pageNumberStr = pageNumberStr.split('#')[0]
            if pageNumberStr.isdigit():
                pageNumber = int(pageNumberStr)
        deleteUrl = path.split('?delete=')[1]
        if '?' in deleteUrl:
            deleteUrl = deleteUrl.split('?')[0]
        timelineStr = self.server.defaultTimeline
        if '?tl=' in path:
            timelineStr = path.split('?tl=')[1]
            if '?' in timelineStr:
                timelineStr = timelineStr.split('?')[0]
        usersPath = path.split('?delete=')[0]
        actor = \
            http_prefix + '://' + domainFull + usersPath
        if self.server.allowDeletion or \
           deleteUrl.startswith(actor):
            if self.server.debug:
                print('DEBUG: deleteUrl=' + deleteUrl)
                print('DEBUG: actor=' + actor)
            if actor not in deleteUrl:
                # You can only delete your own posts
                if callingDomain.endswith('.onion') and onion_domain:
                    actor = 'http://' + onion_domain + usersPath
                elif callingDomain.endswith('.i2p') and i2p_domain:
                    actor = 'http://' + i2p_domain + usersPath
                self._redirect_headers(actor + '/' + timelineStr,
                                       cookie, callingDomain)
                return
            self.postToNickname = getNicknameFromActor(actor)
            if not self.postToNickname:
                print('WARN: unable to find nickname in ' + actor)
                if callingDomain.endswith('.onion') and onion_domain:
                    actor = 'http://' + onion_domain + usersPath
                elif callingDomain.endswith('.i2p') and i2p_domain:
                    actor = 'http://' + i2p_domain + usersPath
                self._redirect_headers(actor + '/' + timelineStr,
                                       cookie, callingDomain)
                return
            if not self._establishSession("deleteButton"):
                self._404()
                return

            deleteStr = \
                htmlConfirmDelete(self.server.cssCache,
                                  self.server.recentPostsCache,
                                  self.server.max_recent_posts,
                                  self.server.translate, pageNumber,
                                  self.server.session, base_dir,
                                  deleteUrl, http_prefix,
                                  self.server.project_version,
                                  self.server.cachedWebfingers,
                                  self.server.personCache, callingDomain,
                                  self.server.yt_replace_domain,
                                  self.server.twitter_replacement_domain,
                                  self.server.show_published_date_only,
                                  self.server.peertubeInstances,
                                  self.server.allow_local_network_access,
                                  self.server.themeName,
                                  self.server.systemLanguage,
                                  self.server.max_like_count,
                                  self.server.signingPrivateKeyPem,
                                  self.server.CWlists,
                                  self.server.lists_enabled)
            if deleteStr:
                deleteStrLen = len(deleteStr)
                self._set_headers('text/html', deleteStrLen,
                                  cookie, callingDomain, False)
                self._write(deleteStr.encode('utf-8'))
                self.server.GETbusy = False
                return
        if callingDomain.endswith('.onion') and onion_domain:
            actor = 'http://' + onion_domain + usersPath
        elif (callingDomain.endswith('.i2p') and i2p_domain):
            actor = 'http://' + i2p_domain + usersPath
        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', '_deleteButton',
                           self.server.debug)
        self._redirect_headers(actor + '/' + timelineStr,
                               cookie, callingDomain)

    def _muteButton(self, callingDomain: str, path: str,
                    base_dir: str, http_prefix: str,
                    domain: str, domainFull: str, port: int,
                    onion_domain: str, i2p_domain: str,
                    GETstartTime,
                    proxy_type: str, cookie: str,
                    debug: str):
        """Mute button is pressed
        """
        muteUrl = path.split('?mute=')[1]
        if '?' in muteUrl:
            muteUrl = muteUrl.split('?')[0]
        timelineBookmark = ''
        if '?bm=' in path:
            timelineBookmark = path.split('?bm=')[1]
            if '?' in timelineBookmark:
                timelineBookmark = timelineBookmark.split('?')[0]
            timelineBookmark = '#' + timelineBookmark
        timelineStr = self.server.defaultTimeline
        if '?tl=' in path:
            timelineStr = path.split('?tl=')[1]
            if '?' in timelineStr:
                timelineStr = timelineStr.split('?')[0]
        pageNumber = 1
        if '?page=' in path:
            pageNumberStr = path.split('?page=')[1]
            if '?' in pageNumberStr:
                pageNumberStr = pageNumberStr.split('?')[0]
            if '#' in pageNumberStr:
                pageNumberStr = pageNumberStr.split('#')[0]
            if pageNumberStr.isdigit():
                pageNumber = int(pageNumberStr)
        actor = \
            http_prefix + '://' + domainFull + path.split('?mute=')[0]
        nickname = getNicknameFromActor(actor)
        mutePost(base_dir, nickname, domain, port,
                 http_prefix, muteUrl,
                 self.server.recentPostsCache, debug)
        muteFilename = \
            locatePost(base_dir, nickname, domain, muteUrl)
        if muteFilename:
            print('mutePost: Regenerating html post for changed mute status')
            mutePostJson = loadJson(muteFilename, 0, 1)
            if mutePostJson:
                cachedPostFilename = \
                    getCachedPostFilename(base_dir, nickname,
                                          domain, mutePostJson)
                print('mutePost: Muted post json: ' + str(mutePostJson))
                print('mutePost: Muted post nickname: ' +
                      nickname + ' ' + domain)
                print('mutePost: Muted post cache: ' + str(cachedPostFilename))
                showIndividualPostIcons = True
                manuallyApproveFollowers = \
                    followerApprovalActive(base_dir,
                                           nickname, domain)
                showRepeats = not isDM(mutePostJson)
                showPublicOnly = False
                storeToCache = True
                useCacheOnly = False
                allowDownloads = False
                showAvatarOptions = True
                avatarUrl = None
                individualPostAsHtml(self.server.signingPrivateKeyPem,
                                     allowDownloads,
                                     self.server.recentPostsCache,
                                     self.server.max_recent_posts,
                                     self.server.translate,
                                     pageNumber, base_dir,
                                     self.server.session,
                                     self.server.cachedWebfingers,
                                     self.server.personCache,
                                     nickname, domain,
                                     self.server.port, mutePostJson,
                                     avatarUrl, showAvatarOptions,
                                     self.server.allowDeletion,
                                     http_prefix,
                                     self.server.project_version, timelineStr,
                                     self.server.yt_replace_domain,
                                     self.server.twitter_replacement_domain,
                                     self.server.show_published_date_only,
                                     self.server.peertubeInstances,
                                     self.server.allow_local_network_access,
                                     self.server.themeName,
                                     self.server.systemLanguage,
                                     self.server.max_like_count,
                                     showRepeats,
                                     showIndividualPostIcons,
                                     manuallyApproveFollowers,
                                     showPublicOnly, storeToCache,
                                     useCacheOnly,
                                     self.server.CWlists,
                                     self.server.lists_enabled)
            else:
                print('WARN: Muted post not found: ' + muteFilename)

        if callingDomain.endswith('.onion') and onion_domain:
            actor = \
                'http://' + onion_domain + \
                path.split('?mute=')[0]
        elif (callingDomain.endswith('.i2p') and i2p_domain):
            actor = \
                'http://' + i2p_domain + \
                path.split('?mute=')[0]
        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', '_muteButton', self.server.debug)
        self._redirect_headers(actor + '/' +
                               timelineStr + timelineBookmark,
                               cookie, callingDomain)

    def _undoMuteButton(self, callingDomain: str, path: str,
                        base_dir: str, http_prefix: str,
                        domain: str, domainFull: str, port: int,
                        onion_domain: str, i2p_domain: str,
                        GETstartTime,
                        proxy_type: str, cookie: str,
                        debug: str):
        """Undo mute button is pressed
        """
        muteUrl = path.split('?unmute=')[1]
        if '?' in muteUrl:
            muteUrl = muteUrl.split('?')[0]
        timelineBookmark = ''
        if '?bm=' in path:
            timelineBookmark = path.split('?bm=')[1]
            if '?' in timelineBookmark:
                timelineBookmark = timelineBookmark.split('?')[0]
            timelineBookmark = '#' + timelineBookmark
        timelineStr = self.server.defaultTimeline
        if '?tl=' in path:
            timelineStr = path.split('?tl=')[1]
            if '?' in timelineStr:
                timelineStr = timelineStr.split('?')[0]
        pageNumber = 1
        if '?page=' in path:
            pageNumberStr = path.split('?page=')[1]
            if '?' in pageNumberStr:
                pageNumberStr = pageNumberStr.split('?')[0]
            if '#' in pageNumberStr:
                pageNumberStr = pageNumberStr.split('#')[0]
            if pageNumberStr.isdigit():
                pageNumber = int(pageNumberStr)
        actor = \
            http_prefix + '://' + domainFull + path.split('?unmute=')[0]
        nickname = getNicknameFromActor(actor)
        unmutePost(base_dir, nickname, domain, port,
                   http_prefix, muteUrl,
                   self.server.recentPostsCache, debug)
        muteFilename = \
            locatePost(base_dir, nickname, domain, muteUrl)
        if muteFilename:
            print('unmutePost: ' +
                  'Regenerating html post for changed unmute status')
            mutePostJson = loadJson(muteFilename, 0, 1)
            if mutePostJson:
                cachedPostFilename = \
                    getCachedPostFilename(base_dir, nickname,
                                          domain, mutePostJson)
                print('unmutePost: Unmuted post json: ' + str(mutePostJson))
                print('unmutePost: Unmuted post nickname: ' +
                      nickname + ' ' + domain)
                print('unmutePost: Unmuted post cache: ' +
                      str(cachedPostFilename))
                showIndividualPostIcons = True
                manuallyApproveFollowers = \
                    followerApprovalActive(base_dir, nickname, domain)
                showRepeats = not isDM(mutePostJson)
                showPublicOnly = False
                storeToCache = True
                useCacheOnly = False
                allowDownloads = False
                showAvatarOptions = True
                avatarUrl = None
                individualPostAsHtml(self.server.signingPrivateKeyPem,
                                     allowDownloads,
                                     self.server.recentPostsCache,
                                     self.server.max_recent_posts,
                                     self.server.translate,
                                     pageNumber, base_dir,
                                     self.server.session,
                                     self.server.cachedWebfingers,
                                     self.server.personCache,
                                     nickname, domain,
                                     self.server.port, mutePostJson,
                                     avatarUrl, showAvatarOptions,
                                     self.server.allowDeletion,
                                     http_prefix,
                                     self.server.project_version, timelineStr,
                                     self.server.yt_replace_domain,
                                     self.server.twitter_replacement_domain,
                                     self.server.show_published_date_only,
                                     self.server.peertubeInstances,
                                     self.server.allow_local_network_access,
                                     self.server.themeName,
                                     self.server.systemLanguage,
                                     self.server.max_like_count,
                                     showRepeats,
                                     showIndividualPostIcons,
                                     manuallyApproveFollowers,
                                     showPublicOnly, storeToCache,
                                     useCacheOnly,
                                     self.server.CWlists,
                                     self.server.lists_enabled)
            else:
                print('WARN: Unmuted post not found: ' + muteFilename)
        if callingDomain.endswith('.onion') and onion_domain:
            actor = \
                'http://' + onion_domain + path.split('?unmute=')[0]
        elif callingDomain.endswith('.i2p') and i2p_domain:
            actor = \
                'http://' + i2p_domain + path.split('?unmute=')[0]
        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', '_undoMuteButton', self.server.debug)
        self._redirect_headers(actor + '/' + timelineStr +
                               timelineBookmark,
                               cookie, callingDomain)

    def _showRepliesToPost(self, authorized: bool,
                           callingDomain: str, path: str,
                           base_dir: str, http_prefix: str,
                           domain: str, domainFull: str, port: int,
                           onion_domain: str, i2p_domain: str,
                           GETstartTime,
                           proxy_type: str, cookie: str,
                           debug: str) -> bool:
        """Shows the replies to a post
        """
        if not ('/statuses/' in path and '/users/' in path):
            return False

        namedStatus = path.split('/users/')[1]
        if '/' not in namedStatus:
            return False

        postSections = namedStatus.split('/')
        if len(postSections) < 4:
            return False

        if not postSections[3].startswith('replies'):
            return False
        nickname = postSections[0]
        statusNumber = postSections[2]
        if not (len(statusNumber) > 10 and statusNumber.isdigit()):
            return False

        boxname = 'outbox'
        # get the replies file
        postDir = \
            acctDir(base_dir, nickname, domain) + '/' + boxname
        postRepliesFilename = \
            postDir + '/' + \
            http_prefix + ':##' + domainFull + '#users#' + \
            nickname + '#statuses#' + statusNumber + '.replies'
        if not os.path.isfile(postRepliesFilename):
            # There are no replies,
            # so show empty collection
            contextStr = \
                'https://www.w3.org/ns/activitystreams'

            firstStr = \
                localActorUrl(http_prefix, nickname, domainFull) + \
                '/statuses/' + statusNumber + '/replies?page=true'

            idStr = \
                localActorUrl(http_prefix, nickname, domainFull) + \
                '/statuses/' + statusNumber + '/replies'

            lastStr = \
                localActorUrl(http_prefix, nickname, domainFull) + \
                '/statuses/' + statusNumber + '/replies?page=true'

            repliesJson = {
                '@context': contextStr,
                'first': firstStr,
                'id': idStr,
                'last': lastStr,
                'totalItems': 0,
                'type': 'OrderedCollection'
            }

            if self._requestHTTP():
                if not self._establishSession("showRepliesToPost"):
                    self._404()
                    return True
                recentPostsCache = self.server.recentPostsCache
                max_recent_posts = self.server.max_recent_posts
                translate = self.server.translate
                session = self.server.session
                cachedWebfingers = self.server.cachedWebfingers
                personCache = self.server.personCache
                project_version = self.server.project_version
                ytDomain = self.server.yt_replace_domain
                twitter_replacement_domain = \
                    self.server.twitter_replacement_domain
                peertubeInstances = self.server.peertubeInstances
                msg = \
                    htmlPostReplies(self.server.cssCache,
                                    recentPostsCache,
                                    max_recent_posts,
                                    translate,
                                    base_dir,
                                    session,
                                    cachedWebfingers,
                                    personCache,
                                    nickname,
                                    domain,
                                    port,
                                    repliesJson,
                                    http_prefix,
                                    project_version,
                                    ytDomain,
                                    twitter_replacement_domain,
                                    self.server.show_published_date_only,
                                    peertubeInstances,
                                    self.server.allow_local_network_access,
                                    self.server.themeName,
                                    self.server.systemLanguage,
                                    self.server.max_like_count,
                                    self.server.signingPrivateKeyPem,
                                    self.server.CWlists,
                                    self.server.lists_enabled)
                msg = msg.encode('utf-8')
                msglen = len(msg)
                self._set_headers('text/html', msglen,
                                  cookie, callingDomain, False)
                self._write(msg)
                fitnessPerformance(GETstartTime, self.server.fitness,
                                   '_GET', '_showRepliesToPost',
                                   self.server.debug)
            else:
                if self._secure_mode():
                    msg = json.dumps(repliesJson, ensure_ascii=False)
                    msg = msg.encode('utf-8')
                    protocolStr = 'application/json'
                    msglen = len(msg)
                    self._set_headers(protocolStr, msglen, None,
                                      callingDomain, False)
                    self._write(msg)
                    fitnessPerformance(GETstartTime, self.server.fitness,
                                       '_GET', '_showRepliesToPost json',
                                       self.server.debug)
                else:
                    self._404()
            return True
        else:
            # replies exist. Itterate through the
            # text file containing message ids
            contextStr = 'https://www.w3.org/ns/activitystreams'

            idStr = \
                localActorUrl(http_prefix, nickname, domainFull) + \
                '/statuses/' + statusNumber + '?page=true'

            partOfStr = \
                localActorUrl(http_prefix, nickname, domainFull) + \
                '/statuses/' + statusNumber

            repliesJson = {
                '@context': contextStr,
                'id': idStr,
                'orderedItems': [
                ],
                'partOf': partOfStr,
                'type': 'OrderedCollectionPage'
            }

            # populate the items list with replies
            populateRepliesJson(base_dir, nickname, domain,
                                postRepliesFilename,
                                authorized, repliesJson)

            # send the replies json
            if self._requestHTTP():
                if not self._establishSession("showRepliesToPost2"):
                    self._404()
                    return True
                recentPostsCache = self.server.recentPostsCache
                max_recent_posts = self.server.max_recent_posts
                translate = self.server.translate
                session = self.server.session
                cachedWebfingers = self.server.cachedWebfingers
                personCache = self.server.personCache
                project_version = self.server.project_version
                ytDomain = self.server.yt_replace_domain
                twitter_replacement_domain = \
                    self.server.twitter_replacement_domain
                peertubeInstances = self.server.peertubeInstances
                msg = \
                    htmlPostReplies(self.server.cssCache,
                                    recentPostsCache,
                                    max_recent_posts,
                                    translate,
                                    base_dir,
                                    session,
                                    cachedWebfingers,
                                    personCache,
                                    nickname,
                                    domain,
                                    port,
                                    repliesJson,
                                    http_prefix,
                                    project_version,
                                    ytDomain,
                                    twitter_replacement_domain,
                                    self.server.show_published_date_only,
                                    peertubeInstances,
                                    self.server.allow_local_network_access,
                                    self.server.themeName,
                                    self.server.systemLanguage,
                                    self.server.max_like_count,
                                    self.server.signingPrivateKeyPem,
                                    self.server.CWlists,
                                    self.server.lists_enabled)
                msg = msg.encode('utf-8')
                msglen = len(msg)
                self._set_headers('text/html', msglen,
                                  cookie, callingDomain, False)
                self._write(msg)
                fitnessPerformance(GETstartTime, self.server.fitness,
                                   '_GET', '_showRepliesToPost',
                                   self.server.debug)
            else:
                if self._secure_mode():
                    msg = json.dumps(repliesJson,
                                     ensure_ascii=False)
                    msg = msg.encode('utf-8')
                    protocolStr = 'application/json'
                    msglen = len(msg)
                    self._set_headers(protocolStr, msglen,
                                      None, callingDomain, False)
                    self._write(msg)
                    fitnessPerformance(GETstartTime, self.server.fitness,
                                       '_GET', '_showRepliesToPost json',
                                       self.server.debug)
                else:
                    self._404()
            return True
        return False

    def _showRoles(self, authorized: bool,
                   callingDomain: str, path: str,
                   base_dir: str, http_prefix: str,
                   domain: str, domainFull: str, port: int,
                   onion_domain: str, i2p_domain: str,
                   GETstartTime,
                   proxy_type: str, cookie: str,
                   debug: str) -> bool:
        """Show roles within profile screen
        """
        namedStatus = path.split('/users/')[1]
        if '/' not in namedStatus:
            return False

        postSections = namedStatus.split('/')
        nickname = postSections[0]
        actorFilename = acctDir(base_dir, nickname, domain) + '.json'
        if not os.path.isfile(actorFilename):
            return False

        actorJson = loadJson(actorFilename)
        if not actorJson:
            return False

        if actorJson.get('hasOccupation'):
            if self._requestHTTP():
                getPerson = \
                    personLookup(domain, path.replace('/roles', ''),
                                 base_dir)
                if getPerson:
                    defaultTimeline = \
                        self.server.defaultTimeline
                    recentPostsCache = \
                        self.server.recentPostsCache
                    cachedWebfingers = \
                        self.server.cachedWebfingers
                    yt_replace_domain = \
                        self.server.yt_replace_domain
                    twitter_replacement_domain = \
                        self.server.twitter_replacement_domain
                    icons_as_buttons = \
                        self.server.icons_as_buttons

                    accessKeys = self.server.accessKeys
                    if self.server.keyShortcuts.get(nickname):
                        accessKeys = self.server.keyShortcuts[nickname]

                    rolesList = getActorRolesList(actorJson)
                    city = \
                        getSpoofedCity(self.server.city,
                                       base_dir, nickname, domain)
                    msg = \
                        htmlProfile(self.server.signingPrivateKeyPem,
                                    self.server.rss_icon_at_top,
                                    self.server.cssCache,
                                    icons_as_buttons,
                                    defaultTimeline,
                                    recentPostsCache,
                                    self.server.max_recent_posts,
                                    self.server.translate,
                                    self.server.project_version,
                                    base_dir, http_prefix, True,
                                    getPerson, 'roles',
                                    self.server.session,
                                    cachedWebfingers,
                                    self.server.personCache,
                                    yt_replace_domain,
                                    twitter_replacement_domain,
                                    self.server.show_published_date_only,
                                    self.server.newswire,
                                    self.server.themeName,
                                    self.server.dormant_months,
                                    self.server.peertubeInstances,
                                    self.server.allow_local_network_access,
                                    self.server.textModeBanner,
                                    self.server.debug,
                                    accessKeys, city,
                                    self.server.systemLanguage,
                                    self.server.max_like_count,
                                    self.server.shared_items_federated_domains,
                                    rolesList,
                                    None, None, self.server.CWlists,
                                    self.server.lists_enabled,
                                    self.server.content_license_url)
                    msg = msg.encode('utf-8')
                    msglen = len(msg)
                    self._set_headers('text/html', msglen,
                                      cookie, callingDomain, False)
                    self._write(msg)
                    fitnessPerformance(GETstartTime, self.server.fitness,
                                       '_GET', '_showRoles',
                                       self.server.debug)
            else:
                if self._secure_mode():
                    rolesList = getActorRolesList(actorJson)
                    msg = json.dumps(rolesList,
                                     ensure_ascii=False)
                    msg = msg.encode('utf-8')
                    msglen = len(msg)
                    self._set_headers('application/json', msglen,
                                      None, callingDomain, False)
                    self._write(msg)
                    fitnessPerformance(GETstartTime, self.server.fitness,
                                       '_GET', '_showRoles json',
                                       self.server.debug)
                else:
                    self._404()
            return True
        return False

    def _showSkills(self, authorized: bool,
                    callingDomain: str, path: str,
                    base_dir: str, http_prefix: str,
                    domain: str, domainFull: str, port: int,
                    onion_domain: str, i2p_domain: str,
                    GETstartTime,
                    proxy_type: str, cookie: str,
                    debug: str) -> bool:
        """Show skills on the profile screen
        """
        namedStatus = path.split('/users/')[1]
        if '/' in namedStatus:
            postSections = namedStatus.split('/')
            nickname = postSections[0]
            actorFilename = acctDir(base_dir, nickname, domain) + '.json'
            if os.path.isfile(actorFilename):
                actorJson = loadJson(actorFilename)
                if actorJson:
                    if noOfActorSkills(actorJson) > 0:
                        if self._requestHTTP():
                            getPerson = \
                                personLookup(domain,
                                             path.replace('/skills', ''),
                                             base_dir)
                            if getPerson:
                                defaultTimeline =  \
                                    self.server.defaultTimeline
                                recentPostsCache = \
                                    self.server.recentPostsCache
                                cachedWebfingers = \
                                    self.server.cachedWebfingers
                                yt_replace_domain = \
                                    self.server.yt_replace_domain
                                twitter_replacement_domain = \
                                    self.server.twitter_replacement_domain
                                show_published_date_only = \
                                    self.server.show_published_date_only
                                icons_as_buttons = \
                                    self.server.icons_as_buttons
                                allow_local_network_access = \
                                    self.server.allow_local_network_access
                                accessKeys = self.server.accessKeys
                                if self.server.keyShortcuts.get(nickname):
                                    accessKeys = \
                                        self.server.keyShortcuts[nickname]
                                actorSkillsList = \
                                    getOccupationSkills(actorJson)
                                skills = getSkillsFromList(actorSkillsList)
                                city = getSpoofedCity(self.server.city,
                                                      base_dir,
                                                      nickname, domain)
                                shared_items_federated_domains = \
                                    self.server.shared_items_federated_domains
                                signingPrivateKeyPem = \
                                    self.server.signingPrivateKeyPem
                                content_license_url = \
                                    self.server.content_license_url
                                msg = \
                                    htmlProfile(signingPrivateKeyPem,
                                                self.server.rss_icon_at_top,
                                                self.server.cssCache,
                                                icons_as_buttons,
                                                defaultTimeline,
                                                recentPostsCache,
                                                self.server.max_recent_posts,
                                                self.server.translate,
                                                self.server.project_version,
                                                base_dir, http_prefix, True,
                                                getPerson, 'skills',
                                                self.server.session,
                                                cachedWebfingers,
                                                self.server.personCache,
                                                yt_replace_domain,
                                                twitter_replacement_domain,
                                                show_published_date_only,
                                                self.server.newswire,
                                                self.server.themeName,
                                                self.server.dormant_months,
                                                self.server.peertubeInstances,
                                                allow_local_network_access,
                                                self.server.textModeBanner,
                                                self.server.debug,
                                                accessKeys, city,
                                                self.server.systemLanguage,
                                                self.server.max_like_count,
                                                shared_items_federated_domains,
                                                skills,
                                                None, None,
                                                self.server.CWlists,
                                                self.server.lists_enabled,
                                                content_license_url)
                                msg = msg.encode('utf-8')
                                msglen = len(msg)
                                self._set_headers('text/html', msglen,
                                                  cookie, callingDomain, False)
                                self._write(msg)
                                fitnessPerformance(GETstartTime,
                                                   self.server.fitness,
                                                   '_GET', '_showSkills',
                                                   self.server.debug)
                        else:
                            if self._secure_mode():
                                actorSkillsList = \
                                    getOccupationSkills(actorJson)
                                skills = getSkillsFromList(actorSkillsList)
                                msg = json.dumps(skills,
                                                 ensure_ascii=False)
                                msg = msg.encode('utf-8')
                                msglen = len(msg)
                                self._set_headers('application/json',
                                                  msglen, None,
                                                  callingDomain, False)
                                self._write(msg)
                                fitnessPerformance(GETstartTime,
                                                   self.server.fitness,
                                                   '_GET', '_showSkills json',
                                                   self.server.debug)
                            else:
                                self._404()
                        return True
        actor = path.replace('/skills', '')
        actorAbsolute = self._getInstanceUrl(callingDomain) + actor
        self._redirect_headers(actorAbsolute, cookie, callingDomain)
        return True

    def _showIndividualAtPost(self, authorized: bool,
                              callingDomain: str, path: str,
                              base_dir: str, http_prefix: str,
                              domain: str, domainFull: str, port: int,
                              onion_domain: str, i2p_domain: str,
                              GETstartTime,
                              proxy_type: str, cookie: str,
                              debug: str) -> bool:
        """get an individual post from the path /@nickname/statusnumber
        """
        if '/@' not in path:
            return False

        likedBy = None
        if '?likedBy=' in path:
            likedBy = path.split('?likedBy=')[1].strip()
            if '?' in likedBy:
                likedBy = likedBy.split('?')[0]
            path = path.split('?likedBy=')[0]

        reactBy = None
        reactEmoji = None
        if '?reactBy=' in path:
            reactBy = path.split('?reactBy=')[1].strip()
            if ';' in reactBy:
                reactBy = reactBy.split(';')[0]
            if ';emoj=' in path:
                reactEmoji = path.split(';emoj=')[1].strip()
                if ';' in reactEmoji:
                    reactEmoji = reactEmoji.split(';')[0]
            path = path.split('?reactBy=')[0]

        namedStatus = path.split('/@')[1]
        if '/' not in namedStatus:
            # show actor
            nickname = namedStatus
            return False

        postSections = namedStatus.split('/')
        if len(postSections) != 2:
            return False
        nickname = postSections[0]
        statusNumber = postSections[1]
        if len(statusNumber) <= 10 or not statusNumber.isdigit():
            return False

        postFilename = \
            acctDir(base_dir, nickname, domain) + '/outbox/' + \
            http_prefix + ':##' + domainFull + '#users#' + nickname + \
            '#statuses#' + statusNumber + '.json'

        includeCreateWrapper = False
        if postSections[-1] == 'activity':
            includeCreateWrapper = True

        result = self._showPostFromFile(postFilename, likedBy,
                                        reactBy, reactEmoji,
                                        authorized, callingDomain, path,
                                        base_dir, http_prefix, nickname,
                                        domain, domainFull, port,
                                        onion_domain, i2p_domain,
                                        GETstartTime,
                                        proxy_type, cookie, debug,
                                        includeCreateWrapper)
        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', '_showIndividualAtPost',
                           self.server.debug)
        return result

    def _showPostFromFile(self, postFilename: str, likedBy: str,
                          reactBy: str, reactEmoji: str,
                          authorized: bool,
                          callingDomain: str, path: str,
                          base_dir: str, http_prefix: str, nickname: str,
                          domain: str, domainFull: str, port: int,
                          onion_domain: str, i2p_domain: str,
                          GETstartTime,
                          proxy_type: str, cookie: str,
                          debug: str, includeCreateWrapper: bool) -> bool:
        """Shows an individual post from its filename
        """
        if not os.path.isfile(postFilename):
            self._404()
            self.server.GETbusy = False
            return True

        postJsonObject = loadJson(postFilename)
        if not postJsonObject:
            self.send_response(429)
            self.end_headers()
            self.server.GETbusy = False
            return True

        # Only authorized viewers get to see likes on posts
        # Otherwize marketers could gain more social graph info
        if not authorized:
            pjo = postJsonObject
            if not isPublicPost(pjo):
                self._404()
                self.server.GETbusy = False
                return True
            removePostInteractions(pjo, True)
        if self._requestHTTP():
            msg = \
                htmlIndividualPost(self.server.cssCache,
                                   self.server.recentPostsCache,
                                   self.server.max_recent_posts,
                                   self.server.translate,
                                   base_dir,
                                   self.server.session,
                                   self.server.cachedWebfingers,
                                   self.server.personCache,
                                   nickname, domain, port,
                                   authorized,
                                   postJsonObject,
                                   http_prefix,
                                   self.server.project_version,
                                   likedBy, reactBy, reactEmoji,
                                   self.server.yt_replace_domain,
                                   self.server.twitter_replacement_domain,
                                   self.server.show_published_date_only,
                                   self.server.peertubeInstances,
                                   self.server.allow_local_network_access,
                                   self.server.themeName,
                                   self.server.systemLanguage,
                                   self.server.max_like_count,
                                   self.server.signingPrivateKeyPem,
                                   self.server.CWlists,
                                   self.server.lists_enabled)
            msg = msg.encode('utf-8')
            msglen = len(msg)
            self._set_headers('text/html', msglen,
                              cookie, callingDomain, False)
            self._write(msg)
            fitnessPerformance(GETstartTime, self.server.fitness,
                               '_GET', '_showPostFromFile',
                               self.server.debug)
        else:
            if self._secure_mode():
                if not includeCreateWrapper and \
                   postJsonObject['type'] == 'Create' and \
                   hasObjectDict(postJsonObject):
                    unwrappedJson = postJsonObject['object']
                    unwrappedJson['@context'] = \
                        getIndividualPostContext()
                    msg = json.dumps(unwrappedJson,
                                     ensure_ascii=False)
                else:
                    msg = json.dumps(postJsonObject,
                                     ensure_ascii=False)
                msg = msg.encode('utf-8')
                msglen = len(msg)
                self._set_headers('application/json',
                                  msglen,
                                  None, callingDomain, False)
                self._write(msg)
                fitnessPerformance(GETstartTime, self.server.fitness,
                                   '_GET', '_showPostFromFile json',
                                   self.server.debug)
            else:
                self._404()
        self.server.GETbusy = False
        return True

    def _showIndividualPost(self, authorized: bool,
                            callingDomain: str, path: str,
                            base_dir: str, http_prefix: str,
                            domain: str, domainFull: str, port: int,
                            onion_domain: str, i2p_domain: str,
                            GETstartTime,
                            proxy_type: str, cookie: str,
                            debug: str) -> bool:
        """Shows an individual post
        """
        likedBy = None
        if '?likedBy=' in path:
            likedBy = path.split('?likedBy=')[1].strip()
            if '?' in likedBy:
                likedBy = likedBy.split('?')[0]
            path = path.split('?likedBy=')[0]

        reactBy = None
        reactEmoji = None
        if '?reactBy=' in path:
            reactBy = path.split('?reactBy=')[1].strip()
            if ';' in reactBy:
                reactBy = reactBy.split(';')[0]
            if ';emoj=' in path:
                reactEmoji = path.split(';emoj=')[1].strip()
                if ';' in reactEmoji:
                    reactEmoji = reactEmoji.split(';')[0]
            path = path.split('?reactBy=')[0]

        namedStatus = path.split('/users/')[1]
        if '/' not in namedStatus:
            return False
        postSections = namedStatus.split('/')
        if len(postSections) < 3:
            return False
        nickname = postSections[0]
        statusNumber = postSections[2]
        if len(statusNumber) <= 10 or (not statusNumber.isdigit()):
            return False

        postFilename = \
            acctDir(base_dir, nickname, domain) + '/outbox/' + \
            http_prefix + ':##' + domainFull + '#users#' + nickname + \
            '#statuses#' + statusNumber + '.json'

        includeCreateWrapper = False
        if postSections[-1] == 'activity':
            includeCreateWrapper = True

        result = self._showPostFromFile(postFilename, likedBy,
                                        reactBy, reactEmoji,
                                        authorized, callingDomain, path,
                                        base_dir, http_prefix, nickname,
                                        domain, domainFull, port,
                                        onion_domain, i2p_domain,
                                        GETstartTime,
                                        proxy_type, cookie, debug,
                                        includeCreateWrapper)
        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', '_showIndividualPost',
                           self.server.debug)
        return result

    def _showNotifyPost(self, authorized: bool,
                        callingDomain: str, path: str,
                        base_dir: str, http_prefix: str,
                        domain: str, domainFull: str, port: int,
                        onion_domain: str, i2p_domain: str,
                        GETstartTime,
                        proxy_type: str, cookie: str,
                        debug: str) -> bool:
        """Shows an individual post from an account which you are following
        and where you have the notify checkbox set on person options
        """
        likedBy = None
        reactBy = None
        reactEmoji = None
        postId = path.split('?notifypost=')[1].strip()
        postId = postId.replace('-', '/')
        path = path.split('?notifypost=')[0]
        nickname = path.split('/users/')[1]
        if '/' in nickname:
            return False
        replies = False

        postFilename = locatePost(base_dir, nickname, domain, postId, replies)
        if not postFilename:
            return False

        includeCreateWrapper = False
        if path.endswith('/activity'):
            includeCreateWrapper = True

        result = self._showPostFromFile(postFilename, likedBy,
                                        reactBy, reactEmoji,
                                        authorized, callingDomain, path,
                                        base_dir, http_prefix, nickname,
                                        domain, domainFull, port,
                                        onion_domain, i2p_domain,
                                        GETstartTime,
                                        proxy_type, cookie, debug,
                                        includeCreateWrapper)
        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', '_showNotifyPost',
                           self.server.debug)
        return result

    def _showInbox(self, authorized: bool,
                   callingDomain: str, path: str,
                   base_dir: str, http_prefix: str,
                   domain: str, domainFull: str, port: int,
                   onion_domain: str, i2p_domain: str,
                   GETstartTime,
                   proxy_type: str, cookie: str,
                   debug: str,
                   recentPostsCache: {}, session,
                   defaultTimeline: str,
                   max_recent_posts: int,
                   translate: {},
                   cachedWebfingers: {},
                   personCache: {},
                   allowDeletion: bool,
                   project_version: str,
                   yt_replace_domain: str,
                   twitter_replacement_domain: str) -> bool:
        """Shows the inbox timeline
        """
        if '/users/' in path:
            if authorized:
                inboxFeed = \
                    personBoxJson(recentPostsCache,
                                  session,
                                  base_dir,
                                  domain,
                                  port,
                                  path,
                                  http_prefix,
                                  maxPostsInFeed, 'inbox',
                                  authorized,
                                  0,
                                  self.server.positive_voting,
                                  self.server.voting_time_mins)
                if inboxFeed:
                    if GETstartTime:
                        fitnessPerformance(GETstartTime,
                                           self.server.fitness,
                                           '_GET', '_showInbox',
                                           self.server.debug)
                    if self._requestHTTP():
                        nickname = path.replace('/users/', '')
                        nickname = nickname.replace('/inbox', '')
                        pageNumber = 1
                        if '?page=' in nickname:
                            pageNumber = nickname.split('?page=')[1]
                            nickname = nickname.split('?page=')[0]
                            if pageNumber.isdigit():
                                pageNumber = int(pageNumber)
                            else:
                                pageNumber = 1
                        if 'page=' not in path:
                            # if no page was specified then show the first
                            inboxFeed = \
                                personBoxJson(recentPostsCache,
                                              session,
                                              base_dir,
                                              domain,
                                              port,
                                              path + '?page=1',
                                              http_prefix,
                                              maxPostsInFeed, 'inbox',
                                              authorized,
                                              0,
                                              self.server.positive_voting,
                                              self.server.voting_time_mins)
                            if GETstartTime:
                                fitnessPerformance(GETstartTime,
                                                   self.server.fitness,
                                                   '_GET', '_showInbox2',
                                                   self.server.debug)
                        full_width_tl_button_header = \
                            self.server.full_width_tl_button_header
                        minimalNick = isMinimal(base_dir, domain, nickname)

                        accessKeys = self.server.accessKeys
                        if self.server.keyShortcuts.get(nickname):
                            accessKeys = \
                                self.server.keyShortcuts[nickname]

                        shared_items_federated_domains = \
                            self.server.shared_items_federated_domains
                        msg = htmlInbox(self.server.cssCache,
                                        defaultTimeline,
                                        recentPostsCache,
                                        max_recent_posts,
                                        translate,
                                        pageNumber, maxPostsInFeed,
                                        session,
                                        base_dir,
                                        cachedWebfingers,
                                        personCache,
                                        nickname,
                                        domain,
                                        port,
                                        inboxFeed,
                                        allowDeletion,
                                        http_prefix,
                                        project_version,
                                        minimalNick,
                                        yt_replace_domain,
                                        twitter_replacement_domain,
                                        self.server.show_published_date_only,
                                        self.server.newswire,
                                        self.server.positive_voting,
                                        self.server.show_publish_as_icon,
                                        full_width_tl_button_header,
                                        self.server.icons_as_buttons,
                                        self.server.rss_icon_at_top,
                                        self.server.publish_button_at_top,
                                        authorized,
                                        self.server.themeName,
                                        self.server.peertubeInstances,
                                        self.server.allow_local_network_access,
                                        self.server.textModeBanner,
                                        accessKeys,
                                        self.server.systemLanguage,
                                        self.server.max_like_count,
                                        shared_items_federated_domains,
                                        self.server.signingPrivateKeyPem,
                                        self.server.CWlists,
                                        self.server.lists_enabled)
                        if GETstartTime:
                            fitnessPerformance(GETstartTime,
                                               self.server.fitness,
                                               '_GET', '_showInbox3',
                                               self.server.debug)
                        if msg:
                            msg = msg.encode('utf-8')
                            msglen = len(msg)
                            self._set_headers('text/html', msglen,
                                              cookie, callingDomain, False)
                            self._write(msg)

                        if GETstartTime:
                            fitnessPerformance(GETstartTime,
                                               self.server.fitness,
                                               '_GET', '_showInbox4',
                                               self.server.debug)
                    else:
                        # don't need authorized fetch here because
                        # there is already the authorization check
                        msg = json.dumps(inboxFeed, ensure_ascii=False)
                        msg = msg.encode('utf-8')
                        msglen = len(msg)
                        self._set_headers('application/json', msglen,
                                          None, callingDomain, False)
                        self._write(msg)
                        fitnessPerformance(GETstartTime,
                                           self.server.fitness,
                                           '_GET', '_showInbox5',
                                           self.server.debug)
                    return True
            else:
                if debug:
                    nickname = path.replace('/users/', '')
                    nickname = nickname.replace('/inbox', '')
                    print('DEBUG: ' + nickname +
                          ' was not authorized to access ' + path)
        if path != '/inbox':
            # not the shared inbox
            if debug:
                print('DEBUG: GET access to inbox is unauthorized')
            self.send_response(405)
            self.end_headers()
            return True
        return False

    def _showDMs(self, authorized: bool,
                 callingDomain: str, path: str,
                 base_dir: str, http_prefix: str,
                 domain: str, domainFull: str, port: int,
                 onion_domain: str, i2p_domain: str,
                 GETstartTime,
                 proxy_type: str, cookie: str,
                 debug: str) -> bool:
        """Shows the DMs timeline
        """
        if '/users/' in path:
            if authorized:
                inboxDMFeed = \
                    personBoxJson(self.server.recentPostsCache,
                                  self.server.session,
                                  base_dir,
                                  domain,
                                  port,
                                  path,
                                  http_prefix,
                                  maxPostsInFeed, 'dm',
                                  authorized,
                                  0, self.server.positive_voting,
                                  self.server.voting_time_mins)
                if inboxDMFeed:
                    if self._requestHTTP():
                        nickname = path.replace('/users/', '')
                        nickname = nickname.replace('/dm', '')
                        pageNumber = 1
                        if '?page=' in nickname:
                            pageNumber = nickname.split('?page=')[1]
                            nickname = nickname.split('?page=')[0]
                            if pageNumber.isdigit():
                                pageNumber = int(pageNumber)
                            else:
                                pageNumber = 1
                        if 'page=' not in path:
                            # if no page was specified then show the first
                            inboxDMFeed = \
                                personBoxJson(self.server.recentPostsCache,
                                              self.server.session,
                                              base_dir,
                                              domain,
                                              port,
                                              path + '?page=1',
                                              http_prefix,
                                              maxPostsInFeed, 'dm',
                                              authorized,
                                              0,
                                              self.server.positive_voting,
                                              self.server.voting_time_mins)
                        full_width_tl_button_header = \
                            self.server.full_width_tl_button_header
                        minimalNick = isMinimal(base_dir, domain, nickname)

                        accessKeys = self.server.accessKeys
                        if self.server.keyShortcuts.get(nickname):
                            accessKeys = \
                                self.server.keyShortcuts[nickname]

                        shared_items_federated_domains = \
                            self.server.shared_items_federated_domains
                        allow_local_network_access = \
                            self.server.allow_local_network_access
                        twitter_replacement_domain = \
                            self.server.twitter_replacement_domain
                        msg = \
                            htmlInboxDMs(self.server.cssCache,
                                         self.server.defaultTimeline,
                                         self.server.recentPostsCache,
                                         self.server.max_recent_posts,
                                         self.server.translate,
                                         pageNumber, maxPostsInFeed,
                                         self.server.session,
                                         base_dir,
                                         self.server.cachedWebfingers,
                                         self.server.personCache,
                                         nickname,
                                         domain,
                                         port,
                                         inboxDMFeed,
                                         self.server.allowDeletion,
                                         http_prefix,
                                         self.server.project_version,
                                         minimalNick,
                                         self.server.yt_replace_domain,
                                         twitter_replacement_domain,
                                         self.server.show_published_date_only,
                                         self.server.newswire,
                                         self.server.positive_voting,
                                         self.server.show_publish_as_icon,
                                         full_width_tl_button_header,
                                         self.server.icons_as_buttons,
                                         self.server.rss_icon_at_top,
                                         self.server.publish_button_at_top,
                                         authorized, self.server.themeName,
                                         self.server.peertubeInstances,
                                         allow_local_network_access,
                                         self.server.textModeBanner,
                                         accessKeys,
                                         self.server.systemLanguage,
                                         self.server.max_like_count,
                                         shared_items_federated_domains,
                                         self.server.signingPrivateKeyPem,
                                         self.server.CWlists,
                                         self.server.lists_enabled)
                        msg = msg.encode('utf-8')
                        msglen = len(msg)
                        self._set_headers('text/html', msglen,
                                          cookie, callingDomain, False)
                        self._write(msg)
                        fitnessPerformance(GETstartTime,
                                           self.server.fitness,
                                           '_GET', '_showDMs',
                                           self.server.debug)
                    else:
                        # don't need authorized fetch here because
                        # there is already the authorization check
                        msg = json.dumps(inboxDMFeed, ensure_ascii=False)
                        msg = msg.encode('utf-8')
                        msglen = len(msg)
                        self._set_headers('application/json',
                                          msglen,
                                          None, callingDomain, False)
                        self._write(msg)
                        fitnessPerformance(GETstartTime,
                                           self.server.fitness,
                                           '_GET', '_showDMs json',
                                           self.server.debug)
                    return True
            else:
                if debug:
                    nickname = path.replace('/users/', '')
                    nickname = nickname.replace('/dm', '')
                    print('DEBUG: ' + nickname +
                          ' was not authorized to access ' + path)
        if path != '/dm':
            # not the DM inbox
            if debug:
                print('DEBUG: GET access to DM timeline is unauthorized')
            self.send_response(405)
            self.end_headers()
            return True
        return False

    def _showReplies(self, authorized: bool,
                     callingDomain: str, path: str,
                     base_dir: str, http_prefix: str,
                     domain: str, domainFull: str, port: int,
                     onion_domain: str, i2p_domain: str,
                     GETstartTime,
                     proxy_type: str, cookie: str,
                     debug: str) -> bool:
        """Shows the replies timeline
        """
        if '/users/' in path:
            if authorized:
                inboxRepliesFeed = \
                    personBoxJson(self.server.recentPostsCache,
                                  self.server.session,
                                  base_dir,
                                  domain,
                                  port,
                                  path,
                                  http_prefix,
                                  maxPostsInFeed, 'tlreplies',
                                  True,
                                  0, self.server.positive_voting,
                                  self.server.voting_time_mins)
                if not inboxRepliesFeed:
                    inboxRepliesFeed = []
                if self._requestHTTP():
                    nickname = path.replace('/users/', '')
                    nickname = nickname.replace('/tlreplies', '')
                    pageNumber = 1
                    if '?page=' in nickname:
                        pageNumber = nickname.split('?page=')[1]
                        nickname = nickname.split('?page=')[0]
                        if pageNumber.isdigit():
                            pageNumber = int(pageNumber)
                        else:
                            pageNumber = 1
                    if 'page=' not in path:
                        # if no page was specified then show the first
                        inboxRepliesFeed = \
                            personBoxJson(self.server.recentPostsCache,
                                          self.server.session,
                                          base_dir,
                                          domain,
                                          port,
                                          path + '?page=1',
                                          http_prefix,
                                          maxPostsInFeed, 'tlreplies',
                                          True,
                                          0, self.server.positive_voting,
                                          self.server.voting_time_mins)
                    full_width_tl_button_header = \
                        self.server.full_width_tl_button_header
                    minimalNick = isMinimal(base_dir, domain, nickname)

                    accessKeys = self.server.accessKeys
                    if self.server.keyShortcuts.get(nickname):
                        accessKeys = \
                            self.server.keyShortcuts[nickname]

                    shared_items_federated_domains = \
                        self.server.shared_items_federated_domains
                    allow_local_network_access = \
                        self.server.allow_local_network_access
                    twitter_replacement_domain = \
                        self.server.twitter_replacement_domain
                    msg = \
                        htmlInboxReplies(self.server.cssCache,
                                         self.server.defaultTimeline,
                                         self.server.recentPostsCache,
                                         self.server.max_recent_posts,
                                         self.server.translate,
                                         pageNumber, maxPostsInFeed,
                                         self.server.session,
                                         base_dir,
                                         self.server.cachedWebfingers,
                                         self.server.personCache,
                                         nickname,
                                         domain,
                                         port,
                                         inboxRepliesFeed,
                                         self.server.allowDeletion,
                                         http_prefix,
                                         self.server.project_version,
                                         minimalNick,
                                         self.server.yt_replace_domain,
                                         twitter_replacement_domain,
                                         self.server.show_published_date_only,
                                         self.server.newswire,
                                         self.server.positive_voting,
                                         self.server.show_publish_as_icon,
                                         full_width_tl_button_header,
                                         self.server.icons_as_buttons,
                                         self.server.rss_icon_at_top,
                                         self.server.publish_button_at_top,
                                         authorized, self.server.themeName,
                                         self.server.peertubeInstances,
                                         allow_local_network_access,
                                         self.server.textModeBanner,
                                         accessKeys,
                                         self.server.systemLanguage,
                                         self.server.max_like_count,
                                         shared_items_federated_domains,
                                         self.server.signingPrivateKeyPem,
                                         self.server.CWlists,
                                         self.server.lists_enabled)
                    msg = msg.encode('utf-8')
                    msglen = len(msg)
                    self._set_headers('text/html', msglen,
                                      cookie, callingDomain, False)
                    self._write(msg)
                    fitnessPerformance(GETstartTime,
                                       self.server.fitness,
                                       '_GET', '_showReplies',
                                       self.server.debug)
                else:
                    # don't need authorized fetch here because there is
                    # already the authorization check
                    msg = json.dumps(inboxRepliesFeed,
                                     ensure_ascii=False)
                    msg = msg.encode('utf-8')
                    msglen = len(msg)
                    self._set_headers('application/json', msglen,
                                      None, callingDomain, False)
                    self._write(msg)
                    fitnessPerformance(GETstartTime,
                                       self.server.fitness,
                                       '_GET', '_showReplies json',
                                       self.server.debug)
                return True
            else:
                if debug:
                    nickname = path.replace('/users/', '')
                    nickname = nickname.replace('/tlreplies', '')
                    print('DEBUG: ' + nickname +
                          ' was not authorized to access ' + path)
        if path != '/tlreplies':
            # not the replies inbox
            if debug:
                print('DEBUG: GET access to inbox is unauthorized')
            self.send_response(405)
            self.end_headers()
            return True
        return False

    def _showMediaTimeline(self, authorized: bool,
                           callingDomain: str, path: str,
                           base_dir: str, http_prefix: str,
                           domain: str, domainFull: str, port: int,
                           onion_domain: str, i2p_domain: str,
                           GETstartTime,
                           proxy_type: str, cookie: str,
                           debug: str) -> bool:
        """Shows the media timeline
        """
        if '/users/' in path:
            if authorized:
                inboxMediaFeed = \
                    personBoxJson(self.server.recentPostsCache,
                                  self.server.session,
                                  base_dir,
                                  domain,
                                  port,
                                  path,
                                  http_prefix,
                                  maxPostsInMediaFeed, 'tlmedia',
                                  True,
                                  0, self.server.positive_voting,
                                  self.server.voting_time_mins)
                if not inboxMediaFeed:
                    inboxMediaFeed = []
                if self._requestHTTP():
                    nickname = path.replace('/users/', '')
                    nickname = nickname.replace('/tlmedia', '')
                    pageNumber = 1
                    if '?page=' in nickname:
                        pageNumber = nickname.split('?page=')[1]
                        nickname = nickname.split('?page=')[0]
                        if pageNumber.isdigit():
                            pageNumber = int(pageNumber)
                        else:
                            pageNumber = 1
                    if 'page=' not in path:
                        # if no page was specified then show the first
                        inboxMediaFeed = \
                            personBoxJson(self.server.recentPostsCache,
                                          self.server.session,
                                          base_dir,
                                          domain,
                                          port,
                                          path + '?page=1',
                                          http_prefix,
                                          maxPostsInMediaFeed, 'tlmedia',
                                          True,
                                          0, self.server.positive_voting,
                                          self.server.voting_time_mins)
                    full_width_tl_button_header = \
                        self.server.full_width_tl_button_header
                    minimalNick = isMinimal(base_dir, domain, nickname)

                    accessKeys = self.server.accessKeys
                    if self.server.keyShortcuts.get(nickname):
                        accessKeys = \
                            self.server.keyShortcuts[nickname]
                    fed_domains = \
                        self.server.shared_items_federated_domains

                    msg = \
                        htmlInboxMedia(self.server.cssCache,
                                       self.server.defaultTimeline,
                                       self.server.recentPostsCache,
                                       self.server.max_recent_posts,
                                       self.server.translate,
                                       pageNumber, maxPostsInMediaFeed,
                                       self.server.session,
                                       base_dir,
                                       self.server.cachedWebfingers,
                                       self.server.personCache,
                                       nickname,
                                       domain,
                                       port,
                                       inboxMediaFeed,
                                       self.server.allowDeletion,
                                       http_prefix,
                                       self.server.project_version,
                                       minimalNick,
                                       self.server.yt_replace_domain,
                                       self.server.twitter_replacement_domain,
                                       self.server.show_published_date_only,
                                       self.server.newswire,
                                       self.server.positive_voting,
                                       self.server.show_publish_as_icon,
                                       full_width_tl_button_header,
                                       self.server.icons_as_buttons,
                                       self.server.rss_icon_at_top,
                                       self.server.publish_button_at_top,
                                       authorized,
                                       self.server.themeName,
                                       self.server.peertubeInstances,
                                       self.server.allow_local_network_access,
                                       self.server.textModeBanner,
                                       accessKeys,
                                       self.server.systemLanguage,
                                       self.server.max_like_count,
                                       fed_domains,
                                       self.server.signingPrivateKeyPem,
                                       self.server.CWlists,
                                       self.server.lists_enabled)
                    msg = msg.encode('utf-8')
                    msglen = len(msg)
                    self._set_headers('text/html', msglen,
                                      cookie, callingDomain, False)
                    self._write(msg)
                    fitnessPerformance(GETstartTime,
                                       self.server.fitness,
                                       '_GET', '_showMediaTimeline',
                                       self.server.debug)
                else:
                    # don't need authorized fetch here because there is
                    # already the authorization check
                    msg = json.dumps(inboxMediaFeed,
                                     ensure_ascii=False)
                    msg = msg.encode('utf-8')
                    msglen = len(msg)
                    self._set_headers('application/json', msglen,
                                      None, callingDomain, False)
                    self._write(msg)
                    fitnessPerformance(GETstartTime,
                                       self.server.fitness,
                                       '_GET', '_showMediaTimeline json',
                                       self.server.debug)
                return True
            else:
                if debug:
                    nickname = path.replace('/users/', '')
                    nickname = nickname.replace('/tlmedia', '')
                    print('DEBUG: ' + nickname +
                          ' was not authorized to access ' + path)
        if path != '/tlmedia':
            # not the media inbox
            if debug:
                print('DEBUG: GET access to inbox is unauthorized')
            self.send_response(405)
            self.end_headers()
            return True
        return False

    def _showBlogsTimeline(self, authorized: bool,
                           callingDomain: str, path: str,
                           base_dir: str, http_prefix: str,
                           domain: str, domainFull: str, port: int,
                           onion_domain: str, i2p_domain: str,
                           GETstartTime,
                           proxy_type: str, cookie: str,
                           debug: str) -> bool:
        """Shows the blogs timeline
        """
        if '/users/' in path:
            if authorized:
                inboxBlogsFeed = \
                    personBoxJson(self.server.recentPostsCache,
                                  self.server.session,
                                  base_dir,
                                  domain,
                                  port,
                                  path,
                                  http_prefix,
                                  maxPostsInBlogsFeed, 'tlblogs',
                                  True,
                                  0, self.server.positive_voting,
                                  self.server.voting_time_mins)
                if not inboxBlogsFeed:
                    inboxBlogsFeed = []
                if self._requestHTTP():
                    nickname = path.replace('/users/', '')
                    nickname = nickname.replace('/tlblogs', '')
                    pageNumber = 1
                    if '?page=' in nickname:
                        pageNumber = nickname.split('?page=')[1]
                        nickname = nickname.split('?page=')[0]
                        if pageNumber.isdigit():
                            pageNumber = int(pageNumber)
                        else:
                            pageNumber = 1
                    if 'page=' not in path:
                        # if no page was specified then show the first
                        inboxBlogsFeed = \
                            personBoxJson(self.server.recentPostsCache,
                                          self.server.session,
                                          base_dir,
                                          domain,
                                          port,
                                          path + '?page=1',
                                          http_prefix,
                                          maxPostsInBlogsFeed, 'tlblogs',
                                          True,
                                          0, self.server.positive_voting,
                                          self.server.voting_time_mins)
                    full_width_tl_button_header = \
                        self.server.full_width_tl_button_header
                    minimalNick = isMinimal(base_dir, domain, nickname)

                    accessKeys = self.server.accessKeys
                    if self.server.keyShortcuts.get(nickname):
                        accessKeys = \
                            self.server.keyShortcuts[nickname]
                    fed_domains = \
                        self.server.shared_items_federated_domains

                    msg = \
                        htmlInboxBlogs(self.server.cssCache,
                                       self.server.defaultTimeline,
                                       self.server.recentPostsCache,
                                       self.server.max_recent_posts,
                                       self.server.translate,
                                       pageNumber, maxPostsInBlogsFeed,
                                       self.server.session,
                                       base_dir,
                                       self.server.cachedWebfingers,
                                       self.server.personCache,
                                       nickname,
                                       domain,
                                       port,
                                       inboxBlogsFeed,
                                       self.server.allowDeletion,
                                       http_prefix,
                                       self.server.project_version,
                                       minimalNick,
                                       self.server.yt_replace_domain,
                                       self.server.twitter_replacement_domain,
                                       self.server.show_published_date_only,
                                       self.server.newswire,
                                       self.server.positive_voting,
                                       self.server.show_publish_as_icon,
                                       full_width_tl_button_header,
                                       self.server.icons_as_buttons,
                                       self.server.rss_icon_at_top,
                                       self.server.publish_button_at_top,
                                       authorized,
                                       self.server.themeName,
                                       self.server.peertubeInstances,
                                       self.server.allow_local_network_access,
                                       self.server.textModeBanner,
                                       accessKeys,
                                       self.server.systemLanguage,
                                       self.server.max_like_count,
                                       fed_domains,
                                       self.server.signingPrivateKeyPem,
                                       self.server.CWlists,
                                       self.server.lists_enabled)
                    msg = msg.encode('utf-8')
                    msglen = len(msg)
                    self._set_headers('text/html', msglen,
                                      cookie, callingDomain, False)
                    self._write(msg)
                    fitnessPerformance(GETstartTime,
                                       self.server.fitness,
                                       '_GET', '_showBlogsTimeline',
                                       self.server.debug)
                else:
                    # don't need authorized fetch here because there is
                    # already the authorization check
                    msg = json.dumps(inboxBlogsFeed,
                                     ensure_ascii=False)
                    msg = msg.encode('utf-8')
                    msglen = len(msg)
                    self._set_headers('application/json',
                                      msglen,
                                      None, callingDomain, False)
                    self._write(msg)
                    fitnessPerformance(GETstartTime,
                                       self.server.fitness,
                                       '_GET', '_showBlogsTimeline json',
                                       self.server.debug)
                return True
            else:
                if debug:
                    nickname = path.replace('/users/', '')
                    nickname = nickname.replace('/tlblogs', '')
                    print('DEBUG: ' + nickname +
                          ' was not authorized to access ' + path)
        if path != '/tlblogs':
            # not the blogs inbox
            if debug:
                print('DEBUG: GET access to blogs is unauthorized')
            self.send_response(405)
            self.end_headers()
            return True
        return False

    def _showNewsTimeline(self, authorized: bool,
                          callingDomain: str, path: str,
                          base_dir: str, http_prefix: str,
                          domain: str, domainFull: str, port: int,
                          onion_domain: str, i2p_domain: str,
                          GETstartTime,
                          proxy_type: str, cookie: str,
                          debug: str) -> bool:
        """Shows the news timeline
        """
        if '/users/' in path:
            if authorized:
                inboxNewsFeed = \
                    personBoxJson(self.server.recentPostsCache,
                                  self.server.session,
                                  base_dir,
                                  domain,
                                  port,
                                  path,
                                  http_prefix,
                                  maxPostsInNewsFeed, 'tlnews',
                                  True,
                                  self.server.newswire_votes_threshold,
                                  self.server.positive_voting,
                                  self.server.voting_time_mins)
                if not inboxNewsFeed:
                    inboxNewsFeed = []
                if self._requestHTTP():
                    nickname = path.replace('/users/', '')
                    nickname = nickname.replace('/tlnews', '')
                    pageNumber = 1
                    if '?page=' in nickname:
                        pageNumber = nickname.split('?page=')[1]
                        nickname = nickname.split('?page=')[0]
                        if pageNumber.isdigit():
                            pageNumber = int(pageNumber)
                        else:
                            pageNumber = 1
                    if 'page=' not in path:
                        # if no page was specified then show the first
                        inboxNewsFeed = \
                            personBoxJson(self.server.recentPostsCache,
                                          self.server.session,
                                          base_dir,
                                          domain,
                                          port,
                                          path + '?page=1',
                                          http_prefix,
                                          maxPostsInBlogsFeed, 'tlnews',
                                          True,
                                          self.server.newswire_votes_threshold,
                                          self.server.positive_voting,
                                          self.server.voting_time_mins)
                    currNickname = path.split('/users/')[1]
                    if '/' in currNickname:
                        currNickname = currNickname.split('/')[0]
                    moderator = isModerator(base_dir, currNickname)
                    editor = isEditor(base_dir, currNickname)
                    artist = isArtist(base_dir, currNickname)
                    full_width_tl_button_header = \
                        self.server.full_width_tl_button_header
                    minimalNick = isMinimal(base_dir, domain, nickname)

                    accessKeys = self.server.accessKeys
                    if self.server.keyShortcuts.get(nickname):
                        accessKeys = \
                            self.server.keyShortcuts[nickname]
                    fed_domains = \
                        self.server.shared_items_federated_domains

                    msg = \
                        htmlInboxNews(self.server.cssCache,
                                      self.server.defaultTimeline,
                                      self.server.recentPostsCache,
                                      self.server.max_recent_posts,
                                      self.server.translate,
                                      pageNumber, maxPostsInNewsFeed,
                                      self.server.session,
                                      base_dir,
                                      self.server.cachedWebfingers,
                                      self.server.personCache,
                                      nickname,
                                      domain,
                                      port,
                                      inboxNewsFeed,
                                      self.server.allowDeletion,
                                      http_prefix,
                                      self.server.project_version,
                                      minimalNick,
                                      self.server.yt_replace_domain,
                                      self.server.twitter_replacement_domain,
                                      self.server.show_published_date_only,
                                      self.server.newswire,
                                      moderator, editor, artist,
                                      self.server.positive_voting,
                                      self.server.show_publish_as_icon,
                                      full_width_tl_button_header,
                                      self.server.icons_as_buttons,
                                      self.server.rss_icon_at_top,
                                      self.server.publish_button_at_top,
                                      authorized,
                                      self.server.themeName,
                                      self.server.peertubeInstances,
                                      self.server.allow_local_network_access,
                                      self.server.textModeBanner,
                                      accessKeys,
                                      self.server.systemLanguage,
                                      self.server.max_like_count,
                                      fed_domains,
                                      self.server.signingPrivateKeyPem,
                                      self.server.CWlists,
                                      self.server.lists_enabled)
                    msg = msg.encode('utf-8')
                    msglen = len(msg)
                    self._set_headers('text/html', msglen,
                                      cookie, callingDomain, False)
                    self._write(msg)
                    fitnessPerformance(GETstartTime,
                                       self.server.fitness,
                                       '_GET', '_showNewsTimeline',
                                       self.server.debug)
                else:
                    # don't need authorized fetch here because there is
                    # already the authorization check
                    msg = json.dumps(inboxNewsFeed,
                                     ensure_ascii=False)
                    msg = msg.encode('utf-8')
                    msglen = len(msg)
                    self._set_headers('application/json',
                                      msglen,
                                      None, callingDomain, False)
                    self._write(msg)
                    fitnessPerformance(GETstartTime,
                                       self.server.fitness,
                                       '_GET', '_showNewsTimeline json',
                                       self.server.debug)
                return True
            else:
                if debug:
                    nickname = 'news'
                    print('DEBUG: ' + nickname +
                          ' was not authorized to access ' + path)
        if path != '/tlnews':
            # not the news inbox
            if debug:
                print('DEBUG: GET access to news is unauthorized')
            self.send_response(405)
            self.end_headers()
            return True
        return False

    def _showFeaturesTimeline(self, authorized: bool,
                              callingDomain: str, path: str,
                              base_dir: str, http_prefix: str,
                              domain: str, domainFull: str, port: int,
                              onion_domain: str, i2p_domain: str,
                              GETstartTime,
                              proxy_type: str, cookie: str,
                              debug: str) -> bool:
        """Shows the features timeline (all local blogs)
        """
        if '/users/' in path:
            if authorized:
                inboxFeaturesFeed = \
                    personBoxJson(self.server.recentPostsCache,
                                  self.server.session,
                                  base_dir,
                                  domain,
                                  port,
                                  path,
                                  http_prefix,
                                  maxPostsInNewsFeed, 'tlfeatures',
                                  True,
                                  self.server.newswire_votes_threshold,
                                  self.server.positive_voting,
                                  self.server.voting_time_mins)
                if not inboxFeaturesFeed:
                    inboxFeaturesFeed = []
                if self._requestHTTP():
                    nickname = path.replace('/users/', '')
                    nickname = nickname.replace('/tlfeatures', '')
                    pageNumber = 1
                    if '?page=' in nickname:
                        pageNumber = nickname.split('?page=')[1]
                        nickname = nickname.split('?page=')[0]
                        if pageNumber.isdigit():
                            pageNumber = int(pageNumber)
                        else:
                            pageNumber = 1
                    if 'page=' not in path:
                        # if no page was specified then show the first
                        inboxFeaturesFeed = \
                            personBoxJson(self.server.recentPostsCache,
                                          self.server.session,
                                          base_dir,
                                          domain,
                                          port,
                                          path + '?page=1',
                                          http_prefix,
                                          maxPostsInBlogsFeed, 'tlfeatures',
                                          True,
                                          self.server.newswire_votes_threshold,
                                          self.server.positive_voting,
                                          self.server.voting_time_mins)
                    currNickname = path.split('/users/')[1]
                    if '/' in currNickname:
                        currNickname = currNickname.split('/')[0]
                    full_width_tl_button_header = \
                        self.server.full_width_tl_button_header
                    minimalNick = isMinimal(base_dir, domain, nickname)

                    accessKeys = self.server.accessKeys
                    if self.server.keyShortcuts.get(nickname):
                        accessKeys = \
                            self.server.keyShortcuts[nickname]

                    shared_items_federated_domains = \
                        self.server.shared_items_federated_domains
                    allow_local_network_access = \
                        self.server.allow_local_network_access
                    twitter_replacement_domain = \
                        self.server.twitter_replacement_domain
                    msg = \
                        htmlInboxFeatures(self.server.cssCache,
                                          self.server.defaultTimeline,
                                          self.server.recentPostsCache,
                                          self.server.max_recent_posts,
                                          self.server.translate,
                                          pageNumber, maxPostsInBlogsFeed,
                                          self.server.session,
                                          base_dir,
                                          self.server.cachedWebfingers,
                                          self.server.personCache,
                                          nickname,
                                          domain,
                                          port,
                                          inboxFeaturesFeed,
                                          self.server.allowDeletion,
                                          http_prefix,
                                          self.server.project_version,
                                          minimalNick,
                                          self.server.yt_replace_domain,
                                          twitter_replacement_domain,
                                          self.server.show_published_date_only,
                                          self.server.newswire,
                                          self.server.positive_voting,
                                          self.server.show_publish_as_icon,
                                          full_width_tl_button_header,
                                          self.server.icons_as_buttons,
                                          self.server.rss_icon_at_top,
                                          self.server.publish_button_at_top,
                                          authorized,
                                          self.server.themeName,
                                          self.server.peertubeInstances,
                                          allow_local_network_access,
                                          self.server.textModeBanner,
                                          accessKeys,
                                          self.server.systemLanguage,
                                          self.server.max_like_count,
                                          shared_items_federated_domains,
                                          self.server.signingPrivateKeyPem,
                                          self.server.CWlists,
                                          self.server.lists_enabled)
                    msg = msg.encode('utf-8')
                    msglen = len(msg)
                    self._set_headers('text/html', msglen,
                                      cookie, callingDomain, False)
                    self._write(msg)
                    fitnessPerformance(GETstartTime,
                                       self.server.fitness,
                                       '_GET', '_showFeaturesTimeline',
                                       self.server.debug)
                else:
                    # don't need authorized fetch here because there is
                    # already the authorization check
                    msg = json.dumps(inboxFeaturesFeed,
                                     ensure_ascii=False)
                    msg = msg.encode('utf-8')
                    msglen = len(msg)
                    self._set_headers('application/json',
                                      msglen,
                                      None, callingDomain, False)
                    self._write(msg)
                    fitnessPerformance(GETstartTime,
                                       self.server.fitness,
                                       '_GET', '_showFeaturesTimeline json',
                                       self.server.debug)
                return True
            else:
                if debug:
                    nickname = 'news'
                    print('DEBUG: ' + nickname +
                          ' was not authorized to access ' + path)
        if path != '/tlfeatures':
            # not the features inbox
            if debug:
                print('DEBUG: GET access to features is unauthorized')
            self.send_response(405)
            self.end_headers()
            return True
        return False

    def _showSharesTimeline(self, authorized: bool,
                            callingDomain: str, path: str,
                            base_dir: str, http_prefix: str,
                            domain: str, domainFull: str, port: int,
                            onion_domain: str, i2p_domain: str,
                            GETstartTime,
                            proxy_type: str, cookie: str,
                            debug: str) -> bool:
        """Shows the shares timeline
        """
        if '/users/' in path:
            if authorized:
                if self._requestHTTP():
                    nickname = path.replace('/users/', '')
                    nickname = nickname.replace('/tlshares', '')
                    pageNumber = 1
                    if '?page=' in nickname:
                        pageNumber = nickname.split('?page=')[1]
                        nickname = nickname.split('?page=')[0]
                        if pageNumber.isdigit():
                            pageNumber = int(pageNumber)
                        else:
                            pageNumber = 1

                    accessKeys = self.server.accessKeys
                    if self.server.keyShortcuts.get(nickname):
                        accessKeys = \
                            self.server.keyShortcuts[nickname]
                    full_width_tl_button_header = \
                        self.server.full_width_tl_button_header

                    msg = \
                        htmlShares(self.server.cssCache,
                                   self.server.defaultTimeline,
                                   self.server.recentPostsCache,
                                   self.server.max_recent_posts,
                                   self.server.translate,
                                   pageNumber, maxPostsInFeed,
                                   self.server.session,
                                   base_dir,
                                   self.server.cachedWebfingers,
                                   self.server.personCache,
                                   nickname,
                                   domain,
                                   port,
                                   self.server.allowDeletion,
                                   http_prefix,
                                   self.server.project_version,
                                   self.server.yt_replace_domain,
                                   self.server.twitter_replacement_domain,
                                   self.server.show_published_date_only,
                                   self.server.newswire,
                                   self.server.positive_voting,
                                   self.server.show_publish_as_icon,
                                   full_width_tl_button_header,
                                   self.server.icons_as_buttons,
                                   self.server.rss_icon_at_top,
                                   self.server.publish_button_at_top,
                                   authorized, self.server.themeName,
                                   self.server.peertubeInstances,
                                   self.server.allow_local_network_access,
                                   self.server.textModeBanner,
                                   accessKeys,
                                   self.server.systemLanguage,
                                   self.server.max_like_count,
                                   self.server.shared_items_federated_domains,
                                   self.server.signingPrivateKeyPem,
                                   self.server.CWlists,
                                   self.server.lists_enabled)
                    msg = msg.encode('utf-8')
                    msglen = len(msg)
                    self._set_headers('text/html', msglen,
                                      cookie, callingDomain, False)
                    self._write(msg)
                    fitnessPerformance(GETstartTime,
                                       self.server.fitness,
                                       '_GET', '_showSharesTimeline',
                                       self.server.debug)
                    return True
        # not the shares timeline
        if debug:
            print('DEBUG: GET access to shares timeline is unauthorized')
        self.send_response(405)
        self.end_headers()
        return True

    def _showWantedTimeline(self, authorized: bool,
                            callingDomain: str, path: str,
                            base_dir: str, http_prefix: str,
                            domain: str, domainFull: str, port: int,
                            onion_domain: str, i2p_domain: str,
                            GETstartTime,
                            proxy_type: str, cookie: str,
                            debug: str) -> bool:
        """Shows the wanted timeline
        """
        if '/users/' in path:
            if authorized:
                if self._requestHTTP():
                    nickname = path.replace('/users/', '')
                    nickname = nickname.replace('/tlwanted', '')
                    pageNumber = 1
                    if '?page=' in nickname:
                        pageNumber = nickname.split('?page=')[1]
                        nickname = nickname.split('?page=')[0]
                        if pageNumber.isdigit():
                            pageNumber = int(pageNumber)
                        else:
                            pageNumber = 1

                    accessKeys = self.server.accessKeys
                    if self.server.keyShortcuts.get(nickname):
                        accessKeys = \
                            self.server.keyShortcuts[nickname]
                    full_width_tl_button_header = \
                        self.server.full_width_tl_button_header
                    msg = \
                        htmlWanted(self.server.cssCache,
                                   self.server.defaultTimeline,
                                   self.server.recentPostsCache,
                                   self.server.max_recent_posts,
                                   self.server.translate,
                                   pageNumber, maxPostsInFeed,
                                   self.server.session,
                                   base_dir,
                                   self.server.cachedWebfingers,
                                   self.server.personCache,
                                   nickname,
                                   domain,
                                   port,
                                   self.server.allowDeletion,
                                   http_prefix,
                                   self.server.project_version,
                                   self.server.yt_replace_domain,
                                   self.server.twitter_replacement_domain,
                                   self.server.show_published_date_only,
                                   self.server.newswire,
                                   self.server.positive_voting,
                                   self.server.show_publish_as_icon,
                                   full_width_tl_button_header,
                                   self.server.icons_as_buttons,
                                   self.server.rss_icon_at_top,
                                   self.server.publish_button_at_top,
                                   authorized, self.server.themeName,
                                   self.server.peertubeInstances,
                                   self.server.allow_local_network_access,
                                   self.server.textModeBanner,
                                   accessKeys,
                                   self.server.systemLanguage,
                                   self.server.max_like_count,
                                   self.server.shared_items_federated_domains,
                                   self.server.signingPrivateKeyPem,
                                   self.server.CWlists,
                                   self.server.lists_enabled)
                    msg = msg.encode('utf-8')
                    msglen = len(msg)
                    self._set_headers('text/html', msglen,
                                      cookie, callingDomain, False)
                    self._write(msg)
                    fitnessPerformance(GETstartTime,
                                       self.server.fitness,
                                       '_GET', '_showWantedTimeline',
                                       self.server.debug)
                    return True
        # not the shares timeline
        if debug:
            print('DEBUG: GET access to wanted timeline is unauthorized')
        self.send_response(405)
        self.end_headers()
        return True

    def _showBookmarksTimeline(self, authorized: bool,
                               callingDomain: str, path: str,
                               base_dir: str, http_prefix: str,
                               domain: str, domainFull: str, port: int,
                               onion_domain: str, i2p_domain: str,
                               GETstartTime,
                               proxy_type: str, cookie: str,
                               debug: str) -> bool:
        """Shows the bookmarks timeline
        """
        if '/users/' in path:
            if authorized:
                bookmarksFeed = \
                    personBoxJson(self.server.recentPostsCache,
                                  self.server.session,
                                  base_dir,
                                  domain,
                                  port,
                                  path,
                                  http_prefix,
                                  maxPostsInFeed, 'tlbookmarks',
                                  authorized,
                                  0, self.server.positive_voting,
                                  self.server.voting_time_mins)
                if bookmarksFeed:
                    if self._requestHTTP():
                        nickname = path.replace('/users/', '')
                        nickname = nickname.replace('/tlbookmarks', '')
                        nickname = nickname.replace('/bookmarks', '')
                        pageNumber = 1
                        if '?page=' in nickname:
                            pageNumber = nickname.split('?page=')[1]
                            nickname = nickname.split('?page=')[0]
                            if pageNumber.isdigit():
                                pageNumber = int(pageNumber)
                            else:
                                pageNumber = 1
                        if 'page=' not in path:
                            # if no page was specified then show the first
                            bookmarksFeed = \
                                personBoxJson(self.server.recentPostsCache,
                                              self.server.session,
                                              base_dir,
                                              domain,
                                              port,
                                              path + '?page=1',
                                              http_prefix,
                                              maxPostsInFeed,
                                              'tlbookmarks',
                                              authorized,
                                              0, self.server.positive_voting,
                                              self.server.voting_time_mins)
                        full_width_tl_button_header = \
                            self.server.full_width_tl_button_header
                        minimalNick = isMinimal(base_dir, domain, nickname)

                        accessKeys = self.server.accessKeys
                        if self.server.keyShortcuts.get(nickname):
                            accessKeys = \
                                self.server.keyShortcuts[nickname]

                        shared_items_federated_domains = \
                            self.server.shared_items_federated_domains
                        allow_local_network_access = \
                            self.server.allow_local_network_access
                        twitter_replacement_domain = \
                            self.server.twitter_replacement_domain
                        msg = \
                            htmlBookmarks(self.server.cssCache,
                                          self.server.defaultTimeline,
                                          self.server.recentPostsCache,
                                          self.server.max_recent_posts,
                                          self.server.translate,
                                          pageNumber, maxPostsInFeed,
                                          self.server.session,
                                          base_dir,
                                          self.server.cachedWebfingers,
                                          self.server.personCache,
                                          nickname,
                                          domain,
                                          port,
                                          bookmarksFeed,
                                          self.server.allowDeletion,
                                          http_prefix,
                                          self.server.project_version,
                                          minimalNick,
                                          self.server.yt_replace_domain,
                                          twitter_replacement_domain,
                                          self.server.show_published_date_only,
                                          self.server.newswire,
                                          self.server.positive_voting,
                                          self.server.show_publish_as_icon,
                                          full_width_tl_button_header,
                                          self.server.icons_as_buttons,
                                          self.server.rss_icon_at_top,
                                          self.server.publish_button_at_top,
                                          authorized,
                                          self.server.themeName,
                                          self.server.peertubeInstances,
                                          allow_local_network_access,
                                          self.server.textModeBanner,
                                          accessKeys,
                                          self.server.systemLanguage,
                                          self.server.max_like_count,
                                          shared_items_federated_domains,
                                          self.server.signingPrivateKeyPem,
                                          self.server.CWlists,
                                          self.server.lists_enabled)
                        msg = msg.encode('utf-8')
                        msglen = len(msg)
                        self._set_headers('text/html', msglen,
                                          cookie, callingDomain, False)
                        self._write(msg)
                        fitnessPerformance(GETstartTime,
                                           self.server.fitness,
                                           '_GET', '_showBookmarksTimeline',
                                           self.server.debug)
                    else:
                        # don't need authorized fetch here because
                        # there is already the authorization check
                        msg = json.dumps(bookmarksFeed,
                                         ensure_ascii=False)
                        msg = msg.encode('utf-8')
                        msglen = len(msg)
                        self._set_headers('application/json', msglen,
                                          None, callingDomain, False)
                        self._write(msg)
                        fitnessPerformance(GETstartTime,
                                           self.server.fitness,
                                           '_GET',
                                           '_showBookmarksTimeline json',
                                           self.server.debug)
                    return True
            else:
                if debug:
                    nickname = path.replace('/users/', '')
                    nickname = nickname.replace('/tlbookmarks', '')
                    nickname = nickname.replace('/bookmarks', '')
                    print('DEBUG: ' + nickname +
                          ' was not authorized to access ' + path)
        if debug:
            print('DEBUG: GET access to bookmarks is unauthorized')
        self.send_response(405)
        self.end_headers()
        return True

    def _showOutboxTimeline(self, authorized: bool,
                            callingDomain: str, path: str,
                            base_dir: str, http_prefix: str,
                            domain: str, domainFull: str, port: int,
                            onion_domain: str, i2p_domain: str,
                            GETstartTime,
                            proxy_type: str, cookie: str,
                            debug: str) -> bool:
        """Shows the outbox timeline
        """
        # get outbox feed for a person
        outboxFeed = \
            personBoxJson(self.server.recentPostsCache,
                          self.server.session,
                          base_dir, domain, port, path,
                          http_prefix, maxPostsInFeed, 'outbox',
                          authorized,
                          self.server.newswire_votes_threshold,
                          self.server.positive_voting,
                          self.server.voting_time_mins)
        if outboxFeed:
            nickname = \
                path.replace('/users/', '').replace('/outbox', '')
            pageNumber = 0
            if '?page=' in nickname:
                pageNumber = nickname.split('?page=')[1]
                nickname = nickname.split('?page=')[0]
                if pageNumber.isdigit():
                    pageNumber = int(pageNumber)
                else:
                    pageNumber = 1
            else:
                if self._requestHTTP():
                    pageNumber = 1
            if authorized and pageNumber >= 1:
                # if a page wasn't specified then show the first one
                pageStr = '?page=' + str(pageNumber)
                outboxFeed = \
                    personBoxJson(self.server.recentPostsCache,
                                  self.server.session,
                                  base_dir, domain, port,
                                  path + pageStr,
                                  http_prefix,
                                  maxPostsInFeed, 'outbox',
                                  authorized,
                                  self.server.newswire_votes_threshold,
                                  self.server.positive_voting,
                                  self.server.voting_time_mins)
            else:
                pageNumber = 1

            if self._requestHTTP():
                full_width_tl_button_header = \
                    self.server.full_width_tl_button_header
                minimalNick = isMinimal(base_dir, domain, nickname)

                accessKeys = self.server.accessKeys
                if self.server.keyShortcuts.get(nickname):
                    accessKeys = \
                        self.server.keyShortcuts[nickname]

                msg = \
                    htmlOutbox(self.server.cssCache,
                               self.server.defaultTimeline,
                               self.server.recentPostsCache,
                               self.server.max_recent_posts,
                               self.server.translate,
                               pageNumber, maxPostsInFeed,
                               self.server.session,
                               base_dir,
                               self.server.cachedWebfingers,
                               self.server.personCache,
                               nickname, domain, port,
                               outboxFeed,
                               self.server.allowDeletion,
                               http_prefix,
                               self.server.project_version,
                               minimalNick,
                               self.server.yt_replace_domain,
                               self.server.twitter_replacement_domain,
                               self.server.show_published_date_only,
                               self.server.newswire,
                               self.server.positive_voting,
                               self.server.show_publish_as_icon,
                               full_width_tl_button_header,
                               self.server.icons_as_buttons,
                               self.server.rss_icon_at_top,
                               self.server.publish_button_at_top,
                               authorized,
                               self.server.themeName,
                               self.server.peertubeInstances,
                               self.server.allow_local_network_access,
                               self.server.textModeBanner,
                               accessKeys,
                               self.server.systemLanguage,
                               self.server.max_like_count,
                               self.server.shared_items_federated_domains,
                               self.server.signingPrivateKeyPem,
                               self.server.CWlists,
                               self.server.lists_enabled)
                msg = msg.encode('utf-8')
                msglen = len(msg)
                self._set_headers('text/html', msglen,
                                  cookie, callingDomain, False)
                self._write(msg)
                fitnessPerformance(GETstartTime,
                                   self.server.fitness,
                                   '_GET', '_showOutboxTimeline',
                                   self.server.debug)
            else:
                if self._secure_mode():
                    msg = json.dumps(outboxFeed,
                                     ensure_ascii=False)
                    msg = msg.encode('utf-8')
                    msglen = len(msg)
                    self._set_headers('application/json', msglen,
                                      None, callingDomain, False)
                    self._write(msg)
                    fitnessPerformance(GETstartTime,
                                       self.server.fitness,
                                       '_GET', '_showOutboxTimeline json',
                                       self.server.debug)
                else:
                    self._404()
            return True
        return False

    def _showModTimeline(self, authorized: bool,
                         callingDomain: str, path: str,
                         base_dir: str, http_prefix: str,
                         domain: str, domainFull: str, port: int,
                         onion_domain: str, i2p_domain: str,
                         GETstartTime,
                         proxy_type: str, cookie: str,
                         debug: str) -> bool:
        """Shows the moderation timeline
        """
        if '/users/' in path:
            if authorized:
                moderationFeed = \
                    personBoxJson(self.server.recentPostsCache,
                                  self.server.session,
                                  base_dir,
                                  domain,
                                  port,
                                  path,
                                  http_prefix,
                                  maxPostsInFeed, 'moderation',
                                  True,
                                  0, self.server.positive_voting,
                                  self.server.voting_time_mins)
                if moderationFeed:
                    if self._requestHTTP():
                        nickname = path.replace('/users/', '')
                        nickname = nickname.replace('/moderation', '')
                        pageNumber = 1
                        if '?page=' in nickname:
                            pageNumber = nickname.split('?page=')[1]
                            nickname = nickname.split('?page=')[0]
                            if pageNumber.isdigit():
                                pageNumber = int(pageNumber)
                            else:
                                pageNumber = 1
                        if 'page=' not in path:
                            # if no page was specified then show the first
                            moderationFeed = \
                                personBoxJson(self.server.recentPostsCache,
                                              self.server.session,
                                              base_dir,
                                              domain,
                                              port,
                                              path + '?page=1',
                                              http_prefix,
                                              maxPostsInFeed, 'moderation',
                                              True,
                                              0, self.server.positive_voting,
                                              self.server.voting_time_mins)
                        full_width_tl_button_header = \
                            self.server.full_width_tl_button_header
                        moderationActionStr = ''

                        accessKeys = self.server.accessKeys
                        if self.server.keyShortcuts.get(nickname):
                            accessKeys = \
                                self.server.keyShortcuts[nickname]

                        shared_items_federated_domains = \
                            self.server.shared_items_federated_domains
                        twitter_replacement_domain = \
                            self.server.twitter_replacement_domain
                        allow_local_network_access = \
                            self.server.allow_local_network_access
                        show_published_date_only = \
                            self.server.show_published_date_only
                        msg = \
                            htmlModeration(self.server.cssCache,
                                           self.server.defaultTimeline,
                                           self.server.recentPostsCache,
                                           self.server.max_recent_posts,
                                           self.server.translate,
                                           pageNumber, maxPostsInFeed,
                                           self.server.session,
                                           base_dir,
                                           self.server.cachedWebfingers,
                                           self.server.personCache,
                                           nickname,
                                           domain,
                                           port,
                                           moderationFeed,
                                           True,
                                           http_prefix,
                                           self.server.project_version,
                                           self.server.yt_replace_domain,
                                           twitter_replacement_domain,
                                           show_published_date_only,
                                           self.server.newswire,
                                           self.server.positive_voting,
                                           self.server.show_publish_as_icon,
                                           full_width_tl_button_header,
                                           self.server.icons_as_buttons,
                                           self.server.rss_icon_at_top,
                                           self.server.publish_button_at_top,
                                           authorized, moderationActionStr,
                                           self.server.themeName,
                                           self.server.peertubeInstances,
                                           allow_local_network_access,
                                           self.server.textModeBanner,
                                           accessKeys,
                                           self.server.systemLanguage,
                                           self.server.max_like_count,
                                           shared_items_federated_domains,
                                           self.server.signingPrivateKeyPem,
                                           self.server.CWlists,
                                           self.server.lists_enabled)
                        msg = msg.encode('utf-8')
                        msglen = len(msg)
                        self._set_headers('text/html', msglen,
                                          cookie, callingDomain, False)
                        self._write(msg)
                        fitnessPerformance(GETstartTime,
                                           self.server.fitness,
                                           '_GET', '_showModTimeline',
                                           self.server.debug)
                    else:
                        # don't need authorized fetch here because
                        # there is already the authorization check
                        msg = json.dumps(moderationFeed,
                                         ensure_ascii=False)
                        msg = msg.encode('utf-8')
                        msglen = len(msg)
                        self._set_headers('application/json', msglen,
                                          None, callingDomain, False)
                        self._write(msg)
                        fitnessPerformance(GETstartTime,
                                           self.server.fitness,
                                           '_GET', '_showModTimeline json',
                                           self.server.debug)
                    return True
            else:
                if debug:
                    nickname = path.replace('/users/', '')
                    nickname = nickname.replace('/moderation', '')
                    print('DEBUG: ' + nickname +
                          ' was not authorized to access ' + path)
        if debug:
            print('DEBUG: GET access to moderation feed is unauthorized')
        self.send_response(405)
        self.end_headers()
        return True

    def _showSharesFeed(self, authorized: bool,
                        callingDomain: str, path: str,
                        base_dir: str, http_prefix: str,
                        domain: str, domainFull: str, port: int,
                        onion_domain: str, i2p_domain: str,
                        GETstartTime,
                        proxy_type: str, cookie: str,
                        debug: str, sharesFileType: str) -> bool:
        """Shows the shares feed
        """
        shares = \
            getSharesFeedForPerson(base_dir, domain, port, path,
                                   http_prefix, sharesFileType, sharesPerPage)
        if shares:
            if self._requestHTTP():
                pageNumber = 1
                if '?page=' not in path:
                    searchPath = path
                    # get a page of shares, not the summary
                    shares = \
                        getSharesFeedForPerson(base_dir, domain, port,
                                               path + '?page=true',
                                               http_prefix, sharesFileType,
                                               sharesPerPage)
                else:
                    pageNumberStr = path.split('?page=')[1]
                    if '#' in pageNumberStr:
                        pageNumberStr = pageNumberStr.split('#')[0]
                    if pageNumberStr.isdigit():
                        pageNumber = int(pageNumberStr)
                    searchPath = path.split('?page=')[0]
                getPerson = \
                    personLookup(domain,
                                 searchPath.replace('/' + sharesFileType, ''),
                                 base_dir)
                if getPerson:
                    if not self._establishSession("showSharesFeed"):
                        self._404()
                        self.server.GETbusy = False
                        return True

                    accessKeys = self.server.accessKeys
                    if '/users/' in path:
                        nickname = path.split('/users/')[1]
                        if '/' in nickname:
                            nickname = nickname.split('/')[0]
                        if self.server.keyShortcuts.get(nickname):
                            accessKeys = \
                                self.server.keyShortcuts[nickname]

                    city = getSpoofedCity(self.server.city,
                                          base_dir, nickname, domain)
                    msg = \
                        htmlProfile(self.server.signingPrivateKeyPem,
                                    self.server.rss_icon_at_top,
                                    self.server.cssCache,
                                    self.server.icons_as_buttons,
                                    self.server.defaultTimeline,
                                    self.server.recentPostsCache,
                                    self.server.max_recent_posts,
                                    self.server.translate,
                                    self.server.project_version,
                                    base_dir, http_prefix,
                                    authorized,
                                    getPerson, sharesFileType,
                                    self.server.session,
                                    self.server.cachedWebfingers,
                                    self.server.personCache,
                                    self.server.yt_replace_domain,
                                    self.server.twitter_replacement_domain,
                                    self.server.show_published_date_only,
                                    self.server.newswire,
                                    self.server.themeName,
                                    self.server.dormant_months,
                                    self.server.peertubeInstances,
                                    self.server.allow_local_network_access,
                                    self.server.textModeBanner,
                                    self.server.debug,
                                    accessKeys, city,
                                    self.server.systemLanguage,
                                    self.server.max_like_count,
                                    self.server.shared_items_federated_domains,
                                    shares,
                                    pageNumber, sharesPerPage,
                                    self.server.CWlists,
                                    self.server.lists_enabled,
                                    self.server.content_license_url)
                    msg = msg.encode('utf-8')
                    msglen = len(msg)
                    self._set_headers('text/html', msglen,
                                      cookie, callingDomain, False)
                    self._write(msg)
                    fitnessPerformance(GETstartTime,
                                       self.server.fitness,
                                       '_GET', '_showSharesFeed',
                                       self.server.debug)
                    self.server.GETbusy = False
                    return True
            else:
                if self._secure_mode():
                    msg = json.dumps(shares,
                                     ensure_ascii=False)
                    msg = msg.encode('utf-8')
                    msglen = len(msg)
                    self._set_headers('application/json', msglen,
                                      None, callingDomain, False)
                    self._write(msg)
                    fitnessPerformance(GETstartTime,
                                       self.server.fitness,
                                       '_GET', '_showSharesFeed json',
                                       self.server.debug)
                else:
                    self._404()
                return True
        return False

    def _showFollowingFeed(self, authorized: bool,
                           callingDomain: str, path: str,
                           base_dir: str, http_prefix: str,
                           domain: str, domainFull: str, port: int,
                           onion_domain: str, i2p_domain: str,
                           GETstartTime,
                           proxy_type: str, cookie: str,
                           debug: str) -> bool:
        """Shows the following feed
        """
        following = \
            getFollowingFeed(base_dir, domain, port, path,
                             http_prefix, authorized, followsPerPage,
                             'following')
        if following:
            if self._requestHTTP():
                pageNumber = 1
                if '?page=' not in path:
                    searchPath = path
                    # get a page of following, not the summary
                    following = \
                        getFollowingFeed(base_dir,
                                         domain,
                                         port,
                                         path + '?page=true',
                                         http_prefix,
                                         authorized, followsPerPage)
                else:
                    pageNumberStr = path.split('?page=')[1]
                    if '#' in pageNumberStr:
                        pageNumberStr = pageNumberStr.split('#')[0]
                    if pageNumberStr.isdigit():
                        pageNumber = int(pageNumberStr)
                    searchPath = path.split('?page=')[0]
                getPerson = \
                    personLookup(domain,
                                 searchPath.replace('/following', ''),
                                 base_dir)
                if getPerson:
                    if not self._establishSession("showFollowingFeed"):
                        self._404()
                        return True

                    accessKeys = self.server.accessKeys
                    city = None
                    if '/users/' in path:
                        nickname = path.split('/users/')[1]
                        if '/' in nickname:
                            nickname = nickname.split('/')[0]
                        if self.server.keyShortcuts.get(nickname):
                            accessKeys = \
                                self.server.keyShortcuts[nickname]

                        city = getSpoofedCity(self.server.city,
                                              base_dir, nickname, domain)
                    content_license_url = \
                        self.server.content_license_url
                    msg = \
                        htmlProfile(self.server.signingPrivateKeyPem,
                                    self.server.rss_icon_at_top,
                                    self.server.cssCache,
                                    self.server.icons_as_buttons,
                                    self.server.defaultTimeline,
                                    self.server.recentPostsCache,
                                    self.server.max_recent_posts,
                                    self.server.translate,
                                    self.server.project_version,
                                    base_dir, http_prefix,
                                    authorized,
                                    getPerson, 'following',
                                    self.server.session,
                                    self.server.cachedWebfingers,
                                    self.server.personCache,
                                    self.server.yt_replace_domain,
                                    self.server.twitter_replacement_domain,
                                    self.server.show_published_date_only,
                                    self.server.newswire,
                                    self.server.themeName,
                                    self.server.dormant_months,
                                    self.server.peertubeInstances,
                                    self.server.allow_local_network_access,
                                    self.server.textModeBanner,
                                    self.server.debug,
                                    accessKeys, city,
                                    self.server.systemLanguage,
                                    self.server.max_like_count,
                                    self.server.shared_items_federated_domains,
                                    following,
                                    pageNumber,
                                    followsPerPage,
                                    self.server.CWlists,
                                    self.server.lists_enabled,
                                    content_license_url).encode('utf-8')
                    msglen = len(msg)
                    self._set_headers('text/html',
                                      msglen, cookie, callingDomain, False)
                    self._write(msg)
                    fitnessPerformance(GETstartTime,
                                       self.server.fitness,
                                       '_GET', '_showFollowingFeed',
                                       self.server.debug)
                    return True
            else:
                if self._secure_mode():
                    msg = json.dumps(following,
                                     ensure_ascii=False).encode('utf-8')
                    msglen = len(msg)
                    self._set_headers('application/json', msglen,
                                      None, callingDomain, False)
                    self._write(msg)
                    fitnessPerformance(GETstartTime,
                                       self.server.fitness,
                                       '_GET', '_showFollowingFeed json',
                                       self.server.debug)
                else:
                    self._404()
                return True
        return False

    def _showFollowersFeed(self, authorized: bool,
                           callingDomain: str, path: str,
                           base_dir: str, http_prefix: str,
                           domain: str, domainFull: str, port: int,
                           onion_domain: str, i2p_domain: str,
                           GETstartTime,
                           proxy_type: str, cookie: str,
                           debug: str) -> bool:
        """Shows the followers feed
        """
        followers = \
            getFollowingFeed(base_dir, domain, port, path, http_prefix,
                             authorized, followsPerPage, 'followers')
        if followers:
            if self._requestHTTP():
                pageNumber = 1
                if '?page=' not in path:
                    searchPath = path
                    # get a page of followers, not the summary
                    followers = \
                        getFollowingFeed(base_dir,
                                         domain,
                                         port,
                                         path + '?page=1',
                                         http_prefix,
                                         authorized, followsPerPage,
                                         'followers')
                else:
                    pageNumberStr = path.split('?page=')[1]
                    if '#' in pageNumberStr:
                        pageNumberStr = pageNumberStr.split('#')[0]
                    if pageNumberStr.isdigit():
                        pageNumber = int(pageNumberStr)
                    searchPath = path.split('?page=')[0]
                getPerson = \
                    personLookup(domain,
                                 searchPath.replace('/followers', ''),
                                 base_dir)
                if getPerson:
                    if not self._establishSession("showFollowersFeed"):
                        self._404()
                        return True

                    accessKeys = self.server.accessKeys
                    city = None
                    if '/users/' in path:
                        nickname = path.split('/users/')[1]
                        if '/' in nickname:
                            nickname = nickname.split('/')[0]
                        if self.server.keyShortcuts.get(nickname):
                            accessKeys = \
                                self.server.keyShortcuts[nickname]

                        city = getSpoofedCity(self.server.city,
                                              base_dir, nickname, domain)
                    content_license_url = \
                        self.server.content_license_url
                    msg = \
                        htmlProfile(self.server.signingPrivateKeyPem,
                                    self.server.rss_icon_at_top,
                                    self.server.cssCache,
                                    self.server.icons_as_buttons,
                                    self.server.defaultTimeline,
                                    self.server.recentPostsCache,
                                    self.server.max_recent_posts,
                                    self.server.translate,
                                    self.server.project_version,
                                    base_dir,
                                    http_prefix,
                                    authorized,
                                    getPerson, 'followers',
                                    self.server.session,
                                    self.server.cachedWebfingers,
                                    self.server.personCache,
                                    self.server.yt_replace_domain,
                                    self.server.twitter_replacement_domain,
                                    self.server.show_published_date_only,
                                    self.server.newswire,
                                    self.server.themeName,
                                    self.server.dormant_months,
                                    self.server.peertubeInstances,
                                    self.server.allow_local_network_access,
                                    self.server.textModeBanner,
                                    self.server.debug,
                                    accessKeys, city,
                                    self.server.systemLanguage,
                                    self.server.max_like_count,
                                    self.server.shared_items_federated_domains,
                                    followers,
                                    pageNumber,
                                    followsPerPage,
                                    self.server.CWlists,
                                    self.server.lists_enabled,
                                    content_license_url).encode('utf-8')
                    msglen = len(msg)
                    self._set_headers('text/html', msglen,
                                      cookie, callingDomain, False)
                    self._write(msg)
                    fitnessPerformance(GETstartTime,
                                       self.server.fitness,
                                       '_GET', '_showFollowersFeed',
                                       self.server.debug)
                    return True
            else:
                if self._secure_mode():
                    msg = json.dumps(followers,
                                     ensure_ascii=False).encode('utf-8')
                    msglen = len(msg)
                    self._set_headers('application/json', msglen,
                                      None, callingDomain, False)
                    self._write(msg)
                    fitnessPerformance(GETstartTime,
                                       self.server.fitness,
                                       '_GET', '_showFollowersFeed json',
                                       self.server.debug)
                else:
                    self._404()
            return True
        return False

    def _getFeaturedCollection(self, callingDomain: str,
                               base_dir: str,
                               path: str,
                               http_prefix: str,
                               nickname: str, domain: str,
                               domainFull: str, systemLanguage: str) -> None:
        """Returns the featured posts collections in
        actor/collections/featured
        """
        featuredCollection = \
            jsonPinPost(base_dir, http_prefix,
                        nickname, domain, domainFull, systemLanguage)
        msg = json.dumps(featuredCollection,
                         ensure_ascii=False).encode('utf-8')
        msglen = len(msg)
        self._set_headers('application/json', msglen,
                          None, callingDomain, False)
        self._write(msg)

    def _getFeaturedTagsCollection(self, callingDomain: str,
                                   path: str,
                                   http_prefix: str,
                                   domainFull: str):
        """Returns the featured tags collections in
        actor/collections/featuredTags
        TODO add ability to set a featured tags
        """
        postContext = getIndividualPostContext()
        featuredTagsCollection = {
            '@context': postContext,
            'id': http_prefix + '://' + domainFull + path,
            'orderedItems': [],
            'totalItems': 0,
            'type': 'OrderedCollection'
        }
        msg = json.dumps(featuredTagsCollection,
                         ensure_ascii=False).encode('utf-8')
        msglen = len(msg)
        self._set_headers('application/json', msglen,
                          None, callingDomain, False)
        self._write(msg)

    def _showPersonProfile(self, authorized: bool,
                           callingDomain: str, path: str,
                           base_dir: str, http_prefix: str,
                           domain: str, domainFull: str, port: int,
                           onion_domain: str, i2p_domain: str,
                           GETstartTime,
                           proxy_type: str, cookie: str,
                           debug: str) -> bool:
        """Shows the profile for a person
        """
        # look up a person
        actorJson = personLookup(domain, path, base_dir)
        if not actorJson:
            return False
        if self._requestHTTP():
            if not self._establishSession("showPersonProfile"):
                self._404()
                return True

            accessKeys = self.server.accessKeys
            city = None
            if '/users/' in path:
                nickname = path.split('/users/')[1]
                if '/' in nickname:
                    nickname = nickname.split('/')[0]
                if self.server.keyShortcuts.get(nickname):
                    accessKeys = \
                        self.server.keyShortcuts[nickname]

                city = getSpoofedCity(self.server.city,
                                      base_dir, nickname, domain)
            msg = \
                htmlProfile(self.server.signingPrivateKeyPem,
                            self.server.rss_icon_at_top,
                            self.server.cssCache,
                            self.server.icons_as_buttons,
                            self.server.defaultTimeline,
                            self.server.recentPostsCache,
                            self.server.max_recent_posts,
                            self.server.translate,
                            self.server.project_version,
                            base_dir,
                            http_prefix,
                            authorized,
                            actorJson, 'posts',
                            self.server.session,
                            self.server.cachedWebfingers,
                            self.server.personCache,
                            self.server.yt_replace_domain,
                            self.server.twitter_replacement_domain,
                            self.server.show_published_date_only,
                            self.server.newswire,
                            self.server.themeName,
                            self.server.dormant_months,
                            self.server.peertubeInstances,
                            self.server.allow_local_network_access,
                            self.server.textModeBanner,
                            self.server.debug,
                            accessKeys, city,
                            self.server.systemLanguage,
                            self.server.max_like_count,
                            self.server.shared_items_federated_domains,
                            None, None, None,
                            self.server.CWlists,
                            self.server.lists_enabled,
                            self.server.content_license_url).encode('utf-8')
            msglen = len(msg)
            self._set_headers('text/html', msglen,
                              cookie, callingDomain, False)
            self._write(msg)
            fitnessPerformance(GETstartTime,
                               self.server.fitness,
                               '_GET', '_showPersonProfile',
                               self.server.debug)
        else:
            if self._secure_mode():
                acceptStr = self.headers['Accept']
                msgStr = json.dumps(actorJson, ensure_ascii=False)
                msg = msgStr.encode('utf-8')
                msglen = len(msg)
                if 'application/ld+json' in acceptStr:
                    self._set_headers('application/ld+json', msglen,
                                      cookie, callingDomain, False)
                elif 'application/jrd+json' in acceptStr:
                    self._set_headers('application/jrd+json', msglen,
                                      cookie, callingDomain, False)
                else:
                    self._set_headers('application/activity+json', msglen,
                                      cookie, callingDomain, False)
                self._write(msg)
                fitnessPerformance(GETstartTime,
                                   self.server.fitness,
                                   '_GET', '_showPersonProfile json',
                                   self.server.debug)
            else:
                self._404()
        return True

    def _showInstanceActor(self, callingDomain: str, path: str,
                           base_dir: str, http_prefix: str,
                           domain: str, domainFull: str, port: int,
                           onion_domain: str, i2p_domain: str,
                           GETstartTime,
                           proxy_type: str, cookie: str,
                           debug: str,
                           enable_shared_inbox: bool) -> bool:
        """Shows the instance actor
        """
        if debug:
            print('Instance actor requested by ' + callingDomain)
        if self._requestHTTP():
            self._404()
            return False
        actorJson = personLookup(domain, path, base_dir)
        if not actorJson:
            print('ERROR: no instance actor found')
            self._404()
            return False
        acceptStr = self.headers['Accept']
        if onion_domain and callingDomain.endswith('.onion'):
            actorDomainUrl = 'http://' + onion_domain
        elif i2p_domain and callingDomain.endswith('.i2p'):
            actorDomainUrl = 'http://' + i2p_domain
        else:
            actorDomainUrl = http_prefix + '://' + domainFull
        actorUrl = actorDomainUrl + '/users/Actor'
        removeFields = ('icon', 'image', 'tts', 'shares',
                        'alsoKnownAs', 'hasOccupation', 'featured',
                        'featuredTags', 'discoverable', 'published',
                        'devices')
        for r in removeFields:
            if r in actorJson:
                del actorJson[r]
        actorJson['endpoints'] = {}
        if enable_shared_inbox:
            actorJson['endpoints'] = {
                'sharedInbox': actorDomainUrl + '/inbox'
            }
        actorJson['name'] = 'ACTOR'
        actorJson['preferredUsername'] = domainFull
        actorJson['id'] = actorDomainUrl + '/actor'
        actorJson['type'] = 'Application'
        actorJson['summary'] = 'Instance Actor'
        actorJson['publicKey']['id'] = actorDomainUrl + '/actor#main-key'
        actorJson['publicKey']['owner'] = actorDomainUrl + '/actor'
        actorJson['url'] = actorDomainUrl + '/actor'
        actorJson['inbox'] = actorUrl + '/inbox'
        actorJson['followers'] = actorUrl + '/followers'
        actorJson['following'] = actorUrl + '/following'
        msgStr = json.dumps(actorJson, ensure_ascii=False)
        if onion_domain and callingDomain.endswith('.onion'):
            msgStr = msgStr.replace(http_prefix + '://' + domainFull,
                                    'http://' + onion_domain)
        elif i2p_domain and callingDomain.endswith('.i2p'):
            msgStr = msgStr.replace(http_prefix + '://' + domainFull,
                                    'http://' + i2p_domain)
        msg = msgStr.encode('utf-8')
        msglen = len(msg)
        if 'application/ld+json' in acceptStr:
            self._set_headers('application/ld+json', msglen,
                              cookie, callingDomain, False)
        elif 'application/jrd+json' in acceptStr:
            self._set_headers('application/jrd+json', msglen,
                              cookie, callingDomain, False)
        else:
            self._set_headers('application/activity+json', msglen,
                              cookie, callingDomain, False)
        self._write(msg)
        fitnessPerformance(GETstartTime,
                           self.server.fitness,
                           '_GET', '_showInstanceActor',
                           self.server.debug)
        return True

    def _showBlogPage(self, authorized: bool,
                      callingDomain: str, path: str,
                      base_dir: str, http_prefix: str,
                      domain: str, domainFull: str, port: int,
                      onion_domain: str, i2p_domain: str,
                      GETstartTime,
                      proxy_type: str, cookie: str,
                      translate: {}, debug: str) -> bool:
        """Shows a blog page
        """
        pageNumber = 1
        nickname = path.split('/blog/')[1]
        if '/' in nickname:
            nickname = nickname.split('/')[0]
        if '?' in nickname:
            nickname = nickname.split('?')[0]
        if '?page=' in path:
            pageNumberStr = path.split('?page=')[1]
            if '?' in pageNumberStr:
                pageNumberStr = pageNumberStr.split('?')[0]
            if '#' in pageNumberStr:
                pageNumberStr = pageNumberStr.split('#')[0]
            if pageNumberStr.isdigit():
                pageNumber = int(pageNumberStr)
                if pageNumber < 1:
                    pageNumber = 1
                elif pageNumber > 10:
                    pageNumber = 10
        if not self._establishSession("showBlogPage"):
            self._404()
            self.server.GETbusy = False
            return True
        msg = htmlBlogPage(authorized,
                           self.server.session,
                           base_dir,
                           http_prefix,
                           translate,
                           nickname,
                           domain, port,
                           maxPostsInBlogsFeed, pageNumber,
                           self.server.peertubeInstances,
                           self.server.systemLanguage,
                           self.server.personCache,
                           self.server.debug)
        if msg is not None:
            msg = msg.encode('utf-8')
            msglen = len(msg)
            self._set_headers('text/html', msglen,
                              cookie, callingDomain, False)
            self._write(msg)
            fitnessPerformance(GETstartTime,
                               self.server.fitness,
                               '_GET', '_showBlogPage',
                               self.server.debug)
            return True
        self._404()
        return True

    def _redirectToLoginScreen(self, callingDomain: str, path: str,
                               http_prefix: str, domainFull: str,
                               onion_domain: str, i2p_domain: str,
                               GETstartTime,
                               authorized: bool, debug: bool):
        """Redirects to the login screen if necessary
        """
        divertToLoginScreen = False
        if '/media/' not in path and \
           '/ontologies/' not in path and \
           '/data/' not in path and \
           '/sharefiles/' not in path and \
           '/statuses/' not in path and \
           '/emoji/' not in path and \
           '/tags/' not in path and \
           '/avatars/' not in path and \
           '/favicons/' not in path and \
           '/headers/' not in path and \
           '/fonts/' not in path and \
           '/icons/' not in path:
            divertToLoginScreen = True
            if path.startswith('/users/'):
                nickStr = path.split('/users/')[1]
                if '/' not in nickStr and '?' not in nickStr:
                    divertToLoginScreen = False
                else:
                    if path.endswith('/following') or \
                       path.endswith('/followers') or \
                       path.endswith('/skills') or \
                       path.endswith('/roles') or \
                       path.endswith('/wanted') or \
                       path.endswith('/shares'):
                        divertToLoginScreen = False

        if divertToLoginScreen and not authorized:
            divertPath = '/login'
            if self.server.news_instance:
                # for news instances if not logged in then show the
                # front page
                divertPath = '/users/news'
            # if debug:
            print('DEBUG: divertToLoginScreen=' +
                  str(divertToLoginScreen))
            print('DEBUG: authorized=' + str(authorized))
            print('DEBUG: path=' + path)
            if callingDomain.endswith('.onion') and onion_domain:
                self._redirect_headers('http://' +
                                       onion_domain + divertPath,
                                       None, callingDomain)
            elif callingDomain.endswith('.i2p') and i2p_domain:
                self._redirect_headers('http://' +
                                       i2p_domain + divertPath,
                                       None, callingDomain)
            else:
                self._redirect_headers(http_prefix + '://' +
                                       domainFull +
                                       divertPath, None, callingDomain)
            fitnessPerformance(GETstartTime,
                               self.server.fitness,
                               '_GET', '_redirectToLoginScreen',
                               self.server.debug)
            return True
        return False

    def _getStyleSheet(self, callingDomain: str, path: str,
                       GETstartTime) -> bool:
        """Returns the content of a css file
        """
        # get the last part of the path
        # eg. /my/path/file.css becomes file.css
        if '/' in path:
            path = path.split('/')[-1]
        if os.path.isfile(path):
            tries = 0
            while tries < 5:
                try:
                    css = getCSS(self.server.base_dir, path,
                                 self.server.cssCache)
                    if css:
                        break
                except Exception as ex:
                    print('ERROR: _getStyleSheet ' +
                          str(tries) + ' ' + str(ex))
                    time.sleep(1)
                    tries += 1
            msg = css.encode('utf-8')
            msglen = len(msg)
            self._set_headers('text/css', msglen,
                              None, callingDomain, False)
            self._write(msg)
            fitnessPerformance(GETstartTime,
                               self.server.fitness,
                               '_GET', '_getStyleSheet',
                               self.server.debug)
            return True
        self._404()
        return True

    def _showQRcode(self, callingDomain: str, path: str,
                    base_dir: str, domain: str, port: int,
                    GETstartTime) -> bool:
        """Shows a QR code for an account
        """
        nickname = getNicknameFromActor(path)
        savePersonQrcode(base_dir, nickname, domain, port)
        qrFilename = \
            acctDir(base_dir, nickname, domain) + '/qrcode.png'
        if os.path.isfile(qrFilename):
            if self._etag_exists(qrFilename):
                # The file has not changed
                self._304()
                return

            tries = 0
            mediaBinary = None
            while tries < 5:
                try:
                    with open(qrFilename, 'rb') as avFile:
                        mediaBinary = avFile.read()
                        break
                except Exception as ex:
                    print('ERROR: _showQRcode ' + str(tries) + ' ' + str(ex))
                    time.sleep(1)
                    tries += 1
            if mediaBinary:
                mimeType = mediaFileMimeType(qrFilename)
                self._set_headers_etag(qrFilename, mimeType,
                                       mediaBinary, None,
                                       self.server.domainFull,
                                       False, None)
                self._write(mediaBinary)
                fitnessPerformance(GETstartTime,
                                   self.server.fitness,
                                   '_GET', '_showQRcode',
                                   self.server.debug)
                return True
        self._404()
        return True

    def _searchScreenBanner(self, callingDomain: str, path: str,
                            base_dir: str, domain: str, port: int,
                            GETstartTime) -> bool:
        """Shows a banner image on the search screen
        """
        nickname = getNicknameFromActor(path)
        bannerFilename = \
            acctDir(base_dir, nickname, domain) + '/search_banner.png'
        if not os.path.isfile(bannerFilename):
            if os.path.isfile(base_dir + '/theme/default/search_banner.png'):
                copyfile(base_dir + '/theme/default/search_banner.png',
                         bannerFilename)
        if os.path.isfile(bannerFilename):
            if self._etag_exists(bannerFilename):
                # The file has not changed
                self._304()
                return True

            tries = 0
            mediaBinary = None
            while tries < 5:
                try:
                    with open(bannerFilename, 'rb') as avFile:
                        mediaBinary = avFile.read()
                        break
                except Exception as ex:
                    print('ERROR: _searchScreenBanner ' +
                          str(tries) + ' ' + str(ex))
                    time.sleep(1)
                    tries += 1
            if mediaBinary:
                mimeType = mediaFileMimeType(bannerFilename)
                self._set_headers_etag(bannerFilename, mimeType,
                                       mediaBinary, None,
                                       self.server.domainFull,
                                       False, None)
                self._write(mediaBinary)
                fitnessPerformance(GETstartTime,
                                   self.server.fitness,
                                   '_GET', '_searchScreenBanner',
                                   self.server.debug)
                return True
        self._404()
        return True

    def _columnImage(self, side: str, callingDomain: str, path: str,
                     base_dir: str, domain: str, port: int,
                     GETstartTime) -> bool:
        """Shows an image at the top of the left/right column
        """
        nickname = getNicknameFromActor(path)
        if not nickname:
            self._404()
            return True
        bannerFilename = \
            acctDir(base_dir, nickname, domain) + '/' + side + '_col_image.png'
        if os.path.isfile(bannerFilename):
            if self._etag_exists(bannerFilename):
                # The file has not changed
                self._304()
                return True

            tries = 0
            mediaBinary = None
            while tries < 5:
                try:
                    with open(bannerFilename, 'rb') as avFile:
                        mediaBinary = avFile.read()
                        break
                except Exception as ex:
                    print('ERROR: _columnImage ' + str(tries) + ' ' + str(ex))
                    time.sleep(1)
                    tries += 1
            if mediaBinary:
                mimeType = mediaFileMimeType(bannerFilename)
                self._set_headers_etag(bannerFilename, mimeType,
                                       mediaBinary, None,
                                       self.server.domainFull,
                                       False, None)
                self._write(mediaBinary)
                fitnessPerformance(GETstartTime,
                                   self.server.fitness,
                                   '_GET', '_columnImage ' + side,
                                   self.server.debug)
                return True
        self._404()
        return True

    def _showBackgroundImage(self, callingDomain: str, path: str,
                             base_dir: str, GETstartTime) -> bool:
        """Show a background image
        """
        imageExtensions = getImageExtensions()
        for ext in imageExtensions:
            for bg in ('follow', 'options', 'login', 'welcome'):
                # follow screen background image
                if path.endswith('/' + bg + '-background.' + ext):
                    bgFilename = \
                        base_dir + '/accounts/' + \
                        bg + '-background.' + ext
                    if os.path.isfile(bgFilename):
                        if self._etag_exists(bgFilename):
                            # The file has not changed
                            self._304()
                            return True

                        tries = 0
                        bgBinary = None
                        while tries < 5:
                            try:
                                with open(bgFilename, 'rb') as avFile:
                                    bgBinary = avFile.read()
                                    break
                            except Exception as ex:
                                print('ERROR: _showBackgroundImage ' +
                                      str(tries) + ' ' + str(ex))
                                time.sleep(1)
                                tries += 1
                        if bgBinary:
                            if ext == 'jpg':
                                ext = 'jpeg'
                            self._set_headers_etag(bgFilename,
                                                   'image/' + ext,
                                                   bgBinary, None,
                                                   self.server.domainFull,
                                                   False, None)
                            self._write(bgBinary)
                            fitnessPerformance(GETstartTime,
                                               self.server.fitness,
                                               '_GET', '_showBackgroundImage',
                                               self.server.debug)
                            return True
        self._404()
        return True

    def _showDefaultProfileBackground(self, callingDomain: str, path: str,
                                      base_dir: str, themeName: str,
                                      GETstartTime) -> bool:
        """If a background image is missing after searching for a handle
        then substitute this image
        """
        imageExtensions = getImageExtensions()
        for ext in imageExtensions:
            bgFilename = \
                base_dir + '/theme/' + themeName + '/image.' + ext
            if os.path.isfile(bgFilename):
                if self._etag_exists(bgFilename):
                    # The file has not changed
                    self._304()
                    return True

                tries = 0
                bgBinary = None
                while tries < 5:
                    try:
                        with open(bgFilename, 'rb') as avFile:
                            bgBinary = avFile.read()
                            break
                    except Exception as ex:
                        print('ERROR: _showDefaultProfileBackground ' +
                              str(tries) + ' ' + str(ex))
                        time.sleep(1)
                        tries += 1
                if bgBinary:
                    if ext == 'jpg':
                        ext = 'jpeg'
                    self._set_headers_etag(bgFilename,
                                           'image/' + ext,
                                           bgBinary, None,
                                           self.server.domainFull,
                                           False, None)
                    self._write(bgBinary)
                    fitnessPerformance(GETstartTime,
                                       self.server.fitness,
                                       '_GET',
                                       '_showDefaultProfileBackground',
                                       self.server.debug)
                    return True
                break

        self._404()
        return True

    def _showShareImage(self, callingDomain: str, path: str,
                        base_dir: str, GETstartTime) -> bool:
        """Show a shared item image
        """
        if not isImageFile(path):
            self._404()
            return True

        mediaStr = path.split('/sharefiles/')[1]
        mediaFilename = base_dir + '/sharefiles/' + mediaStr
        if not os.path.isfile(mediaFilename):
            self._404()
            return True

        if self._etag_exists(mediaFilename):
            # The file has not changed
            self._304()
            return True

        mediaFileType = getImageMimeType(mediaFilename)
        mediaBinary = None
        try:
            with open(mediaFilename, 'rb') as avFile:
                mediaBinary = avFile.read()
        except OSError:
            print('EX: unable to read binary ' + mediaFilename)
        if mediaBinary:
            self._set_headers_etag(mediaFilename,
                                   mediaFileType,
                                   mediaBinary, None,
                                   self.server.domainFull,
                                   False, None)
            self._write(mediaBinary)
        fitnessPerformance(GETstartTime,
                           self.server.fitness,
                           '_GET', '_showShareImage',
                           self.server.debug)
        return True

    def _showAvatarOrBanner(self, refererDomain: str, path: str,
                            base_dir: str, domain: str,
                            GETstartTime) -> bool:
        """Shows an avatar or banner or profile background image
        """
        if '/users/' not in path:
            if '/system/accounts/avatars/' not in path and \
               '/system/accounts/headers/' not in path and \
               '/accounts/avatars/' not in path and \
               '/accounts/headers/' not in path:
                return False
        if not isImageFile(path):
            return False
        if '/system/accounts/avatars/' in path:
            avatarStr = path.split('/system/accounts/avatars/')[1]
        elif '/accounts/avatars/' in path:
            avatarStr = path.split('/accounts/avatars/')[1]
        elif '/system/accounts/headers/' in path:
            avatarStr = path.split('/system/accounts/headers/')[1]
        elif '/accounts/headers/' in path:
            avatarStr = path.split('/accounts/headers/')[1]
        else:
            avatarStr = path.split('/users/')[1]
        if not ('/' in avatarStr and '.temp.' not in path):
            return False
        avatarNickname = avatarStr.split('/')[0]
        avatarFile = avatarStr.split('/')[1]
        avatarFileExt = avatarFile.split('.')[-1]
        # remove any numbers, eg. avatar123.png becomes avatar.png
        if avatarFile.startswith('avatar'):
            avatarFile = 'avatar.' + avatarFileExt
        elif avatarFile.startswith('banner'):
            avatarFile = 'banner.' + avatarFileExt
        elif avatarFile.startswith('search_banner'):
            avatarFile = 'search_banner.' + avatarFileExt
        elif avatarFile.startswith('image'):
            avatarFile = 'image.' + avatarFileExt
        elif avatarFile.startswith('left_col_image'):
            avatarFile = 'left_col_image.' + avatarFileExt
        elif avatarFile.startswith('right_col_image'):
            avatarFile = 'right_col_image.' + avatarFileExt
        avatarFilename = \
            acctDir(base_dir, avatarNickname, domain) + '/' + avatarFile
        if not os.path.isfile(avatarFilename):
            originalExt = avatarFileExt
            originalAvatarFile = avatarFile
            altExt = getImageExtensions()
            altFound = False
            for alt in altExt:
                if alt == originalExt:
                    continue
                avatarFile = \
                    originalAvatarFile.replace('.' + originalExt,
                                               '.' + alt)
                avatarFilename = \
                    acctDir(base_dir, avatarNickname, domain) + \
                    '/' + avatarFile
                if os.path.isfile(avatarFilename):
                    altFound = True
                    break
            if not altFound:
                return False
        if self._etag_exists(avatarFilename):
            # The file has not changed
            self._304()
            return True

        t = os.path.getmtime(avatarFilename)
        lastModifiedTime = datetime.datetime.fromtimestamp(t)
        lastModifiedTimeStr = \
            lastModifiedTime.strftime('%a, %d %b %Y %H:%M:%S GMT')

        mediaImageType = getImageMimeType(avatarFile)
        mediaBinary = None
        try:
            with open(avatarFilename, 'rb') as avFile:
                mediaBinary = avFile.read()
        except OSError:
            print('EX: unable to read avatar ' + avatarFilename)
        if mediaBinary:
            self._set_headers_etag(avatarFilename, mediaImageType,
                                   mediaBinary, None,
                                   refererDomain, True,
                                   lastModifiedTimeStr)
            self._write(mediaBinary)
        fitnessPerformance(GETstartTime,
                           self.server.fitness,
                           '_GET', '_showAvatarOrBanner',
                           self.server.debug)
        return True

    def _confirmDeleteEvent(self, callingDomain: str, path: str,
                            base_dir: str, http_prefix: str, cookie: str,
                            translate: {}, domainFull: str,
                            onion_domain: str, i2p_domain: str,
                            GETstartTime) -> bool:
        """Confirm whether to delete a calendar event
        """
        postId = path.split('?eventid=')[1]
        if '?' in postId:
            postId = postId.split('?')[0]
        postTime = path.split('?time=')[1]
        if '?' in postTime:
            postTime = postTime.split('?')[0]
        postYear = path.split('?year=')[1]
        if '?' in postYear:
            postYear = postYear.split('?')[0]
        postMonth = path.split('?month=')[1]
        if '?' in postMonth:
            postMonth = postMonth.split('?')[0]
        postDay = path.split('?day=')[1]
        if '?' in postDay:
            postDay = postDay.split('?')[0]
        # show the confirmation screen screen
        msg = htmlCalendarDeleteConfirm(self.server.cssCache,
                                        translate,
                                        base_dir, path,
                                        http_prefix,
                                        domainFull,
                                        postId, postTime,
                                        postYear, postMonth, postDay,
                                        callingDomain)
        if not msg:
            actor = \
                http_prefix + '://' + \
                domainFull + \
                path.split('/eventdelete')[0]
            if callingDomain.endswith('.onion') and onion_domain:
                actor = \
                    'http://' + onion_domain + \
                    path.split('/eventdelete')[0]
            elif callingDomain.endswith('.i2p') and i2p_domain:
                actor = \
                    'http://' + i2p_domain + \
                    path.split('/eventdelete')[0]
            self._redirect_headers(actor + '/calendar',
                                   cookie, callingDomain)
            fitnessPerformance(GETstartTime,
                               self.server.fitness,
                               '_GET', '_confirmDeleteEvent',
                               self.server.debug)
            return True
        msg = msg.encode('utf-8')
        msglen = len(msg)
        self._set_headers('text/html', msglen,
                          cookie, callingDomain, False)
        self._write(msg)
        return True

    def _showNewPost(self, callingDomain: str, path: str,
                     media_instance: bool, translate: {},
                     base_dir: str, http_prefix: str,
                     inReplyToUrl: str, replyToList: [],
                     shareDescription: str, replyPageNumber: int,
                     replyCategory: str,
                     domain: str, domainFull: str,
                     GETstartTime, cookie,
                     noDropDown: bool, conversationId: str) -> bool:
        """Shows the new post screen
        """
        isNewPostEndpoint = False
        if '/users/' in path and '/new' in path:
            # Various types of new post in the web interface
            newPostEndpoints = getNewPostEndpoints()
            for currPostType in newPostEndpoints:
                if path.endswith('/' + currPostType):
                    isNewPostEndpoint = True
                    break
        if isNewPostEndpoint:
            nickname = getNicknameFromActor(path)

            if inReplyToUrl:
                replyIntervalHours = self.server.default_reply_interval_hrs
                if not canReplyTo(base_dir, nickname, domain,
                                  inReplyToUrl, replyIntervalHours):
                    print('Reply outside of time window ' + inReplyToUrl +
                          str(replyIntervalHours) + ' hours')
                    self._403()
                    return True
                elif self.server.debug:
                    print('Reply is within time interval: ' +
                          str(replyIntervalHours) + ' hours')

            accessKeys = self.server.accessKeys
            if self.server.keyShortcuts.get(nickname):
                accessKeys = self.server.keyShortcuts[nickname]

            customSubmitText = getConfigParam(base_dir, 'customSubmitText')

            postJsonObject = None
            if inReplyToUrl:
                replyPostFilename = \
                    locatePost(base_dir, nickname, domain, inReplyToUrl)
                if replyPostFilename:
                    postJsonObject = loadJson(replyPostFilename)

            msg = htmlNewPost(self.server.cssCache,
                              media_instance,
                              translate,
                              base_dir,
                              http_prefix,
                              path, inReplyToUrl,
                              replyToList,
                              shareDescription, None,
                              replyPageNumber,
                              replyCategory,
                              nickname, domain,
                              domainFull,
                              self.server.defaultTimeline,
                              self.server.newswire,
                              self.server.themeName,
                              noDropDown, accessKeys,
                              customSubmitText,
                              conversationId,
                              self.server.recentPostsCache,
                              self.server.max_recent_posts,
                              self.server.session,
                              self.server.cachedWebfingers,
                              self.server.personCache,
                              self.server.port,
                              postJsonObject,
                              self.server.project_version,
                              self.server.yt_replace_domain,
                              self.server.twitter_replacement_domain,
                              self.server.show_published_date_only,
                              self.server.peertubeInstances,
                              self.server.allow_local_network_access,
                              self.server.systemLanguage,
                              self.server.max_like_count,
                              self.server.signingPrivateKeyPem,
                              self.server.CWlists,
                              self.server.lists_enabled,
                              self.server.defaultTimeline).encode('utf-8')
            if not msg:
                print('Error replying to ' + inReplyToUrl)
                self._404()
                return True
            msglen = len(msg)
            self._set_headers('text/html', msglen,
                              cookie, callingDomain, False)
            self._write(msg)
            fitnessPerformance(GETstartTime,
                               self.server.fitness,
                               '_GET', '_showNewPost',
                               self.server.debug)
            return True
        return False

    def _showKnownCrawlers(self, callingDomain: str, path: str,
                           base_dir: str, knownCrawlers: {}) -> bool:
        """Show a list of known web crawlers
        """
        if '/users/' not in path:
            return False
        if not path.endswith('/crawlers'):
            return False
        nickname = getNicknameFromActor(path)
        if not nickname:
            return False
        if not isModerator(base_dir, nickname):
            return False
        crawlersList = []
        currTime = int(time.time())
        recentCrawlers = 60 * 60 * 24 * 30
        for uaStr, item in knownCrawlers.items():
            if item['lastseen'] - currTime < recentCrawlers:
                hitsStr = str(item['hits']).zfill(8)
                crawlersList.append(hitsStr + ' ' + uaStr)
        crawlersList.sort(reverse=True)
        msg = ''
        for lineStr in crawlersList:
            msg += lineStr + '\n'
        msg = msg.encode('utf-8')
        msglen = len(msg)
        self._set_headers('text/plain; charset=utf-8', msglen,
                          None, callingDomain, True)
        self._write(msg)
        return True

    def _editProfile(self, callingDomain: str, path: str,
                     translate: {}, base_dir: str,
                     http_prefix: str, domain: str, port: int,
                     cookie: str) -> bool:
        """Show the edit profile screen
        """
        if '/users/' in path and path.endswith('/editprofile'):
            peertubeInstances = self.server.peertubeInstances
            nickname = getNicknameFromActor(path)
            if nickname:
                city = getSpoofedCity(self.server.city,
                                      base_dir, nickname, domain)
            else:
                city = self.server.city

            accessKeys = self.server.accessKeys
            if '/users/' in path:
                if self.server.keyShortcuts.get(nickname):
                    accessKeys = self.server.keyShortcuts[nickname]

            default_reply_interval_hrs = self.server.default_reply_interval_hrs
            msg = htmlEditProfile(self.server.cssCache,
                                  translate,
                                  base_dir,
                                  path, domain,
                                  port,
                                  http_prefix,
                                  self.server.defaultTimeline,
                                  self.server.themeName,
                                  peertubeInstances,
                                  self.server.textModeBanner,
                                  city,
                                  self.server.user_agents_blocked,
                                  accessKeys,
                                  default_reply_interval_hrs,
                                  self.server.CWlists,
                                  self.server.lists_enabled).encode('utf-8')
            if msg:
                msglen = len(msg)
                self._set_headers('text/html', msglen,
                                  cookie, callingDomain, False)
                self._write(msg)
            else:
                self._404()
            return True
        return False

    def _editLinks(self, callingDomain: str, path: str,
                   translate: {}, base_dir: str,
                   http_prefix: str, domain: str, port: int,
                   cookie: str, theme: str) -> bool:
        """Show the links from the left column
        """
        if '/users/' in path and path.endswith('/editlinks'):
            nickname = path.split('/users/')[1]
            if '/' in nickname:
                nickname = nickname.split('/')[0]

            accessKeys = self.server.accessKeys
            if self.server.keyShortcuts.get(nickname):
                accessKeys = self.server.keyShortcuts[nickname]

            msg = htmlEditLinks(self.server.cssCache,
                                translate,
                                base_dir,
                                path, domain,
                                port,
                                http_prefix,
                                self.server.defaultTimeline,
                                theme, accessKeys).encode('utf-8')
            if msg:
                msglen = len(msg)
                self._set_headers('text/html', msglen,
                                  cookie, callingDomain, False)
                self._write(msg)
            else:
                self._404()
            return True
        return False

    def _editNewswire(self, callingDomain: str, path: str,
                      translate: {}, base_dir: str,
                      http_prefix: str, domain: str, port: int,
                      cookie: str) -> bool:
        """Show the newswire from the right column
        """
        if '/users/' in path and path.endswith('/editnewswire'):
            nickname = path.split('/users/')[1]
            if '/' in nickname:
                nickname = nickname.split('/')[0]

            accessKeys = self.server.accessKeys
            if self.server.keyShortcuts.get(nickname):
                accessKeys = self.server.keyShortcuts[nickname]

            msg = htmlEditNewswire(self.server.cssCache,
                                   translate,
                                   base_dir,
                                   path, domain,
                                   port,
                                   http_prefix,
                                   self.server.defaultTimeline,
                                   self.server.themeName,
                                   accessKeys).encode('utf-8')
            if msg:
                msglen = len(msg)
                self._set_headers('text/html', msglen,
                                  cookie, callingDomain, False)
                self._write(msg)
            else:
                self._404()
            return True
        return False

    def _editNewsPost(self, callingDomain: str, path: str,
                      translate: {}, base_dir: str,
                      http_prefix: str, domain: str, port: int,
                      domainFull: str,
                      cookie: str) -> bool:
        """Show the edit screen for a news post
        """
        if '/users/' in path and '/editnewspost=' in path:
            postActor = 'news'
            if '?actor=' in path:
                postActor = path.split('?actor=')[1]
                if '?' in postActor:
                    postActor = postActor.split('?')[0]
            postId = path.split('/editnewspost=')[1]
            if '?' in postId:
                postId = postId.split('?')[0]
            postUrl = localActorUrl(http_prefix, postActor, domainFull) + \
                '/statuses/' + postId
            path = path.split('/editnewspost=')[0]
            msg = htmlEditNewsPost(self.server.cssCache,
                                   translate, base_dir,
                                   path, domain, port,
                                   http_prefix,
                                   postUrl,
                                   self.server.systemLanguage).encode('utf-8')
            if msg:
                msglen = len(msg)
                self._set_headers('text/html', msglen,
                                  cookie, callingDomain, False)
                self._write(msg)
            else:
                self._404()
            return True
        return False

    def _getFollowingJson(self, base_dir: str, path: str,
                          callingDomain: str,
                          http_prefix: str,
                          domain: str, port: int,
                          followingItemsPerPage: int,
                          debug: bool, listName='following') -> None:
        """Returns json collection for following.txt
        """
        followingJson = \
            getFollowingFeed(base_dir, domain, port, path, http_prefix,
                             True, followingItemsPerPage, listName)
        if not followingJson:
            if debug:
                print(listName + ' json feed not found for ' + path)
            self._404()
            return
        msg = json.dumps(followingJson,
                         ensure_ascii=False).encode('utf-8')
        msglen = len(msg)
        self._set_headers('application/json',
                          msglen, None, callingDomain, False)
        self._write(msg)

    def _sendBlock(self, http_prefix: str,
                   blockerNickname: str, blockerDomainFull: str,
                   blockingNickname: str, blockingDomainFull: str) -> bool:
        if blockerDomainFull == blockingDomainFull:
            if blockerNickname == blockingNickname:
                # don't block self
                return False
        blockActor = \
            localActorUrl(http_prefix, blockerNickname, blockerDomainFull)
        toUrl = 'https://www.w3.org/ns/activitystreams#Public'
        ccUrl = blockActor + '/followers'

        blockedUrl = \
            http_prefix + '://' + blockingDomainFull + \
            '/@' + blockingNickname
        blockJson = {
            "@context": "https://www.w3.org/ns/activitystreams",
            'type': 'Block',
            'actor': blockActor,
            'object': blockedUrl,
            'to': [toUrl],
            'cc': [ccUrl]
        }
        self._postToOutbox(blockJson, self.server.project_version,
                           blockerNickname)
        return True

    def _getRefererDomain(self, uaStr: str) -> str:
        """Returns the referer domain
        Which domain is the GET request coming from?
        """
        refererDomain = None
        if self.headers.get('referer'):
            refererDomain, refererPort = \
                getDomainFromActor(self.headers['referer'])
            refererDomain = getFullDomain(refererDomain, refererPort)
        elif self.headers.get('Referer'):
            refererDomain, refererPort = \
                getDomainFromActor(self.headers['Referer'])
            refererDomain = getFullDomain(refererDomain, refererPort)
        elif self.headers.get('Signature'):
            if 'keyId="' in self.headers['Signature']:
                refererDomain = self.headers['Signature'].split('keyId="')[1]
                if '/' in refererDomain:
                    refererDomain = refererDomain.split('/')[0]
                elif '#' in refererDomain:
                    refererDomain = refererDomain.split('#')[0]
                elif '"' in refererDomain:
                    refererDomain = refererDomain.split('"')[0]
        elif uaStr:
            if '+https://' in uaStr:
                refererDomain = uaStr.split('+https://')[1]
                if '/' in refererDomain:
                    refererDomain = refererDomain.split('/')[0]
                elif ')' in refererDomain:
                    refererDomain = refererDomain.split(')')[0]
            elif '+http://' in uaStr:
                refererDomain = uaStr.split('+http://')[1]
                if '/' in refererDomain:
                    refererDomain = refererDomain.split('/')[0]
                elif ')' in refererDomain:
                    refererDomain = refererDomain.split(')')[0]
        return refererDomain

    def _getUserAgent(self) -> str:
        """Returns the user agent string from the headers
        """
        uaStr = None
        if self.headers.get('User-Agent'):
            uaStr = self.headers['User-Agent']
        elif self.headers.get('user-agent'):
            uaStr = self.headers['user-agent']
        elif self.headers.get('User-agent'):
            uaStr = self.headers['User-agent']
        return uaStr

    def _permittedCrawlerPath(self, path: str) -> bool:
        """Is the given path permitted to be crawled by a search engine?
        this should only allow through basic information, such as nodeinfo
        """
        if path == '/' or path == '/about' or path == '/login' or \
           path.startswith('/blog/'):
            return True
        return False

    def do_GET(self):
        callingDomain = self.server.domainFull

        if self.headers.get('Host'):
            callingDomain = decodedHost(self.headers['Host'])
            if self.server.onion_domain:
                if callingDomain != self.server.domain and \
                   callingDomain != self.server.domainFull and \
                   callingDomain != self.server.onion_domain:
                    print('GET domain blocked: ' + callingDomain)
                    self._400()
                    return
            elif self.server.i2p_domain:
                if callingDomain != self.server.domain and \
                   callingDomain != self.server.domainFull and \
                   callingDomain != self.server.i2p_domain:
                    print('GET domain blocked: ' + callingDomain)
                    self._400()
                    return
            else:
                if callingDomain != self.server.domain and \
                   callingDomain != self.server.domainFull:
                    print('GET domain blocked: ' + callingDomain)
                    self._400()
                    return

        uaStr = self._getUserAgent()

        if not self._permittedCrawlerPath(self.path):
            if self._blockedUserAgent(callingDomain, uaStr):
                self._400()
                return

        refererDomain = self._getRefererDomain(uaStr)

        GETstartTime = time.time()

        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', 'start', self.server.debug)

        # Since fediverse crawlers are quite active,
        # make returning info to them high priority
        # get nodeinfo endpoint
        if self._nodeinfo(uaStr, callingDomain):
            return

        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', '_nodeinfo[callingDomain]',
                           self.server.debug)

        if self.path == '/logout':
            if not self.server.news_instance:
                msg = \
                    htmlLogin(self.server.cssCache,
                              self.server.translate,
                              self.server.base_dir,
                              self.server.http_prefix,
                              self.server.domainFull,
                              self.server.systemLanguage,
                              False).encode('utf-8')
                msglen = len(msg)
                self._logout_headers('text/html', msglen, callingDomain)
                self._write(msg)
            else:
                if callingDomain.endswith('.onion') and \
                   self.server.onion_domain:
                    self._logout_redirect('http://' +
                                          self.server.onion_domain +
                                          '/users/news', None,
                                          callingDomain)
                elif (callingDomain.endswith('.i2p') and
                      self.server.i2p_domain):
                    self._logout_redirect('http://' +
                                          self.server.i2p_domain +
                                          '/users/news', None,
                                          callingDomain)
                else:
                    self._logout_redirect(self.server.http_prefix +
                                          '://' +
                                          self.server.domainFull +
                                          '/users/news',
                                          None, callingDomain)
            fitnessPerformance(GETstartTime, self.server.fitness,
                               '_GET', 'logout',
                               self.server.debug)
            return

        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', 'show logout',
                           self.server.debug)

        # replace https://domain/@nick with https://domain/users/nick
        if self.path.startswith('/@'):
            self.path = self.path.replace('/@', '/users/')
            # replace https://domain/@nick/statusnumber
            # with https://domain/users/nick/statuses/statusnumber
            nickname = self.path.split('/users/')[1]
            if '/' in nickname:
                statusNumberStr = nickname.split('/')[1]
                if statusNumberStr.isdigit():
                    nickname = nickname.split('/')[0]
                    self.path = \
                        self.path.replace('/users/' + nickname + '/',
                                          '/users/' + nickname + '/statuses/')

        # instance actor
        if self.path == '/actor' or \
           self.path == '/users/actor' or \
           self.path == '/Actor' or \
           self.path == '/users/Actor':
            self.path = '/users/inbox'
            if self._showInstanceActor(callingDomain, self.path,
                                       self.server.base_dir,
                                       self.server.http_prefix,
                                       self.server.domain,
                                       self.server.domainFull,
                                       self.server.port,
                                       self.server.onion_domain,
                                       self.server.i2p_domain,
                                       GETstartTime,
                                       self.server.proxy_type,
                                       None, self.server.debug,
                                       self.server.enable_shared_inbox):
                return
            else:
                self._404()
                return

        # turn off dropdowns on new post screen
        noDropDown = False
        if self.path.endswith('?nodropdown'):
            noDropDown = True
            self.path = self.path.replace('?nodropdown', '')

        # redirect music to #nowplaying list
        if self.path == '/music' or self.path == '/nowplaying':
            self.path = '/tags/nowplaying'

        if self.server.debug:
            print('DEBUG: GET from ' + self.server.base_dir +
                  ' path: ' + self.path + ' busy: ' +
                  str(self.server.GETbusy))

        if self.server.debug:
            print(str(self.headers))

        cookie = None
        if self.headers.get('Cookie'):
            cookie = self.headers['Cookie']

        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', 'get cookie',
                           self.server.debug)

        if '/manifest.json' in self.path:
            if self._hasAccept(callingDomain):
                if not self._requestHTTP():
                    self._progressiveWebAppManifest(callingDomain,
                                                    GETstartTime)
                    return
                else:
                    self.path = '/'

        if '/browserconfig.xml' in self.path:
            if self._hasAccept(callingDomain):
                self._browserConfig(callingDomain, GETstartTime)
                return

        # default newswire favicon, for links to sites which
        # have no favicon
        if not self.path.startswith('/favicons/'):
            if 'newswire_favicon.ico' in self.path:
                self._getFavicon(callingDomain, self.server.base_dir,
                                 self.server.debug,
                                 'newswire_favicon.ico')
                return

            # favicon image
            if 'favicon.ico' in self.path:
                self._getFavicon(callingDomain, self.server.base_dir,
                                 self.server.debug,
                                 'favicon.ico')
                return

        # check authorization
        authorized = self._isAuthorized()
        if self.server.debug:
            if authorized:
                print('GET Authorization granted')
            else:
                print('GET Not authorized')

        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', 'isAuthorized',
                           self.server.debug)

        # shared items catalog for this instance
        # this is only accessible to instance members or to
        # other instances which present an authorization token
        if self.path.startswith('/catalog') or \
           (self.path.startswith('/users/') and '/catalog' in self.path):
            catalogAuthorized = authorized
            if not catalogAuthorized:
                if self.server.debug:
                    print('Catalog access is not authorized. ' +
                          'Checking Authorization header')
                # Check the authorization token
                if self.headers.get('Origin') and \
                   self.headers.get('Authorization'):
                    permittedDomains = \
                        self.server.shared_items_federated_domains
                    sharedItemTokens = self.server.sharedItemFederationTokens
                    if authorizeSharedItems(permittedDomains,
                                            self.server.base_dir,
                                            self.headers['Origin'],
                                            callingDomain,
                                            self.headers['Authorization'],
                                            self.server.debug,
                                            sharedItemTokens):
                        catalogAuthorized = True
                    elif self.server.debug:
                        print('Authorization token refused for ' +
                              'shared items federation')
                elif self.server.debug:
                    print('No Authorization header is available for ' +
                          'shared items federation')
            # show shared items catalog for federation
            if self._hasAccept(callingDomain) and catalogAuthorized:
                catalogType = 'json'
                if self.path.endswith('.csv') or self._requestCSV():
                    catalogType = 'csv'
                elif self.path.endswith('.json') or not self._requestHTTP():
                    catalogType = 'json'
                if self.server.debug:
                    print('Preparing DFC catalog in format ' + catalogType)

                if catalogType == 'json':
                    # catalog as a json
                    if not self.path.startswith('/users/'):
                        if self.server.debug:
                            print('Catalog for the instance')
                        catalogJson = \
                            sharesCatalogEndpoint(self.server.base_dir,
                                                  self.server.http_prefix,
                                                  self.server.domainFull,
                                                  self.path, 'shares')
                    else:
                        domainFull = self.server.domainFull
                        http_prefix = self.server.http_prefix
                        nickname = self.path.split('/users/')[1]
                        if '/' in nickname:
                            nickname = nickname.split('/')[0]
                        if self.server.debug:
                            print('Catalog for account: ' + nickname)
                        catalogJson = \
                            sharesCatalogAccountEndpoint(self.server.base_dir,
                                                         http_prefix,
                                                         nickname,
                                                         self.server.domain,
                                                         domainFull,
                                                         self.path,
                                                         self.server.debug,
                                                         'shares')
                    msg = json.dumps(catalogJson,
                                     ensure_ascii=False).encode('utf-8')
                    msglen = len(msg)
                    self._set_headers('application/json',
                                      msglen, None, callingDomain, False)
                    self._write(msg)
                    return
                elif catalogType == 'csv':
                    # catalog as a CSV file for import into a spreadsheet
                    msg = \
                        sharesCatalogCSVEndpoint(self.server.base_dir,
                                                 self.server.http_prefix,
                                                 self.server.domainFull,
                                                 self.path,
                                                 'shares').encode('utf-8')
                    msglen = len(msg)
                    self._set_headers('text/csv',
                                      msglen, None, callingDomain, False)
                    self._write(msg)
                    return
                self._404()
                return
            self._400()
            return

        # wanted items catalog for this instance
        # this is only accessible to instance members or to
        # other instances which present an authorization token
        if self.path.startswith('/wantedItems') or \
           (self.path.startswith('/users/') and '/wantedItems' in self.path):
            catalogAuthorized = authorized
            if not catalogAuthorized:
                if self.server.debug:
                    print('Wanted catalog access is not authorized. ' +
                          'Checking Authorization header')
                # Check the authorization token
                if self.headers.get('Origin') and \
                   self.headers.get('Authorization'):
                    permittedDomains = \
                        self.server.shared_items_federated_domains
                    sharedItemTokens = self.server.sharedItemFederationTokens
                    if authorizeSharedItems(permittedDomains,
                                            self.server.base_dir,
                                            self.headers['Origin'],
                                            callingDomain,
                                            self.headers['Authorization'],
                                            self.server.debug,
                                            sharedItemTokens):
                        catalogAuthorized = True
                    elif self.server.debug:
                        print('Authorization token refused for ' +
                              'wanted items federation')
                elif self.server.debug:
                    print('No Authorization header is available for ' +
                          'wanted items federation')
            # show wanted items catalog for federation
            if self._hasAccept(callingDomain) and catalogAuthorized:
                catalogType = 'json'
                if self.path.endswith('.csv') or self._requestCSV():
                    catalogType = 'csv'
                elif self.path.endswith('.json') or not self._requestHTTP():
                    catalogType = 'json'
                if self.server.debug:
                    print('Preparing DFC wanted catalog in format ' +
                          catalogType)

                if catalogType == 'json':
                    # catalog as a json
                    if not self.path.startswith('/users/'):
                        if self.server.debug:
                            print('Wanted catalog for the instance')
                        catalogJson = \
                            sharesCatalogEndpoint(self.server.base_dir,
                                                  self.server.http_prefix,
                                                  self.server.domainFull,
                                                  self.path, 'wanted')
                    else:
                        domainFull = self.server.domainFull
                        http_prefix = self.server.http_prefix
                        nickname = self.path.split('/users/')[1]
                        if '/' in nickname:
                            nickname = nickname.split('/')[0]
                        if self.server.debug:
                            print('Wanted catalog for account: ' + nickname)
                        catalogJson = \
                            sharesCatalogAccountEndpoint(self.server.base_dir,
                                                         http_prefix,
                                                         nickname,
                                                         self.server.domain,
                                                         domainFull,
                                                         self.path,
                                                         self.server.debug,
                                                         'wanted')
                    msg = json.dumps(catalogJson,
                                     ensure_ascii=False).encode('utf-8')
                    msglen = len(msg)
                    self._set_headers('application/json',
                                      msglen, None, callingDomain, False)
                    self._write(msg)
                    return
                elif catalogType == 'csv':
                    # catalog as a CSV file for import into a spreadsheet
                    msg = \
                        sharesCatalogCSVEndpoint(self.server.base_dir,
                                                 self.server.http_prefix,
                                                 self.server.domainFull,
                                                 self.path,
                                                 'wanted').encode('utf-8')
                    msglen = len(msg)
                    self._set_headers('text/csv',
                                      msglen, None, callingDomain, False)
                    self._write(msg)
                    return
                self._404()
                return
            self._400()
            return

        # minimal mastodon api
        if self._mastoApi(self.path, callingDomain, uaStr,
                          authorized,
                          self.server.http_prefix,
                          self.server.base_dir,
                          self.authorizedNickname,
                          self.server.domain,
                          self.server.domainFull,
                          self.server.onion_domain,
                          self.server.i2p_domain,
                          self.server.translate,
                          self.server.registration,
                          self.server.systemLanguage,
                          self.server.project_version,
                          self.server.customEmoji,
                          self.server.show_node_info_accounts):
            return

        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', '_mastoApi[callingDomain]',
                           self.server.debug)

        if not self._establishSession("GET"):
            self._404()
            fitnessPerformance(GETstartTime, self.server.fitness,
                               '_GET', 'session fail',
                               self.server.debug)
            self.server.GETbusy = False
            return

        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', 'create session',
                           self.server.debug)

        # is this a html request?
        htmlGET = False
        if self._hasAccept(callingDomain):
            if self._requestHTTP():
                htmlGET = True
        else:
            if self.headers.get('Connection'):
                # https://developer.mozilla.org/en-US/
                # docs/Web/HTTP/Protocol_upgrade_mechanism
                if self.headers.get('Upgrade'):
                    print('HTTP Connection request: ' +
                          self.headers['Upgrade'])
                else:
                    print('HTTP Connection request: ' +
                          self.headers['Connection'])
                self._200()
            else:
                print('WARN: No Accept header ' + str(self.headers))
                self._400()
            return

        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', 'hasAccept',
                           self.server.debug)

        # cached favicon images
        # Note that this comes before the busy flag to avoid conflicts
        if self.path.startswith('/favicons/'):
            if self.server.domainFull in self.path:
                # favicon for this instance
                self._getFavicon(callingDomain, self.server.base_dir,
                                 self.server.debug,
                                 'favicon.ico')
                return
            self._showCachedFavicon(refererDomain, self.path,
                                    self.server.base_dir,
                                    GETstartTime)
            return

        # get css
        # Note that this comes before the busy flag to avoid conflicts
        if self.path.endswith('.css'):
            if self._getStyleSheet(callingDomain, self.path,
                                   GETstartTime):
                return

        if authorized and '/exports/' in self.path:
            self._getExportedTheme(callingDomain, self.path,
                                   self.server.base_dir,
                                   self.server.domainFull,
                                   self.server.debug)
            return

        # get fonts
        if '/fonts/' in self.path:
            self._getFonts(callingDomain, self.path,
                           self.server.base_dir, self.server.debug,
                           GETstartTime)
            return

        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', 'fonts',
                           self.server.debug)

        if self.path == '/sharedInbox' or \
           self.path == '/users/inbox' or \
           self.path == '/actor/inbox' or \
           self.path == '/users/' + self.server.domain:
            # if shared inbox is not enabled
            if not self.server.enable_shared_inbox:
                self._503()
                return

            self.path = '/inbox'

        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', 'sharedInbox enabled',
                           self.server.debug)

        if self.path == '/categories.xml':
            self._getHashtagCategoriesFeed(authorized,
                                           callingDomain, self.path,
                                           self.server.base_dir,
                                           self.server.http_prefix,
                                           self.server.domain,
                                           self.server.port,
                                           self.server.proxy_type,
                                           GETstartTime,
                                           self.server.debug)
            return

        if self.path == '/newswire.xml':
            self._getNewswireFeed(authorized,
                                  callingDomain, self.path,
                                  self.server.base_dir,
                                  self.server.http_prefix,
                                  self.server.domain,
                                  self.server.port,
                                  self.server.proxy_type,
                                  GETstartTime,
                                  self.server.debug)
            return

        # RSS 2.0
        if self.path.startswith('/blog/') and \
           self.path.endswith('/rss.xml'):
            if not self.path == '/blog/rss.xml':
                self._getRSS2feed(authorized,
                                  callingDomain, self.path,
                                  self.server.base_dir,
                                  self.server.http_prefix,
                                  self.server.domain,
                                  self.server.port,
                                  self.server.proxy_type,
                                  GETstartTime,
                                  self.server.debug)
            else:
                self._getRSS2site(authorized,
                                  callingDomain, self.path,
                                  self.server.base_dir,
                                  self.server.http_prefix,
                                  self.server.domainFull,
                                  self.server.port,
                                  self.server.proxy_type,
                                  self.server.translate,
                                  GETstartTime,
                                  self.server.debug)
            return

        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', 'rss2 done',
                           self.server.debug)

        # RSS 3.0
        if self.path.startswith('/blog/') and \
           self.path.endswith('/rss.txt'):
            self._getRSS3feed(authorized,
                              callingDomain, self.path,
                              self.server.base_dir,
                              self.server.http_prefix,
                              self.server.domain,
                              self.server.port,
                              self.server.proxy_type,
                              GETstartTime,
                              self.server.debug,
                              self.server.systemLanguage)
            return

        usersInPath = False
        if '/users/' in self.path:
            usersInPath = True

        if authorized and not htmlGET and usersInPath:
            if '/following?page=' in self.path:
                self._getFollowingJson(self.server.base_dir,
                                       self.path,
                                       callingDomain,
                                       self.server.http_prefix,
                                       self.server.domain,
                                       self.server.port,
                                       self.server.followingItemsPerPage,
                                       self.server.debug, 'following')
                return
            elif '/followers?page=' in self.path:
                self._getFollowingJson(self.server.base_dir,
                                       self.path,
                                       callingDomain,
                                       self.server.http_prefix,
                                       self.server.domain,
                                       self.server.port,
                                       self.server.followingItemsPerPage,
                                       self.server.debug, 'followers')
                return
            elif '/followrequests?page=' in self.path:
                self._getFollowingJson(self.server.base_dir,
                                       self.path,
                                       callingDomain,
                                       self.server.http_prefix,
                                       self.server.domain,
                                       self.server.port,
                                       self.server.followingItemsPerPage,
                                       self.server.debug,
                                       'followrequests')
                return

        # authorized endpoint used for TTS of posts
        # arriving in your inbox
        if authorized and usersInPath and \
           self.path.endswith('/speaker'):
            if 'application/ssml' not in self.headers['Accept']:
                # json endpoint
                self._getSpeaker(callingDomain, self.path,
                                 self.server.base_dir,
                                 self.server.domain,
                                 self.server.debug)
            else:
                xmlStr = \
                    getSSMLbox(self.server.base_dir,
                               self.path, self.server.domain,
                               self.server.systemLanguage,
                               self.server.instanceTitle,
                               'inbox')
                if xmlStr:
                    msg = xmlStr.encode('utf-8')
                    msglen = len(msg)
                    self._set_headers('application/xrd+xml', msglen,
                                      None, callingDomain, False)
                    self._write(msg)
            return

        # redirect to the welcome screen
        if htmlGET and authorized and usersInPath and \
           '/welcome' not in self.path:
            nickname = self.path.split('/users/')[1]
            if '/' in nickname:
                nickname = nickname.split('/')[0]
            if '?' in nickname:
                nickname = nickname.split('?')[0]
            if nickname == self.authorizedNickname and \
               self.path != '/users/' + nickname:
                if not isWelcomeScreenComplete(self.server.base_dir,
                                               nickname,
                                               self.server.domain):
                    self._redirect_headers('/users/' + nickname + '/welcome',
                                           cookie, callingDomain)
                    return

        if not htmlGET and \
           usersInPath and self.path.endswith('/pinned'):
            nickname = self.path.split('/users/')[1]
            if '/' in nickname:
                nickname = nickname.split('/')[0]
            pinnedPostJson = \
                getPinnedPostAsJson(self.server.base_dir,
                                    self.server.http_prefix,
                                    nickname, self.server.domain,
                                    self.server.domainFull,
                                    self.server.systemLanguage)
            messageJson = {}
            if pinnedPostJson:
                postId = removeIdEnding(pinnedPostJson['id'])
                messageJson = \
                    outboxMessageCreateWrap(self.server.http_prefix,
                                            nickname,
                                            self.server.domain,
                                            self.server.port,
                                            pinnedPostJson)
                messageJson['id'] = postId + '/activity'
                messageJson['object']['id'] = postId
                messageJson['object']['url'] = replaceUsersWithAt(postId)
                messageJson['object']['atomUri'] = postId
            msg = json.dumps(messageJson,
                             ensure_ascii=False).encode('utf-8')
            msglen = len(msg)
            self._set_headers('application/json',
                              msglen, None, callingDomain, False)
            self._write(msg)
            return

        if not htmlGET and \
           usersInPath and self.path.endswith('/collections/featured'):
            nickname = self.path.split('/users/')[1]
            if '/' in nickname:
                nickname = nickname.split('/')[0]
            # return the featured posts collection
            self._getFeaturedCollection(callingDomain,
                                        self.server.base_dir,
                                        self.path,
                                        self.server.http_prefix,
                                        nickname, self.server.domain,
                                        self.server.domainFull,
                                        self.server.systemLanguage)
            return

        if not htmlGET and \
           usersInPath and self.path.endswith('/collections/featuredTags'):
            self._getFeaturedTagsCollection(callingDomain,
                                            self.path,
                                            self.server.http_prefix,
                                            self.server.domainFull)
            return

        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', '_getFeaturedTagsCollection done',
                           self.server.debug)

        # show a performance graph
        if authorized and '/performance?graph=' in self.path:
            graph = self.path.split('?graph=')[1]
            if htmlGET and not graph.endswith('.json'):
                if graph == 'post':
                    graph = '_POST'
                elif graph == 'get':
                    graph = '_GET'
                msg = \
                    htmlWatchPointsGraph(self.server.base_dir,
                                         self.server.fitness,
                                         graph, 16).encode('utf-8')
                msglen = len(msg)
                self._set_headers('text/html', msglen,
                                  cookie, callingDomain, False)
                self._write(msg)
                fitnessPerformance(GETstartTime, self.server.fitness,
                                   '_GET', 'graph',
                                   self.server.debug)
                return
            else:
                graph = graph.replace('.json', '')
                if graph == 'post':
                    graph = '_POST'
                elif graph == 'get':
                    graph = '_GET'
                watchPointsJson = sortedWatchPoints(self.server.fitness, graph)
                msg = json.dumps(watchPointsJson,
                                 ensure_ascii=False).encode('utf-8')
                msglen = len(msg)
                self._set_headers('application/json', msglen,
                                  None, callingDomain, False)
                self._write(msg)
                fitnessPerformance(GETstartTime, self.server.fitness,
                                   '_GET', 'graph json',
                                   self.server.debug)
                return

        # show the main blog page
        if htmlGET and (self.path == '/blog' or
                        self.path == '/blog/' or
                        self.path == '/blogs' or
                        self.path == '/blogs/'):
            if '/rss.xml' not in self.path:
                if not self._establishSession("show the main blog page"):
                    self._404()
                    return
                msg = htmlBlogView(authorized,
                                   self.server.session,
                                   self.server.base_dir,
                                   self.server.http_prefix,
                                   self.server.translate,
                                   self.server.domain,
                                   self.server.port,
                                   maxPostsInBlogsFeed,
                                   self.server.peertubeInstances,
                                   self.server.systemLanguage,
                                   self.server.personCache,
                                   self.server.debug)
                if msg is not None:
                    msg = msg.encode('utf-8')
                    msglen = len(msg)
                    self._set_headers('text/html', msglen,
                                      cookie, callingDomain, False)
                    self._write(msg)
                    fitnessPerformance(GETstartTime, self.server.fitness,
                                       '_GET', 'blog view',
                                       self.server.debug)
                    return
                self._404()
                return

        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', 'blog view done',
                           self.server.debug)

        # show a particular page of blog entries
        # for a particular account
        if htmlGET and self.path.startswith('/blog/'):
            if '/rss.xml' not in self.path:
                if self._showBlogPage(authorized,
                                      callingDomain, self.path,
                                      self.server.base_dir,
                                      self.server.http_prefix,
                                      self.server.domain,
                                      self.server.domainFull,
                                      self.server.port,
                                      self.server.onion_domain,
                                      self.server.i2p_domain,
                                      GETstartTime,
                                      self.server.proxy_type,
                                      cookie, self.server.translate,
                                      self.server.debug):
                    return

        # list of registered devices for e2ee
        # see https://github.com/tootsuite/mastodon/pull/13820
        if authorized and usersInPath:
            if self.path.endswith('/collections/devices'):
                nickname = self.path.split('/users/')
                if '/' in nickname:
                    nickname = nickname.split('/')[0]
                devJson = E2EEdevicesCollection(self.server.base_dir,
                                                nickname,
                                                self.server.domain,
                                                self.server.domainFull,
                                                self.server.http_prefix)
                msg = json.dumps(devJson,
                                 ensure_ascii=False).encode('utf-8')
                msglen = len(msg)
                self._set_headers('application/json',
                                  msglen,
                                  None, callingDomain, False)
                self._write(msg)
                fitnessPerformance(GETstartTime, self.server.fitness,
                                   '_GET', 'registered devices',
                                   self.server.debug)
                return

        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', 'registered devices done',
                           self.server.debug)

        if htmlGET and usersInPath:
            # show the person options screen with view/follow/block/report
            if '?options=' in self.path:
                self._showPersonOptions(callingDomain, self.path,
                                        self.server.base_dir,
                                        self.server.http_prefix,
                                        self.server.domain,
                                        self.server.domainFull,
                                        GETstartTime,
                                        self.server.onion_domain,
                                        self.server.i2p_domain,
                                        cookie, self.server.debug,
                                        authorized)
                return

            fitnessPerformance(GETstartTime, self.server.fitness,
                               '_GET', 'person options done',
                               self.server.debug)
            # show blog post
            blogFilename, nickname = \
                pathContainsBlogLink(self.server.base_dir,
                                     self.server.http_prefix,
                                     self.server.domain,
                                     self.server.domainFull,
                                     self.path)
            if blogFilename and nickname:
                postJsonObject = loadJson(blogFilename)
                if isBlogPost(postJsonObject):
                    msg = htmlBlogPost(self.server.session,
                                       authorized,
                                       self.server.base_dir,
                                       self.server.http_prefix,
                                       self.server.translate,
                                       nickname, self.server.domain,
                                       self.server.domainFull,
                                       postJsonObject,
                                       self.server.peertubeInstances,
                                       self.server.systemLanguage,
                                       self.server.personCache,
                                       self.server.debug,
                                       self.server.content_license_url)
                    if msg is not None:
                        msg = msg.encode('utf-8')
                        msglen = len(msg)
                        self._set_headers('text/html', msglen,
                                          cookie, callingDomain, False)
                        self._write(msg)
                        fitnessPerformance(GETstartTime, self.server.fitness,
                                           '_GET', 'blog post 2',
                                           self.server.debug)
                        return
                    self._404()
                    return

        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', 'blog post 2 done',
                           self.server.debug)

        # after selecting a shared item from the left column then show it
        if htmlGET and '?showshare=' in self.path and '/users/' in self.path:
            itemID = self.path.split('?showshare=')[1]
            if '?' in itemID:
                itemID = itemID.split('?')[0]
            category = ''
            if '?category=' in self.path:
                category = self.path.split('?category=')[1]
            if '?' in category:
                category = category.split('?')[0]
            usersPath = self.path.split('?showshare=')[0]
            nickname = usersPath.replace('/users/', '')
            itemID = urllib.parse.unquote_plus(itemID.strip())
            msg = \
                htmlShowShare(self.server.base_dir,
                              self.server.domain, nickname,
                              self.server.http_prefix, self.server.domainFull,
                              itemID, self.server.translate,
                              self.server.shared_items_federated_domains,
                              self.server.defaultTimeline,
                              self.server.themeName, 'shares', category)
            if not msg:
                if callingDomain.endswith('.onion') and \
                   self.server.onion_domain:
                    actor = 'http://' + self.server.onion_domain + usersPath
                elif (callingDomain.endswith('.i2p') and
                      self.server.i2p_domain):
                    actor = 'http://' + self.server.i2p_domain + usersPath
                self._redirect_headers(actor + '/tlshares',
                                       cookie, callingDomain)
                return
            msg = msg.encode('utf-8')
            msglen = len(msg)
            self._set_headers('text/html', msglen,
                              cookie, callingDomain, False)
            self._write(msg)
            fitnessPerformance(GETstartTime, self.server.fitness,
                               '_GET', 'htmlShowShare',
                               self.server.debug)
            return

        # after selecting a wanted item from the left column then show it
        if htmlGET and '?showwanted=' in self.path and '/users/' in self.path:
            itemID = self.path.split('?showwanted=')[1]
            if ';' in itemID:
                itemID = itemID.split(';')[0]
            category = self.path.split('?category=')[1]
            if ';' in category:
                category = category.split(';')[0]
            usersPath = self.path.split('?showwanted=')[0]
            nickname = usersPath.replace('/users/', '')
            itemID = urllib.parse.unquote_plus(itemID.strip())
            msg = \
                htmlShowShare(self.server.base_dir,
                              self.server.domain, nickname,
                              self.server.http_prefix, self.server.domainFull,
                              itemID, self.server.translate,
                              self.server.shared_items_federated_domains,
                              self.server.defaultTimeline,
                              self.server.themeName, 'wanted', category)
            if not msg:
                if callingDomain.endswith('.onion') and \
                   self.server.onion_domain:
                    actor = 'http://' + self.server.onion_domain + usersPath
                elif (callingDomain.endswith('.i2p') and
                      self.server.i2p_domain):
                    actor = 'http://' + self.server.i2p_domain + usersPath
                self._redirect_headers(actor + '/tlwanted',
                                       cookie, callingDomain)
                return
            msg = msg.encode('utf-8')
            msglen = len(msg)
            self._set_headers('text/html', msglen,
                              cookie, callingDomain, False)
            self._write(msg)
            fitnessPerformance(GETstartTime, self.server.fitness,
                               '_GET', 'htmlShowWanted',
                               self.server.debug)
            return

        # remove a shared item
        if htmlGET and '?rmshare=' in self.path:
            itemID = self.path.split('?rmshare=')[1]
            itemID = urllib.parse.unquote_plus(itemID.strip())
            usersPath = self.path.split('?rmshare=')[0]
            actor = \
                self.server.http_prefix + '://' + \
                self.server.domainFull + usersPath
            msg = htmlConfirmRemoveSharedItem(self.server.cssCache,
                                              self.server.translate,
                                              self.server.base_dir,
                                              actor, itemID,
                                              callingDomain, 'shares')
            if not msg:
                if callingDomain.endswith('.onion') and \
                   self.server.onion_domain:
                    actor = 'http://' + self.server.onion_domain + usersPath
                elif (callingDomain.endswith('.i2p') and
                      self.server.i2p_domain):
                    actor = 'http://' + self.server.i2p_domain + usersPath
                self._redirect_headers(actor + '/tlshares',
                                       cookie, callingDomain)
                return
            msg = msg.encode('utf-8')
            msglen = len(msg)
            self._set_headers('text/html', msglen,
                              cookie, callingDomain, False)
            self._write(msg)
            fitnessPerformance(GETstartTime, self.server.fitness,
                               '_GET', 'remove shared item',
                               self.server.debug)
            return

        # remove a wanted item
        if htmlGET and '?rmwanted=' in self.path:
            itemID = self.path.split('?rmwanted=')[1]
            itemID = urllib.parse.unquote_plus(itemID.strip())
            usersPath = self.path.split('?rmwanted=')[0]
            actor = \
                self.server.http_prefix + '://' + \
                self.server.domainFull + usersPath
            msg = htmlConfirmRemoveSharedItem(self.server.cssCache,
                                              self.server.translate,
                                              self.server.base_dir,
                                              actor, itemID,
                                              callingDomain, 'wanted')
            if not msg:
                if callingDomain.endswith('.onion') and \
                   self.server.onion_domain:
                    actor = 'http://' + self.server.onion_domain + usersPath
                elif (callingDomain.endswith('.i2p') and
                      self.server.i2p_domain):
                    actor = 'http://' + self.server.i2p_domain + usersPath
                self._redirect_headers(actor + '/tlwanted',
                                       cookie, callingDomain)
                return
            msg = msg.encode('utf-8')
            msglen = len(msg)
            self._set_headers('text/html', msglen,
                              cookie, callingDomain, False)
            self._write(msg)
            fitnessPerformance(GETstartTime, self.server.fitness,
                               '_GET', 'remove shared item',
                               self.server.debug)
            return

        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', 'remove shared item done',
                           self.server.debug)

        if self.path.startswith('/terms'):
            if callingDomain.endswith('.onion') and \
               self.server.onion_domain:
                msg = htmlTermsOfService(self.server.cssCache,
                                         self.server.base_dir, 'http',
                                         self.server.onion_domain)
            elif (callingDomain.endswith('.i2p') and
                  self.server.i2p_domain):
                msg = htmlTermsOfService(self.server.cssCache,
                                         self.server.base_dir, 'http',
                                         self.server.i2p_domain)
            else:
                msg = htmlTermsOfService(self.server.cssCache,
                                         self.server.base_dir,
                                         self.server.http_prefix,
                                         self.server.domainFull)
            msg = msg.encode('utf-8')
            msglen = len(msg)
            self._login_headers('text/html', msglen, callingDomain)
            self._write(msg)
            fitnessPerformance(GETstartTime, self.server.fitness,
                               '_GET', 'terms of service shown',
                               self.server.debug)
            return

        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', 'terms of service done',
                           self.server.debug)

        # show a list of who you are following
        if htmlGET and authorized and usersInPath and \
           self.path.endswith('/followingaccounts'):
            nickname = getNicknameFromActor(self.path)
            followingFilename = \
                acctDir(self.server.base_dir,
                        nickname, self.server.domain) + '/following.txt'
            if not os.path.isfile(followingFilename):
                self._404()
                return
            msg = htmlFollowingList(self.server.cssCache,
                                    self.server.base_dir, followingFilename)
            msglen = len(msg)
            self._login_headers('text/html', msglen, callingDomain)
            self._write(msg.encode('utf-8'))
            fitnessPerformance(GETstartTime, self.server.fitness,
                               '_GET', 'following accounts shown',
                               self.server.debug)
            return

        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', 'following accounts done',
                           self.server.debug)

        if self.path.endswith('/about'):
            if callingDomain.endswith('.onion'):
                msg = \
                    htmlAbout(self.server.cssCache,
                              self.server.base_dir, 'http',
                              self.server.onion_domain,
                              None, self.server.translate,
                              self.server.systemLanguage)
            elif callingDomain.endswith('.i2p'):
                msg = \
                    htmlAbout(self.server.cssCache,
                              self.server.base_dir, 'http',
                              self.server.i2p_domain,
                              None, self.server.translate,
                              self.server.systemLanguage)
            else:
                msg = \
                    htmlAbout(self.server.cssCache,
                              self.server.base_dir,
                              self.server.http_prefix,
                              self.server.domainFull,
                              self.server.onion_domain,
                              self.server.translate,
                              self.server.systemLanguage)
            msg = msg.encode('utf-8')
            msglen = len(msg)
            self._login_headers('text/html', msglen, callingDomain)
            self._write(msg)
            fitnessPerformance(GETstartTime, self.server.fitness,
                               '_GET', 'show about screen',
                               self.server.debug)
            return

        if htmlGET and usersInPath and authorized and \
           self.path.endswith('/accesskeys'):
            nickname = self.path.split('/users/')[1]
            if '/' in nickname:
                nickname = nickname.split('/')[0]

            accessKeys = self.server.accessKeys
            if self.server.keyShortcuts.get(nickname):
                accessKeys = \
                    self.server.keyShortcuts[nickname]

            msg = \
                htmlAccessKeys(self.server.cssCache,
                               self.server.base_dir,
                               nickname, self.server.domain,
                               self.server.translate,
                               accessKeys,
                               self.server.accessKeys,
                               self.server.defaultTimeline)
            msg = msg.encode('utf-8')
            msglen = len(msg)
            self._login_headers('text/html', msglen, callingDomain)
            self._write(msg)
            fitnessPerformance(GETstartTime, self.server.fitness,
                               '_GET', 'show accesskeys screen',
                               self.server.debug)
            return

        if htmlGET and usersInPath and authorized and \
           self.path.endswith('/themedesigner'):
            nickname = self.path.split('/users/')[1]
            if '/' in nickname:
                nickname = nickname.split('/')[0]

            if not isArtist(self.server.base_dir, nickname):
                self._403()
                return

            msg = \
                htmlThemeDesigner(self.server.cssCache,
                                  self.server.base_dir,
                                  nickname, self.server.domain,
                                  self.server.translate,
                                  self.server.defaultTimeline,
                                  self.server.themeName,
                                  self.server.accessKeys)
            msg = msg.encode('utf-8')
            msglen = len(msg)
            self._login_headers('text/html', msglen, callingDomain)
            self._write(msg)
            fitnessPerformance(GETstartTime, self.server.fitness,
                               '_GET', 'show theme designer screen',
                               self.server.debug)
            return

        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', 'show about screen done',
                           self.server.debug)

        # the initial welcome screen after first logging in
        if htmlGET and authorized and \
           '/users/' in self.path and self.path.endswith('/welcome'):
            nickname = self.path.split('/users/')[1]
            if '/' in nickname:
                nickname = nickname.split('/')[0]
            if not isWelcomeScreenComplete(self.server.base_dir,
                                           nickname,
                                           self.server.domain):
                msg = \
                    htmlWelcomeScreen(self.server.base_dir, nickname,
                                      self.server.systemLanguage,
                                      self.server.translate,
                                      self.server.themeName)
                msg = msg.encode('utf-8')
                msglen = len(msg)
                self._login_headers('text/html', msglen, callingDomain)
                self._write(msg)
                fitnessPerformance(GETstartTime, self.server.fitness,
                                   '_GET', 'show welcome screen',
                                   self.server.debug)
                return
            else:
                self.path = self.path.replace('/welcome', '')

        # the welcome screen which allows you to set an avatar image
        if htmlGET and authorized and \
           '/users/' in self.path and self.path.endswith('/welcome_profile'):
            nickname = self.path.split('/users/')[1]
            if '/' in nickname:
                nickname = nickname.split('/')[0]
            if not isWelcomeScreenComplete(self.server.base_dir,
                                           nickname,
                                           self.server.domain):
                msg = \
                    htmlWelcomeProfile(self.server.base_dir, nickname,
                                       self.server.domain,
                                       self.server.http_prefix,
                                       self.server.domainFull,
                                       self.server.systemLanguage,
                                       self.server.translate,
                                       self.server.themeName)
                msg = msg.encode('utf-8')
                msglen = len(msg)
                self._login_headers('text/html', msglen, callingDomain)
                self._write(msg)
                fitnessPerformance(GETstartTime, self.server.fitness,
                                   '_GET', 'show welcome profile screen',
                                   self.server.debug)
                return
            else:
                self.path = self.path.replace('/welcome_profile', '')

        # the final welcome screen
        if htmlGET and authorized and \
           '/users/' in self.path and self.path.endswith('/welcome_final'):
            nickname = self.path.split('/users/')[1]
            if '/' in nickname:
                nickname = nickname.split('/')[0]
            if not isWelcomeScreenComplete(self.server.base_dir,
                                           nickname,
                                           self.server.domain):
                msg = \
                    htmlWelcomeFinal(self.server.base_dir, nickname,
                                     self.server.domain,
                                     self.server.http_prefix,
                                     self.server.domainFull,
                                     self.server.systemLanguage,
                                     self.server.translate,
                                     self.server.themeName)
                msg = msg.encode('utf-8')
                msglen = len(msg)
                self._login_headers('text/html', msglen, callingDomain)
                self._write(msg)
                fitnessPerformance(GETstartTime, self.server.fitness,
                                   '_GET', 'show welcome final screen',
                                   self.server.debug)
                return
            else:
                self.path = self.path.replace('/welcome_final', '')

        # if not authorized then show the login screen
        if htmlGET and self.path != '/login' and \
           not isImageFile(self.path) and \
           self.path != '/' and \
           self.path != '/users/news/linksmobile' and \
           self.path != '/users/news/newswiremobile':
            if self._redirectToLoginScreen(callingDomain, self.path,
                                           self.server.http_prefix,
                                           self.server.domainFull,
                                           self.server.onion_domain,
                                           self.server.i2p_domain,
                                           GETstartTime,
                                           authorized, self.server.debug):
                return

        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', 'show login screen done',
                           self.server.debug)

        # manifest images used to create a home screen icon
        # when selecting "add to home screen" in browsers
        # which support progressive web apps
        if self.path == '/logo72.png' or \
           self.path == '/logo96.png' or \
           self.path == '/logo128.png' or \
           self.path == '/logo144.png' or \
           self.path == '/logo150.png' or \
           self.path == '/logo192.png' or \
           self.path == '/logo256.png' or \
           self.path == '/logo512.png' or \
           self.path == '/apple-touch-icon.png':
            mediaFilename = \
                self.server.base_dir + '/img' + self.path
            if os.path.isfile(mediaFilename):
                if self._etag_exists(mediaFilename):
                    # The file has not changed
                    self._304()
                    return

                tries = 0
                mediaBinary = None
                while tries < 5:
                    try:
                        with open(mediaFilename, 'rb') as avFile:
                            mediaBinary = avFile.read()
                            break
                    except Exception as ex:
                        print('ERROR: manifest logo ' +
                              str(tries) + ' ' + str(ex))
                        time.sleep(1)
                        tries += 1
                if mediaBinary:
                    mimeType = mediaFileMimeType(mediaFilename)
                    self._set_headers_etag(mediaFilename, mimeType,
                                           mediaBinary, cookie,
                                           self.server.domainFull,
                                           False, None)
                    self._write(mediaBinary)
                    fitnessPerformance(GETstartTime, self.server.fitness,
                                       '_GET', 'manifest logo shown',
                                       self.server.debug)
                    return
            self._404()
            return

        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', 'manifest logo done',
                           self.server.debug)

        # manifest images used to show example screenshots
        # for use by app stores
        if self.path == '/screenshot1.jpg' or \
           self.path == '/screenshot2.jpg':
            screenFilename = \
                self.server.base_dir + '/img' + self.path
            if os.path.isfile(screenFilename):
                if self._etag_exists(screenFilename):
                    # The file has not changed
                    self._304()
                    return

                tries = 0
                mediaBinary = None
                while tries < 5:
                    try:
                        with open(screenFilename, 'rb') as avFile:
                            mediaBinary = avFile.read()
                            break
                    except Exception as ex:
                        print('ERROR: manifest screenshot ' +
                              str(tries) + ' ' + str(ex))
                        time.sleep(1)
                        tries += 1
                if mediaBinary:
                    mimeType = mediaFileMimeType(screenFilename)
                    self._set_headers_etag(screenFilename, mimeType,
                                           mediaBinary, cookie,
                                           self.server.domainFull,
                                           False, None)
                    self._write(mediaBinary)
                    fitnessPerformance(GETstartTime, self.server.fitness,
                                       '_GET', 'show screenshot',
                                       self.server.debug)
                    return
            self._404()
            return

        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', 'show screenshot done',
                           self.server.debug)

        # image on login screen or qrcode
        if (isImageFile(self.path) and
            (self.path.startswith('/login.') or
             self.path.startswith('/qrcode.png'))):
            iconFilename = \
                self.server.base_dir + '/accounts' + self.path
            if os.path.isfile(iconFilename):
                if self._etag_exists(iconFilename):
                    # The file has not changed
                    self._304()
                    return

                tries = 0
                mediaBinary = None
                while tries < 5:
                    try:
                        with open(iconFilename, 'rb') as avFile:
                            mediaBinary = avFile.read()
                            break
                    except Exception as ex:
                        print('ERROR: login screen image ' +
                              str(tries) + ' ' + str(ex))
                        time.sleep(1)
                        tries += 1
                if mediaBinary:
                    mimeTypeStr = mediaFileMimeType(iconFilename)
                    self._set_headers_etag(iconFilename,
                                           mimeTypeStr,
                                           mediaBinary, cookie,
                                           self.server.domainFull,
                                           False, None)
                    self._write(mediaBinary)
                    fitnessPerformance(GETstartTime, self.server.fitness,
                                       '_GET', 'login screen logo',
                                       self.server.debug)
                    return
            self._404()
            return

        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', 'login screen logo done',
                           self.server.debug)

        # QR code for account handle
        if usersInPath and \
           self.path.endswith('/qrcode.png'):
            if self._showQRcode(callingDomain, self.path,
                                self.server.base_dir,
                                self.server.domain,
                                self.server.port,
                                GETstartTime):
                return

        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', 'account qrcode done',
                           self.server.debug)

        # search screen banner image
        if usersInPath:
            if self.path.endswith('/search_banner.png'):
                if self._searchScreenBanner(callingDomain, self.path,
                                            self.server.base_dir,
                                            self.server.domain,
                                            self.server.port,
                                            GETstartTime):
                    return

            if self.path.endswith('/left_col_image.png'):
                if self._columnImage('left', callingDomain, self.path,
                                     self.server.base_dir,
                                     self.server.domain,
                                     self.server.port,
                                     GETstartTime):
                    return

            if self.path.endswith('/right_col_image.png'):
                if self._columnImage('right', callingDomain, self.path,
                                     self.server.base_dir,
                                     self.server.domain,
                                     self.server.port,
                                     GETstartTime):
                    return

        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', 'search screen banner done',
                           self.server.debug)

        if self.path.startswith('/defaultprofilebackground'):
            self._showDefaultProfileBackground(callingDomain, self.path,
                                               self.server.base_dir,
                                               self.server.themeName,
                                               GETstartTime)
            return

        # show a background image on the login or person options page
        if '-background.' in self.path:
            if self._showBackgroundImage(callingDomain, self.path,
                                         self.server.base_dir,
                                         GETstartTime):
                return

        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', 'background shown done',
                           self.server.debug)

        # emoji images
        if '/emoji/' in self.path:
            self._showEmoji(callingDomain, self.path,
                            self.server.base_dir,
                            GETstartTime)
            return

        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', 'show emoji done',
                           self.server.debug)

        # show media
        # Note that this comes before the busy flag to avoid conflicts
        # replace mastoson-style media path
        if '/system/media_attachments/files/' in self.path:
            self.path = self.path.replace('/system/media_attachments/files/',
                                          '/media/')
        if '/media/' in self.path:
            self._showMedia(callingDomain,
                            self.path, self.server.base_dir,
                            GETstartTime)
            return

        if '/ontologies/' in self.path or \
           '/data/' in self.path:
            if not hasUsersPath(self.path):
                self._getOntology(callingDomain,
                                  self.path, self.server.base_dir,
                                  GETstartTime)
                return

        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', 'show media done',
                           self.server.debug)

        # show shared item images
        # Note that this comes before the busy flag to avoid conflicts
        if '/sharefiles/' in self.path:
            if self._showShareImage(callingDomain, self.path,
                                    self.server.base_dir,
                                    GETstartTime):
                return

        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', 'share image done',
                           self.server.debug)

        # icon images
        # Note that this comes before the busy flag to avoid conflicts
        if self.path.startswith('/icons/'):
            self._showIcon(callingDomain, self.path,
                           self.server.base_dir, GETstartTime)
            return

        # help screen images
        # Note that this comes before the busy flag to avoid conflicts
        if self.path.startswith('/helpimages/'):
            self._showHelpScreenImage(callingDomain, self.path,
                                      self.server.base_dir, GETstartTime)
            return

        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', 'help screen image done',
                           self.server.debug)

        # cached avatar images
        # Note that this comes before the busy flag to avoid conflicts
        if self.path.startswith('/avatars/'):
            self._showCachedAvatar(refererDomain, self.path,
                                   self.server.base_dir,
                                   GETstartTime)
            return

        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', 'cached avatar done',
                           self.server.debug)

        # show avatar or background image
        # Note that this comes before the busy flag to avoid conflicts
        if self._showAvatarOrBanner(refererDomain, self.path,
                                    self.server.base_dir,
                                    self.server.domain,
                                    GETstartTime):
            return

        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', 'avatar or banner shown done',
                           self.server.debug)

        # This busy state helps to avoid flooding
        # Resources which are expected to be called from a web page
        # should be above this
        currTimeGET = int(time.time() * 1000)
        if self.server.GETbusy:
            if currTimeGET - self.server.lastGET < 500:
                if self.server.debug:
                    print('DEBUG: GET Busy')
                self.send_response(429)
                self.end_headers()
                return
        self.server.GETbusy = True
        self.server.lastGET = currTimeGET

        # returns after this point should set GETbusy to False

        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', 'GET busy time',
                           self.server.debug)

        if not permittedDir(self.path):
            if self.server.debug:
                print('DEBUG: GET Not permitted')
            self._404()
            self.server.GETbusy = False
            return

        # get webfinger endpoint for a person
        if self._webfinger(callingDomain):
            fitnessPerformance(GETstartTime, self.server.fitness,
                               '_GET', 'webfinger called',
                               self.server.debug)
            self.server.GETbusy = False
            return

        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', 'permitted directory',
                           self.server.debug)

        # show the login screen
        if (self.path.startswith('/login') or
            (self.path == '/' and
             not authorized and
             not self.server.news_instance)):
            # request basic auth
            msg = htmlLogin(self.server.cssCache,
                            self.server.translate,
                            self.server.base_dir,
                            self.server.http_prefix,
                            self.server.domainFull,
                            self.server.systemLanguage,
                            True).encode('utf-8')
            msglen = len(msg)
            self._login_headers('text/html', msglen, callingDomain)
            self._write(msg)
            fitnessPerformance(GETstartTime, self.server.fitness,
                               '_GET', 'login shown',
                               self.server.debug)
            self.server.GETbusy = False
            return

        # show the news front page
        if self.path == '/' and \
           not authorized and \
           self.server.news_instance:
            if callingDomain.endswith('.onion') and \
               self.server.onion_domain:
                self._logout_redirect('http://' +
                                      self.server.onion_domain +
                                      '/users/news', None,
                                      callingDomain)
            elif (callingDomain.endswith('.i2p') and
                  self.server.i2p_domain):
                self._logout_redirect('http://' +
                                      self.server.i2p_domain +
                                      '/users/news', None,
                                      callingDomain)
            else:
                self._logout_redirect(self.server.http_prefix +
                                      '://' +
                                      self.server.domainFull +
                                      '/users/news',
                                      None, callingDomain)
            fitnessPerformance(GETstartTime, self.server.fitness,
                               '_GET', 'news front page shown',
                               self.server.debug)
            self.server.GETbusy = False
            return

        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', 'login shown done',
                           self.server.debug)

        # the newswire screen on mobile
        if htmlGET and self.path.startswith('/users/') and \
           self.path.endswith('/newswiremobile'):
            if (authorized or
                (not authorized and
                 self.path.startswith('/users/news/') and
                 self.server.news_instance)):
                nickname = getNicknameFromActor(self.path)
                if not nickname:
                    self._404()
                    self.server.GETbusy = False
                    return
                timelinePath = \
                    '/users/' + nickname + '/' + self.server.defaultTimeline
                show_publish_as_icon = self.server.show_publish_as_icon
                rss_icon_at_top = self.server.rss_icon_at_top
                icons_as_buttons = self.server.icons_as_buttons
                defaultTimeline = self.server.defaultTimeline
                accessKeys = self.server.accessKeys
                if self.server.keyShortcuts.get(nickname):
                    accessKeys = self.server.keyShortcuts[nickname]
                msg = htmlNewswireMobile(self.server.cssCache,
                                         self.server.base_dir,
                                         nickname,
                                         self.server.domain,
                                         self.server.domainFull,
                                         self.server.http_prefix,
                                         self.server.translate,
                                         self.server.newswire,
                                         self.server.positive_voting,
                                         timelinePath,
                                         show_publish_as_icon,
                                         authorized,
                                         rss_icon_at_top,
                                         icons_as_buttons,
                                         defaultTimeline,
                                         self.server.themeName,
                                         accessKeys).encode('utf-8')
                msglen = len(msg)
                self._set_headers('text/html', msglen,
                                  cookie, callingDomain, False)
                self._write(msg)
                self.server.GETbusy = False
                return

        if htmlGET and self.path.startswith('/users/') and \
           self.path.endswith('/linksmobile'):
            if (authorized or
                (not authorized and
                 self.path.startswith('/users/news/') and
                 self.server.news_instance)):
                nickname = getNicknameFromActor(self.path)
                if not nickname:
                    self._404()
                    self.server.GETbusy = False
                    return
                accessKeys = self.server.accessKeys
                if self.server.keyShortcuts.get(nickname):
                    accessKeys = self.server.keyShortcuts[nickname]
                timelinePath = \
                    '/users/' + nickname + '/' + self.server.defaultTimeline
                icons_as_buttons = self.server.icons_as_buttons
                defaultTimeline = self.server.defaultTimeline
                sharedItemsDomains = \
                    self.server.shared_items_federated_domains
                msg = htmlLinksMobile(self.server.cssCache,
                                      self.server.base_dir, nickname,
                                      self.server.domainFull,
                                      self.server.http_prefix,
                                      self.server.translate,
                                      timelinePath,
                                      authorized,
                                      self.server.rss_icon_at_top,
                                      icons_as_buttons,
                                      defaultTimeline,
                                      self.server.themeName,
                                      accessKeys,
                                      sharedItemsDomains).encode('utf-8')
                msglen = len(msg)
                self._set_headers('text/html', msglen, cookie, callingDomain,
                                  False)
                self._write(msg)
                self.server.GETbusy = False
                return

        # hashtag search
        if self.path.startswith('/tags/') or \
           (authorized and '/tags/' in self.path):
            if self.path.startswith('/tags/rss2/'):
                self._hashtagSearchRSS2(callingDomain,
                                        self.path, cookie,
                                        self.server.base_dir,
                                        self.server.http_prefix,
                                        self.server.domain,
                                        self.server.domainFull,
                                        self.server.port,
                                        self.server.onion_domain,
                                        self.server.i2p_domain,
                                        GETstartTime)
                self.server.GETbusy = False
                return
            self._hashtagSearch(callingDomain,
                                self.path, cookie,
                                self.server.base_dir,
                                self.server.http_prefix,
                                self.server.domain,
                                self.server.domainFull,
                                self.server.port,
                                self.server.onion_domain,
                                self.server.i2p_domain,
                                GETstartTime)
            self.server.GETbusy = False
            return

        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', 'hashtag search done',
                           self.server.debug)

        # show or hide buttons in the web interface
        if htmlGET and usersInPath and \
           self.path.endswith('/minimal') and \
           authorized:
            nickname = self.path.split('/users/')[1]
            if '/' in nickname:
                nickname = nickname.split('/')[0]
                notMin = not isMinimal(self.server.base_dir,
                                       self.server.domain, nickname)
                setMinimal(self.server.base_dir,
                           self.server.domain, nickname, notMin)
                if not (self.server.media_instance or
                        self.server.blogs_instance):
                    self.path = '/users/' + nickname + '/inbox'
                else:
                    if self.server.blogs_instance:
                        self.path = '/users/' + nickname + '/tlblogs'
                    elif self.server.media_instance:
                        self.path = '/users/' + nickname + '/tlmedia'
                    else:
                        self.path = '/users/' + nickname + '/tlfeatures'

        # search for a fediverse address, shared item or emoji
        # from the web interface by selecting search icon
        if htmlGET and usersInPath:
            if self.path.endswith('/search') or \
               '/search?' in self.path:
                if '?' in self.path:
                    self.path = self.path.split('?')[0]

                nickname = self.path.split('/users/')[1]
                if '/' in nickname:
                    nickname = nickname.split('/')[0]

                accessKeys = self.server.accessKeys
                if self.server.keyShortcuts.get(nickname):
                    accessKeys = self.server.keyShortcuts[nickname]

                # show the search screen
                msg = htmlSearch(self.server.cssCache,
                                 self.server.translate,
                                 self.server.base_dir, self.path,
                                 self.server.domain,
                                 self.server.defaultTimeline,
                                 self.server.themeName,
                                 self.server.textModeBanner,
                                 accessKeys).encode('utf-8')
                msglen = len(msg)
                self._set_headers('text/html', msglen, cookie, callingDomain,
                                  False)
                self._write(msg)
                fitnessPerformance(GETstartTime, self.server.fitness,
                                   '_GET', 'search screen shown',
                                   self.server.debug)
                self.server.GETbusy = False
                return

        # show a hashtag category from the search screen
        if htmlGET and '/category/' in self.path:
            msg = htmlSearchHashtagCategory(self.server.cssCache,
                                            self.server.translate,
                                            self.server.base_dir, self.path,
                                            self.server.domain,
                                            self.server.themeName)
            if msg:
                msg = msg.encode('utf-8')
                msglen = len(msg)
                self._set_headers('text/html', msglen, cookie, callingDomain,
                                  False)
                self._write(msg)
            fitnessPerformance(GETstartTime, self.server.fitness,
                               '_GET', 'hashtag category screen shown',
                               self.server.debug)
            self.server.GETbusy = False
            return

        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', 'search screen shown done',
                           self.server.debug)

        # Show the calendar for a user
        if htmlGET and usersInPath:
            if '/calendar' in self.path:
                nickname = self.path.split('/users/')[1]
                if '/' in nickname:
                    nickname = nickname.split('/')[0]

                accessKeys = self.server.accessKeys
                if self.server.keyShortcuts.get(nickname):
                    accessKeys = self.server.keyShortcuts[nickname]

                # show the calendar screen
                msg = htmlCalendar(self.server.personCache,
                                   self.server.cssCache,
                                   self.server.translate,
                                   self.server.base_dir, self.path,
                                   self.server.http_prefix,
                                   self.server.domainFull,
                                   self.server.textModeBanner,
                                   accessKeys).encode('utf-8')
                msglen = len(msg)
                self._set_headers('text/html', msglen, cookie, callingDomain,
                                  False)
                self._write(msg)
                fitnessPerformance(GETstartTime, self.server.fitness,
                                   '_GET', 'calendar shown',
                                   self.server.debug)
                self.server.GETbusy = False
                return

        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', 'calendar shown done',
                           self.server.debug)

        # Show confirmation for deleting a calendar event
        if htmlGET and usersInPath:
            if '/eventdelete' in self.path and \
               '?time=' in self.path and \
               '?eventid=' in self.path:
                if self._confirmDeleteEvent(callingDomain, self.path,
                                            self.server.base_dir,
                                            self.server.http_prefix,
                                            cookie,
                                            self.server.translate,
                                            self.server.domainFull,
                                            self.server.onion_domain,
                                            self.server.i2p_domain,
                                            GETstartTime):
                    self.server.GETbusy = False
                    return

        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', 'calendar delete shown done',
                           self.server.debug)

        # search for emoji by name
        if htmlGET and usersInPath:
            if self.path.endswith('/searchemoji'):
                # show the search screen
                msg = htmlSearchEmojiTextEntry(self.server.cssCache,
                                               self.server.translate,
                                               self.server.base_dir,
                                               self.path).encode('utf-8')
                msglen = len(msg)
                self._set_headers('text/html', msglen,
                                  cookie, callingDomain, False)
                self._write(msg)
                fitnessPerformance(GETstartTime, self.server.fitness,
                                   '_GET', 'emoji search shown',
                                   self.server.debug)
                self.server.GETbusy = False
                return

        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', 'emoji search shown done',
                           self.server.debug)

        repeatPrivate = False
        if htmlGET and '?repeatprivate=' in self.path:
            repeatPrivate = True
            self.path = self.path.replace('?repeatprivate=', '?repeat=')
        # announce/repeat button was pressed
        if authorized and htmlGET and '?repeat=' in self.path:
            self._announceButton(callingDomain, self.path,
                                 self.server.base_dir,
                                 cookie, self.server.proxy_type,
                                 self.server.http_prefix,
                                 self.server.domain,
                                 self.server.domainFull,
                                 self.server.port,
                                 self.server.onion_domain,
                                 self.server.i2p_domain,
                                 GETstartTime,
                                 repeatPrivate,
                                 self.server.debug)
            self.server.GETbusy = False
            return

        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', 'show announce done',
                           self.server.debug)

        if authorized and htmlGET and '?unrepeatprivate=' in self.path:
            self.path = self.path.replace('?unrepeatprivate=', '?unrepeat=')

        # undo an announce/repeat from the web interface
        if authorized and htmlGET and '?unrepeat=' in self.path:
            self._undoAnnounceButton(callingDomain, self.path,
                                     self.server.base_dir,
                                     cookie, self.server.proxy_type,
                                     self.server.http_prefix,
                                     self.server.domain,
                                     self.server.domainFull,
                                     self.server.port,
                                     self.server.onion_domain,
                                     self.server.i2p_domain,
                                     GETstartTime,
                                     repeatPrivate,
                                     self.server.debug,
                                     self.server.recentPostsCache)
            self.server.GETbusy = False
            return

        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', 'unannounce done',
                           self.server.debug)

        # send a newswire moderation vote from the web interface
        if authorized and '/newswirevote=' in self.path and \
           self.path.startswith('/users/'):
            self._newswireVote(callingDomain, self.path,
                               cookie,
                               self.server.base_dir,
                               self.server.http_prefix,
                               self.server.domain,
                               self.server.domainFull,
                               self.server.port,
                               self.server.onion_domain,
                               self.server.i2p_domain,
                               GETstartTime,
                               self.server.proxy_type,
                               self.server.debug,
                               self.server.newswire)
            self.server.GETbusy = False
            return

        # send a newswire moderation unvote from the web interface
        if authorized and '/newswireunvote=' in self.path and \
           self.path.startswith('/users/'):
            self._newswireUnvote(callingDomain, self.path,
                                 cookie,
                                 self.server.base_dir,
                                 self.server.http_prefix,
                                 self.server.domain,
                                 self.server.domainFull,
                                 self.server.port,
                                 self.server.onion_domain,
                                 self.server.i2p_domain,
                                 GETstartTime,
                                 self.server.proxy_type,
                                 self.server.debug,
                                 self.server.newswire)
            self.server.GETbusy = False
            return

        # send a follow request approval from the web interface
        if authorized and '/followapprove=' in self.path and \
           self.path.startswith('/users/'):
            self._followApproveButton(callingDomain, self.path,
                                      cookie,
                                      self.server.base_dir,
                                      self.server.http_prefix,
                                      self.server.domain,
                                      self.server.domainFull,
                                      self.server.port,
                                      self.server.onion_domain,
                                      self.server.i2p_domain,
                                      GETstartTime,
                                      self.server.proxy_type,
                                      self.server.debug)
            self.server.GETbusy = False
            return

        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', 'follow approve done',
                           self.server.debug)

        # deny a follow request from the web interface
        if authorized and '/followdeny=' in self.path and \
           self.path.startswith('/users/'):
            self._followDenyButton(callingDomain, self.path,
                                   cookie,
                                   self.server.base_dir,
                                   self.server.http_prefix,
                                   self.server.domain,
                                   self.server.domainFull,
                                   self.server.port,
                                   self.server.onion_domain,
                                   self.server.i2p_domain,
                                   GETstartTime,
                                   self.server.proxy_type,
                                   self.server.debug)
            self.server.GETbusy = False
            return

        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', 'follow deny done',
                           self.server.debug)

        # like from the web interface icon
        if authorized and htmlGET and '?like=' in self.path:
            self._likeButton(callingDomain, self.path,
                             self.server.base_dir,
                             self.server.http_prefix,
                             self.server.domain,
                             self.server.domainFull,
                             self.server.onion_domain,
                             self.server.i2p_domain,
                             GETstartTime,
                             self.server.proxy_type,
                             cookie,
                             self.server.debug)
            self.server.GETbusy = False
            return

        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', 'like button done',
                           self.server.debug)

        # undo a like from the web interface icon
        if authorized and htmlGET and '?unlike=' in self.path:
            self._undoLikeButton(callingDomain, self.path,
                                 self.server.base_dir,
                                 self.server.http_prefix,
                                 self.server.domain,
                                 self.server.domainFull,
                                 self.server.onion_domain,
                                 self.server.i2p_domain,
                                 GETstartTime,
                                 self.server.proxy_type,
                                 cookie, self.server.debug)
            self.server.GETbusy = False
            return

        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', 'unlike button done',
                           self.server.debug)

        # emoji reaction from the web interface icon
        if authorized and htmlGET and \
           '?react=' in self.path and \
           '?actor=' in self.path:
            self._reactionButton(callingDomain, self.path,
                                 self.server.base_dir,
                                 self.server.http_prefix,
                                 self.server.domain,
                                 self.server.domainFull,
                                 self.server.onion_domain,
                                 self.server.i2p_domain,
                                 GETstartTime,
                                 self.server.proxy_type,
                                 cookie,
                                 self.server.debug)
            self.server.GETbusy = False
            return

        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', 'emoji reaction button done',
                           self.server.debug)

        # undo an emoji reaction from the web interface icon
        if authorized and htmlGET and \
           '?unreact=' in self.path and \
           '?actor=' in self.path:
            self._undoReactionButton(callingDomain, self.path,
                                     self.server.base_dir,
                                     self.server.http_prefix,
                                     self.server.domain,
                                     self.server.domainFull,
                                     self.server.onion_domain,
                                     self.server.i2p_domain,
                                     GETstartTime,
                                     self.server.proxy_type,
                                     cookie, self.server.debug)
            self.server.GETbusy = False
            return

        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', 'unreaction button done',
                           self.server.debug)

        # bookmark from the web interface icon
        if authorized and htmlGET and '?bookmark=' in self.path:
            self._bookmarkButton(callingDomain, self.path,
                                 self.server.base_dir,
                                 self.server.http_prefix,
                                 self.server.domain,
                                 self.server.domainFull,
                                 self.server.port,
                                 self.server.onion_domain,
                                 self.server.i2p_domain,
                                 GETstartTime,
                                 self.server.proxy_type,
                                 cookie, self.server.debug)
            self.server.GETbusy = False
            return

        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', 'bookmark shown done',
                           self.server.debug)

        # emoji recation from the web interface bottom icon
        if authorized and htmlGET and '?selreact=' in self.path:
            self._reactionPicker(callingDomain, self.path,
                                 self.server.base_dir,
                                 self.server.http_prefix,
                                 self.server.domain,
                                 self.server.domainFull,
                                 self.server.port,
                                 self.server.onion_domain,
                                 self.server.i2p_domain,
                                 GETstartTime,
                                 self.server.proxy_type,
                                 cookie, self.server.debug)
            self.server.GETbusy = False
            return

        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', 'bookmark shown done',
                           self.server.debug)

        # undo a bookmark from the web interface icon
        if authorized and htmlGET and '?unbookmark=' in self.path:
            self._undoBookmarkButton(callingDomain, self.path,
                                     self.server.base_dir,
                                     self.server.http_prefix,
                                     self.server.domain,
                                     self.server.domainFull,
                                     self.server.port,
                                     self.server.onion_domain,
                                     self.server.i2p_domain,
                                     GETstartTime,
                                     self.server.proxy_type, cookie,
                                     self.server.debug)
            self.server.GETbusy = False
            return

        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', 'unbookmark shown done',
                           self.server.debug)

        # delete button is pressed on a post
        if authorized and htmlGET and '?delete=' in self.path:
            self._deleteButton(callingDomain, self.path,
                               self.server.base_dir,
                               self.server.http_prefix,
                               self.server.domain,
                               self.server.domainFull,
                               self.server.port,
                               self.server.onion_domain,
                               self.server.i2p_domain,
                               GETstartTime,
                               self.server.proxy_type, cookie,
                               self.server.debug)
            self.server.GETbusy = False
            return

        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', 'delete shown done',
                           self.server.debug)

        # The mute button is pressed
        if authorized and htmlGET and '?mute=' in self.path:
            self._muteButton(callingDomain, self.path,
                             self.server.base_dir,
                             self.server.http_prefix,
                             self.server.domain,
                             self.server.domainFull,
                             self.server.port,
                             self.server.onion_domain,
                             self.server.i2p_domain,
                             GETstartTime,
                             self.server.proxy_type, cookie,
                             self.server.debug)
            self.server.GETbusy = False
            return

        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', 'post muted done',
                           self.server.debug)

        # unmute a post from the web interface icon
        if authorized and htmlGET and '?unmute=' in self.path:
            self._undoMuteButton(callingDomain, self.path,
                                 self.server.base_dir,
                                 self.server.http_prefix,
                                 self.server.domain,
                                 self.server.domainFull,
                                 self.server.port,
                                 self.server.onion_domain,
                                 self.server.i2p_domain,
                                 GETstartTime,
                                 self.server.proxy_type, cookie,
                                 self.server.debug)
            self.server.GETbusy = False
            return

        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', 'unmute activated done',
                           self.server.debug)

        # reply from the web interface icon
        inReplyToUrl = None
#        replyWithDM = False
        replyToList = []
        replyPageNumber = 1
        replyCategory = ''
        shareDescription = None
        conversationId = None
#        replytoActor = None
        if htmlGET:
            if '?conversationId=' in self.path:
                conversationId = self.path.split('?conversationId=')[1]
                if '?' in conversationId:
                    conversationId = conversationId.split('?')[0]
            # public reply
            if '?replyto=' in self.path:
                inReplyToUrl = self.path.split('?replyto=')[1]
                if '?' in inReplyToUrl:
                    mentionsList = inReplyToUrl.split('?')
                    for m in mentionsList:
                        if m.startswith('mention='):
                            replyHandle = m.replace('mention=', '')
                            if replyHandle not in replyToList:
                                replyToList.append(replyHandle)
                        if m.startswith('page='):
                            replyPageStr = m.replace('page=', '')
                            if replyPageStr.isdigit():
                                replyPageNumber = int(replyPageStr)
#                        if m.startswith('actor='):
#                            replytoActor = m.replace('actor=', '')
                    inReplyToUrl = mentionsList[0]
                self.path = self.path.split('?replyto=')[0] + '/newpost'
                if self.server.debug:
                    print('DEBUG: replyto path ' + self.path)

            # reply to followers
            if '?replyfollowers=' in self.path:
                inReplyToUrl = self.path.split('?replyfollowers=')[1]
                if '?' in inReplyToUrl:
                    mentionsList = inReplyToUrl.split('?')
                    for m in mentionsList:
                        if m.startswith('mention='):
                            replyHandle = m.replace('mention=', '')
                            if m.replace('mention=', '') not in replyToList:
                                replyToList.append(replyHandle)
                        if m.startswith('page='):
                            replyPageStr = m.replace('page=', '')
                            if replyPageStr.isdigit():
                                replyPageNumber = int(replyPageStr)
#                        if m.startswith('actor='):
#                            replytoActor = m.replace('actor=', '')
                    inReplyToUrl = mentionsList[0]
                self.path = self.path.split('?replyfollowers=')[0] + \
                    '/newfollowers'
                if self.server.debug:
                    print('DEBUG: replyfollowers path ' + self.path)

            # replying as a direct message,
            # for moderation posts or the dm timeline
            if '?replydm=' in self.path:
                inReplyToUrl = self.path.split('?replydm=')[1]
                inReplyToUrl = urllib.parse.unquote_plus(inReplyToUrl)
                if '?' in inReplyToUrl:
                    # multiple parameters
                    mentionsList = inReplyToUrl.split('?')
                    for m in mentionsList:
                        if m.startswith('mention='):
                            replyHandle = m.replace('mention=', '')
                            inReplyToUrl = replyHandle
                            if replyHandle not in replyToList:
                                replyToList.append(replyHandle)
                        elif m.startswith('page='):
                            replyPageStr = m.replace('page=', '')
                            if replyPageStr.isdigit():
                                replyPageNumber = int(replyPageStr)
                        elif m.startswith('category='):
                            replyCategory = m.replace('category=', '')
                        elif m.startswith('sharedesc:'):
                            # get the title for the shared item
                            shareDescription = \
                                m.replace('sharedesc:', '').strip()
                            shareDescription = \
                                shareDescription.replace('_', ' ')
                else:
                    # single parameter
                    if inReplyToUrl.startswith('mention='):
                        replyHandle = inReplyToUrl.replace('mention=', '')
                        inReplyToUrl = replyHandle
                        if replyHandle not in replyToList:
                            replyToList.append(replyHandle)
                    elif inReplyToUrl.startswith('sharedesc:'):
                        # get the title for the shared item
                        shareDescription = \
                            inReplyToUrl.replace('sharedesc:', '').strip()
                        shareDescription = \
                            shareDescription.replace('_', ' ')

                self.path = self.path.split('?replydm=')[0] + '/newdm'
                if self.server.debug:
                    print('DEBUG: replydm path ' + self.path)

            # Edit a blog post
            if authorized and \
               '/users/' in self.path and \
               '?editblogpost=' in self.path and \
               ';actor=' in self.path:
                messageId = self.path.split('?editblogpost=')[1]
                if ';' in messageId:
                    messageId = messageId.split(';')[0]
                actor = self.path.split(';actor=')[1]
                if ';' in actor:
                    actor = actor.split(';')[0]
                nickname = getNicknameFromActor(self.path.split('?')[0])
                if nickname == actor:
                    postUrl = \
                        localActorUrl(self.server.http_prefix, nickname,
                                      self.server.domainFull) + \
                        '/statuses/' + messageId
                    msg = htmlEditBlog(self.server.media_instance,
                                       self.server.translate,
                                       self.server.base_dir,
                                       self.server.http_prefix,
                                       self.path,
                                       replyPageNumber,
                                       nickname, self.server.domain,
                                       postUrl, self.server.systemLanguage)
                    if msg:
                        msg = msg.encode('utf-8')
                        msglen = len(msg)
                        self._set_headers('text/html', msglen,
                                          cookie, callingDomain, False)
                        self._write(msg)
                        self.server.GETbusy = False
                        return

            # list of known crawlers accessing nodeinfo or masto API
            if self._showKnownCrawlers(callingDomain, self.path,
                                       self.server.base_dir,
                                       self.server.knownCrawlers):
                self.server.GETbusy = False
                return

            # edit profile in web interface
            if self._editProfile(callingDomain, self.path,
                                 self.server.translate,
                                 self.server.base_dir,
                                 self.server.http_prefix,
                                 self.server.domain,
                                 self.server.port,
                                 cookie):
                self.server.GETbusy = False
                return

            # edit links from the left column of the timeline in web interface
            if self._editLinks(callingDomain, self.path,
                               self.server.translate,
                               self.server.base_dir,
                               self.server.http_prefix,
                               self.server.domain,
                               self.server.port,
                               cookie,
                               self.server.themeName):
                self.server.GETbusy = False
                return

            # edit newswire from the right column of the timeline
            if self._editNewswire(callingDomain, self.path,
                                  self.server.translate,
                                  self.server.base_dir,
                                  self.server.http_prefix,
                                  self.server.domain,
                                  self.server.port,
                                  cookie):
                self.server.GETbusy = False
                return

            # edit news post
            if self._editNewsPost(callingDomain, self.path,
                                  self.server.translate,
                                  self.server.base_dir,
                                  self.server.http_prefix,
                                  self.server.domain,
                                  self.server.port,
                                  self.server.domainFull,
                                  cookie):
                self.server.GETbusy = False
                return

            if self._showNewPost(callingDomain, self.path,
                                 self.server.media_instance,
                                 self.server.translate,
                                 self.server.base_dir,
                                 self.server.http_prefix,
                                 inReplyToUrl, replyToList,
                                 shareDescription, replyPageNumber,
                                 replyCategory,
                                 self.server.domain,
                                 self.server.domainFull,
                                 GETstartTime,
                                 cookie, noDropDown, conversationId):
                self.server.GETbusy = False
                return

        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', 'new post done',
                           self.server.debug)

        # get an individual post from the path /@nickname/statusnumber
        if self._showIndividualAtPost(authorized,
                                      callingDomain, self.path,
                                      self.server.base_dir,
                                      self.server.http_prefix,
                                      self.server.domain,
                                      self.server.domainFull,
                                      self.server.port,
                                      self.server.onion_domain,
                                      self.server.i2p_domain,
                                      GETstartTime,
                                      self.server.proxy_type,
                                      cookie, self.server.debug):
            self.server.GETbusy = False
            return

        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', 'individual post done',
                           self.server.debug)

        # get replies to a post /users/nickname/statuses/number/replies
        if self.path.endswith('/replies') or '/replies?page=' in self.path:
            if self._showRepliesToPost(authorized,
                                       callingDomain, self.path,
                                       self.server.base_dir,
                                       self.server.http_prefix,
                                       self.server.domain,
                                       self.server.domainFull,
                                       self.server.port,
                                       self.server.onion_domain,
                                       self.server.i2p_domain,
                                       GETstartTime,
                                       self.server.proxy_type, cookie,
                                       self.server.debug):
                self.server.GETbusy = False
                return

        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', 'post replies done',
                           self.server.debug)

        # roles on profile screen
        if self.path.endswith('/roles') and usersInPath:
            if self._showRoles(authorized,
                               callingDomain, self.path,
                               self.server.base_dir,
                               self.server.http_prefix,
                               self.server.domain,
                               self.server.domainFull,
                               self.server.port,
                               self.server.onion_domain,
                               self.server.i2p_domain,
                               GETstartTime,
                               self.server.proxy_type,
                               cookie, self.server.debug):
                self.server.GETbusy = False
                return

        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', 'show roles done',
                           self.server.debug)

        # show skills on the profile page
        if self.path.endswith('/skills') and usersInPath:
            if self._showSkills(authorized,
                                callingDomain, self.path,
                                self.server.base_dir,
                                self.server.http_prefix,
                                self.server.domain,
                                self.server.domainFull,
                                self.server.port,
                                self.server.onion_domain,
                                self.server.i2p_domain,
                                GETstartTime,
                                self.server.proxy_type,
                                cookie, self.server.debug):
                self.server.GETbusy = False
                return

        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', 'show skills done',
                           self.server.debug)

        if '?notifypost=' in self.path and usersInPath and authorized:
            if self._showNotifyPost(authorized,
                                    callingDomain, self.path,
                                    self.server.base_dir,
                                    self.server.http_prefix,
                                    self.server.domain,
                                    self.server.domainFull,
                                    self.server.port,
                                    self.server.onion_domain,
                                    self.server.i2p_domain,
                                    GETstartTime,
                                    self.server.proxy_type,
                                    cookie, self.server.debug):
                self.server.GETbusy = False
                return

        # get an individual post from the path
        # /users/nickname/statuses/number
        if '/statuses/' in self.path and usersInPath:
            if self._showIndividualPost(authorized,
                                        callingDomain, self.path,
                                        self.server.base_dir,
                                        self.server.http_prefix,
                                        self.server.domain,
                                        self.server.domainFull,
                                        self.server.port,
                                        self.server.onion_domain,
                                        self.server.i2p_domain,
                                        GETstartTime,
                                        self.server.proxy_type,
                                        cookie, self.server.debug):
                self.server.GETbusy = False
                return

        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', 'show status done',
                           self.server.debug)

        # get the inbox timeline for a given person
        if self.path.endswith('/inbox') or '/inbox?page=' in self.path:
            if self._showInbox(authorized,
                               callingDomain, self.path,
                               self.server.base_dir,
                               self.server.http_prefix,
                               self.server.domain,
                               self.server.domainFull,
                               self.server.port,
                               self.server.onion_domain,
                               self.server.i2p_domain,
                               GETstartTime,
                               self.server.proxy_type,
                               cookie, self.server.debug,
                               self.server.recentPostsCache,
                               self.server.session,
                               self.server.defaultTimeline,
                               self.server.max_recent_posts,
                               self.server.translate,
                               self.server.cachedWebfingers,
                               self.server.personCache,
                               self.server.allowDeletion,
                               self.server.project_version,
                               self.server.yt_replace_domain,
                               self.server.twitter_replacement_domain):
                self.server.GETbusy = False
                return

        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', 'show inbox done',
                           self.server.debug)

        # get the direct messages timeline for a given person
        if self.path.endswith('/dm') or '/dm?page=' in self.path:
            if self._showDMs(authorized,
                             callingDomain, self.path,
                             self.server.base_dir,
                             self.server.http_prefix,
                             self.server.domain,
                             self.server.domainFull,
                             self.server.port,
                             self.server.onion_domain,
                             self.server.i2p_domain,
                             GETstartTime,
                             self.server.proxy_type,
                             cookie, self.server.debug):
                self.server.GETbusy = False
                return

        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', 'show dms done',
                           self.server.debug)

        # get the replies timeline for a given person
        if self.path.endswith('/tlreplies') or '/tlreplies?page=' in self.path:
            if self._showReplies(authorized,
                                 callingDomain, self.path,
                                 self.server.base_dir,
                                 self.server.http_prefix,
                                 self.server.domain,
                                 self.server.domainFull,
                                 self.server.port,
                                 self.server.onion_domain,
                                 self.server.i2p_domain,
                                 GETstartTime,
                                 self.server.proxy_type,
                                 cookie, self.server.debug):
                self.server.GETbusy = False
                return

        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', 'show replies 2 done',
                           self.server.debug)

        # get the media timeline for a given person
        if self.path.endswith('/tlmedia') or '/tlmedia?page=' in self.path:
            if self._showMediaTimeline(authorized,
                                       callingDomain, self.path,
                                       self.server.base_dir,
                                       self.server.http_prefix,
                                       self.server.domain,
                                       self.server.domainFull,
                                       self.server.port,
                                       self.server.onion_domain,
                                       self.server.i2p_domain,
                                       GETstartTime,
                                       self.server.proxy_type,
                                       cookie, self.server.debug):
                self.server.GETbusy = False
                return

        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', 'show media 2 done',
                           self.server.debug)

        # get the blogs for a given person
        if self.path.endswith('/tlblogs') or '/tlblogs?page=' in self.path:
            if self._showBlogsTimeline(authorized,
                                       callingDomain, self.path,
                                       self.server.base_dir,
                                       self.server.http_prefix,
                                       self.server.domain,
                                       self.server.domainFull,
                                       self.server.port,
                                       self.server.onion_domain,
                                       self.server.i2p_domain,
                                       GETstartTime,
                                       self.server.proxy_type,
                                       cookie, self.server.debug):
                self.server.GETbusy = False
                return

        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', 'show blogs 2 done',
                           self.server.debug)

        # get the news for a given person
        if self.path.endswith('/tlnews') or '/tlnews?page=' in self.path:
            if self._showNewsTimeline(authorized,
                                      callingDomain, self.path,
                                      self.server.base_dir,
                                      self.server.http_prefix,
                                      self.server.domain,
                                      self.server.domainFull,
                                      self.server.port,
                                      self.server.onion_domain,
                                      self.server.i2p_domain,
                                      GETstartTime,
                                      self.server.proxy_type,
                                      cookie, self.server.debug):
                self.server.GETbusy = False
                return

        # get features (local blogs) for a given person
        if self.path.endswith('/tlfeatures') or \
           '/tlfeatures?page=' in self.path:
            if self._showFeaturesTimeline(authorized,
                                          callingDomain, self.path,
                                          self.server.base_dir,
                                          self.server.http_prefix,
                                          self.server.domain,
                                          self.server.domainFull,
                                          self.server.port,
                                          self.server.onion_domain,
                                          self.server.i2p_domain,
                                          GETstartTime,
                                          self.server.proxy_type,
                                          cookie, self.server.debug):
                self.server.GETbusy = False
                return

        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', 'show news 2 done',
                           self.server.debug)

        # get the shared items timeline for a given person
        if self.path.endswith('/tlshares') or '/tlshares?page=' in self.path:
            if self._showSharesTimeline(authorized,
                                        callingDomain, self.path,
                                        self.server.base_dir,
                                        self.server.http_prefix,
                                        self.server.domain,
                                        self.server.domainFull,
                                        self.server.port,
                                        self.server.onion_domain,
                                        self.server.i2p_domain,
                                        GETstartTime,
                                        self.server.proxy_type,
                                        cookie, self.server.debug):
                self.server.GETbusy = False
                return

        # get the wanted items timeline for a given person
        if self.path.endswith('/tlwanted') or '/tlwanted?page=' in self.path:
            if self._showWantedTimeline(authorized,
                                        callingDomain, self.path,
                                        self.server.base_dir,
                                        self.server.http_prefix,
                                        self.server.domain,
                                        self.server.domainFull,
                                        self.server.port,
                                        self.server.onion_domain,
                                        self.server.i2p_domain,
                                        GETstartTime,
                                        self.server.proxy_type,
                                        cookie, self.server.debug):
                self.server.GETbusy = False
                return

        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', 'show shares 2 done',
                           self.server.debug)

        # block a domain from htmlAccountInfo
        if authorized and usersInPath and \
           '/accountinfo?blockdomain=' in self.path and \
           '?handle=' in self.path:
            nickname = self.path.split('/users/')[1]
            if '/' in nickname:
                nickname = nickname.split('/')[0]
            if not isModerator(self.server.base_dir, nickname):
                self._400()
                self.server.GETbusy = False
                return
            blockDomain = self.path.split('/accountinfo?blockdomain=')[1]
            searchHandle = blockDomain.split('?handle=')[1]
            searchHandle = urllib.parse.unquote_plus(searchHandle)
            blockDomain = blockDomain.split('?handle=')[0]
            blockDomain = urllib.parse.unquote_plus(blockDomain.strip())
            if '?' in blockDomain:
                blockDomain = blockDomain.split('?')[0]
            addGlobalBlock(self.server.base_dir, '*', blockDomain)
            msg = \
                htmlAccountInfo(self.server.cssCache,
                                self.server.translate,
                                self.server.base_dir,
                                self.server.http_prefix,
                                nickname,
                                self.server.domain,
                                self.server.port,
                                searchHandle,
                                self.server.debug,
                                self.server.systemLanguage,
                                self.server.signingPrivateKeyPem)
            msg = msg.encode('utf-8')
            msglen = len(msg)
            self._login_headers('text/html',
                                msglen, callingDomain)
            self._write(msg)
            self.server.GETbusy = False
            return

        # unblock a domain from htmlAccountInfo
        if authorized and usersInPath and \
           '/accountinfo?unblockdomain=' in self.path and \
           '?handle=' in self.path:
            nickname = self.path.split('/users/')[1]
            if '/' in nickname:
                nickname = nickname.split('/')[0]
            if not isModerator(self.server.base_dir, nickname):
                self._400()
                self.server.GETbusy = False
                return
            blockDomain = self.path.split('/accountinfo?unblockdomain=')[1]
            searchHandle = blockDomain.split('?handle=')[1]
            searchHandle = urllib.parse.unquote_plus(searchHandle)
            blockDomain = blockDomain.split('?handle=')[0]
            blockDomain = urllib.parse.unquote_plus(blockDomain.strip())
            removeGlobalBlock(self.server.base_dir, '*', blockDomain)
            msg = \
                htmlAccountInfo(self.server.cssCache,
                                self.server.translate,
                                self.server.base_dir,
                                self.server.http_prefix,
                                nickname,
                                self.server.domain,
                                self.server.port,
                                searchHandle,
                                self.server.debug,
                                self.server.systemLanguage,
                                self.server.signingPrivateKeyPem)
            msg = msg.encode('utf-8')
            msglen = len(msg)
            self._login_headers('text/html',
                                msglen, callingDomain)
            self._write(msg)
            self.server.GETbusy = False
            return

        # get the bookmarks timeline for a given person
        if self.path.endswith('/tlbookmarks') or \
           '/tlbookmarks?page=' in self.path or \
           self.path.endswith('/bookmarks') or \
           '/bookmarks?page=' in self.path:
            if self._showBookmarksTimeline(authorized,
                                           callingDomain, self.path,
                                           self.server.base_dir,
                                           self.server.http_prefix,
                                           self.server.domain,
                                           self.server.domainFull,
                                           self.server.port,
                                           self.server.onion_domain,
                                           self.server.i2p_domain,
                                           GETstartTime,
                                           self.server.proxy_type,
                                           cookie, self.server.debug):
                self.server.GETbusy = False
                return

        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', 'show bookmarks 2 done',
                           self.server.debug)

        # outbox timeline
        if self.path.endswith('/outbox') or \
           '/outbox?page=' in self.path:
            if self._showOutboxTimeline(authorized,
                                        callingDomain, self.path,
                                        self.server.base_dir,
                                        self.server.http_prefix,
                                        self.server.domain,
                                        self.server.domainFull,
                                        self.server.port,
                                        self.server.onion_domain,
                                        self.server.i2p_domain,
                                        GETstartTime,
                                        self.server.proxy_type,
                                        cookie, self.server.debug):
                self.server.GETbusy = False
                return

        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', 'show outbox done',
                           self.server.debug)

        # get the moderation feed for a moderator
        if self.path.endswith('/moderation') or \
           '/moderation?' in self.path:
            if self._showModTimeline(authorized,
                                     callingDomain, self.path,
                                     self.server.base_dir,
                                     self.server.http_prefix,
                                     self.server.domain,
                                     self.server.domainFull,
                                     self.server.port,
                                     self.server.onion_domain,
                                     self.server.i2p_domain,
                                     GETstartTime,
                                     self.server.proxy_type,
                                     cookie, self.server.debug):
                self.server.GETbusy = False
                return

        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', 'show moderation done',
                           self.server.debug)

        if self._showSharesFeed(authorized,
                                callingDomain, self.path,
                                self.server.base_dir,
                                self.server.http_prefix,
                                self.server.domain,
                                self.server.domainFull,
                                self.server.port,
                                self.server.onion_domain,
                                self.server.i2p_domain,
                                GETstartTime,
                                self.server.proxy_type,
                                cookie, self.server.debug, 'shares'):
            self.server.GETbusy = False
            return

        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', 'show profile 2 done',
                           self.server.debug)

        if self._showFollowingFeed(authorized,
                                   callingDomain, self.path,
                                   self.server.base_dir,
                                   self.server.http_prefix,
                                   self.server.domain,
                                   self.server.domainFull,
                                   self.server.port,
                                   self.server.onion_domain,
                                   self.server.i2p_domain,
                                   GETstartTime,
                                   self.server.proxy_type,
                                   cookie, self.server.debug):
            self.server.GETbusy = False
            return

        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', 'show profile 3 done',
                           self.server.debug)

        if self._showFollowersFeed(authorized,
                                   callingDomain, self.path,
                                   self.server.base_dir,
                                   self.server.http_prefix,
                                   self.server.domain,
                                   self.server.domainFull,
                                   self.server.port,
                                   self.server.onion_domain,
                                   self.server.i2p_domain,
                                   GETstartTime,
                                   self.server.proxy_type,
                                   cookie, self.server.debug):
            self.server.GETbusy = False
            return

        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', 'show profile 4 done',
                           self.server.debug)

        # look up a person
        if self._showPersonProfile(authorized,
                                   callingDomain, self.path,
                                   self.server.base_dir,
                                   self.server.http_prefix,
                                   self.server.domain,
                                   self.server.domainFull,
                                   self.server.port,
                                   self.server.onion_domain,
                                   self.server.i2p_domain,
                                   GETstartTime,
                                   self.server.proxy_type,
                                   cookie, self.server.debug):
            self.server.GETbusy = False
            return

        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', 'show profile posts done',
                           self.server.debug)

        # check that a json file was requested
        if not self.path.endswith('.json'):
            if self.server.debug:
                print('DEBUG: GET Not json: ' + self.path +
                      ' ' + self.server.base_dir)
            self._404()
            self.server.GETbusy = False
            return

        if not self._secure_mode():
            if self.server.debug:
                print('WARN: Unauthorized GET')
            self._404()
            self.server.GETbusy = False
            return

        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', 'authorized fetch',
                           self.server.debug)

        # check that the file exists
        filename = self.server.base_dir + self.path
        if os.path.isfile(filename):
            content = None
            try:
                with open(filename, 'r', encoding='utf-8') as File:
                    content = File.read()
            except OSError:
                print('EX: unable to read file ' + filename)
            if content:
                contentJson = json.loads(content)
                msg = json.dumps(contentJson,
                                 ensure_ascii=False).encode('utf-8')
                msglen = len(msg)
                self._set_headers('application/json',
                                  msglen,
                                  None, callingDomain, False)
                self._write(msg)
                fitnessPerformance(GETstartTime, self.server.fitness,
                                   '_GET', 'arbitrary json',
                                   self.server.debug)
        else:
            if self.server.debug:
                print('DEBUG: GET Unknown file')
            self._404()
        self.server.GETbusy = False

        fitnessPerformance(GETstartTime, self.server.fitness,
                           '_GET', 'end benchmarks',
                           self.server.debug)

    def do_HEAD(self):
        callingDomain = self.server.domainFull
        if self.headers.get('Host'):
            callingDomain = decodedHost(self.headers['Host'])
            if self.server.onion_domain:
                if callingDomain != self.server.domain and \
                   callingDomain != self.server.domainFull and \
                   callingDomain != self.server.onion_domain:
                    print('HEAD domain blocked: ' + callingDomain)
                    self._400()
                    return
            else:
                if callingDomain != self.server.domain and \
                   callingDomain != self.server.domainFull:
                    print('HEAD domain blocked: ' + callingDomain)
                    self._400()
                    return

        checkPath = self.path
        etag = None
        fileLength = -1

        if '/media/' in self.path:
            if isImageFile(self.path) or \
               pathIsVideo(self.path) or \
               pathIsAudio(self.path):
                mediaStr = self.path.split('/media/')[1]
                mediaFilename = \
                    self.server.base_dir + '/media/' + mediaStr
                if os.path.isfile(mediaFilename):
                    checkPath = mediaFilename
                    fileLength = os.path.getsize(mediaFilename)
                    mediaTagFilename = mediaFilename + '.etag'
                    if os.path.isfile(mediaTagFilename):
                        try:
                            with open(mediaTagFilename, 'r') as etagFile:
                                etag = etagFile.read()
                        except OSError:
                            print('EX: do_HEAD unable to read ' +
                                  mediaTagFilename)
                    else:
                        mediaBinary = None
                        try:
                            with open(mediaFilename, 'rb') as avFile:
                                mediaBinary = avFile.read()
                        except OSError:
                            print('EX: unable to read media binary ' +
                                  mediaFilename)
                        if mediaBinary:
                            etag = md5(mediaBinary).hexdigest()  # nosec
                            try:
                                with open(mediaTagFilename, 'w+') as etagFile:
                                    etagFile.write(etag)
                            except OSError:
                                print('EX: do_HEAD unable to write ' +
                                      mediaTagFilename)

        mediaFileType = mediaFileMimeType(checkPath)
        self._set_headers_head(mediaFileType, fileLength,
                               etag, callingDomain, False)

    def _receiveNewPostProcess(self, postType: str, path: str, headers: {},
                               length: int, postBytes, boundary: str,
                               callingDomain: str, cookie: str,
                               authorized: bool,
                               content_license_url: str) -> int:
        # Note: this needs to happen synchronously
        # 0=this is not a new post
        # 1=new post success
        # -1=new post failed
        # 2=new post canceled
        if self.server.debug:
            print('DEBUG: receiving POST')

        if ' boundary=' in headers['Content-Type']:
            if self.server.debug:
                print('DEBUG: receiving POST headers ' +
                      headers['Content-Type'] +
                      ' path ' + path)
            nickname = None
            nicknameStr = path.split('/users/')[1]
            if '?' in nicknameStr:
                nicknameStr = nicknameStr.split('?')[0]
            if '/' in nicknameStr:
                nickname = nicknameStr.split('/')[0]
            else:
                nickname = nicknameStr
            if self.server.debug:
                print('DEBUG: POST nickname ' + str(nickname))
            if not nickname:
                print('WARN: no nickname found when receiving ' + postType +
                      ' path ' + path)
                return -1
            length = int(headers['Content-Length'])
            if length > self.server.maxPostLength:
                print('POST size too large')
                return -1

            boundary = headers['Content-Type'].split('boundary=')[1]
            if ';' in boundary:
                boundary = boundary.split(';')[0]

            # Note: we don't use cgi here because it's due to be deprecated
            # in Python 3.8/3.10
            # Instead we use the multipart mime parser from the email module
            if self.server.debug:
                print('DEBUG: extracting media from POST')
            mediaBytes, postBytes = \
                extractMediaInFormPOST(postBytes, boundary, 'attachpic')
            if self.server.debug:
                if mediaBytes:
                    print('DEBUG: media was found. ' +
                          str(len(mediaBytes)) + ' bytes')
                else:
                    print('DEBUG: no media was found in POST')

            # Note: a .temp extension is used here so that at no time is
            # an image with metadata publicly exposed, even for a few mS
            filenameBase = \
                acctDir(self.server.base_dir,
                        nickname, self.server.domain) + '/upload.temp'

            filename, attachmentMediaType = \
                saveMediaInFormPOST(mediaBytes, self.server.debug,
                                    filenameBase)
            if self.server.debug:
                if filename:
                    print('DEBUG: POST media filename is ' + filename)
                else:
                    print('DEBUG: no media filename in POST')

            if filename:
                if isImageFile(filename):
                    postImageFilename = filename.replace('.temp', '')
                    print('Removing metadata from ' + postImageFilename)
                    city = getSpoofedCity(self.server.city,
                                          self.server.base_dir,
                                          nickname, self.server.domain)
                    if self.server.low_bandwidth:
                        convertImageToLowBandwidth(filename)
                    processMetaData(self.server.base_dir,
                                    nickname, self.server.domain,
                                    filename, postImageFilename, city,
                                    content_license_url)
                    if os.path.isfile(postImageFilename):
                        print('POST media saved to ' + postImageFilename)
                    else:
                        print('ERROR: POST media could not be saved to ' +
                              postImageFilename)
                else:
                    if os.path.isfile(filename):
                        newFilename = filename.replace('.temp', '')
                        os.rename(filename, newFilename)
                        filename = newFilename

            fields = \
                extractTextFieldsInPOST(postBytes, boundary,
                                        self.server.debug)
            if self.server.debug:
                if fields:
                    print('DEBUG: text field extracted from POST ' +
                          str(fields))
                else:
                    print('WARN: no text fields could be extracted from POST')

            # was the citations button pressed on the newblog screen?
            citationsButtonPress = False
            if postType == 'newblog' and fields.get('submitCitations'):
                if fields['submitCitations'] == \
                   self.server.translate['Citations']:
                    citationsButtonPress = True

            if not citationsButtonPress:
                # process the received text fields from the POST
                if not fields.get('message') and \
                   not fields.get('imageDescription') and \
                   not fields.get('pinToProfile'):
                    print('WARN: no message, image description or pin')
                    return -1
                submitText = self.server.translate['Submit']
                customSubmitText = \
                    getConfigParam(self.server.base_dir, 'customSubmitText')
                if customSubmitText:
                    submitText = customSubmitText
                if fields.get('submitPost'):
                    if fields['submitPost'] != submitText:
                        print('WARN: no submit field ' + fields['submitPost'])
                        return -1
                else:
                    print('WARN: no submitPost')
                    return 2

            if not fields.get('imageDescription'):
                fields['imageDescription'] = None
            if not fields.get('subject'):
                fields['subject'] = None
            if not fields.get('replyTo'):
                fields['replyTo'] = None

            if not fields.get('schedulePost'):
                fields['schedulePost'] = False
            else:
                fields['schedulePost'] = True
            print('DEBUG: shedulePost ' + str(fields['schedulePost']))

            if not fields.get('eventDate'):
                fields['eventDate'] = None
            if not fields.get('eventTime'):
                fields['eventTime'] = None
            if not fields.get('location'):
                fields['location'] = None

            if not citationsButtonPress:
                # Store a file which contains the time in seconds
                # since epoch when an attempt to post something was made.
                # This is then used for active monthly users counts
                lastUsedFilename = \
                    acctDir(self.server.base_dir,
                            nickname, self.server.domain) + '/.lastUsed'
                try:
                    with open(lastUsedFilename, 'w+') as lastUsedFile:
                        lastUsedFile.write(str(int(time.time())))
                except OSError:
                    print('EX: _receiveNewPostProcess unable to write ' +
                          lastUsedFilename)

            mentionsStr = ''
            if fields.get('mentions'):
                mentionsStr = fields['mentions'].strip() + ' '
            if not fields.get('commentsEnabled'):
                commentsEnabled = False
            else:
                commentsEnabled = True

            if postType == 'newpost':
                if not fields.get('pinToProfile'):
                    pinToProfile = False
                else:
                    pinToProfile = True
                    # is the post message empty?
                    if not fields['message']:
                        # remove the pinned content from profile screen
                        undoPinnedPost(self.server.base_dir,
                                       nickname, self.server.domain)
                        return 1

                city = getSpoofedCity(self.server.city,
                                      self.server.base_dir,
                                      nickname, self.server.domain)
                conversationId = None
                if fields.get('conversationId'):
                    conversationId = fields['conversationId']
                messageJson = \
                    createPublicPost(self.server.base_dir,
                                     nickname,
                                     self.server.domain,
                                     self.server.port,
                                     self.server.http_prefix,
                                     mentionsStr + fields['message'],
                                     False, False, False, commentsEnabled,
                                     filename, attachmentMediaType,
                                     fields['imageDescription'],
                                     city,
                                     fields['replyTo'], fields['replyTo'],
                                     fields['subject'], fields['schedulePost'],
                                     fields['eventDate'], fields['eventTime'],
                                     fields['location'], False,
                                     self.server.systemLanguage,
                                     conversationId,
                                     self.server.low_bandwidth,
                                     self.server.content_license_url)
                if messageJson:
                    if fields['schedulePost']:
                        return 1
                    if pinToProfile:
                        contentStr = \
                            getBaseContentFromPost(messageJson,
                                                   self.server.systemLanguage)
                        followersOnly = False
                        pinPost(self.server.base_dir,
                                nickname, self.server.domain, contentStr,
                                followersOnly)
                        return 1
                    if self._postToOutbox(messageJson,
                                          self.server.project_version,
                                          nickname):
                        populateReplies(self.server.base_dir,
                                        self.server.http_prefix,
                                        self.server.domainFull,
                                        messageJson,
                                        self.server.max_replies,
                                        self.server.debug)
                        return 1
                    else:
                        return -1
            elif postType == 'newblog':
                # citations button on newblog screen
                if citationsButtonPress:
                    messageJson = \
                        htmlCitations(self.server.base_dir,
                                      nickname,
                                      self.server.domain,
                                      self.server.http_prefix,
                                      self.server.defaultTimeline,
                                      self.server.translate,
                                      self.server.newswire,
                                      self.server.cssCache,
                                      fields['subject'],
                                      fields['message'],
                                      filename, attachmentMediaType,
                                      fields['imageDescription'],
                                      self.server.themeName)
                    if messageJson:
                        messageJson = messageJson.encode('utf-8')
                        messageJsonLen = len(messageJson)
                        self._set_headers('text/html',
                                          messageJsonLen,
                                          cookie, callingDomain, False)
                        self._write(messageJson)
                        return 1
                    else:
                        return -1
                if not fields['subject']:
                    print('WARN: blog posts must have a title')
                    return -1
                if not fields['message']:
                    print('WARN: blog posts must have content')
                    return -1
                # submit button on newblog screen
                followersOnly = False
                saveToFile = False
                client_to_server = False
                city = None
                conversationId = None
                if fields.get('conversationId'):
                    conversationId = fields['conversationId']
                messageJson = \
                    createBlogPost(self.server.base_dir, nickname,
                                   self.server.domain, self.server.port,
                                   self.server.http_prefix,
                                   fields['message'],
                                   followersOnly, saveToFile,
                                   client_to_server, commentsEnabled,
                                   filename, attachmentMediaType,
                                   fields['imageDescription'],
                                   city,
                                   fields['replyTo'], fields['replyTo'],
                                   fields['subject'],
                                   fields['schedulePost'],
                                   fields['eventDate'],
                                   fields['eventTime'],
                                   fields['location'],
                                   self.server.systemLanguage,
                                   conversationId,
                                   self.server.low_bandwidth,
                                   self.server.content_license_url)
                if messageJson:
                    if fields['schedulePost']:
                        return 1
                    if self._postToOutbox(messageJson,
                                          self.server.project_version,
                                          nickname):
                        refreshNewswire(self.server.base_dir)
                        populateReplies(self.server.base_dir,
                                        self.server.http_prefix,
                                        self.server.domainFull,
                                        messageJson,
                                        self.server.max_replies,
                                        self.server.debug)
                        return 1
                    else:
                        return -1
            elif postType == 'editblogpost':
                print('Edited blog post received')
                postFilename = \
                    locatePost(self.server.base_dir,
                               nickname, self.server.domain,
                               fields['postUrl'])
                if os.path.isfile(postFilename):
                    postJsonObject = loadJson(postFilename)
                    if postJsonObject:
                        cachedFilename = \
                            acctDir(self.server.base_dir,
                                    nickname, self.server.domain) + \
                            '/postcache/' + \
                            fields['postUrl'].replace('/', '#') + '.html'
                        if os.path.isfile(cachedFilename):
                            print('Edited blog post, removing cached html')
                            try:
                                os.remove(cachedFilename)
                            except OSError:
                                print('EX: _receiveNewPostProcess ' +
                                      'unable to delete ' + cachedFilename)
                        # remove from memory cache
                        removePostFromCache(postJsonObject,
                                            self.server.recentPostsCache)
                        # change the blog post title
                        postJsonObject['object']['summary'] = fields['subject']
                        # format message
                        tags = []
                        hashtagsDict = {}
                        mentionedRecipients = []
                        fields['message'] = \
                            addHtmlTags(self.server.base_dir,
                                        self.server.http_prefix,
                                        nickname, self.server.domain,
                                        fields['message'],
                                        mentionedRecipients,
                                        hashtagsDict, True)
                        # replace emoji with unicode
                        tags = []
                        for tagName, tag in hashtagsDict.items():
                            tags.append(tag)
                        # get list of tags
                        fields['message'] = \
                            replaceEmojiFromTags(self.server.session,
                                                 self.server.base_dir,
                                                 fields['message'],
                                                 tags, 'content',
                                                 self.server.debug)

                        postJsonObject['object']['content'] = fields['message']
                        contentMap = postJsonObject['object']['contentMap']
                        contentMap[self.server.systemLanguage] = \
                            fields['message']

                        imgDescription = ''
                        if fields.get('imageDescription'):
                            imgDescription = fields['imageDescription']

                        if filename:
                            city = getSpoofedCity(self.server.city,
                                                  self.server.base_dir,
                                                  nickname,
                                                  self.server.domain)
                            postJsonObject['object'] = \
                                attachMedia(self.server.base_dir,
                                            self.server.http_prefix,
                                            nickname,
                                            self.server.domain,
                                            self.server.port,
                                            postJsonObject['object'],
                                            filename,
                                            attachmentMediaType,
                                            imgDescription,
                                            city,
                                            self.server.low_bandwidth,
                                            self.server.content_license_url)

                        replaceYouTube(postJsonObject,
                                       self.server.yt_replace_domain,
                                       self.server.systemLanguage)
                        replaceTwitter(postJsonObject,
                                       self.server.twitter_replacement_domain,
                                       self.server.systemLanguage)
                        saveJson(postJsonObject, postFilename)
                        # also save to the news actor
                        if nickname != 'news':
                            postFilename = \
                                postFilename.replace('#users#' +
                                                     nickname + '#',
                                                     '#users#news#')
                            saveJson(postJsonObject, postFilename)
                        print('Edited blog post, resaved ' + postFilename)
                        return 1
                    else:
                        print('Edited blog post, unable to load json for ' +
                              postFilename)
                else:
                    print('Edited blog post not found ' +
                          str(fields['postUrl']))
                return -1
            elif postType == 'newunlisted':
                city = getSpoofedCity(self.server.city,
                                      self.server.base_dir,
                                      nickname,
                                      self.server.domain)
                followersOnly = False
                saveToFile = False
                client_to_server = False

                conversationId = None
                if fields.get('conversationId'):
                    conversationId = fields['conversationId']

                messageJson = \
                    createUnlistedPost(self.server.base_dir,
                                       nickname,
                                       self.server.domain, self.server.port,
                                       self.server.http_prefix,
                                       mentionsStr + fields['message'],
                                       followersOnly, saveToFile,
                                       client_to_server, commentsEnabled,
                                       filename, attachmentMediaType,
                                       fields['imageDescription'],
                                       city,
                                       fields['replyTo'],
                                       fields['replyTo'],
                                       fields['subject'],
                                       fields['schedulePost'],
                                       fields['eventDate'],
                                       fields['eventTime'],
                                       fields['location'],
                                       self.server.systemLanguage,
                                       conversationId,
                                       self.server.low_bandwidth,
                                       self.server.content_license_url)
                if messageJson:
                    if fields['schedulePost']:
                        return 1
                    if self._postToOutbox(messageJson,
                                          self.server.project_version,
                                          nickname):
                        populateReplies(self.server.base_dir,
                                        self.server.http_prefix,
                                        self.server.domain,
                                        messageJson,
                                        self.server.max_replies,
                                        self.server.debug)
                        return 1
                    else:
                        return -1
            elif postType == 'newfollowers':
                city = getSpoofedCity(self.server.city,
                                      self.server.base_dir,
                                      nickname,
                                      self.server.domain)
                followersOnly = True
                saveToFile = False
                client_to_server = False

                conversationId = None
                if fields.get('conversationId'):
                    conversationId = fields['conversationId']

                messageJson = \
                    createFollowersOnlyPost(self.server.base_dir,
                                            nickname,
                                            self.server.domain,
                                            self.server.port,
                                            self.server.http_prefix,
                                            mentionsStr + fields['message'],
                                            followersOnly, saveToFile,
                                            client_to_server,
                                            commentsEnabled,
                                            filename, attachmentMediaType,
                                            fields['imageDescription'],
                                            city,
                                            fields['replyTo'],
                                            fields['replyTo'],
                                            fields['subject'],
                                            fields['schedulePost'],
                                            fields['eventDate'],
                                            fields['eventTime'],
                                            fields['location'],
                                            self.server.systemLanguage,
                                            conversationId,
                                            self.server.low_bandwidth,
                                            self.server.content_license_url)
                if messageJson:
                    if fields['schedulePost']:
                        return 1
                    if self._postToOutbox(messageJson,
                                          self.server.project_version,
                                          nickname):
                        populateReplies(self.server.base_dir,
                                        self.server.http_prefix,
                                        self.server.domain,
                                        messageJson,
                                        self.server.max_replies,
                                        self.server.debug)
                        return 1
                    else:
                        return -1
            elif postType == 'newdm':
                messageJson = None
                print('A DM was posted')
                if '@' in mentionsStr:
                    city = getSpoofedCity(self.server.city,
                                          self.server.base_dir,
                                          nickname,
                                          self.server.domain)
                    followersOnly = True
                    saveToFile = False
                    client_to_server = False

                    conversationId = None
                    if fields.get('conversationId'):
                        conversationId = fields['conversationId']
                    content_license_url = self.server.content_license_url

                    messageJson = \
                        createDirectMessagePost(self.server.base_dir,
                                                nickname,
                                                self.server.domain,
                                                self.server.port,
                                                self.server.http_prefix,
                                                mentionsStr +
                                                fields['message'],
                                                followersOnly, saveToFile,
                                                client_to_server,
                                                commentsEnabled,
                                                filename, attachmentMediaType,
                                                fields['imageDescription'],
                                                city,
                                                fields['replyTo'],
                                                fields['replyTo'],
                                                fields['subject'],
                                                True, fields['schedulePost'],
                                                fields['eventDate'],
                                                fields['eventTime'],
                                                fields['location'],
                                                self.server.systemLanguage,
                                                conversationId,
                                                self.server.low_bandwidth,
                                                content_license_url)
                if messageJson:
                    if fields['schedulePost']:
                        return 1
                    print('Sending new DM to ' +
                          str(messageJson['object']['to']))
                    if self._postToOutbox(messageJson,
                                          self.server.project_version,
                                          nickname):
                        populateReplies(self.server.base_dir,
                                        self.server.http_prefix,
                                        self.server.domain,
                                        messageJson,
                                        self.server.max_replies,
                                        self.server.debug)
                        return 1
                    else:
                        return -1
            elif postType == 'newreminder':
                messageJson = None
                handle = nickname + '@' + self.server.domainFull
                print('A reminder was posted for ' + handle)
                if '@' + handle not in mentionsStr:
                    mentionsStr = '@' + handle + ' ' + mentionsStr
                city = getSpoofedCity(self.server.city,
                                      self.server.base_dir,
                                      nickname,
                                      self.server.domain)
                followersOnly = True
                saveToFile = False
                client_to_server = False
                commentsEnabled = False
                conversationId = None
                messageJson = \
                    createDirectMessagePost(self.server.base_dir,
                                            nickname,
                                            self.server.domain,
                                            self.server.port,
                                            self.server.http_prefix,
                                            mentionsStr + fields['message'],
                                            followersOnly, saveToFile,
                                            client_to_server, commentsEnabled,
                                            filename, attachmentMediaType,
                                            fields['imageDescription'],
                                            city,
                                            None, None,
                                            fields['subject'],
                                            True, fields['schedulePost'],
                                            fields['eventDate'],
                                            fields['eventTime'],
                                            fields['location'],
                                            self.server.systemLanguage,
                                            conversationId,
                                            self.server.low_bandwidth,
                                            self.server.content_license_url)
                if messageJson:
                    if fields['schedulePost']:
                        return 1
                    print('DEBUG: new reminder to ' +
                          str(messageJson['object']['to']))
                    if self._postToOutbox(messageJson,
                                          self.server.project_version,
                                          nickname):
                        return 1
                    else:
                        return -1
            elif postType == 'newreport':
                if attachmentMediaType:
                    if attachmentMediaType != 'image':
                        return -1
                # So as to be sure that this only goes to moderators
                # and not accounts being reported we disable any
                # included fediverse addresses by replacing '@' with '-at-'
                fields['message'] = fields['message'].replace('@', '-at-')
                city = getSpoofedCity(self.server.city,
                                      self.server.base_dir,
                                      nickname,
                                      self.server.domain)
                messageJson = \
                    createReportPost(self.server.base_dir,
                                     nickname,
                                     self.server.domain, self.server.port,
                                     self.server.http_prefix,
                                     mentionsStr + fields['message'],
                                     True, False, False, True,
                                     filename, attachmentMediaType,
                                     fields['imageDescription'],
                                     city,
                                     self.server.debug, fields['subject'],
                                     self.server.systemLanguage,
                                     self.server.low_bandwidth,
                                     self.server.content_license_url)
                if messageJson:
                    if self._postToOutbox(messageJson,
                                          self.server.project_version,
                                          nickname):
                        return 1
                    else:
                        return -1
            elif postType == 'newquestion':
                if not fields.get('duration'):
                    return -1
                if not fields.get('message'):
                    return -1
#                questionStr = fields['message']
                qOptions = []
                for questionCtr in range(8):
                    if fields.get('questionOption' + str(questionCtr)):
                        qOptions.append(fields['questionOption' +
                                               str(questionCtr)])
                if not qOptions:
                    return -1
                city = getSpoofedCity(self.server.city,
                                      self.server.base_dir,
                                      nickname,
                                      self.server.domain)
                intDuration = int(fields['duration'])
                messageJson = \
                    createQuestionPost(self.server.base_dir,
                                       nickname,
                                       self.server.domain,
                                       self.server.port,
                                       self.server.http_prefix,
                                       fields['message'], qOptions,
                                       False, False, False,
                                       commentsEnabled,
                                       filename, attachmentMediaType,
                                       fields['imageDescription'],
                                       city,
                                       fields['subject'],
                                       intDuration,
                                       self.server.systemLanguage,
                                       self.server.low_bandwidth,
                                       self.server.content_license_url)
                if messageJson:
                    if self.server.debug:
                        print('DEBUG: new Question')
                    if self._postToOutbox(messageJson,
                                          self.server.project_version,
                                          nickname):
                        return 1
                return -1
            elif postType == 'newshare' or postType == 'newwanted':
                if not fields.get('itemQty'):
                    print(postType + ' no itemQty')
                    return -1
                if not fields.get('itemType'):
                    print(postType + ' no itemType')
                    return -1
                if 'itemPrice' not in fields:
                    print(postType + ' no itemPrice')
                    return -1
                if 'itemCurrency' not in fields:
                    print(postType + ' no itemCurrency')
                    return -1
                if not fields.get('category'):
                    print(postType + ' no category')
                    return -1
                if not fields.get('duration'):
                    print(postType + ' no duratio')
                    return -1
                if attachmentMediaType:
                    if attachmentMediaType != 'image':
                        print('Attached media is not an image')
                        return -1
                durationStr = fields['duration']
                if durationStr:
                    if ' ' not in durationStr:
                        durationStr = durationStr + ' days'
                city = getSpoofedCity(self.server.city,
                                      self.server.base_dir,
                                      nickname,
                                      self.server.domain)
                itemQty = 1
                if fields['itemQty']:
                    if isfloat(fields['itemQty']):
                        itemQty = float(fields['itemQty'])
                itemPrice = "0.00"
                itemCurrency = "EUR"
                if fields['itemPrice']:
                    itemPrice, itemCurrency = \
                        getPriceFromString(fields['itemPrice'])
                if fields['itemCurrency']:
                    itemCurrency = fields['itemCurrency']
                if postType == 'newshare':
                    print('Adding shared item')
                    sharesFileType = 'shares'
                else:
                    print('Adding wanted item')
                    sharesFileType = 'wanted'
                addShare(self.server.base_dir,
                         self.server.http_prefix,
                         nickname,
                         self.server.domain, self.server.port,
                         fields['subject'],
                         fields['message'],
                         filename,
                         itemQty, fields['itemType'],
                         fields['category'],
                         fields['location'],
                         durationStr,
                         self.server.debug,
                         city, itemPrice, itemCurrency,
                         self.server.systemLanguage,
                         self.server.translate, sharesFileType,
                         self.server.low_bandwidth,
                         self.server.content_license_url)
                if filename:
                    if os.path.isfile(filename):
                        try:
                            os.remove(filename)
                        except OSError:
                            print('EX: _receiveNewPostProcess ' +
                                  'unable to delete ' + filename)
                self.postToNickname = nickname
                return 1
        return -1

    def _receiveNewPost(self, postType: str, path: str,
                        callingDomain: str, cookie: str,
                        authorized: bool,
                        content_license_url: str) -> int:
        """A new post has been created
        This creates a thread to send the new post
        """
        pageNumber = 1

        if '/users/' not in path:
            print('Not receiving new post for ' + path +
                  ' because /users/ not in path')
            return None

        if '?' + postType + '?' not in path:
            print('Not receiving new post for ' + path +
                  ' because ?' + postType + '? not in path')
            return None

        print('New post begins: ' + postType + ' ' + path)

        if '?page=' in path:
            pageNumberStr = path.split('?page=')[1]
            if '?' in pageNumberStr:
                pageNumberStr = pageNumberStr.split('?')[0]
            if '#' in pageNumberStr:
                pageNumberStr = pageNumberStr.split('#')[0]
            if pageNumberStr.isdigit():
                pageNumber = int(pageNumberStr)
                path = path.split('?page=')[0]

        # get the username who posted
        newPostThreadName = None
        if '/users/' in path:
            newPostThreadName = path.split('/users/')[1]
            if '/' in newPostThreadName:
                newPostThreadName = newPostThreadName.split('/')[0]
        if not newPostThreadName:
            newPostThreadName = '*'

        if self.server.newPostThread.get(newPostThreadName):
            print('Waiting for previous new post thread to end')
            waitCtr = 0
            while (self.server.newPostThread[newPostThreadName].is_alive() and
                   waitCtr < 8):
                time.sleep(1)
                waitCtr += 1
            if waitCtr >= 8:
                print('Killing previous new post thread for ' +
                      newPostThreadName)
                self.server.newPostThread[newPostThreadName].kill()

        # make a copy of self.headers
        headers = {}
        headersWithoutCookie = {}
        for dictEntryName, headerLine in self.headers.items():
            headers[dictEntryName] = headerLine
            if dictEntryName.lower() != 'cookie':
                headersWithoutCookie[dictEntryName] = headerLine
        print('New post headers: ' + str(headersWithoutCookie))

        length = int(headers['Content-Length'])
        if length > self.server.maxPostLength:
            print('POST size too large')
            return None

        if not headers.get('Content-Type'):
            if headers.get('Content-type'):
                headers['Content-Type'] = headers['Content-type']
            elif headers.get('content-type'):
                headers['Content-Type'] = headers['content-type']
        if headers.get('Content-Type'):
            if ' boundary=' in headers['Content-Type']:
                boundary = headers['Content-Type'].split('boundary=')[1]
                if ';' in boundary:
                    boundary = boundary.split(';')[0]

                try:
                    postBytes = self.rfile.read(length)
                except SocketError as ex:
                    if ex.errno == errno.ECONNRESET:
                        print('WARN: POST postBytes ' +
                              'connection reset by peer')
                    else:
                        print('WARN: POST postBytes socket error')
                    return None
                except ValueError as ex:
                    print('ERROR: POST postBytes rfile.read failed, ' +
                          str(ex))
                    return None

                # second length check from the bytes received
                # since Content-Length could be untruthful
                length = len(postBytes)
                if length > self.server.maxPostLength:
                    print('POST size too large')
                    return None

                # Note sending new posts needs to be synchronous,
                # otherwise any attachments can get mangled if
                # other events happen during their decoding
                print('Creating new post from: ' + newPostThreadName)
                self._receiveNewPostProcess(postType,
                                            path, headers, length,
                                            postBytes, boundary,
                                            callingDomain, cookie,
                                            authorized,
                                            content_license_url)
        return pageNumber

    def _cryptoAPIreadHandle(self):
        """Reads handle
        """
        messageBytes = None
        maxDeviceIdLength = 2048
        length = int(self.headers['Content-length'])
        if length >= maxDeviceIdLength:
            print('WARN: handle post to crypto API is too long ' +
                  str(length) + ' bytes')
            return {}
        try:
            messageBytes = self.rfile.read(length)
        except SocketError as ex:
            if ex.errno == errno.ECONNRESET:
                print('WARN: handle POST messageBytes ' +
                      'connection reset by peer')
            else:
                print('WARN: handle POST messageBytes socket error')
            return {}
        except ValueError as ex:
            print('ERROR: handle POST messageBytes rfile.read failed ' +
                  str(ex))
            return {}

        lenMessage = len(messageBytes)
        if lenMessage > 2048:
            print('WARN: handle post to crypto API is too long ' +
                  str(lenMessage) + ' bytes')
            return {}

        handle = messageBytes.decode("utf-8")
        if not handle:
            return None
        if '@' not in handle:
            return None
        if '[' in handle:
            return json.loads(messageBytes)
        if handle.startswith('@'):
            handle = handle[1:]
        if '@' not in handle:
            return None
        return handle.strip()

    def _cryptoAPIreadJson(self) -> {}:
        """Obtains json from POST to the crypto API
        """
        messageBytes = None
        maxCryptoMessageLength = 10240
        length = int(self.headers['Content-length'])
        if length >= maxCryptoMessageLength:
            print('WARN: post to crypto API is too long ' +
                  str(length) + ' bytes')
            return {}
        try:
            messageBytes = self.rfile.read(length)
        except SocketError as ex:
            if ex.errno == errno.ECONNRESET:
                print('WARN: POST messageBytes ' +
                      'connection reset by peer')
            else:
                print('WARN: POST messageBytes socket error')
            return {}
        except ValueError as ex:
            print('ERROR: POST messageBytes rfile.read failed, ' + str(ex))
            return {}

        lenMessage = len(messageBytes)
        if lenMessage > 10240:
            print('WARN: post to crypto API is too long ' +
                  str(lenMessage) + ' bytes')
            return {}

        return json.loads(messageBytes)

    def _cryptoAPIQuery(self, callingDomain: str) -> bool:
        handle = self._cryptoAPIreadHandle()
        if not handle:
            return False
        if isinstance(handle, str):
            personDir = self.server.base_dir + '/accounts/' + handle
            if not os.path.isdir(personDir + '/devices'):
                return False
            devicesList = []
            for subdir, dirs, files in os.walk(personDir + '/devices'):
                for f in files:
                    deviceFilename = os.path.join(personDir + '/devices', f)
                    if not os.path.isfile(deviceFilename):
                        continue
                    contentJson = loadJson(deviceFilename)
                    if contentJson:
                        devicesList.append(contentJson)
                break
            # return the list of devices for this handle
            msg = \
                json.dumps(devicesList,
                           ensure_ascii=False).encode('utf-8')
            msglen = len(msg)
            self._set_headers('application/json',
                              msglen,
                              None, callingDomain, False)
            self._write(msg)
            return True
        return False

    def _cryptoAPI(self, path: str, authorized: bool) -> None:
        """POST or GET with the crypto API
        """
        if authorized and path.startswith('/api/v1/crypto/keys/upload'):
            # register a device to an authorized account
            if not self.authorizedNickname:
                self._400()
                return
            deviceKeys = self._cryptoAPIreadJson()
            if not deviceKeys:
                self._400()
                return
            if isinstance(deviceKeys, dict):
                if not E2EEvalidDevice(deviceKeys):
                    self._400()
                    return
                E2EEaddDevice(self.server.base_dir,
                              self.authorizedNickname,
                              self.server.domain,
                              deviceKeys['deviceId'],
                              deviceKeys['name'],
                              deviceKeys['claim'],
                              deviceKeys['fingerprintKey']['publicKeyBase64'],
                              deviceKeys['identityKey']['publicKeyBase64'],
                              deviceKeys['fingerprintKey']['type'],
                              deviceKeys['identityKey']['type'])
                self._200()
                return
            self._400()
        elif path.startswith('/api/v1/crypto/keys/query'):
            # given a handle (nickname@domain) return a list of the devices
            # registered to that handle
            if not self._cryptoAPIQuery():
                self._400()
        elif path.startswith('/api/v1/crypto/keys/claim'):
            # TODO
            self._200()
        elif authorized and path.startswith('/api/v1/crypto/delivery'):
            # TODO
            self._200()
        elif (authorized and
              path.startswith('/api/v1/crypto/encrypted_messages/clear')):
            # TODO
            self._200()
        elif path.startswith('/api/v1/crypto/encrypted_messages'):
            # TODO
            self._200()
        else:
            self._400()

    def do_POST(self):
        POSTstartTime = time.time()

        if not self._establishSession("POST"):
            fitnessPerformance(POSTstartTime, self.server.fitness,
                               '_POST', 'createSession',
                               self.server.debug)
            self._404()
            return

        if self.server.debug:
            print('DEBUG: POST to ' + self.server.base_dir +
                  ' path: ' + self.path + ' busy: ' +
                  str(self.server.POSTbusy))

        callingDomain = self.server.domainFull
        if self.headers.get('Host'):
            callingDomain = decodedHost(self.headers['Host'])
            if self.server.onion_domain:
                if callingDomain != self.server.domain and \
                   callingDomain != self.server.domainFull and \
                   callingDomain != self.server.onion_domain:
                    print('POST domain blocked: ' + callingDomain)
                    self._400()
                    return
            elif self.server.i2p_domain:
                if callingDomain != self.server.domain and \
                   callingDomain != self.server.domainFull and \
                   callingDomain != self.server.i2p_domain:
                    print('POST domain blocked: ' + callingDomain)
                    self._400()
                    return
            else:
                if callingDomain != self.server.domain and \
                   callingDomain != self.server.domainFull:
                    print('POST domain blocked: ' + callingDomain)
                    self._400()
                    return

        currTimePOST = int(time.time() * 1000)
        if self.server.POSTbusy:
            if currTimePOST - self.server.lastPOST < 500:
                self.send_response(429)
                self.end_headers()
                return
        self.server.POSTbusy = True
        self.server.lastPOST = currTimePOST

        uaStr = self._getUserAgent()

        if self._blockedUserAgent(callingDomain, uaStr):
            self._400()
            self.server.POSTbusy = False
            return

        if not self.headers.get('Content-type'):
            print('Content-type header missing')
            self._400()
            self.server.POSTbusy = False
            return

        # returns after this point should set POSTbusy to False

        # remove any trailing slashes from the path
        if not self.path.endswith('confirm'):
            self.path = self.path.replace('/outbox/', '/outbox')
            self.path = self.path.replace('/tlblogs/', '/tlblogs')
            self.path = self.path.replace('/inbox/', '/inbox')
            self.path = self.path.replace('/shares/', '/shares')
            self.path = self.path.replace('/wanted/', '/wanted')
            self.path = self.path.replace('/sharedInbox/', '/sharedInbox')

        if self.path == '/inbox':
            if not self.server.enable_shared_inbox:
                self._503()
                self.server.POSTbusy = False
                return

        cookie = None
        if self.headers.get('Cookie'):
            cookie = self.headers['Cookie']

        # check authorization
        authorized = self._isAuthorized()
        if not authorized and self.server.debug:
            print('POST Not authorized')
            print(str(self.headers))

        if self.path.startswith('/api/v1/crypto/'):
            self._cryptoAPI(self.path, authorized)
            self.server.POSTbusy = False
            return

        # if this is a POST to the outbox then check authentication
        self.outboxAuthenticated = False
        self.postToNickname = None

        fitnessPerformance(POSTstartTime, self.server.fitness,
                           '_POST', 'start',
                           self.server.debug)

        # login screen
        if self.path.startswith('/login'):
            self._loginScreen(self.path, callingDomain, cookie,
                              self.server.base_dir, self.server.http_prefix,
                              self.server.domain, self.server.domainFull,
                              self.server.port,
                              self.server.onion_domain, self.server.i2p_domain,
                              self.server.debug)
            self.server.POSTbusy = False
            return

        fitnessPerformance(POSTstartTime, self.server.fitness,
                           '_POST', '_loginScreen',
                           self.server.debug)

        if authorized and self.path.endswith('/sethashtagcategory'):
            self._setHashtagCategory(callingDomain, cookie,
                                     authorized, self.path,
                                     self.server.base_dir,
                                     self.server.http_prefix,
                                     self.server.domain,
                                     self.server.domainFull,
                                     self.server.onion_domain,
                                     self.server.i2p_domain,
                                     self.server.debug,
                                     self.server.defaultTimeline,
                                     self.server.allow_local_network_access)
            self.server.POSTbusy = False
            return

        # update of profile/avatar from web interface,
        # after selecting Edit button then Submit
        if authorized and self.path.endswith('/profiledata'):
            self._profileUpdate(callingDomain, cookie, authorized, self.path,
                                self.server.base_dir, self.server.http_prefix,
                                self.server.domain,
                                self.server.domainFull,
                                self.server.onion_domain,
                                self.server.i2p_domain, self.server.debug,
                                self.server.allow_local_network_access,
                                self.server.systemLanguage,
                                self.server.content_license_url)
            self.server.POSTbusy = False
            return

        if authorized and self.path.endswith('/linksdata'):
            self._linksUpdate(callingDomain, cookie, authorized, self.path,
                              self.server.base_dir, self.server.http_prefix,
                              self.server.domain,
                              self.server.domainFull,
                              self.server.onion_domain,
                              self.server.i2p_domain, self.server.debug,
                              self.server.defaultTimeline,
                              self.server.allow_local_network_access)
            self.server.POSTbusy = False
            return

        if authorized and self.path.endswith('/newswiredata'):
            self._newswireUpdate(callingDomain, cookie, authorized, self.path,
                                 self.server.base_dir, self.server.http_prefix,
                                 self.server.domain,
                                 self.server.domainFull,
                                 self.server.onion_domain,
                                 self.server.i2p_domain, self.server.debug,
                                 self.server.defaultTimeline)
            self.server.POSTbusy = False
            return

        if authorized and self.path.endswith('/citationsdata'):
            self._citationsUpdate(callingDomain, cookie, authorized, self.path,
                                  self.server.base_dir,
                                  self.server.http_prefix,
                                  self.server.domain,
                                  self.server.domainFull,
                                  self.server.onion_domain,
                                  self.server.i2p_domain, self.server.debug,
                                  self.server.defaultTimeline,
                                  self.server.newswire)
            self.server.POSTbusy = False
            return

        if authorized and self.path.endswith('/newseditdata'):
            self._newsPostEdit(callingDomain, cookie, authorized, self.path,
                               self.server.base_dir, self.server.http_prefix,
                               self.server.domain,
                               self.server.domainFull,
                               self.server.onion_domain,
                               self.server.i2p_domain, self.server.debug,
                               self.server.defaultTimeline)
            self.server.POSTbusy = False
            return

        fitnessPerformance(POSTstartTime, self.server.fitness,
                           '_POST', '_newsPostEdit',
                           self.server.debug)

        usersInPath = False
        if '/users/' in self.path:
            usersInPath = True

        # moderator action buttons
        if authorized and usersInPath and \
           self.path.endswith('/moderationaction'):
            self._moderatorActions(self.path, callingDomain, cookie,
                                   self.server.base_dir,
                                   self.server.http_prefix,
                                   self.server.domain,
                                   self.server.domainFull,
                                   self.server.port,
                                   self.server.onion_domain,
                                   self.server.i2p_domain,
                                   self.server.debug)
            self.server.POSTbusy = False
            return

        fitnessPerformance(POSTstartTime, self.server.fitness,
                           '_POST', '_moderatorActions',
                           self.server.debug)

        searchForEmoji = False
        if self.path.endswith('/searchhandleemoji'):
            searchForEmoji = True
            self.path = self.path.replace('/searchhandleemoji',
                                          '/searchhandle')
            if self.server.debug:
                print('DEBUG: searching for emoji')
                print('authorized: ' + str(authorized))

        fitnessPerformance(POSTstartTime, self.server.fitness,
                           '_POST', 'searchhandleemoji',
                           self.server.debug)

        # a search was made
        if ((authorized or searchForEmoji) and
            (self.path.endswith('/searchhandle') or
             '/searchhandle?page=' in self.path)):
            self._receiveSearchQuery(callingDomain, cookie,
                                     authorized, self.path,
                                     self.server.base_dir,
                                     self.server.http_prefix,
                                     self.server.domain,
                                     self.server.domainFull,
                                     self.server.port,
                                     searchForEmoji,
                                     self.server.onion_domain,
                                     self.server.i2p_domain,
                                     POSTstartTime, {},
                                     self.server.debug)
            self.server.POSTbusy = False
            return

        fitnessPerformance(POSTstartTime, self.server.fitness,
                           '_POST', '_receiveSearchQuery',
                           self.server.debug)

        if not authorized:
            if self.path.endswith('/rmpost'):
                print('ERROR: attempt to remove post was not authorized. ' +
                      self.path)
                self._400()
                self.server.POSTbusy = False
                return
        else:
            # a vote/question/poll is posted
            if self.path.endswith('/question') or \
               '/question?page=' in self.path:
                self._receiveVote(callingDomain, cookie,
                                  authorized, self.path,
                                  self.server.base_dir,
                                  self.server.http_prefix,
                                  self.server.domain,
                                  self.server.domainFull,
                                  self.server.onion_domain,
                                  self.server.i2p_domain,
                                  self.server.debug)
                self.server.POSTbusy = False
                return

            # removes a shared item
            if self.path.endswith('/rmshare'):
                self._removeShare(callingDomain, cookie,
                                  authorized, self.path,
                                  self.server.base_dir,
                                  self.server.http_prefix,
                                  self.server.domain,
                                  self.server.domainFull,
                                  self.server.onion_domain,
                                  self.server.i2p_domain,
                                  self.server.debug)
                self.server.POSTbusy = False
                return

            # removes a wanted item
            if self.path.endswith('/rmwanted'):
                self._removeWanted(callingDomain, cookie,
                                   authorized, self.path,
                                   self.server.base_dir,
                                   self.server.http_prefix,
                                   self.server.domain,
                                   self.server.domainFull,
                                   self.server.onion_domain,
                                   self.server.i2p_domain,
                                   self.server.debug)
                self.server.POSTbusy = False
                return

            fitnessPerformance(POSTstartTime, self.server.fitness,
                               '_POST', '_removeWanted',
                               self.server.debug)

            # removes a post
            if self.path.endswith('/rmpost'):
                if '/users/' not in self.path:
                    print('ERROR: attempt to remove post ' +
                          'was not authorized. ' + self.path)
                    self._400()
                    self.server.POSTbusy = False
                    return
            if self.path.endswith('/rmpost'):
                self._removePost(callingDomain, cookie,
                                 authorized, self.path,
                                 self.server.base_dir,
                                 self.server.http_prefix,
                                 self.server.domain,
                                 self.server.domainFull,
                                 self.server.onion_domain,
                                 self.server.i2p_domain,
                                 self.server.debug)
                self.server.POSTbusy = False
                return

            fitnessPerformance(POSTstartTime, self.server.fitness,
                               '_POST', '_removePost',
                               self.server.debug)

            # decision to follow in the web interface is confirmed
            if self.path.endswith('/followconfirm'):
                self._followConfirm(callingDomain, cookie,
                                    authorized, self.path,
                                    self.server.base_dir,
                                    self.server.http_prefix,
                                    self.server.domain,
                                    self.server.domainFull,
                                    self.server.port,
                                    self.server.onion_domain,
                                    self.server.i2p_domain,
                                    self.server.debug)
                self.server.POSTbusy = False
                return

            fitnessPerformance(POSTstartTime, self.server.fitness,
                               '_POST', '_followConfirm',
                               self.server.debug)

            # decision to unfollow in the web interface is confirmed
            if self.path.endswith('/unfollowconfirm'):
                self._unfollowConfirm(callingDomain, cookie,
                                      authorized, self.path,
                                      self.server.base_dir,
                                      self.server.http_prefix,
                                      self.server.domain,
                                      self.server.domainFull,
                                      self.server.port,
                                      self.server.onion_domain,
                                      self.server.i2p_domain,
                                      self.server.debug)
                self.server.POSTbusy = False
                return

            fitnessPerformance(POSTstartTime, self.server.fitness,
                               '_POST', '_unfollowConfirm',
                               self.server.debug)

            # decision to unblock in the web interface is confirmed
            if self.path.endswith('/unblockconfirm'):
                self._unblockConfirm(callingDomain, cookie,
                                     authorized, self.path,
                                     self.server.base_dir,
                                     self.server.http_prefix,
                                     self.server.domain,
                                     self.server.domainFull,
                                     self.server.port,
                                     self.server.onion_domain,
                                     self.server.i2p_domain,
                                     self.server.debug)
                self.server.POSTbusy = False
                return

            fitnessPerformance(POSTstartTime, self.server.fitness,
                               '_POST', '_unblockConfirm',
                               self.server.debug)

            # decision to block in the web interface is confirmed
            if self.path.endswith('/blockconfirm'):
                self._blockConfirm(callingDomain, cookie,
                                   authorized, self.path,
                                   self.server.base_dir,
                                   self.server.http_prefix,
                                   self.server.domain,
                                   self.server.domainFull,
                                   self.server.port,
                                   self.server.onion_domain,
                                   self.server.i2p_domain,
                                   self.server.debug)
                self.server.POSTbusy = False
                return

            fitnessPerformance(POSTstartTime, self.server.fitness,
                               '_POST', '_blockConfirm',
                               self.server.debug)

            # an option was chosen from person options screen
            # view/follow/block/report
            if self.path.endswith('/personoptions'):
                self._personOptions(self.path,
                                    callingDomain, cookie,
                                    self.server.base_dir,
                                    self.server.http_prefix,
                                    self.server.domain,
                                    self.server.domainFull,
                                    self.server.port,
                                    self.server.onion_domain,
                                    self.server.i2p_domain,
                                    self.server.debug)
                self.server.POSTbusy = False
                return

            # Change the key shortcuts
            if usersInPath and \
               self.path.endswith('/changeAccessKeys'):
                nickname = self.path.split('/users/')[1]
                if '/' in nickname:
                    nickname = nickname.split('/')[0]

                if not self.server.keyShortcuts.get(nickname):
                    accessKeys = self.server.accessKeys
                    self.server.keyShortcuts[nickname] = accessKeys.copy()
                accessKeys = self.server.keyShortcuts[nickname]

                self._keyShortcuts(self.path,
                                   callingDomain, cookie,
                                   self.server.base_dir,
                                   self.server.http_prefix,
                                   nickname,
                                   self.server.domain,
                                   self.server.domainFull,
                                   self.server.port,
                                   self.server.onion_domain,
                                   self.server.i2p_domain,
                                   self.server.debug,
                                   accessKeys,
                                   self.server.defaultTimeline)
                self.server.POSTbusy = False
                return

            # theme designer submit/cancel button
            if usersInPath and \
               self.path.endswith('/changeThemeSettings'):
                nickname = self.path.split('/users/')[1]
                if '/' in nickname:
                    nickname = nickname.split('/')[0]

                if not self.server.keyShortcuts.get(nickname):
                    accessKeys = self.server.accessKeys
                    self.server.keyShortcuts[nickname] = accessKeys.copy()
                accessKeys = self.server.keyShortcuts[nickname]

                self._themeDesigner(self.path,
                                    callingDomain, cookie,
                                    self.server.base_dir,
                                    self.server.http_prefix,
                                    nickname,
                                    self.server.domain,
                                    self.server.domainFull,
                                    self.server.port,
                                    self.server.onion_domain,
                                    self.server.i2p_domain,
                                    self.server.debug,
                                    accessKeys,
                                    self.server.defaultTimeline,
                                    self.server.themeName,
                                    self.server.allow_local_network_access,
                                    self.server.systemLanguage)
                self.server.POSTbusy = False
                return

        # update the shared item federation token for the calling domain
        # if it is within the permitted federation
        if self.headers.get('Origin') and \
           self.headers.get('SharesCatalog'):
            if self.server.debug:
                print('SharesCatalog header: ' + self.headers['SharesCatalog'])
            if not self.server.shared_items_federated_domains:
                siDomainsStr = getConfigParam(self.server.base_dir,
                                              'shared_items_federated_domains')
                if siDomainsStr:
                    if self.server.debug:
                        print('Loading shared items federated domains list')
                    siDomainsList = siDomainsStr.split(',')
                    domainsList = self.server.shared_items_federated_domains
                    for siDomain in siDomainsList:
                        domainsList.append(siDomain.strip())
            originDomain = self.headers.get('Origin')
            if originDomain != self.server.domainFull and \
               originDomain != self.server.onion_domain and \
               originDomain != self.server.i2p_domain and \
               originDomain in self.server.shared_items_federated_domains:
                if self.server.debug:
                    print('DEBUG: ' +
                          'POST updating shared item federation ' +
                          'token for ' + originDomain + ' to ' +
                          self.server.domainFull)
                sharedItemTokens = self.server.sharedItemFederationTokens
                sharesToken = self.headers['SharesCatalog']
                self.server.sharedItemFederationTokens = \
                    updateSharedItemFederationToken(self.server.base_dir,
                                                    originDomain,
                                                    sharesToken,
                                                    self.server.debug,
                                                    sharedItemTokens)
            elif self.server.debug:
                fed_domains = self.server.shared_items_federated_domains
                if originDomain not in fed_domains:
                    print('originDomain is not in federated domains list ' +
                          originDomain)
                else:
                    print('originDomain is not a different instance. ' +
                          originDomain + ' ' + self.server.domainFull + ' ' +
                          str(fed_domains))

        fitnessPerformance(POSTstartTime, self.server.fitness,
                           '_POST', 'SharesCatalog',
                           self.server.debug)

        # receive different types of post created by htmlNewPost
        newPostEndpoints = getNewPostEndpoints()
        for currPostType in newPostEndpoints:
            if not authorized:
                if self.server.debug:
                    print('POST was not authorized')
                break

            postRedirect = self.server.defaultTimeline
            if currPostType == 'newshare':
                postRedirect = 'tlshares'
            elif currPostType == 'newwanted':
                postRedirect = 'tlwanted'

            pageNumber = \
                self._receiveNewPost(currPostType, self.path,
                                     callingDomain, cookie,
                                     authorized,
                                     self.server.content_license_url)
            if pageNumber:
                print(currPostType + ' post received')
                nickname = self.path.split('/users/')[1]
                if '?' in nickname:
                    nickname = nickname.split('?')[0]
                if '/' in nickname:
                    nickname = nickname.split('/')[0]

                if callingDomain.endswith('.onion') and \
                   self.server.onion_domain:
                    actorPathStr = \
                        localActorUrl('http', nickname,
                                      self.server.onion_domain) + \
                        '/' + postRedirect + \
                        '?page=' + str(pageNumber)
                    self._redirect_headers(actorPathStr, cookie,
                                           callingDomain)
                elif (callingDomain.endswith('.i2p') and
                      self.server.i2p_domain):
                    actorPathStr = \
                        localActorUrl('http', nickname,
                                      self.server.i2p_domain) + \
                        '/' + postRedirect + \
                        '?page=' + str(pageNumber)
                    self._redirect_headers(actorPathStr, cookie,
                                           callingDomain)
                else:
                    actorPathStr = \
                        localActorUrl(self.server.http_prefix, nickname,
                                      self.server.domainFull) + \
                        '/' + postRedirect + '?page=' + str(pageNumber)
                    self._redirect_headers(actorPathStr, cookie,
                                           callingDomain)
                self.server.POSTbusy = False
                return

        fitnessPerformance(POSTstartTime, self.server.fitness,
                           '_POST', 'receive post',
                           self.server.debug)

        if self.path.endswith('/outbox') or \
           self.path.endswith('/wanted') or \
           self.path.endswith('/shares'):
            if usersInPath:
                if authorized:
                    self.outboxAuthenticated = True
                    pathUsersSection = self.path.split('/users/')[1]
                    self.postToNickname = pathUsersSection.split('/')[0]
            if not self.outboxAuthenticated:
                self.send_response(405)
                self.end_headers()
                self.server.POSTbusy = False
                return

        fitnessPerformance(POSTstartTime, self.server.fitness,
                           '_POST', 'authorized',
                           self.server.debug)

        # check that the post is to an expected path
        if not (self.path.endswith('/outbox') or
                self.path.endswith('/inbox') or
                self.path.endswith('/wanted') or
                self.path.endswith('/shares') or
                self.path.endswith('/moderationaction') or
                self.path == '/sharedInbox'):
            print('Attempt to POST to invalid path ' + self.path)
            self._400()
            self.server.POSTbusy = False
            return

        fitnessPerformance(POSTstartTime, self.server.fitness,
                           '_POST', 'check path',
                           self.server.debug)

        # read the message and convert it into a python dictionary
        length = int(self.headers['Content-length'])
        if self.server.debug:
            print('DEBUG: content-length: ' + str(length))
        if not self.headers['Content-type'].startswith('image/') and \
           not self.headers['Content-type'].startswith('video/') and \
           not self.headers['Content-type'].startswith('audio/'):
            if length > self.server.maxMessageLength:
                print('Maximum message length exceeded ' + str(length))
                self._400()
                self.server.POSTbusy = False
                return
        else:
            if length > self.server.maxMediaSize:
                print('Maximum media size exceeded ' + str(length))
                self._400()
                self.server.POSTbusy = False
                return

        # receive images to the outbox
        if self.headers['Content-type'].startswith('image/') and \
           usersInPath:
            self._receiveImage(length, callingDomain, cookie,
                               authorized, self.path,
                               self.server.base_dir,
                               self.server.http_prefix,
                               self.server.domain,
                               self.server.domainFull,
                               self.server.onion_domain,
                               self.server.i2p_domain,
                               self.server.debug)
            self.server.POSTbusy = False
            return

        # refuse to receive non-json content
        contentTypeStr = self.headers['Content-type']
        if not contentTypeStr.startswith('application/json') and \
           not contentTypeStr.startswith('application/activity+json') and \
           not contentTypeStr.startswith('application/ld+json'):
            print("POST is not json: " + self.headers['Content-type'])
            if self.server.debug:
                print(str(self.headers))
                length = int(self.headers['Content-length'])
                if length < self.server.maxPostLength:
                    try:
                        unknownPost = self.rfile.read(length).decode('utf-8')
                    except SocketError as ex:
                        if ex.errno == errno.ECONNRESET:
                            print('WARN: POST unknownPost ' +
                                  'connection reset by peer')
                        else:
                            print('WARN: POST unknownPost socket error')
                        self.send_response(400)
                        self.end_headers()
                        self.server.POSTbusy = False
                        return
                    except ValueError as ex:
                        print('ERROR: POST unknownPost rfile.read failed, ' +
                              str(ex))
                        self.send_response(400)
                        self.end_headers()
                        self.server.POSTbusy = False
                        return
                    print(str(unknownPost))
            self._400()
            self.server.POSTbusy = False
            return

        if self.server.debug:
            print('DEBUG: Reading message')

        fitnessPerformance(POSTstartTime, self.server.fitness,
                           '_POST', 'check content type',
                           self.server.debug)

        # check content length before reading bytes
        if self.path == '/sharedInbox' or self.path == '/inbox':
            length = 0
            if self.headers.get('Content-length'):
                length = int(self.headers['Content-length'])
            elif self.headers.get('Content-Length'):
                length = int(self.headers['Content-Length'])
            elif self.headers.get('content-length'):
                length = int(self.headers['content-length'])
            if length > 10240:
                print('WARN: post to shared inbox is too long ' +
                      str(length) + ' bytes')
                self._400()
                self.server.POSTbusy = False
                return

        try:
            messageBytes = self.rfile.read(length)
        except SocketError as ex:
            if ex.errno == errno.ECONNRESET:
                print('WARN: POST messageBytes ' +
                      'connection reset by peer')
            else:
                print('WARN: POST messageBytes socket error')
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy = False
            return
        except ValueError as ex:
            print('ERROR: POST messageBytes rfile.read failed, ' + str(ex))
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy = False
            return

        # check content length after reading bytes
        if self.path == '/sharedInbox' or self.path == '/inbox':
            lenMessage = len(messageBytes)
            if lenMessage > 10240:
                print('WARN: post to shared inbox is too long ' +
                      str(lenMessage) + ' bytes')
                self._400()
                self.server.POSTbusy = False
                return

        if containsInvalidChars(messageBytes.decode("utf-8")):
            self._400()
            self.server.POSTbusy = False
            return

        # convert the raw bytes to json
        messageJson = json.loads(messageBytes)

        fitnessPerformance(POSTstartTime, self.server.fitness,
                           '_POST', 'load json',
                           self.server.debug)

        # https://www.w3.org/TR/activitypub/#object-without-create
        if self.outboxAuthenticated:
            if self._postToOutbox(messageJson,
                                  self.server.project_version, None):
                if messageJson.get('id'):
                    locnStr = removeIdEnding(messageJson['id'])
                    self.headers['Location'] = locnStr
                self.send_response(201)
                self.end_headers()
                self.server.POSTbusy = False
                return
            else:
                if self.server.debug:
                    print('Failed to post to outbox')
                self.send_response(403)
                self.end_headers()
                self.server.POSTbusy = False
                return

        fitnessPerformance(POSTstartTime, self.server.fitness,
                           '_POST', '_postToOutbox',
                           self.server.debug)

        # check the necessary properties are available
        if self.server.debug:
            print('DEBUG: Check message has params')

        if not messageJson:
            self.send_response(403)
            self.end_headers()
            self.server.POSTbusy = False
            return

        if self.path.endswith('/inbox') or \
           self.path == '/sharedInbox':
            if not inboxMessageHasParams(messageJson):
                if self.server.debug:
                    print("DEBUG: inbox message doesn't have the " +
                          "required parameters")
                self.send_response(403)
                self.end_headers()
                self.server.POSTbusy = False
                return

        fitnessPerformance(POSTstartTime, self.server.fitness,
                           '_POST', 'inboxMessageHasParams',
                           self.server.debug)

        headerSignature = self._getheaderSignatureInput()

        if headerSignature:
            if 'keyId=' not in headerSignature:
                if self.server.debug:
                    print('DEBUG: POST to inbox has no keyId in ' +
                          'header signature parameter')
                self.send_response(403)
                self.end_headers()
                self.server.POSTbusy = False
                return

        fitnessPerformance(POSTstartTime, self.server.fitness,
                           '_POST', 'keyId check',
                           self.server.debug)

        if not self.server.unitTest:
            if not inboxPermittedMessage(self.server.domain,
                                         messageJson,
                                         self.server.federationList):
                if self.server.debug:
                    # https://www.youtube.com/watch?v=K3PrSj9XEu4
                    print('DEBUG: Ah Ah Ah')
                self.send_response(403)
                self.end_headers()
                self.server.POSTbusy = False
                return

        fitnessPerformance(POSTstartTime, self.server.fitness,
                           '_POST', 'inboxPermittedMessage',
                           self.server.debug)

        if self.server.debug:
            print('DEBUG: POST saving to inbox queue')
        if usersInPath:
            pathUsersSection = self.path.split('/users/')[1]
            if '/' not in pathUsersSection:
                if self.server.debug:
                    print('DEBUG: This is not a users endpoint')
            else:
                self.postToNickname = pathUsersSection.split('/')[0]
                if self.postToNickname:
                    queueStatus = \
                        self._updateInboxQueue(self.postToNickname,
                                               messageJson, messageBytes)
                    if queueStatus >= 0 and queueStatus <= 3:
                        self.server.POSTbusy = False
                        return
                    if self.server.debug:
                        print('_updateInboxQueue exited ' +
                              'without doing anything')
                else:
                    if self.server.debug:
                        print('self.postToNickname is None')
            self.send_response(403)
            self.end_headers()
            self.server.POSTbusy = False
            return
        else:
            if self.path == '/sharedInbox' or self.path == '/inbox':
                if self.server.debug:
                    print('DEBUG: POST to shared inbox')
                queueStatus = \
                    self._updateInboxQueue('inbox', messageJson, messageBytes)
                if queueStatus >= 0 and queueStatus <= 3:
                    self.server.POSTbusy = False
                    return
        self._200()
        self.server.POSTbusy = False


class PubServerUnitTest(PubServer):
    protocol_version = 'HTTP/1.0'


class EpicyonServer(ThreadingHTTPServer):
    def handle_error(self, request, client_address):
        # surpress connection reset errors
        cls, e = sys.exc_info()[:2]
        if cls is ConnectionResetError:
            if e.errno != errno.ECONNRESET:
                print('ERROR: (EpicyonServer) ' + str(cls) + ", " + str(e))
            pass
        elif cls is BrokenPipeError:
            pass
        else:
            print('ERROR: (EpicyonServer) ' + str(cls) + ", " + str(e))
            return HTTPServer.handle_error(self, request, client_address)


def runPostsQueue(base_dir: str, sendThreads: [], debug: bool,
                  timeoutMins: int) -> None:
    """Manages the threads used to send posts
    """
    while True:
        time.sleep(1)
        removeDormantThreads(base_dir, sendThreads, debug, timeoutMins)


def runSharesExpire(versionNumber: str, base_dir: str) -> None:
    """Expires shares as needed
    """
    while True:
        time.sleep(120)
        expireShares(base_dir)


def runPostsWatchdog(project_version: str, httpd) -> None:
    """This tries to keep the posts thread running even if it dies
    """
    print('Starting posts queue watchdog')
    postsQueueOriginal = httpd.thrPostsQueue.clone(runPostsQueue)
    httpd.thrPostsQueue.start()
    while True:
        time.sleep(20)
        if httpd.thrPostsQueue.is_alive():
            continue
        httpd.thrPostsQueue.kill()
        httpd.thrPostsQueue = postsQueueOriginal.clone(runPostsQueue)
        httpd.thrPostsQueue.start()
        print('Restarting posts queue...')


def runSharesExpireWatchdog(project_version: str, httpd) -> None:
    """This tries to keep the shares expiry thread running even if it dies
    """
    print('Starting shares expiry watchdog')
    sharesExpireOriginal = httpd.thrSharesExpire.clone(runSharesExpire)
    httpd.thrSharesExpire.start()
    while True:
        time.sleep(20)
        if httpd.thrSharesExpire.is_alive():
            continue
        httpd.thrSharesExpire.kill()
        httpd.thrSharesExpire = sharesExpireOriginal.clone(runSharesExpire)
        httpd.thrSharesExpire.start()
        print('Restarting shares expiry...')


def loadTokens(base_dir: str, tokensDict: {}, tokensLookup: {}) -> None:
    for subdir, dirs, files in os.walk(base_dir + '/accounts'):
        for handle in dirs:
            if '@' in handle:
                tokenFilename = base_dir + '/accounts/' + handle + '/.token'
                if not os.path.isfile(tokenFilename):
                    continue
                nickname = handle.split('@')[0]
                token = None
                try:
                    with open(tokenFilename, 'r') as fp:
                        token = fp.read()
                except Exception as ex:
                    print('WARN: Unable to read token for ' +
                          nickname + ' ' + str(ex))
                if not token:
                    continue
                tokensDict[nickname] = token
                tokensLookup[token] = nickname
        break


def runDaemon(content_license_url: str,
              lists_enabled: str,
              default_reply_interval_hrs: int,
              low_bandwidth: bool,
              max_like_count: int,
              shared_items_federated_domains: [],
              user_agents_blocked: [],
              log_login_failures: bool,
              city: str,
              show_node_info_accounts: bool,
              show_node_info_version: bool,
              broch_mode: bool,
              verify_all_signatures: bool,
              send_threads_timeout_mins: int,
              dormant_months: int,
              max_newswire_posts: int,
              allow_local_network_access: bool,
              max_feed_item_size_kb: int,
              publish_button_at_top: bool,
              rss_icon_at_top: bool,
              icons_as_buttons: bool,
              full_width_tl_button_header: bool,
              show_publish_as_icon: bool,
              max_followers: int,
              max_news_posts: int,
              max_mirrored_articles: int,
              max_newswire_feed_size_kb: int,
              max_newswire_postsPerSource: int,
              show_published_date_only: bool,
              voting_time_mins: int,
              positive_voting: bool,
              newswire_votes_threshold: int,
              news_instance: bool,
              blogs_instance: bool,
              media_instance: bool,
              max_recent_posts: int,
              enable_shared_inbox: bool, registration: bool,
              language: str, project_version: str,
              instance_id: str, client_to_server: bool,
              base_dir: str, domain: str,
              onion_domain: str, i2p_domain: str,
              yt_replace_domain: str,
              twitter_replacement_domain: str,
              port: int = 80, proxy_port: int = 80,
              http_prefix: str = 'https',
              fed_list: [] = [],
              max_mentions: int = 10, max_emoji: int = 10,
              secure_mode: bool = False,
              proxy_type: str = None, max_replies: int = 64,
              domain_max_posts_per_day: int = 8640,
              account_max_posts_per_day: int = 864,
              allowDeletion: bool = False,
              debug: bool = False, unitTest: bool = False,
              instanceOnlySkillsSearch: bool = False,
              sendThreads: [] = [],
              manualFollowerApproval: bool = True) -> None:
    if len(domain) == 0:
        domain = 'localhost'
    if '.' not in domain:
        if domain != 'localhost':
            print('Invalid domain: ' + domain)
            return

    if unitTest:
        serverAddress = (domain, proxy_port)
        pubHandler = partial(PubServerUnitTest)
    else:
        serverAddress = ('', proxy_port)
        pubHandler = partial(PubServer)

    if not os.path.isdir(base_dir + '/accounts'):
        print('Creating accounts directory')
        os.mkdir(base_dir + '/accounts')

    try:
        httpd = EpicyonServer(serverAddress, pubHandler)
    except Exception as ex:
        if ex.errno == 98:
            print('ERROR: HTTP server address is already in use. ' +
                  str(serverAddress))
            return False

        print('ERROR: HTTP server failed to start. ' + str(ex))
        print('serverAddress: ' + str(serverAddress))
        return False

    # scan the theme directory for any svg files containing scripts
    assert not scanThemesForScripts(base_dir)

    # license for content of the instance
    if not content_license_url:
        content_license_url = 'https://creativecommons.org/licenses/by/4.0'
    httpd.content_license_url = content_license_url

    # fitness metrics
    fitnessFilename = base_dir + '/accounts/fitness.json'
    httpd.fitness = {}
    if os.path.isfile(fitnessFilename):
        httpd.fitness = loadJson(fitnessFilename)

    # initialize authorized fetch key
    httpd.signingPrivateKeyPem = None

    httpd.show_node_info_accounts = show_node_info_accounts
    httpd.show_node_info_version = show_node_info_version

    # ASCII/ANSI text banner used in shell browsers, such as Lynx
    httpd.textModeBanner = getTextModeBanner(base_dir)

    # key shortcuts SHIFT + ALT + [key]
    httpd.accessKeys = {
        'Page up': ',',
        'Page down': '.',
        'submitButton': 'y',
        'followButton': 'f',
        'blockButton': 'b',
        'infoButton': 'i',
        'snoozeButton': 's',
        'reportButton': '[',
        'viewButton': 'v',
        'enterPetname': 'p',
        'enterNotes': 'n',
        'menuTimeline': 't',
        'menuEdit': 'e',
        'menuThemeDesigner': 'z',
        'menuProfile': 'p',
        'menuInbox': 'i',
        'menuSearch': '/',
        'menuNewPost': 'n',
        'menuCalendar': 'c',
        'menuDM': 'd',
        'menuReplies': 'r',
        'menuOutbox': 's',
        'menuBookmarks': 'q',
        'menuShares': 'h',
        'menuWanted': 'w',
        'menuBlogs': 'b',
        'menuNewswire': 'u',
        'menuLinks': 'l',
        'menuMedia': 'm',
        'menuModeration': 'o',
        'menuFollowing': 'f',
        'menuFollowers': 'g',
        'menuRoles': 'o',
        'menuSkills': 'a',
        'menuLogout': 'x',
        'menuKeys': 'k',
        'Public': 'p',
        'Reminder': 'r'
    }

    # how many hours after a post was publushed can a reply be made
    default_reply_interval_hrs = 9999999
    httpd.default_reply_interval_hrs = default_reply_interval_hrs

    httpd.keyShortcuts = {}
    loadAccessKeysForAccounts(base_dir, httpd.keyShortcuts, httpd.accessKeys)

    # wheither to use low bandwidth images
    httpd.low_bandwidth = low_bandwidth

    # list of blocked user agent types within the User-Agent header
    httpd.user_agents_blocked = user_agents_blocked

    httpd.unitTest = unitTest
    httpd.allow_local_network_access = allow_local_network_access
    if unitTest:
        # unit tests are run on the local network with LAN addresses
        httpd.allow_local_network_access = True
    httpd.yt_replace_domain = yt_replace_domain
    httpd.twitter_replacement_domain = twitter_replacement_domain

    # newswire storing rss feeds
    httpd.newswire = {}

    # maximum number of posts to appear in the newswire on the right column
    httpd.max_newswire_posts = max_newswire_posts

    # whether to require that all incoming posts have valid jsonld signatures
    httpd.verify_all_signatures = verify_all_signatures

    # This counter is used to update the list of blocked domains in memory.
    # It helps to avoid touching the disk and so improves flooding resistance
    httpd.blocklistUpdateCtr = 0
    httpd.blocklistUpdateInterval = 100
    httpd.domainBlocklist = getDomainBlocklist(base_dir)

    httpd.manualFollowerApproval = manualFollowerApproval
    httpd.onion_domain = onion_domain
    httpd.i2p_domain = i2p_domain
    httpd.media_instance = media_instance
    httpd.blogs_instance = blogs_instance

    # load translations dictionary
    httpd.translate = {}
    httpd.systemLanguage = 'en'
    if not unitTest:
        httpd.translate, httpd.systemLanguage = \
            loadTranslationsFromFile(base_dir, language)
        if not httpd.systemLanguage:
            print('ERROR: no system language loaded')
            sys.exit()
        print('System language: ' + httpd.systemLanguage)
        if not httpd.translate:
            print('ERROR: no translations were loaded')
            sys.exit()

    # spoofed city for gps location misdirection
    httpd.city = city

    # For moderated newswire feeds this is the amount of time allowed
    # for voting after the post arrives
    httpd.voting_time_mins = voting_time_mins
    # on the newswire, whether moderators vote positively for items
    # or against them (veto)
    httpd.positive_voting = positive_voting
    # number of votes needed to remove a newswire item from the news timeline
    # or if positive voting is anabled to add the item to the news timeline
    httpd.newswire_votes_threshold = newswire_votes_threshold
    # maximum overall size of an rss/atom feed read by the newswire daemon
    # If the feed is too large then this is probably a DoS attempt
    httpd.max_newswire_feed_size_kb = max_newswire_feed_size_kb

    # For each newswire source (account or rss feed)
    # this is the maximum number of posts to show for each.
    # This avoids one or two sources from dominating the news,
    # and also prevents big feeds from slowing down page load times
    httpd.max_newswire_postsPerSource = max_newswire_postsPerSource

    # Show only the date at the bottom of posts, and not the time
    httpd.show_published_date_only = show_published_date_only

    # maximum number of news articles to mirror
    httpd.max_mirrored_articles = max_mirrored_articles

    # maximum number of posts in the news timeline/outbox
    httpd.max_news_posts = max_news_posts

    # The maximum number of tags per post which can be
    # attached to RSS feeds pulled in via the newswire
    httpd.maxTags = 32

    # maximum number of followers per account
    httpd.max_followers = max_followers

    # whether to show an icon for publish on the
    # newswire, or a 'Publish' button
    httpd.show_publish_as_icon = show_publish_as_icon

    # Whether to show the timeline header containing inbox, outbox
    # calendar, etc as the full width of the screen or not
    httpd.full_width_tl_button_header = full_width_tl_button_header

    # whether to show icons in the header (eg calendar) as buttons
    httpd.icons_as_buttons = icons_as_buttons

    # whether to show the RSS icon at the top or the bottom of the timeline
    httpd.rss_icon_at_top = rss_icon_at_top

    # Whether to show the newswire publish button at the top,
    # above the header image
    httpd.publish_button_at_top = publish_button_at_top

    # maximum size of individual RSS feed items, in K
    httpd.max_feed_item_size_kb = max_feed_item_size_kb

    # maximum size of a hashtag category, in K
    httpd.maxCategoriesFeedItemSizeKb = 1024

    # how many months does a followed account need to be unseen
    # for it to be considered dormant?
    httpd.dormant_months = dormant_months

    # maximum number of likes to display on a post
    httpd.max_like_count = max_like_count
    if httpd.max_like_count < 0:
        httpd.max_like_count = 0
    elif httpd.max_like_count > 16:
        httpd.max_like_count = 16

    httpd.followingItemsPerPage = 12
    if registration == 'open':
        httpd.registration = True
    else:
        httpd.registration = False
    httpd.enable_shared_inbox = enable_shared_inbox
    httpd.outboxThread = {}
    httpd.outboxThreadIndex = {}
    httpd.newPostThread = {}
    httpd.project_version = project_version
    httpd.secure_mode = secure_mode
    # max POST size of 30M
    httpd.maxPostLength = 1024 * 1024 * 30
    httpd.maxMediaSize = httpd.maxPostLength
    # Maximum text length is 64K - enough for a blog post
    httpd.maxMessageLength = 64000
    # Maximum overall number of posts per box
    httpd.maxPostsInBox = 32000
    httpd.domain = domain
    httpd.port = port
    httpd.domainFull = getFullDomain(domain, port)
    saveDomainQrcode(base_dir, http_prefix, httpd.domainFull)
    httpd.http_prefix = http_prefix
    httpd.debug = debug
    httpd.federationList = fed_list.copy()
    httpd.shared_items_federated_domains = \
        shared_items_federated_domains.copy()
    httpd.base_dir = base_dir
    httpd.instance_id = instance_id
    httpd.personCache = {}
    httpd.cachedWebfingers = {}
    httpd.faviconsCache = {}
    httpd.proxy_type = proxy_type
    httpd.session = None
    httpd.sessionLastUpdate = 0
    httpd.lastGET = 0
    httpd.lastPOST = 0
    httpd.GETbusy = False
    httpd.POSTbusy = False
    httpd.receivedMessage = False
    httpd.inboxQueue = []
    httpd.sendThreads = sendThreads
    httpd.postLog = []
    httpd.maxQueueLength = 64
    httpd.allowDeletion = allowDeletion
    httpd.lastLoginTime = 0
    httpd.lastLoginFailure = 0
    httpd.loginFailureCount = {}
    httpd.log_login_failures = log_login_failures
    httpd.max_replies = max_replies
    httpd.tokens = {}
    httpd.tokensLookup = {}
    loadTokens(base_dir, httpd.tokens, httpd.tokensLookup)
    httpd.instanceOnlySkillsSearch = instanceOnlySkillsSearch
    # contains threads used to send posts to followers
    httpd.followersThreads = []

    # create a cache of blocked domains in memory.
    # This limits the amount of slow disk reads which need to be done
    httpd.blockedCache = []
    httpd.blockedCacheLastUpdated = 0
    httpd.blockedCacheUpdateSecs = 120
    httpd.blockedCacheLastUpdated = \
        updateBlockedCache(base_dir, httpd.blockedCache,
                           httpd.blockedCacheLastUpdated,
                           httpd.blockedCacheUpdateSecs)

    # cache to store css files
    httpd.cssCache = {}

    # get the list of custom emoji, for use by the mastodon api
    httpd.customEmoji = \
        metadataCustomEmoji(base_dir, http_prefix, httpd.domainFull)

    # whether to enable broch mode, which locks down the instance
    setBrochMode(base_dir, httpd.domainFull, broch_mode)

    if not os.path.isdir(base_dir + '/accounts/inbox@' + domain):
        print('Creating shared inbox: inbox@' + domain)
        createSharedInbox(base_dir, 'inbox', domain, port, http_prefix)

    if not os.path.isdir(base_dir + '/accounts/news@' + domain):
        print('Creating news inbox: news@' + domain)
        createNewsInbox(base_dir, domain, port, http_prefix)
        setConfigParam(base_dir, "lists_enabled", "Murdoch press")

    # dict of known web crawlers accessing nodeinfo or the masto API
    # and how many times they have been seen
    httpd.knownCrawlers = {}
    knownCrawlersFilename = base_dir + '/accounts/knownCrawlers.json'
    if os.path.isfile(knownCrawlersFilename):
        httpd.knownCrawlers = loadJson(knownCrawlersFilename)
    # when was the last crawler seen?
    httpd.lastKnownCrawler = 0

    if lists_enabled:
        httpd.lists_enabled = lists_enabled
    else:
        httpd.lists_enabled = getConfigParam(base_dir, "lists_enabled")
    httpd.CWlists = loadCWLists(base_dir, True)

    # set the avatar for the news account
    httpd.themeName = getConfigParam(base_dir, 'theme')
    if not httpd.themeName:
        httpd.themeName = 'default'
    if isNewsThemeName(base_dir, httpd.themeName):
        news_instance = True

    httpd.news_instance = news_instance
    httpd.defaultTimeline = 'inbox'
    if media_instance:
        httpd.defaultTimeline = 'tlmedia'
    if blogs_instance:
        httpd.defaultTimeline = 'tlblogs'
    if news_instance:
        httpd.defaultTimeline = 'tlfeatures'

    setNewsAvatar(base_dir,
                  httpd.themeName,
                  http_prefix,
                  domain,
                  httpd.domainFull)

    if not os.path.isdir(base_dir + '/cache'):
        os.mkdir(base_dir + '/cache')
    if not os.path.isdir(base_dir + '/cache/actors'):
        print('Creating actors cache')
        os.mkdir(base_dir + '/cache/actors')
    if not os.path.isdir(base_dir + '/cache/announce'):
        print('Creating announce cache')
        os.mkdir(base_dir + '/cache/announce')
    if not os.path.isdir(base_dir + '/cache/avatars'):
        print('Creating avatars cache')
        os.mkdir(base_dir + '/cache/avatars')

    archiveDir = base_dir + '/archive'
    if not os.path.isdir(archiveDir):
        print('Creating archive')
        os.mkdir(archiveDir)

    if not os.path.isdir(base_dir + '/sharefiles'):
        print('Creating shared item files directory')
        os.mkdir(base_dir + '/sharefiles')

    print('Creating fitness thread')
    httpd.thrFitness = \
        threadWithTrace(target=fitnessThread,
                        args=(base_dir, httpd.fitness), daemon=True)
    httpd.thrFitness.start()

    print('Creating cache expiry thread')
    httpd.thrCache = \
        threadWithTrace(target=expireCache,
                        args=(base_dir, httpd.personCache,
                              httpd.http_prefix,
                              archiveDir,
                              httpd.maxPostsInBox), daemon=True)
    httpd.thrCache.start()

    # number of mins after which sending posts or updates will expire
    httpd.send_threads_timeout_mins = send_threads_timeout_mins

    print('Creating posts queue')
    httpd.thrPostsQueue = \
        threadWithTrace(target=runPostsQueue,
                        args=(base_dir, httpd.sendThreads, debug,
                              httpd.send_threads_timeout_mins), daemon=True)
    if not unitTest:
        httpd.thrPostsWatchdog = \
            threadWithTrace(target=runPostsWatchdog,
                            args=(project_version, httpd), daemon=True)
        httpd.thrPostsWatchdog.start()
    else:
        httpd.thrPostsQueue.start()

    print('Creating expire thread for shared items')
    httpd.thrSharesExpire = \
        threadWithTrace(target=runSharesExpire,
                        args=(project_version, base_dir), daemon=True)
    if not unitTest:
        httpd.thrSharesExpireWatchdog = \
            threadWithTrace(target=runSharesExpireWatchdog,
                            args=(project_version, httpd), daemon=True)
        httpd.thrSharesExpireWatchdog.start()
    else:
        httpd.thrSharesExpire.start()

    httpd.recentPostsCache = {}
    httpd.max_recent_posts = max_recent_posts
    httpd.iconsCache = {}
    httpd.fontsCache = {}

    # create tokens used for shared item federation
    fed_domains = httpd.shared_items_federated_domains
    httpd.sharedItemFederationTokens = \
        generateSharedItemFederationTokens(fed_domains,
                                           base_dir)
    httpd.sharedItemFederationTokens = \
        createSharedItemFederationToken(base_dir, httpd.domainFull, False,
                                        httpd.sharedItemFederationTokens)

    # load peertube instances from file into a list
    httpd.peertubeInstances = []
    loadPeertubeInstances(base_dir, httpd.peertubeInstances)

    createInitialLastSeen(base_dir, http_prefix)

    print('Creating inbox queue')
    httpd.thrInboxQueue = \
        threadWithTrace(target=runInboxQueue,
                        args=(httpd.recentPostsCache,
                              httpd.max_recent_posts,
                              project_version,
                              base_dir, http_prefix, httpd.sendThreads,
                              httpd.postLog, httpd.cachedWebfingers,
                              httpd.personCache, httpd.inboxQueue,
                              domain, onion_domain, i2p_domain,
                              port, proxy_type,
                              httpd.federationList,
                              max_replies,
                              domain_max_posts_per_day,
                              account_max_posts_per_day,
                              allowDeletion, debug,
                              max_mentions, max_emoji,
                              httpd.translate, unitTest,
                              httpd.yt_replace_domain,
                              httpd.twitter_replacement_domain,
                              httpd.show_published_date_only,
                              httpd.max_followers,
                              httpd.allow_local_network_access,
                              httpd.peertubeInstances,
                              verify_all_signatures,
                              httpd.themeName,
                              httpd.systemLanguage,
                              httpd.max_like_count,
                              httpd.signingPrivateKeyPem,
                              httpd.default_reply_interval_hrs,
                              httpd.CWlists), daemon=True)

    print('Creating scheduled post thread')
    httpd.thrPostSchedule = \
        threadWithTrace(target=runPostSchedule,
                        args=(base_dir, httpd, 20), daemon=True)

    print('Creating newswire thread')
    httpd.thrNewswireDaemon = \
        threadWithTrace(target=runNewswireDaemon,
                        args=(base_dir, httpd,
                              http_prefix, domain, port,
                              httpd.translate), daemon=True)

    print('Creating federated shares thread')
    httpd.thrFederatedSharesDaemon = \
        threadWithTrace(target=runFederatedSharesDaemon,
                        args=(base_dir, httpd,
                              http_prefix, httpd.domainFull,
                              proxy_type, debug,
                              httpd.systemLanguage), daemon=True)

    # flags used when restarting the inbox queue
    httpd.restartInboxQueueInProgress = False
    httpd.restartInboxQueue = False

    updateHashtagCategories(base_dir)

    print('Adding hashtag categories for language ' + httpd.systemLanguage)
    loadHashtagCategories(base_dir, httpd.systemLanguage)

    # signing key used for authorized fetch
    # this is the instance actor private key
    httpd.signingPrivateKeyPem = getInstanceActorKey(base_dir, domain)

    if not unitTest:
        print('Creating inbox queue watchdog')
        httpd.thrWatchdog = \
            threadWithTrace(target=runInboxQueueWatchdog,
                            args=(project_version, httpd), daemon=True)
        httpd.thrWatchdog.start()

        print('Creating scheduled post watchdog')
        httpd.thrWatchdogSchedule = \
            threadWithTrace(target=runPostScheduleWatchdog,
                            args=(project_version, httpd), daemon=True)
        httpd.thrWatchdogSchedule.start()

        print('Creating newswire watchdog')
        httpd.thrNewswireWatchdog = \
            threadWithTrace(target=runNewswireWatchdog,
                            args=(project_version, httpd), daemon=True)
        httpd.thrNewswireWatchdog.start()

        print('Creating federated shares watchdog')
        httpd.thrFederatedSharesWatchdog = \
            threadWithTrace(target=runFederatedSharesWatchdog,
                            args=(project_version, httpd), daemon=True)
        httpd.thrFederatedSharesWatchdog.start()
    else:
        print('Starting inbox queue')
        httpd.thrInboxQueue.start()
        print('Starting scheduled posts daemon')
        httpd.thrPostSchedule.start()
        print('Starting federated shares daemon')
        httpd.thrFederatedSharesDaemon.start()

    if client_to_server:
        print('Running ActivityPub client on ' +
              domain + ' port ' + str(proxy_port))
    else:
        print('Running ActivityPub server on ' +
              domain + ' port ' + str(proxy_port))
    httpd.serve_forever()
