__filename__ = "daemon.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.1.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@freedombone.net"
__status__ = "Production"

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer, HTTPServer
import sys
import json
import time
import locale
import urllib.parse
from socket import error as SocketError
import errno
from functools import partial
import pyqrcode
# for saving images
from hashlib import sha256
from hashlib import sha1
from session import createSession
from webfinger import parseHandle
from webfinger import webfingerMeta
from webfinger import webfingerNodeInfo
from webfinger import webfingerLookup
from webfinger import webfingerUpdate
from metadata import metaDataInstance
from metadata import metaDataNodeInfo
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
from matrix import getMatrixAddress
from matrix import setMatrixAddress
from donate import getDonationUrl
from donate import setDonationUrl
from person import setPersonNotes
from person import getDefaultPersonContext
from person import savePersonQrcode
from person import randomizeActorImages
from person import personUpgradeActor
from person import activateAccount
from person import deactivateAccount
from person import registerAccount
from person import personLookup
from person import personBoxJson
from person import createSharedInbox
from person import suspendAccount
from person import unsuspendAccount
from person import removeAccount
from person import canRemovePost
from person import personSnooze
from person import personUnsnooze
from posts import isModerator
from posts import mutePost
from posts import unmutePost
from posts import createQuestionPost
from posts import createPublicPost
from posts import createBlogPost
from posts import createReportPost
from posts import createUnlistedPost
from posts import createFollowersOnlyPost
from posts import createEventPost
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
from inbox import getPersonPubKey
from follow import getFollowingFeed
from follow import sendFollowRequest
from auth import authorize
from auth import createPassword
from auth import createBasicAuthHeader
from auth import authorizeBasic
from auth import storeBasicCredentials
from threads import threadWithTrace
from threads import removeDormantThreads
from media import replaceYouTube
from media import attachMedia
from blocking import addBlock
from blocking import removeBlock
from blocking import addGlobalBlock
from blocking import removeGlobalBlock
from blocking import isBlockedHashtag
from blocking import isBlockedDomain
from blocking import getDomainBlocklist
from roles import setRole
from roles import clearModeratorStatus
from blog import htmlBlogPageRSS2
from blog import htmlBlogPageRSS3
from blog import htmlBlogView
from blog import htmlBlogPage
from blog import htmlBlogPost
from blog import htmlEditBlog
from webinterface import htmlFollowingList
from webinterface import getBlogAddress
from webinterface import setBlogAddress
from webinterface import htmlCalendarDeleteConfirm
from webinterface import htmlDeletePost
from webinterface import htmlAbout
from webinterface import htmlRemoveSharedItem
from webinterface import htmlInboxDMs
from webinterface import htmlInboxReplies
from webinterface import htmlInboxMedia
from webinterface import htmlInboxBlogs
from webinterface import htmlUnblockConfirm
from webinterface import htmlPersonOptions
from webinterface import htmlIndividualPost
from webinterface import htmlProfile
from webinterface import htmlInbox
from webinterface import htmlBookmarks
from webinterface import htmlEvents
from webinterface import htmlShares
from webinterface import htmlOutbox
from webinterface import htmlModeration
from webinterface import htmlPostReplies
from webinterface import htmlLogin
from webinterface import htmlSuspended
from webinterface import htmlGetLoginCredentials
from webinterface import htmlNewPost
from webinterface import htmlFollowConfirm
from webinterface import htmlCalendar
from webinterface import htmlSearch
from webinterface import htmlSearchEmoji
from webinterface import htmlSearchEmojiTextEntry
from webinterface import htmlUnfollowConfirm
from webinterface import htmlProfileAfterSearch
from webinterface import htmlEditProfile
from webinterface import htmlEditLinks
from webinterface import htmlEditNewswire
from webinterface import htmlTermsOfService
from webinterface import htmlSkillsSearch
from webinterface import htmlHistorySearch
from webinterface import htmlHashtagSearch
from webinterface import rssHashtagSearch
from webinterface import htmlModerationInfo
from webinterface import htmlSearchSharedItems
from webinterface import htmlHashtagBlocked
from shares import getSharesFeedForPerson
from shares import addShare
from shares import removeShare
from shares import expireShares
from utils import setConfigParam
from utils import getConfigParam
from utils import removeIdEnding
from utils import updateLikesCollection
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
from manualapprove import manualDenyFollowRequest
from manualapprove import manualApproveFollowRequest
from announce import createAnnounce
from content import replaceEmojiFromTags
from content import addHtmlTags
from content import extractMediaInFormPOST
from content import saveMediaInFormPOST
from content import extractTextFieldsInPOST
from media import removeMetaData
from cache import storePersonInCache
from cache import getPersonFromCache
from httpsig import verifyPostHeaders
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
from devices import E2EEdevicesCollection
from devices import E2EEvalidDevice
from devices import E2EEaddDevice
from newswire import getRSSfromDict
from newswire import runNewswireWatchdog
from newswire import runNewswireDaemon
import os


# maximum number of posts to list in outbox feed
maxPostsInFeed = 12

# reduced posts for media feed because it can take a while
maxPostsInMediaFeed = 6

# Blogs can be longer, so don't show many per page
maxPostsInBlogsFeed = 4

# Maximum number of entries in returned rss.xml
maxPostsInRSSFeed = 10

# number of follows/followers per page
followsPerPage = 12

# number of item shares per page
sharesPerPage = 12


def saveDomainQrcode(baseDir: str, httpPrefix: str,
                     domainFull: str, scale=6) -> None:
    """Saves a qrcode image for the domain name
    This helps to transfer onion or i2p domains to a mobile device
    """
    qrcodeFilename = baseDir + '/accounts/qrcode.png'
    url = pyqrcode.create(httpPrefix + '://' + domainFull)
    url.png(qrcodeFilename, scale)


def readFollowList(filename: str) -> None:
    """Returns a list of ActivityPub addresses to follow
    """
    followlist = []
    if not os.path.isfile(filename):
        return followlist
    followUsers = open(filename, "r")
    for u in followUsers:
        if u not in followlist:
            nickname, domain = parseHandle(u)
            if nickname:
                followlist.append(nickname + '@' + domain)
    followUsers.close()
    return followlist


class PubServer(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def _pathIsImage(self, path: str) -> bool:
        if path.endswith('.png') or \
           path.endswith('.jpg') or \
           path.endswith('.gif') or \
           path.endswith('.avif') or \
           path.endswith('.webp'):
            return True
        return False

    def _pathIsVideo(self, path: str) -> bool:
        if path.endswith('.ogv') or \
           path.endswith('.mp4'):
            return True
        return False

    def _pathIsAudio(self, path: str) -> bool:
        if path.endswith('.ogg') or \
           path.endswith('.mp3'):
            return True
        return False

    def handle_error(self, request, client_address):
        print('ERROR: http server error: ' + str(request) + ', ' +
              str(client_address))
        pass

    def _isMinimal(self, nickname: str) -> bool:
        """Returns true if minimal buttons should be shown
        for the given account
        """
        accountDir = self.server.baseDir + '/accounts/' + \
            nickname + '@' + self.server.domain
        if not os.path.isdir(accountDir):
            return False
        minimalFilename = accountDir + '/minimal'
        if os.path.isfile(minimalFilename):
            return True
        return False

    def _setMinimal(self, nickname: str, minimal: bool) -> None:
        """Sets whether an account should display minimal buttons
        """
        accountDir = self.server.baseDir + '/accounts/' + \
            nickname + '@' + self.server.domain
        if not os.path.isdir(accountDir):
            return
        minimalFilename = accountDir + '/minimal'
        minimalFileExists = os.path.isfile(minimalFilename)
        if not minimal and minimalFileExists:
            os.remove(minimalFilename)
        elif minimal and not minimalFileExists:
            with open(minimalFilename, 'w+') as fp:
                fp.write('\n')

    def _sendReplyToQuestion(self, nickname: str, messageId: str,
                             answer: str) -> None:
        """Sends a reply to a question
        """
        votesFilename = self.server.baseDir + '/accounts/' + \
            nickname + '@' + self.server.domain + '/questions.txt'

        if os.path.isfile(votesFilename):
            # have we already voted on this?
            if messageId in open(votesFilename).read():
                print('Already voted on message ' + messageId)
                return

        print('Voting on message ' + messageId)
        print('Vote for: ' + answer)
        commentsEnabled = True
        messageJson = \
            createPublicPost(self.server.baseDir,
                             nickname,
                             self.server.domain, self.server.port,
                             self.server.httpPrefix,
                             answer, False, False, False,
                             commentsEnabled,
                             None, None, None, True,
                             messageId, messageId, None,
                             False, None, None, None)
        if messageJson:
            # name field contains the answer
            messageJson['object']['name'] = answer
            if self._postToOutbox(messageJson, __version__, nickname):
                postFilename = \
                    locatePost(self.server.baseDir, nickname,
                               self.server.domain, messageId)
                if postFilename:
                    postJsonObject = loadJson(postFilename)
                    if postJsonObject:
                        populateReplies(self.server.baseDir,
                                        self.server.httpPrefix,
                                        self.server.domainFull,
                                        postJsonObject,
                                        self.server.maxReplies,
                                        self.server.debug)
                        # record the vote
                        votesFile = open(votesFilename, 'a+')
                        if votesFile:
                            votesFile.write(messageId + '\n')
                            votesFile.close()

                        # ensure that the cached post is removed if it exists,
                        # so that it then will be recreated
                        cachedPostFilename = \
                            getCachedPostFilename(self.server.baseDir,
                                                  nickname,
                                                  self.server.domain,
                                                  postJsonObject)
                        if cachedPostFilename:
                            if os.path.isfile(cachedPostFilename):
                                os.remove(cachedPostFilename)
                        # remove from memory cache
                        removePostFromCache(postJsonObject,
                                            self.server.recentPostsCache)
            else:
                print('ERROR: unable to post vote to outbox')
        else:
            print('ERROR: unable to create vote')

    def _removePostInteractions(self, postJsonObject: {}) -> None:
        """Removes potentially sensitive interactions from a post
        This is the type of thing which would be of interest to marketers
        or of saleable value to them. eg. Knowing who likes who or what.
        """
        if postJsonObject.get('likes'):
            postJsonObject['likes'] = {'items': []}
        if postJsonObject.get('shares'):
            postJsonObject['shares'] = {}
        if postJsonObject.get('replies'):
            postJsonObject['replies'] = {}
        if postJsonObject.get('bookmarks'):
            postJsonObject['bookmarks'] = {}
        if not postJsonObject.get('object'):
            return
        if not isinstance(postJsonObject['object'], dict):
            return
        if postJsonObject['object'].get('likes'):
            postJsonObject['object']['likes'] = {'items': []}
        if postJsonObject['object'].get('shares'):
            postJsonObject['object']['shares'] = {}
        if postJsonObject['object'].get('replies'):
            postJsonObject['object']['replies'] = {}
        if postJsonObject['object'].get('bookmarks'):
            postJsonObject['object']['bookmarks'] = {}

    def _requestHTTP(self) -> bool:
        """Should a http response be given?
        """
        if not self.headers.get('Accept'):
            return False
        if self.server.debug:
            print('ACCEPT: ' + self.headers['Accept'])
        if 'image/' in self.headers['Accept']:
            if 'text/html' not in self.headers['Accept']:
                return False
        if 'video/' in self.headers['Accept']:
            if 'text/html' not in self.headers['Accept']:
                return False
        if 'audio/' in self.headers['Accept']:
            if 'text/html' not in self.headers['Accept']:
                return False
        if self.headers['Accept'].startswith('*'):
            return False
        if 'json' in self.headers['Accept']:
            return False
        return True

    def _fetchAuthenticated(self) -> bool:
        """http authentication of GET requests for json
        """
        if not self.server.authenticatedFetch:
            return True
        # check that the headers are signed
        if not self.headers.get('signature'):
            if self.server.debug:
                print('WARN: authenticated fetch, ' +
                      'GET has no signature in headers')
            return False
        # get the keyId
        keyId = None
        signatureParams = self.headers['signature'].split(',')
        for signatureItem in signatureParams:
            if signatureItem.startswith('keyId='):
                if '"' in signatureItem:
                    keyId = signatureItem.split('"')[1]
                    break
        if not keyId:
            if self.server.debug:
                print('WARN: authenticated fetch, ' +
                      'failed to obtain keyId from signature')
            return False
        # is the keyId (actor) valid?
        if not urlPermitted(keyId, self.server.federationList):
            if self.server.debug:
                print('Authorized fetch failed: ' + keyId +
                      ' is not permitted')
            return False
        # make sure we have a session
        if not self.server.session:
            print('DEBUG: creating new session during authenticated fetch')
            self.server.session = createSession(self.server.proxyType)
            if not self.server.session:
                print('ERROR: GET failed to create session during ' +
                      'authenticated fetch')
                return False
        # obtain the public key
        pubKey = \
            getPersonPubKey(self.server.baseDir, self.server.session, keyId,
                            self.server.personCache, self.server.debug,
                            __version__, self.server.httpPrefix,
                            self.server.domain, self.server.onionDomain)
        if not pubKey:
            if self.server.debug:
                print('DEBUG: Authenticated fetch failed to ' +
                      'obtain public key for ' + keyId)
            return False
        # it is assumed that there will be no message body on
        # authenticated fetches and also consequently no digest
        GETrequestBody = ''
        GETrequestDigest = None
        # verify the GET request without any digest
        if verifyPostHeaders(self.server.httpPrefix,
                             pubKey, self.headers,
                             self.path, True,
                             GETrequestDigest,
                             GETrequestBody,
                             self.server.debug):
            return True
        return False

    def _login_headers(self, fileFormat: str, length: int,
                       callingDomain: str) -> None:
        self.send_response(200)
        self.send_header('Content-type', fileFormat)
        self.send_header('Content-Length', str(length))
        self.send_header('Host', callingDomain)
        self.send_header('WWW-Authenticate',
                         'title="Login to Epicyon", Basic realm="epicyon"')
        self.send_header('X-Robots-Tag', 'noindex')
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
        self.send_header('X-Robots-Tag', 'noindex')
        self.end_headers()

    def _set_headers_base(self, fileFormat: str, length: int, cookie: str,
                          callingDomain: str) -> None:
        self.send_response(200)
        self.send_header('Content-type', fileFormat)
        if length > -1:
            self.send_header('Content-Length', str(length))
        if cookie:
            cookieStr = cookie
            if 'HttpOnly;' not in cookieStr:
                if self.server.httpPrefix == 'https':
                    cookieStr += '; Secure'
                cookieStr += '; HttpOnly; SameSite=Strict'
            self.send_header('Cookie', cookieStr)
        self.send_header('Host', callingDomain)
        self.send_header('InstanceID', self.server.instanceId)
        self.send_header('X-Robots-Tag', 'noindex')
        self.send_header('X-Clacks-Overhead', 'GNU Natalie Nguyen')
        self.send_header('Accept-Ranges', 'none')

    def _set_headers(self, fileFormat: str, length: int, cookie: str,
                     callingDomain: str) -> None:
        self._set_headers_base(fileFormat, length, cookie, callingDomain)
        self.send_header('Cache-Control', 'public, max-age=0')
        self.end_headers()

    def _set_headers_head(self, fileFormat: str, length: int, etag: str,
                          callingDomain: str) -> None:
        self._set_headers_base(fileFormat, length, None, callingDomain)
        if etag:
            self.send_header('ETag', etag)
        self.end_headers()

    def _set_headers_etag(self, mediaFilename: str, fileFormat: str,
                          data, cookie: str, callingDomain: str) -> None:
        self._set_headers_base(fileFormat, len(data), cookie, callingDomain)
        self.send_header('Cache-Control', 'public, max-age=86400')
        etag = None
        if os.path.isfile(mediaFilename + '.etag'):
            try:
                with open(mediaFilename + '.etag', 'r') as etagFile:
                    etag = etagFile.read()
            except BaseException:
                pass
        if not etag:
            etag = sha1(data).hexdigest()  # nosec
            try:
                with open(mediaFilename + '.etag', 'w+') as etagFile:
                    etagFile.write(etag)
            except BaseException:
                pass
        if etag:
            self.send_header('ETag', etag)
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
            oldEtag = self.headers['If-None-Match']
            if os.path.isfile(mediaFilename + '.etag'):
                # load the etag from file
                currEtag = ''
                try:
                    with open(mediaFilename, 'r') as etagFile:
                        currEtag = etagFile.read()
                except BaseException:
                    pass
                if oldEtag == currEtag:
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
                if self.server.httpPrefix == 'https':
                    cookieStr += '; Secure'
                cookieStr += '; HttpOnly; SameSite=Strict'
            if not cookie.startswith('SET:'):
                self.send_header('Cookie', cookieStr)
            else:
                self.send_header('Set-Cookie', cookieStr)
        self.send_header('Location', redirect)
        self.send_header('Host', callingDomain)
        self.send_header('InstanceID', self.server.instanceId)
        self.send_header('Content-Length', '0')
        self.send_header('X-Robots-Tag', 'noindex')
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
            'small-caps;">' + httpDescription + '</div>' \
            '<div style="text-align: center;">' + longDescription + '</div>' \
            '</body></html>'
        msg = msg.encode('utf-8')
        self.send_response(httpCode)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(msg)))
        self.send_header('X-Robots-Tag', 'noindex')
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
            except Exception as e:
                print(e)
                time.sleep(0.5)
            tries += 1
        return False

    def _robotsTxt(self) -> bool:
        if not self.path.lower().startswith('/robot'):
            return False
        msg = 'User-agent: *\nDisallow: /'
        msg = msg.encode('utf-8')
        self._set_headers('text/plain; charset=utf-8', len(msg),
                          None, self.server.domainFull)
        self._write(msg)
        return True

    def _hasAccept(self, callingDomain: str) -> bool:
        if self.headers.get('Accept') or callingDomain.endswith('.b32.i2p'):
            if not self.headers.get('Accept'):
                self.headers['Accept'] = \
                    'text/html,application/xhtml+xml,' \
                    'application/xml;q=0.9,image/webp,*/*;q=0.8'
            return True
        return False

    def _mastoApi(self, callingDomain: str) -> bool:
        """This is a vestigil mastodon API for the purpose
        of returning an empty result to sites like
        https://mastopeek.app-dist.eu
        """
        if not self.path.startswith('/api/v1/'):
            return False
        if self.server.debug:
            print('DEBUG: mastodon api ' + self.path)
        if self.path == '/api/v1/instance':
            adminNickname = getConfigParam(self.server.baseDir, 'admin')
            instanceDescriptionShort = \
                getConfigParam(self.server.baseDir,
                               'instanceDescriptionShort')
            instanceDescription = getConfigParam(self.server.baseDir,
                                                 'instanceDescription')
            instanceTitle = getConfigParam(self.server.baseDir,
                                           'instanceTitle')
            instanceJson = \
                metaDataInstance(instanceTitle,
                                 instanceDescriptionShort,
                                 instanceDescription,
                                 self.server.httpPrefix,
                                 self.server.baseDir,
                                 adminNickname,
                                 self.server.domain,
                                 self.server.domainFull,
                                 self.server.registration,
                                 self.server.systemLanguage,
                                 self.server.projectVersion)
            msg = json.dumps(instanceJson).encode('utf-8')
            if self._hasAccept(callingDomain):
                if 'application/ld+json' in self.headers['Accept']:
                    self._set_headers('application/ld+json', len(msg),
                                      None, callingDomain)
                else:
                    self._set_headers('application/json', len(msg),
                                      None, callingDomain)
            else:
                self._set_headers('application/ld+json', len(msg),
                                  None, callingDomain)
            self._write(msg)
            print('instance metadata sent')
            return True
        if self.path.startswith('/api/v1/instance/peers'):
            # This is just a dummy result.
            # Showing the full list of peers would have privacy implications.
            # On a large instance you are somewhat lost in the crowd, but on
            # small instances a full list of peers would convey a lot of
            # information about the interests of a small number of accounts
            msg = json.dumps(['mastodon.social',
                              self.server.domainFull]).encode('utf-8')
            if self._hasAccept(callingDomain):
                if 'application/ld+json' in self.headers['Accept']:
                    self._set_headers('application/ld+json', len(msg),
                                      None, callingDomain)
                else:
                    self._set_headers('application/json', len(msg),
                                      None, callingDomain)
            else:
                self._set_headers('application/ld+json', len(msg),
                                  None, callingDomain)
            self._write(msg)
            print('instance peers metadata sent')
            return True
        if self.path.startswith('/api/v1/instance/activity'):
            # This is just a dummy result.
            msg = json.dumps([]).encode('utf-8')
            if self._hasAccept(callingDomain):
                if 'application/ld+json' in self.headers['Accept']:
                    self._set_headers('application/ld+json', len(msg),
                                      None, callingDomain)
                else:
                    self._set_headers('application/json', len(msg),
                                      None, callingDomain)
            else:
                self._set_headers('application/ld+json', len(msg),
                                  None, callingDomain)
            self._write(msg)
            print('instance activity metadata sent')
            return True
        self._404()
        return True

    def _nodeinfo(self, callingDomain: str) -> bool:
        if not self.path.startswith('/nodeinfo/2.0'):
            return False
        if self.server.debug:
            print('DEBUG: nodeinfo ' + self.path)
        info = metaDataNodeInfo(self.server.baseDir,
                                self.server.registration,
                                self.server.projectVersion)
        if info:
            msg = json.dumps(info).encode('utf-8')
            if self._hasAccept(callingDomain):
                if 'application/ld+json' in self.headers['Accept']:
                    self._set_headers('application/ld+json', len(msg),
                                      None, callingDomain)
                else:
                    self._set_headers('application/json', len(msg),
                                      None, callingDomain)
            else:
                self._set_headers('application/ld+json', len(msg),
                                  None, callingDomain)
            self._write(msg)
            print('nodeinfo sent')
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
               self.server.onionDomain:
                wfResult = \
                    webfingerMeta('http', self.server.onionDomain)
            elif (callingDomain.endswith('.i2p') and
                  self.server.i2pDomain):
                wfResult = \
                    webfingerMeta('http', self.server.i2pDomain)
            else:
                wfResult = \
                    webfingerMeta(self.server.httpPrefix,
                                  self.server.domainFull)
            if wfResult:
                msg = wfResult.encode('utf-8')
                self._set_headers('application/xrd+xml', len(msg),
                                  None, callingDomain)
                self._write(msg)
                return True
            self._404()
            return True
        if self.path.startswith('/.well-known/nodeinfo'):
            if callingDomain.endswith('.onion') and \
               self.server.onionDomain:
                wfResult = \
                    webfingerNodeInfo('http', self.server.onionDomain)
            elif (callingDomain.endswith('.i2p') and
                  self.server.i2pDomain):
                wfResult = \
                    webfingerNodeInfo('http', self.server.i2pDomain)
            else:
                wfResult = \
                    webfingerNodeInfo(self.server.httpPrefix,
                                      self.server.domainFull)
            if wfResult:
                msg = json.dumps(wfResult).encode('utf-8')
                if self._hasAccept(callingDomain):
                    if 'application/ld+json' in self.headers['Accept']:
                        self._set_headers('application/ld+json', len(msg),
                                          None, callingDomain)
                    else:
                        self._set_headers('application/json', len(msg),
                                          None, callingDomain)
                else:
                    self._set_headers('application/ld+json', len(msg),
                                      None, callingDomain)
                self._write(msg)
                return True
            self._404()
            return True

        if self.server.debug:
            print('DEBUG: WEBFINGER lookup ' + self.path + ' ' +
                  str(self.server.baseDir))
        wfResult = \
            webfingerLookup(self.path, self.server.baseDir,
                            self.server.domain, self.server.onionDomain,
                            self.server.port, self.server.debug)
        if wfResult:
            msg = json.dumps(wfResult).encode('utf-8')
            self._set_headers('application/jrd+json', len(msg),
                              None, callingDomain)
            self._write(msg)
        else:
            if self.server.debug:
                print('DEBUG: WEBFINGER lookup 404 ' + self.path)
            self._404()
        return True

    def _permittedDir(self, path: str) -> bool:
        """These are special paths which should not be accessible
        directly via GET or POST
        """
        if path.startswith('/wfendpoints') or \
           path.startswith('/keys') or \
           path.startswith('/accounts'):
            return False
        return True

    def _postToOutbox(self, messageJson: {}, version: str,
                      postToNickname=None) -> bool:
        """post is received by the outbox
        Client to server message post
        https://www.w3.org/TR/activitypub/#client-to-server-outbox-delivery
        """
        if postToNickname:
            print('Posting to nickname ' + postToNickname)
            self.postToNickname = postToNickname

        return postMessageToOutbox(messageJson, self.postToNickname,
                                   self.server, self.server.baseDir,
                                   self.server.httpPrefix,
                                   self.server.domain,
                                   self.server.domainFull,
                                   self.server.onionDomain,
                                   self.server.i2pDomain,
                                   self.server.port,
                                   self.server.recentPostsCache,
                                   self.server.followersThreads,
                                   self.server.federationList,
                                   self.server.sendThreads,
                                   self.server.postLog,
                                   self.server.cachedWebfingers,
                                   self.server.personCache,
                                   self.server.allowDeletion,
                                   self.server.proxyType, version,
                                   self.server.debug,
                                   self.server.YTReplacementDomain)

    def _postToOutboxThread(self, messageJson: {}) -> bool:
        """Creates a thread to send a post
        """
        accountOutboxThreadName = self.postToNickname
        if not accountOutboxThreadName:
            accountOutboxThreadName = '*'

        if self.server.outboxThread.get(accountOutboxThreadName):
            print('Waiting for previous outbox thread to end')
            waitCtr = 0
            thName = accountOutboxThreadName
            while self.server.outboxThread[thName].isAlive() and waitCtr < 8:
                time.sleep(1)
                waitCtr += 1
            if waitCtr >= 8:
                self.server.outboxThread[accountOutboxThreadName].kill()

        print('Creating outbox thread')
        self.server.outboxThread[accountOutboxThreadName] = \
            threadWithTrace(target=self._postToOutbox,
                            args=(messageJson.copy(), __version__),
                            daemon=True)
        print('Starting outbox thread')
        self.server.outboxThread[accountOutboxThreadName].start()
        return True

    def _updateInboxQueue(self, nickname: str, messageJson: {},
                          messageBytes: str) -> int:
        """Update the inbox queue
        """
        if self.server.restartInboxQueueInProgress:
            self._503()
            print('Message arrrived but currently restarting inbox queue')
            self.server.POSTbusy = False
            return 2

        # check for blocked domains so that they can be rejected early
        messageDomain = None
        if messageJson.get('actor'):
            messageDomain, messagePort = \
                getDomainFromActor(messageJson['actor'])
            if isBlockedDomain(self.server.baseDir, messageDomain):
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
            clearQueueItems(self.server.baseDir, self.server.inboxQueue)
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
        if self.headers.get('digest'):
            headersDict['digest'] = self.headers['digest']
        if self.headers.get('Content-type'):
            headersDict['Content-type'] = self.headers['Content-type']
        if self.headers.get('Content-Length'):
            headersDict['Content-Length'] = self.headers['Content-Length']
        elif self.headers.get('content-length'):
            headersDict['content-length'] = self.headers['content-length']

        # For follow activities add a 'to' field, which is a copy
        # of the object field
        messageJson, toFieldExists = \
            addToField('Follow', messageJson, self.server.debug)

        # For like activities add a 'to' field, which is a copy of
        # the actor within the object field
        messageJson, toFieldExists = \
            addToField('Like', messageJson, self.server.debug)

        beginSaveTime = time.time()
        # save the json for later queue processing
        queueFilename = \
            savePostToInboxQueue(self.server.baseDir,
                                 self.server.httpPrefix,
                                 nickname,
                                 self.server.domainFull,
                                 messageJson,
                                 messageBytes.decode('utf-8'),
                                 headersDict,
                                 self.path,
                                 self.server.debug)
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

        if self.path.startswith('/icons/') or \
           self.path.startswith('/avatars/') or \
           self.path.startswith('/favicon.ico') or \
           self.path.startswith('/newswire.xml'):
            return False

        # token based authenticated used by the web interface
        if self.headers.get('Cookie'):
            if self.headers['Cookie'].startswith('epicyon='):
                tokenStr = self.headers['Cookie'].split('=', 1)[1].strip()
                if ';' in tokenStr:
                    tokenStr = tokenStr.split(';')[0].strip()
                if self.server.tokensLookup.get(tokenStr):
                    nickname = self.server.tokensLookup[tokenStr]
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
                    elif self.path.endswith('/'+nickname):
                        return True
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
        # basic auth
        if self.headers.get('Authorization'):
            if authorize(self.server.baseDir, self.path,
                         self.headers['Authorization'],
                         self.server.debug):
                return True
            print('AUTH: Basic auth did not authorize ' +
                  self.headers['Authorization'])
        return False

    def _clearLoginDetails(self, nickname: str, callingDomain: str):
        """Clears login details for the given account
        """
        # remove any token
        if self.server.tokens.get(nickname):
            del self.server.tokensLookup[self.server.tokens[nickname]]
            del self.server.tokens[nickname]
        self._redirect_headers(self.server.httpPrefix + '://' +
                               self.server.domainFull + '/login',
                               'epicyon=; SameSite=Strict',
                               callingDomain)

    def _benchmarkGETtimings(self, GETstartTime, GETtimings: {},
                             prevGetId: str, currGetId: str):
        """Updates a dictionary containing how long each segment of GET takes
        """
        timeDiff = int((time.time() - GETstartTime) * 1000)
        logEvent = False
        if timeDiff > 100:
            logEvent = True
        if prevGetId:
            if GETtimings.get(prevGetId):
                timeDiff = int(timeDiff - int(GETtimings[prevGetId]))
        GETtimings[currGetId] = str(timeDiff)
        if logEvent:
            print('GET TIMING ' + currGetId + ' = ' + str(timeDiff))

    def _benchmarkPOSTtimings(self, POSTstartTime, POSTtimings: [],
                              postID: int):
        """Updates a list containing how long each segment of POST takes
        """
        if self.server.debug:
            timeDiff = int((time.time() - POSTstartTime) * 1000)
            logEvent = False
            if timeDiff > 100:
                logEvent = True
            if POSTtimings:
                timeDiff = int(timeDiff - int(POSTtimings[-1]))
            POSTtimings.append(str(timeDiff))
            if logEvent:
                ctr = 1
                for timeDiff in POSTtimings:
                    print('POST TIMING|' + str(ctr) + '|' + timeDiff)
                    ctr += 1

    def _pathContainsBlogLink(self, baseDir: str,
                              httpPrefix: str, domain: str,
                              domainFull: str, path: str) -> (str, str):
        """If the path contains a blog entry then return its filename
        """
        if '/users/' not in path:
            return None, None
        userEnding = path.split('/users/', 1)[1]
        if '/' not in userEnding:
            return None, None
        userEnding2 = userEnding.split('/')
        nickname = userEnding2[0]
        if len(userEnding2) != 2:
            return None, None
        if len(userEnding2[1]) < 14:
            return None, None
        userEnding2[1] = userEnding2[1].strip()
        if not userEnding2[1].isdigit():
            return None, None
        # check for blog posts
        blogIndexFilename = baseDir + '/accounts/' + \
            nickname + '@' + domain + '/tlblogs.index'
        if not os.path.isfile(blogIndexFilename):
            return None, None
        if '#' + userEnding2[1] + '.' not in open(blogIndexFilename).read():
            return None, None
        messageId = httpPrefix + '://' + domainFull + \
            '/users/' + nickname + '/statuses/' + userEnding2[1]
        return locatePost(baseDir, nickname, domain, messageId), nickname

    def _loginScreen(self, path: str, callingDomain: str, cookie: str,
                     baseDir: str, httpPrefix: str,
                     domain: str, domainFull: str, port: int,
                     onionDomain: str, i2pDomain: str,
                     debug: bool):
        """Shows the login screen
        """
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
        except SocketError as e:
            if e.errno == errno.ECONNRESET:
                print('WARN: POST login read ' +
                      'connection reset by peer')
            else:
                print('WARN: POST login read socket error')
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy = False
            return
        except ValueError as e:
            print('ERROR: POST login read failed')
            print(e)
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy = False
            return

        loginNickname, loginPassword, register = \
            htmlGetLoginCredentials(loginParams, self.server.lastLoginTime)
        if loginNickname:
            self.server.lastLoginTime = int(time.time())
            if register:
                if not registerAccount(baseDir, httpPrefix, domain, port,
                                       loginNickname, loginPassword,
                                       self.server.manualFollowerApproval):
                    self.server.POSTbusy = False
                    if callingDomain.endswith('.onion') and onionDomain:
                        self._redirect_headers('http://' + onionDomain +
                                               '/login', cookie,
                                               callingDomain)
                    elif (callingDomain.endswith('.i2p') and i2pDomain):
                        self._redirect_headers('http://' + i2pDomain +
                                               '/login', cookie,
                                               callingDomain)
                    else:
                        self._redirect_headers(httpPrefix + '://' +
                                               domainFull + '/login',
                                               cookie, callingDomain)
                    return
            authHeader = \
                createBasicAuthHeader(loginNickname, loginPassword)
            if not authorizeBasic(baseDir, '/users/' +
                                  loginNickname + '/outbox',
                                  authHeader, False):
                print('Login failed: ' + loginNickname)
                self._clearLoginDetails(loginNickname, callingDomain)
                self.server.POSTbusy = False
                return
            else:
                if isSuspended(baseDir, loginNickname):
                    msg = \
                        htmlSuspended(baseDir).encode('utf-8')
                    self._login_headers('text/html',
                                        len(msg), callingDomain)
                    self._write(msg)
                    self.server.POSTbusy = False
                    return
                # login success - redirect with authorization
                print('Login success: ' + loginNickname)
                # re-activate account if needed
                activateAccount(baseDir, loginNickname, domain)
                # This produces a deterministic token based
                # on nick+password+salt
                saltFilename = \
                    baseDir+'/accounts/' + \
                    loginNickname + '@' + domain + '/.salt'
                salt = createPassword(32)
                if os.path.isfile(saltFilename):
                    try:
                        with open(saltFilename, 'r') as fp:
                            salt = fp.read()
                    except Exception as e:
                        print('WARN: Unable to read salt for ' +
                              loginNickname + ' ' + str(e))
                else:
                    try:
                        with open(saltFilename, 'w+') as fp:
                            fp.write(salt)
                    except Exception as e:
                        print('WARN: Unable to save salt for ' +
                              loginNickname + ' ' + str(e))

                tokenText = loginNickname + loginPassword + salt
                token = sha256(tokenText.encode('utf-8')).hexdigest()
                self.server.tokens[loginNickname] = token
                loginHandle = loginNickname + '@' + domain
                tokenFilename = \
                    baseDir+'/accounts/' + \
                    loginHandle + '/.token'
                try:
                    with open(tokenFilename, 'w+') as fp:
                        fp.write(token)
                except Exception as e:
                    print('WARN: Unable to save token for ' +
                          loginNickname + ' ' + str(e))

                personUpgradeActor(baseDir, None, loginHandle,
                                   baseDir + '/accounts/' +
                                   loginHandle + '.json')

                index = self.server.tokens[loginNickname]
                self.server.tokensLookup[index] = loginNickname
                cookieStr = 'SET:epicyon=' + \
                    self.server.tokens[loginNickname] + '; SameSite=Strict'
                if callingDomain.endswith('.onion') and onionDomain:
                    self._redirect_headers('http://' +
                                           onionDomain +
                                           '/users/' +
                                           loginNickname + '/' +
                                           self.server.defaultTimeline,
                                           cookieStr, callingDomain)
                elif (callingDomain.endswith('.i2p') and i2pDomain):
                    self._redirect_headers('http://' +
                                           i2pDomain +
                                           '/users/' +
                                           loginNickname + '/' +
                                           self.server.defaultTimeline,
                                           cookieStr, callingDomain)
                else:
                    self._redirect_headers(httpPrefix + '://' +
                                           domainFull + '/users/' +
                                           loginNickname + '/' +
                                           self.server.defaultTimeline,
                                           cookieStr, callingDomain)
                self.server.POSTbusy = False
                return
        self._200()
        self.server.POSTbusy = False

    def _moderatorActions(self, path: str, callingDomain: str, cookie: str,
                          baseDir: str, httpPrefix: str,
                          domain: str, domainFull: str, port: int,
                          onionDomain: str, i2pDomain: str,
                          debug: bool):
        """Actions on the moderator screeen
        """
        usersPath = path.replace('/moderationaction', '')
        actorStr = httpPrefix + '://' + domainFull + usersPath

        length = int(self.headers['Content-length'])

        try:
            moderationParams = self.rfile.read(length).decode('utf-8')
        except SocketError as e:
            if e.errno == errno.ECONNRESET:
                print('WARN: POST moderationParams connection was reset')
            else:
                print('WARN: POST moderationParams ' +
                      'rfile.read socket error')
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy = False
            return
        except ValueError as e:
            print('ERROR: POST moderationParams rfile.read failed')
            print(e)
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
                    msg = htmlModerationInfo(self.server.translate,
                                             baseDir, httpPrefix)
                    msg = msg.encode('utf-8')
                    self._login_headers('text/html',
                                        len(msg), callingDomain)
                    self._write(msg)
                    self.server.POSTbusy = False
                    return
                elif moderationStr.startswith('submitBlock'):
                    moderationButton = 'block'
                elif moderationStr.startswith('submitUnblock'):
                    moderationButton = 'unblock'
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
                   nickname.startswith('dat'):
                    nickname = getNicknameFromActor(nickname)
                if '@' in nickname:
                    nickname = nickname.split('@')[0]
                if moderationButton == 'suspend':
                    suspendAccount(baseDir, nickname, domain)
                if moderationButton == 'unsuspend':
                    unsuspendAccount(baseDir, nickname)
                if moderationButton == 'block':
                    fullBlockDomain = None
                    if moderationText.startswith('http') or \
                       moderationText.startswith('dat'):
                        # https://domain
                        blockDomain, blockPort = \
                            getDomainFromActor(moderationText)
                        fullBlockDomain = blockDomain
                        if blockPort:
                            if blockPort != 80 and blockPort != 443:
                                if ':' not in blockDomain:
                                    fullBlockDomain = \
                                        blockDomain + ':' + str(blockPort)
                    if '@' in moderationText:
                        # nick@domain or *@domain
                        fullBlockDomain = moderationText.split('@')[1]
                    else:
                        # assume the text is a domain name
                        if not fullBlockDomain and '.' in moderationText:
                            nickname = '*'
                            fullBlockDomain = moderationText.strip()
                    if fullBlockDomain or nickname.startswith('#'):
                        addGlobalBlock(baseDir, nickname, fullBlockDomain)
                if moderationButton == 'unblock':
                    fullBlockDomain = None
                    if moderationText.startswith('http') or \
                       moderationText.startswith('dat'):
                        # https://domain
                        blockDomain, blockPort = \
                            getDomainFromActor(moderationText)
                        fullBlockDomain = blockDomain
                        if blockPort:
                            if blockPort != 80 and blockPort != 443:
                                if ':' not in blockDomain:
                                    fullBlockDomain = \
                                        blockDomain + ':' + str(blockPort)
                    if '@' in moderationText:
                        # nick@domain or *@domain
                        fullBlockDomain = moderationText.split('@')[1]
                    else:
                        # assume the text is a domain name
                        if not fullBlockDomain and '.' in moderationText:
                            nickname = '*'
                            fullBlockDomain = moderationText.strip()
                    if fullBlockDomain or nickname.startswith('#'):
                        removeGlobalBlock(baseDir, nickname, fullBlockDomain)
                if moderationButton == 'remove':
                    if '/statuses/' not in moderationText:
                        removeAccount(baseDir, nickname, domain, port)
                    else:
                        # remove a post or thread
                        postFilename = \
                            locatePost(baseDir, nickname, domain,
                                       moderationText)
                        if postFilename:
                            if canRemovePost(baseDir,
                                             nickname,
                                             domain,
                                             port,
                                             moderationText):
                                deletePost(baseDir,
                                           httpPrefix,
                                           nickname, domain,
                                           postFilename,
                                           debug,
                                           self.server.recentPostsCache)
        if callingDomain.endswith('.onion') and onionDomain:
            actorStr = 'http://' + onionDomain + usersPath
        elif (callingDomain.endswith('.i2p') and i2pDomain):
            actorStr = 'http://' + i2pDomain + usersPath
        self._redirect_headers(actorStr + '/moderation',
                               cookie, callingDomain)
        self.server.POSTbusy = False
        return

    def _personOptions(self, path: str,
                       callingDomain: str, cookie: str,
                       baseDir: str, httpPrefix: str,
                       domain: str, domainFull: str, port: int,
                       onionDomain: str, i2pDomain: str,
                       debug: bool):
        """Receive POST from person options screen
        """
        pageNumber = 1
        usersPath = path.split('/personoptions')[0]
        originPathStr = httpPrefix + '://' + domainFull + usersPath

        chooserNickname = getNicknameFromActor(originPathStr)
        if not chooserNickname:
            if callingDomain.endswith('.onion') and onionDomain:
                originPathStr = 'http://' + onionDomain + usersPath
            elif (callingDomain.endswith('.i2p') and i2pDomain):
                originPathStr = 'http://' + i2pDomain + usersPath
            print('WARN: unable to find nickname in ' + originPathStr)
            self._redirect_headers(originPathStr, cookie, callingDomain)
            self.server.POSTbusy = False
            return

        length = int(self.headers['Content-length'])

        try:
            optionsConfirmParams = self.rfile.read(length).decode('utf-8')
        except SocketError as e:
            if e.errno == errno.ECONNRESET:
                print('WARN: POST optionsConfirmParams ' +
                      'connection reset by peer')
            else:
                print('WARN: POST optionsConfirmParams socket error')
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy = False
            return
        except ValueError as e:
            print('ERROR: POST optionsConfirmParams rfile.read failed')
            print(e)
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
            if callingDomain.endswith('.onion') and onionDomain:
                originPathStr = 'http://' + onionDomain + usersPath
            elif (callingDomain.endswith('.i2p') and i2pDomain):
                originPathStr = 'http://' + i2pDomain + usersPath
            print('WARN: unable to find nickname in ' + optionsActor)
            self._redirect_headers(originPathStr, cookie, callingDomain)
            self.server.POSTbusy = False
            return

        optionsDomain, optionsPort = getDomainFromActor(optionsActor)
        optionsDomainFull = optionsDomain
        if optionsPort:
            if optionsPort != 80 and optionsPort != 443:
                if ':' not in optionsDomain:
                    optionsDomainFull = optionsDomain + ':' + \
                        str(optionsPort)
        if chooserNickname == optionsNickname and \
           optionsDomain == domain and \
           optionsPort == port:
            if debug:
                print('You cannot perform an option action on yourself')

        # view button on person option screen
        if '&submitView=' in optionsConfirmParams:
            if debug:
                print('Viewing ' + optionsActor)
            self._redirect_headers(optionsActor,
                                   cookie, callingDomain)
            self.server.POSTbusy = False
            return

        # petname submit button on person option screen
        if '&submitPetname=' in optionsConfirmParams and petname:
            if debug:
                print('Change petname to ' + petname)
            handle = optionsNickname + '@' + optionsDomainFull
            setPetName(baseDir,
                       chooserNickname,
                       domain,
                       handle, petname)
            self._redirect_headers(usersPath + '/' +
                                   self.server.defaultTimeline +
                                   '?page='+str(pageNumber), cookie,
                                   callingDomain)
            self.server.POSTbusy = False
            return

        # person notes submit button on person option screen
        if '&submitPersonNotes=' in optionsConfirmParams:
            if debug:
                print('Change person notes')
            handle = optionsNickname + '@' + optionsDomainFull
            if not personNotes:
                personNotes = ''
            setPersonNotes(baseDir,
                           chooserNickname,
                           domain,
                           handle, personNotes)
            self._redirect_headers(usersPath + '/' +
                                   self.server.defaultTimeline +
                                   '?page='+str(pageNumber), cookie,
                                   callingDomain)
            self.server.POSTbusy = False
            return

        # person on calendar checkbox on person option screen
        if '&submitOnCalendar=' in optionsConfirmParams:
            onCalendar = None
            if 'onCalendar=' in optionsConfirmParams:
                onCalendar = optionsConfirmParams.split('onCalendar=')[1]
                if '&' in onCalendar:
                    onCalendar = onCalendar.split('&')[0]
            if onCalendar == 'on':
                addPersonToCalendar(baseDir,
                                    chooserNickname,
                                    domain,
                                    optionsNickname,
                                    optionsDomainFull)
            else:
                removePersonFromCalendar(baseDir,
                                         chooserNickname,
                                         domain,
                                         optionsNickname,
                                         optionsDomainFull)
            self._redirect_headers(usersPath + '/' +
                                   self.server.defaultTimeline +
                                   '?page='+str(pageNumber), cookie,
                                   callingDomain)
            self.server.POSTbusy = False
            return

        # block person button on person option screen
        if '&submitBlock=' in optionsConfirmParams:
            if debug:
                print('Adding block by ' + chooserNickname +
                      ' of ' + optionsActor)
            addBlock(baseDir, chooserNickname,
                     domain,
                     optionsNickname, optionsDomainFull)

        # unblock button on person option screen
        if '&submitUnblock=' in optionsConfirmParams:
            if debug:
                print('Unblocking ' + optionsActor)
            msg = \
                htmlUnblockConfirm(self.server.translate,
                                   baseDir,
                                   usersPath,
                                   optionsActor,
                                   optionsAvatarUrl).encode('utf-8')
            self._set_headers('text/html', len(msg),
                              cookie, callingDomain)
            self._write(msg)
            self.server.POSTbusy = False
            return

        # follow button on person option screen
        if '&submitFollow=' in optionsConfirmParams:
            if debug:
                print('Following ' + optionsActor)
            msg = \
                htmlFollowConfirm(self.server.translate,
                                  baseDir,
                                  usersPath,
                                  optionsActor,
                                  optionsAvatarUrl).encode('utf-8')
            self._set_headers('text/html', len(msg),
                              cookie, callingDomain)
            self._write(msg)
            self.server.POSTbusy = False
            return

        # unfollow button on person option screen
        if '&submitUnfollow=' in optionsConfirmParams:
            if debug:
                print('Unfollowing ' + optionsActor)
            msg = \
                htmlUnfollowConfirm(self.server.translate,
                                    baseDir,
                                    usersPath,
                                    optionsActor,
                                    optionsAvatarUrl).encode('utf-8')
            self._set_headers('text/html', len(msg),
                              cookie, callingDomain)
            self._write(msg)
            self.server.POSTbusy = False
            return

        # DM button on person option screen
        if '&submitDM=' in optionsConfirmParams:
            if debug:
                print('Sending DM to ' + optionsActor)
            reportPath = path.replace('/personoptions', '') + '/newdm'
            msg = htmlNewPost(False, self.server.translate,
                              baseDir,
                              httpPrefix,
                              reportPath, None,
                              [optionsActor], None,
                              pageNumber,
                              chooserNickname,
                              domain,
                              domainFull).encode('utf-8')
            self._set_headers('text/html', len(msg),
                              cookie, callingDomain)
            self._write(msg)
            self.server.POSTbusy = False
            return

        # snooze button on person option screen
        if '&submitSnooze=' in optionsConfirmParams:
            usersPath = path.split('/personoptions')[0]
            thisActor = httpPrefix + '://' + domainFull + usersPath
            if debug:
                print('Snoozing ' + optionsActor + ' ' + thisActor)
            if '/users/' in thisActor:
                nickname = thisActor.split('/users/')[1]
                personSnooze(baseDir, nickname,
                             domain, optionsActor)
                if callingDomain.endswith('.onion') and onionDomain:
                    thisActor = 'http://' + onionDomain + usersPath
                elif (callingDomain.endswith('.i2p') and i2pDomain):
                    thisActor = 'http://' + i2pDomain + usersPath
                self._redirect_headers(thisActor + '/' +
                                       self.server.defaultTimeline +
                                       '?page='+str(pageNumber), cookie,
                                       callingDomain)
                self.server.POSTbusy = False
                return

        # unsnooze button on person option screen
        if '&submitUnSnooze=' in optionsConfirmParams:
            usersPath = path.split('/personoptions')[0]
            thisActor = httpPrefix + '://' + domainFull + usersPath
            if debug:
                print('Unsnoozing ' + optionsActor + ' ' + thisActor)
            if '/users/' in thisActor:
                nickname = thisActor.split('/users/')[1]
                personUnsnooze(baseDir, nickname,
                               domain, optionsActor)
                if callingDomain.endswith('.onion') and onionDomain:
                    thisActor = 'http://' + onionDomain + usersPath
                elif (callingDomain.endswith('.i2p') and i2pDomain):
                    thisActor = 'http://' + i2pDomain + usersPath
                self._redirect_headers(thisActor + '/' +
                                       self.server.defaultTimeline +
                                       '?page=' + str(pageNumber), cookie,
                                       callingDomain)
                self.server.POSTbusy = False
                return

        # report button on person option screen
        if '&submitReport=' in optionsConfirmParams:
            if debug:
                print('Reporting ' + optionsActor)
            reportPath = \
                path.replace('/personoptions', '') + '/newreport'
            msg = htmlNewPost(False, self.server.translate,
                              baseDir,
                              httpPrefix,
                              reportPath, None, [],
                              postUrl, pageNumber,
                              chooserNickname,
                              domain,
                              domainFull).encode('utf-8')
            self._set_headers('text/html', len(msg),
                              cookie, callingDomain)
            self._write(msg)
            self.server.POSTbusy = False
            return

        # redirect back from person options screen
        if callingDomain.endswith('.onion') and onionDomain:
            originPathStr = 'http://' + onionDomain + usersPath
        elif callingDomain.endswith('.i2p') and i2pDomain:
            originPathStr = 'http://' + i2pDomain + usersPath
        self._redirect_headers(originPathStr, cookie, callingDomain)
        self.server.POSTbusy = False
        return

    def _unfollowConfirm(self, callingDomain: str, cookie: str,
                         authorized: bool, path: str,
                         baseDir: str, httpPrefix: str,
                         domain: str, domainFull: str, port: int,
                         onionDomain: str, i2pDomain: str, debug: bool):
        """Confirm to unfollow
        """
        usersPath = path.split('/unfollowconfirm')[0]
        originPathStr = httpPrefix + '://' + domainFull + usersPath
        followerNickname = getNicknameFromActor(originPathStr)

        length = int(self.headers['Content-length'])

        try:
            followConfirmParams = self.rfile.read(length).decode('utf-8')
        except SocketError as e:
            if e.errno == errno.ECONNRESET:
                print('WARN: POST followConfirmParams ' +
                      'connection was reset')
            else:
                print('WARN: POST followConfirmParams socket error')
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy = False
            return
        except ValueError as e:
            print('ERROR: POST followConfirmParams rfile.read failed')
            print(e)
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
                    httpPrefix + '://' + domainFull + \
                    '/users/' + followerNickname
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
                self._postToOutboxThread(unfollowJson)

        if callingDomain.endswith('.onion') and onionDomain:
            originPathStr = 'http://' + onionDomain + usersPath
        elif (callingDomain.endswith('.i2p') and i2pDomain):
            originPathStr = 'http://' + i2pDomain + usersPath
        self._redirect_headers(originPathStr, cookie, callingDomain)
        self.server.POSTbusy = False

    def _followConfirm(self, callingDomain: str, cookie: str,
                       authorized: bool, path: str,
                       baseDir: str, httpPrefix: str,
                       domain: str, domainFull: str, port: int,
                       onionDomain: str, i2pDomain: str, debug: bool):
        """Confirm to follow
        """
        usersPath = path.split('/followconfirm')[0]
        originPathStr = httpPrefix + '://' + domainFull + usersPath
        followerNickname = getNicknameFromActor(originPathStr)

        length = int(self.headers['Content-length'])

        try:
            followConfirmParams = self.rfile.read(length).decode('utf-8')
        except SocketError as e:
            if e.errno == errno.ECONNRESET:
                print('WARN: POST followConfirmParams ' +
                      'connection was reset')
            else:
                print('WARN: POST followConfirmParams socket error')
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy = False
            return
        except ValueError as e:
            print('ERROR: POST followConfirmParams rfile.read failed')
            print(e)
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
            else:
                if debug:
                    print('Sending follow request from ' +
                          followerNickname + ' to ' + followingActor)
                sendFollowRequest(self.server.session,
                                  baseDir, followerNickname,
                                  domain, port,
                                  httpPrefix,
                                  followingNickname,
                                  followingDomain,
                                  followingPort, httpPrefix,
                                  False, self.server.federationList,
                                  self.server.sendThreads,
                                  self.server.postLog,
                                  self.server.cachedWebfingers,
                                  self.server.personCache,
                                  debug,
                                  self.server.projectVersion)
        if callingDomain.endswith('.onion') and onionDomain:
            originPathStr = 'http://' + onionDomain + usersPath
        elif (callingDomain.endswith('.i2p') and i2pDomain):
            originPathStr = 'http://' + i2pDomain + usersPath
        self._redirect_headers(originPathStr, cookie, callingDomain)
        self.server.POSTbusy = False

    def _blockConfirm(self, callingDomain: str, cookie: str,
                      authorized: bool, path: str,
                      baseDir: str, httpPrefix: str,
                      domain: str, domainFull: str, port: int,
                      onionDomain: str, i2pDomain: str, debug: bool):
        """Confirms a block
        """
        usersPath = path.split('/blockconfirm')[0]
        originPathStr = httpPrefix + '://' + domainFull + usersPath
        blockerNickname = getNicknameFromActor(originPathStr)
        if not blockerNickname:
            if callingDomain.endswith('.onion') and onionDomain:
                originPathStr = 'http://' + onionDomain + usersPath
            elif (callingDomain.endswith('.i2p') and i2pDomain):
                originPathStr = 'http://' + i2pDomain + usersPath
            print('WARN: unable to find nickname in ' + originPathStr)
            self._redirect_headers(originPathStr,
                                   cookie, callingDomain)
            self.server.POSTbusy = False
            return

        length = int(self.headers['Content-length'])

        try:
            blockConfirmParams = self.rfile.read(length).decode('utf-8')
        except SocketError as e:
            if e.errno == errno.ECONNRESET:
                print('WARN: POST blockConfirmParams ' +
                      'connection was reset')
            else:
                print('WARN: POST blockConfirmParams socket error')
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy = False
            return
        except ValueError as e:
            print('ERROR: POST blockConfirmParams rfile.read failed')
            print(e)
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
                if callingDomain.endswith('.onion') and onionDomain:
                    originPathStr = 'http://' + onionDomain + usersPath
                elif (callingDomain.endswith('.i2p') and i2pDomain):
                    originPathStr = 'http://' + i2pDomain + usersPath
                print('WARN: unable to find nickname in ' + blockingActor)
                self._redirect_headers(originPathStr,
                                       cookie, callingDomain)
                self.server.POSTbusy = False
                return
            blockingDomain, blockingPort = \
                getDomainFromActor(blockingActor)
            blockingDomainFull = blockingDomain
            if blockingPort:
                if blockingPort != 80 and blockingPort != 443:
                    if ':' not in blockingDomain:
                        blockingDomainFull = \
                            blockingDomain + ':' + str(blockingPort)
            if blockerNickname == blockingNickname and \
               blockingDomain == domain and \
               blockingPort == port:
                if debug:
                    print('You cannot block yourself!')
            else:
                if debug:
                    print('Adding block by ' + blockerNickname +
                          ' of ' + blockingActor)
                addBlock(baseDir, blockerNickname,
                         domain,
                         blockingNickname,
                         blockingDomainFull)
        if callingDomain.endswith('.onion') and onionDomain:
            originPathStr = 'http://' + onionDomain + usersPath
        elif (callingDomain.endswith('.i2p') and i2pDomain):
            originPathStr = 'http://' + i2pDomain + usersPath
        self._redirect_headers(originPathStr, cookie, callingDomain)
        self.server.POSTbusy = False

    def _unblockConfirm(self, callingDomain: str, cookie: str,
                        authorized: bool, path: str,
                        baseDir: str, httpPrefix: str,
                        domain: str, domainFull: str, port: int,
                        onionDomain: str, i2pDomain: str, debug: bool):
        """Confirms a unblock
        """
        usersPath = path.split('/unblockconfirm')[0]
        originPathStr = httpPrefix + '://' + domainFull + usersPath
        blockerNickname = getNicknameFromActor(originPathStr)
        if not blockerNickname:
            if callingDomain.endswith('.onion') and onionDomain:
                originPathStr = 'http://' + onionDomain + usersPath
            elif (callingDomain.endswith('.i2p') and i2pDomain):
                originPathStr = 'http://' + i2pDomain + usersPath
            print('WARN: unable to find nickname in ' + originPathStr)
            self._redirect_headers(originPathStr,
                                   cookie, callingDomain)
            self.server.POSTbusy = False
            return

        length = int(self.headers['Content-length'])

        try:
            blockConfirmParams = self.rfile.read(length).decode('utf-8')
        except SocketError as e:
            if e.errno == errno.ECONNRESET:
                print('WARN: POST blockConfirmParams ' +
                      'connection was reset')
            else:
                print('WARN: POST blockConfirmParams socket error')
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy = False
            return
        except ValueError as e:
            print('ERROR: POST blockConfirmParams rfile.read failed')
            print(e)
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
                if callingDomain.endswith('.onion') and onionDomain:
                    originPathStr = 'http://' + onionDomain + usersPath
                elif (callingDomain.endswith('.i2p') and i2pDomain):
                    originPathStr = 'http://' + i2pDomain + usersPath
                print('WARN: unable to find nickname in ' + blockingActor)
                self._redirect_headers(originPathStr,
                                       cookie, callingDomain)
                self.server.POSTbusy = False
                return
            blockingDomain, blockingPort = \
                getDomainFromActor(blockingActor)
            blockingDomainFull = blockingDomain
            if blockingPort:
                if blockingPort != 80 and blockingPort != 443:
                    if ':' not in blockingDomain:
                        blockingDomainFull = \
                            blockingDomain + ':' + str(blockingPort)
            if blockerNickname == blockingNickname and \
               blockingDomain == domain and \
               blockingPort == port:
                if debug:
                    print('You cannot unblock yourself!')
            else:
                if debug:
                    print(blockerNickname + ' stops blocking ' +
                          blockingActor)
                removeBlock(baseDir,
                            blockerNickname, domain,
                            blockingNickname, blockingDomainFull)
        if callingDomain.endswith('.onion') and onionDomain:
            originPathStr = 'http://' + onionDomain + usersPath
        elif (callingDomain.endswith('.i2p') and i2pDomain):
            originPathStr = 'http://' + i2pDomain + usersPath
        self._redirect_headers(originPathStr,
                               cookie, callingDomain)
        self.server.POSTbusy = False

    def _receiveSearchQuery(self, callingDomain: str, cookie: str,
                            authorized: bool, path: str,
                            baseDir: str, httpPrefix: str,
                            domain: str, domainFull: str,
                            port: int, searchForEmoji: bool,
                            onionDomain: str, i2pDomain: str, debug: bool):
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
        actorStr = httpPrefix + '://' + domainFull + usersPath
        length = int(self.headers['Content-length'])
        try:
            searchParams = self.rfile.read(length).decode('utf-8')
        except SocketError as e:
            if e.errno == errno.ECONNRESET:
                print('WARN: POST searchParams connection was reset')
            else:
                print('WARN: POST searchParams socket error')
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy = False
            return
        except ValueError as e:
            print('ERROR: POST searchParams rfile.read failed')
            print(e)
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy = False
            return
        if 'submitBack=' in searchParams:
            # go back on search screen
            if callingDomain.endswith('.onion') and onionDomain:
                actorStr = 'http://' + onionDomain + usersPath
            elif (callingDomain.endswith('.i2p') and i2pDomain):
                actorStr = 'http://' + i2pDomain + usersPath
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
                    htmlHashtagSearch(nickname,
                                      domain,
                                      port,
                                      self.server.recentPostsCache,
                                      self.server.maxRecentPosts,
                                      self.server.translate,
                                      baseDir,
                                      searchStr[1:], 1,
                                      maxPostsInFeed,
                                      self.server.session,
                                      self.server.cachedWebfingers,
                                      self.server.personCache,
                                      httpPrefix,
                                      self.server.projectVersion,
                                      self.server.YTReplacementDomain)
                if hashtagStr:
                    msg = hashtagStr.encode('utf-8')
                    self._login_headers('text/html',
                                        len(msg), callingDomain)
                    self._write(msg)
                    self.server.POSTbusy = False
                    return
            elif searchStr.startswith('*'):
                # skill search
                searchStr = searchStr.replace('*', '').strip()
                skillStr = \
                    htmlSkillsSearch(self.server.translate,
                                     baseDir,
                                     httpPrefix,
                                     searchStr,
                                     self.server.instanceOnlySkillsSearch,
                                     64)
                if skillStr:
                    msg = skillStr.encode('utf-8')
                    self._login_headers('text/html',
                                        len(msg), callingDomain)
                    self._write(msg)
                    self.server.POSTbusy = False
                    return
            elif searchStr.startswith('!'):
                # your post history search
                nickname = getNicknameFromActor(actorStr)
                searchStr = searchStr.replace('!', '').strip()
                historyStr = \
                    htmlHistorySearch(self.server.translate,
                                      baseDir,
                                      httpPrefix,
                                      nickname,
                                      domain,
                                      searchStr,
                                      maxPostsInFeed,
                                      pageNumber,
                                      self.server.projectVersion,
                                      self.server.recentPostsCache,
                                      self.server.maxRecentPosts,
                                      self.server.session,
                                      self.server.cachedWebfingers,
                                      self.server.personCache,
                                      port,
                                      self.server.YTReplacementDomain)
                if historyStr:
                    msg = historyStr.encode('utf-8')
                    self._login_headers('text/html',
                                        len(msg), callingDomain)
                    self._write(msg)
                    self.server.POSTbusy = False
                    return
            elif ('@' in searchStr or
                  ('://' in searchStr and
                   ('/users/' in searchStr or
                    '/profile/' in searchStr or
                    '/accounts/' in searchStr or
                    '/channel/' in searchStr))):
                # profile search
                nickname = getNicknameFromActor(actorStr)
                if not self.server.session:
                    print('Starting new session during handle search')
                    self.server.session = \
                        createSession(self.server.proxyType)
                    if not self.server.session:
                        print('ERROR: POST failed to create session ' +
                              'during handle search')
                        self._404()
                        self.server.POSTbusy = False
                        return
                profilePathStr = path.replace('/searchhandle', '')
                profileStr = \
                    htmlProfileAfterSearch(self.server.recentPostsCache,
                                           self.server.maxRecentPosts,
                                           self.server.translate,
                                           baseDir,
                                           profilePathStr,
                                           httpPrefix,
                                           nickname,
                                           domain,
                                           port,
                                           searchStr,
                                           self.server.session,
                                           self.server.cachedWebfingers,
                                           self.server.personCache,
                                           self.server.debug,
                                           self.server.projectVersion,
                                           self.server.YTReplacementDomain)
                if profileStr:
                    msg = profileStr.encode('utf-8')
                    self._login_headers('text/html',
                                        len(msg), callingDomain)
                    self._write(msg)
                    self.server.POSTbusy = False
                    return
                else:
                    if callingDomain.endswith('.onion') and onionDomain:
                        actorStr = 'http://' + onionDomain + usersPath
                    elif (callingDomain.endswith('.i2p') and i2pDomain):
                        actorStr = 'http://' + i2pDomain + usersPath
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
                    htmlSearchEmoji(self.server.translate,
                                    baseDir,
                                    httpPrefix,
                                    searchStr)
                if emojiStr:
                    msg = emojiStr.encode('utf-8')
                    self._login_headers('text/html',
                                        len(msg), callingDomain)
                    self._write(msg)
                    self.server.POSTbusy = False
                    return
            else:
                # shared items search
                sharedItemsStr = \
                    htmlSearchSharedItems(self.server.translate,
                                          baseDir,
                                          searchStr, pageNumber,
                                          maxPostsInFeed,
                                          httpPrefix,
                                          domainFull,
                                          actorStr, callingDomain)
                if sharedItemsStr:
                    msg = sharedItemsStr.encode('utf-8')
                    self._login_headers('text/html',
                                        len(msg), callingDomain)
                    self._write(msg)
                    self.server.POSTbusy = False
                    return
        if callingDomain.endswith('.onion') and onionDomain:
            actorStr = 'http://' + onionDomain + usersPath
        elif callingDomain.endswith('.i2p') and i2pDomain:
            actorStr = 'http://' + i2pDomain + usersPath
        self._redirect_headers(actorStr + '/' +
                               self.server.defaultTimeline,
                               cookie, callingDomain)
        self.server.POSTbusy = False

    def _receiveVote(self, callingDomain: str, cookie: str,
                     authorized: bool, path: str,
                     baseDir: str, httpPrefix: str,
                     domain: str, domainFull: str,
                     onionDomain: str, i2pDomain: str, debug: bool):
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
        actor = httpPrefix + '://' + domainFull + usersPath
        nickname = getNicknameFromActor(actor)
        if not nickname:
            if callingDomain.endswith('.onion') and onionDomain:
                actor = 'http://' + onionDomain + usersPath
            elif (callingDomain.endswith('.i2p') and i2pDomain):
                actor = 'http://' + i2pDomain + usersPath
            self._redirect_headers(actor + '/' +
                                   self.server.defaultTimeline +
                                   '?page=' + str(pageNumber),
                                   cookie, callingDomain)
            self.server.POSTbusy = False
            return

        # get the parameters
        length = int(self.headers['Content-length'])

        try:
            questionParams = self.rfile.read(length).decode('utf-8')
        except SocketError as e:
            if e.errno == errno.ECONNRESET:
                print('WARN: POST questionParams connection was reset')
            else:
                print('WARN: POST questionParams socket error')
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy = False
            return
        except ValueError as e:
            print('ERROR: POST questionParams rfile.read failed')
            print(e)
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
        if callingDomain.endswith('.onion') and onionDomain:
            actor = 'http://' + onionDomain + usersPath
        elif (callingDomain.endswith('.i2p') and i2pDomain):
            actor = 'http://' + i2pDomain + usersPath
        self._redirect_headers(actor + '/' +
                               self.server.defaultTimeline +
                               '?page=' + str(pageNumber), cookie,
                               callingDomain)
        self.server.POSTbusy = False
        return

    def _receiveImage(self, length: int,
                      callingDomain: str, cookie: str,
                      authorized: bool, path: str,
                      baseDir: str, httpPrefix: str,
                      domain: str, domainFull: str,
                      onionDomain: str, i2pDomain: str, debug: bool):
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
        accountsDir = \
            baseDir + '/accounts/' + \
            self.postFromNickname + '@' + domain
        if not os.path.isdir(accountsDir):
            self._404()
            self.server.POSTbusy = False
            return

        try:
            mediaBytes = self.rfile.read(length)
        except SocketError as e:
            if e.errno == errno.ECONNRESET:
                print('WARN: POST mediaBytes ' +
                      'connection reset by peer')
            else:
                print('WARN: POST mediaBytes socket error')
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy = False
            return
        except ValueError as e:
            print('ERROR: POST mediaBytes rfile.read failed')
            print(e)
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy = False
            return

        mediaFilenameBase = accountsDir + '/upload'
        mediaFilename = mediaFilenameBase + '.png'
        if self.headers['Content-type'].endswith('jpeg'):
            mediaFilename = mediaFilenameBase + '.jpg'
        if self.headers['Content-type'].endswith('gif'):
            mediaFilename = mediaFilenameBase + '.gif'
        if self.headers['Content-type'].endswith('webp'):
            mediaFilename = mediaFilenameBase + '.webp'
        if self.headers['Content-type'].endswith('avif'):
            mediaFilename = mediaFilenameBase + '.avif'
        with open(mediaFilename, 'wb') as avFile:
            avFile.write(mediaBytes)
        if debug:
            print('DEBUG: image saved to ' + mediaFilename)
        self.send_response(201)
        self.end_headers()
        self.server.POSTbusy = False

    def _removeShare(self, callingDomain: str, cookie: str,
                     authorized: bool, path: str,
                     baseDir: str, httpPrefix: str,
                     domain: str, domainFull: str,
                     onionDomain: str, i2pDomain: str, debug: bool):
        """Removes a shared item
        """
        usersPath = path.split('/rmshare')[0]
        originPathStr = httpPrefix + '://' + domainFull + usersPath

        length = int(self.headers['Content-length'])

        try:
            removeShareConfirmParams = \
                self.rfile.read(length).decode('utf-8')
        except SocketError as e:
            if e.errno == errno.ECONNRESET:
                print('WARN: POST removeShareConfirmParams ' +
                      'connection was reset')
            else:
                print('WARN: POST removeShareConfirmParams socket error')
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy = False
            return
        except ValueError as e:
            print('ERROR: POST removeShareConfirmParams rfile.read failed')
            print(e)
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy = False
            return

        if '&submitYes=' in removeShareConfirmParams:
            removeShareConfirmParams = \
                removeShareConfirmParams.replace('+', ' ').strip()
            removeShareConfirmParams = \
                urllib.parse.unquote_plus(removeShareConfirmParams)
            shareActor = removeShareConfirmParams.split('actor=')[1]
            if '&' in shareActor:
                shareActor = shareActor.split('&')[0]
            shareName = removeShareConfirmParams.split('shareName=')[1]
            if '&' in shareName:
                shareName = shareName.split('&')[0]
            shareNickname = getNicknameFromActor(shareActor)
            if shareNickname:
                shareDomain, sharePort = getDomainFromActor(shareActor)
                removeShare(baseDir,
                            shareNickname, shareDomain, shareName)

        if callingDomain.endswith('.onion') and onionDomain:
            originPathStr = 'http://' + onionDomain + usersPath
        elif (callingDomain.endswith('.i2p') and i2pDomain):
            originPathStr = 'http://' + i2pDomain + usersPath
        self._redirect_headers(originPathStr + '/tlshares',
                               cookie, callingDomain)
        self.server.POSTbusy = False

    def _removePost(self, callingDomain: str, cookie: str,
                    authorized: bool, path: str,
                    baseDir: str, httpPrefix: str,
                    domain: str, domainFull: str,
                    onionDomain: str, i2pDomain: str, debug: bool):
        """Endpoint for removing posts
        """
        pageNumber = 1
        usersPath = path.split('/rmpost')[0]
        originPathStr = \
            httpPrefix + '://' + \
            domainFull + usersPath

        length = int(self.headers['Content-length'])

        try:
            removePostConfirmParams = \
                self.rfile.read(length).decode('utf-8')
        except SocketError as e:
            if e.errno == errno.ECONNRESET:
                print('WARN: POST removePostConfirmParams ' +
                      'connection was reset')
            else:
                print('WARN: POST removePostConfirmParams socket error')
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy = False
            return
        except ValueError as e:
            print('ERROR: POST removePostConfirmParams rfile.read failed')
            print(e)
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
                    'cc': [removePostActor+'/followers'],
                    'type': 'Delete'
                }
                self.postToNickname = getNicknameFromActor(removePostActor)
                if self.postToNickname:
                    if monthStr and yearStr:
                        if monthStr.isdigit() and yearStr.isdigit():
                            removeCalendarEvent(baseDir,
                                                self.postToNickname,
                                                domain,
                                                int(yearStr),
                                                int(monthStr),
                                                removeMessageId)
                    self._postToOutboxThread(deleteJson)
        if callingDomain.endswith('.onion') and onionDomain:
            originPathStr = 'http://' + onionDomain + usersPath
        elif (callingDomain.endswith('.i2p') and i2pDomain):
            originPathStr = 'http://' + i2pDomain + usersPath
        if pageNumber == 1:
            self._redirect_headers(originPathStr + '/outbox', cookie,
                                   callingDomain)
        else:
            self._redirect_headers(originPathStr + '/outbox?page=' +
                                   str(pageNumber),
                                   cookie, callingDomain)
        self.server.POSTbusy = False

    def _linksUpdate(self, callingDomain: str, cookie: str,
                     authorized: bool, path: str,
                     baseDir: str, httpPrefix: str,
                     domain: str, domainFull: str,
                     onionDomain: str, i2pDomain: str, debug: bool,
                     defaultTimeline: str):
        """Updates the left links column of the timeline
        """
        usersPath = path.replace('/linksdata', '')
        usersPath = usersPath.replace('/editlinks', '')
        actorStr = httpPrefix + '://' + domainFull + usersPath
        if ' boundary=' in self.headers['Content-type']:
            boundary = self.headers['Content-type'].split('boundary=')[1]
            if ';' in boundary:
                boundary = boundary.split(';')[0]

            # get the nickname
            nickname = getNicknameFromActor(actorStr)
            moderator = None
            if nickname:
                moderator = isModerator(baseDir, nickname)
            if not nickname or not moderator:
                if callingDomain.endswith('.onion') and \
                   onionDomain:
                    actorStr = \
                        'http://' + onionDomain + usersPath
                elif (callingDomain.endswith('.i2p') and
                      i2pDomain):
                    actorStr = \
                        'http://' + i2pDomain + usersPath
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
                if callingDomain.endswith('.onion') and \
                   onionDomain:
                    actorStr = \
                        'http://' + onionDomain + usersPath
                elif (callingDomain.endswith('.i2p') and
                      i2pDomain):
                    actorStr = \
                        'http://' + i2pDomain + usersPath
                print('Maximum links data length exceeded ' + str(length))
                self._redirect_headers(actorStr, cookie, callingDomain)
                self.server.POSTbusy = False
                return

            try:
                # read the bytes of the http form POST
                postBytes = self.rfile.read(length)
            except SocketError as e:
                if e.errno == errno.ECONNRESET:
                    print('WARN: connection was reset while ' +
                          'reading bytes from http form POST')
                else:
                    print('WARN: error while reading bytes ' +
                          'from http form POST')
                self.send_response(400)
                self.end_headers()
                self.server.POSTbusy = False
                return
            except ValueError as e:
                print('ERROR: failed to read bytes for POST')
                print(e)
                self.send_response(400)
                self.end_headers()
                self.server.POSTbusy = False
                return

            linksFilename = baseDir + '/accounts/links.txt'

            # extract all of the text fields into a dict
            fields = \
                extractTextFieldsInPOST(postBytes, boundary, debug)
            if fields.get('editedLinks'):
                linksStr = fields['editedLinks']
                linksFile = open(linksFilename, "w+")
                if linksFile:
                    linksFile.write(linksStr)
                    linksFile.close()
            else:
                if os.path.isfile(linksFilename):
                    os.remove(linksFilename)

        # redirect back to the default timeline
        if callingDomain.endswith('.onion') and \
           onionDomain:
            actorStr = \
                'http://' + onionDomain + usersPath
        elif (callingDomain.endswith('.i2p') and
              i2pDomain):
            actorStr = \
                'http://' + i2pDomain + usersPath
        self._redirect_headers(actorStr + '/' + defaultTimeline,
                               cookie, callingDomain)
        self.server.POSTbusy = False

    def _newswireUpdate(self, callingDomain: str, cookie: str,
                        authorized: bool, path: str,
                        baseDir: str, httpPrefix: str,
                        domain: str, domainFull: str,
                        onionDomain: str, i2pDomain: str, debug: bool,
                        defaultTimeline: str):
        """Updates the right newswire column of the timeline
        """
        usersPath = path.replace('/newswiredata', '')
        usersPath = usersPath.replace('/editnewswire', '')
        actorStr = httpPrefix + '://' + domainFull + usersPath
        if ' boundary=' in self.headers['Content-type']:
            boundary = self.headers['Content-type'].split('boundary=')[1]
            if ';' in boundary:
                boundary = boundary.split(';')[0]

            # get the nickname
            nickname = getNicknameFromActor(actorStr)
            moderator = None
            if nickname:
                moderator = isModerator(baseDir, nickname)
            if not nickname or not moderator:
                if callingDomain.endswith('.onion') and \
                   onionDomain:
                    actorStr = \
                        'http://' + onionDomain + usersPath
                elif (callingDomain.endswith('.i2p') and
                      i2pDomain):
                    actorStr = \
                        'http://' + i2pDomain + usersPath
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
                if callingDomain.endswith('.onion') and \
                   onionDomain:
                    actorStr = \
                        'http://' + onionDomain + usersPath
                elif (callingDomain.endswith('.i2p') and
                      i2pDomain):
                    actorStr = \
                        'http://' + i2pDomain + usersPath
                print('Maximum newswire data length exceeded ' + str(length))
                self._redirect_headers(actorStr, cookie, callingDomain)
                self.server.POSTbusy = False
                return

            try:
                # read the bytes of the http form POST
                postBytes = self.rfile.read(length)
            except SocketError as e:
                if e.errno == errno.ECONNRESET:
                    print('WARN: connection was reset while ' +
                          'reading bytes from http form POST')
                else:
                    print('WARN: error while reading bytes ' +
                          'from http form POST')
                self.send_response(400)
                self.end_headers()
                self.server.POSTbusy = False
                return
            except ValueError as e:
                print('ERROR: failed to read bytes for POST')
                print(e)
                self.send_response(400)
                self.end_headers()
                self.server.POSTbusy = False
                return

            newswireFilename = baseDir + '/accounts/newswire.txt'

            # extract all of the text fields into a dict
            fields = \
                extractTextFieldsInPOST(postBytes, boundary, debug)
            if fields.get('editedNewswire'):
                newswireStr = fields['editedNewswire']
                newswireFile = open(newswireFilename, "w+")
                if newswireFile:
                    newswireFile.write(newswireStr)
                    newswireFile.close()
            else:
                if os.path.isfile(newswireFilename):
                    os.remove(newswireFilename)

            newswireTrustedFilename = baseDir + '/accounts/newswiretrusted.txt'
            if fields.get('trustedNewswire'):
                newswireTrusted = fields['trustedNewswire']
                if not newswireTrusted.endswith('\n'):
                    newswireTrusted += '\n'
                trustFile = open(newswireTrustedFilename, "w+")
                if trustFile:
                    trustFile.write(newswireTrusted)
                    trustFile.close()
            else:
                if os.path.isfile(newswireTrustedFilename):
                    os.remove(newswireTrustedFilename)

        # redirect back to the default timeline
        if callingDomain.endswith('.onion') and \
           onionDomain:
            actorStr = \
                'http://' + onionDomain + usersPath
        elif (callingDomain.endswith('.i2p') and
              i2pDomain):
            actorStr = \
                'http://' + i2pDomain + usersPath
        self._redirect_headers(actorStr + '/' + defaultTimeline,
                               cookie, callingDomain)
        self.server.POSTbusy = False

    def _profileUpdate(self, callingDomain: str, cookie: str,
                       authorized: bool, path: str,
                       baseDir: str, httpPrefix: str,
                       domain: str, domainFull: str,
                       onionDomain: str, i2pDomain: str, debug: bool):
        """Updates your user profile after editing via the Edit button
        on the profile screen
        """
        usersPath = path.replace('/profiledata', '')
        usersPath = usersPath.replace('/editprofile', '')
        actorStr = httpPrefix + '://' + domainFull + usersPath
        if ' boundary=' in self.headers['Content-type']:
            boundary = self.headers['Content-type'].split('boundary=')[1]
            if ';' in boundary:
                boundary = boundary.split(';')[0]

            # get the nickname
            nickname = getNicknameFromActor(actorStr)
            if not nickname:
                if callingDomain.endswith('.onion') and \
                   onionDomain:
                    actorStr = \
                        'http://' + onionDomain + usersPath
                elif (callingDomain.endswith('.i2p') and
                      i2pDomain):
                    actorStr = \
                        'http://' + i2pDomain + usersPath
                print('WARN: nickname not found in ' + actorStr)
                self._redirect_headers(actorStr, cookie, callingDomain)
                self.server.POSTbusy = False
                return

            length = int(self.headers['Content-length'])

            # check that the POST isn't too large
            if length > self.server.maxPostLength:
                if callingDomain.endswith('.onion') and \
                   onionDomain:
                    actorStr = \
                        'http://' + onionDomain + usersPath
                elif (callingDomain.endswith('.i2p') and
                      i2pDomain):
                    actorStr = \
                        'http://' + i2pDomain + usersPath
                print('Maximum profile data length exceeded ' +
                      str(length))
                self._redirect_headers(actorStr, cookie, callingDomain)
                self.server.POSTbusy = False
                return

            try:
                # read the bytes of the http form POST
                postBytes = self.rfile.read(length)
            except SocketError as e:
                if e.errno == errno.ECONNRESET:
                    print('WARN: connection was reset while ' +
                          'reading bytes from http form POST')
                else:
                    print('WARN: error while reading bytes ' +
                          'from http form POST')
                self.send_response(400)
                self.end_headers()
                self.server.POSTbusy = False
                return
            except ValueError as e:
                print('ERROR: failed to read bytes for POST')
                print(e)
                self.send_response(400)
                self.end_headers()
                self.server.POSTbusy = False
                return

            # get the various avatar, banner and background images
            actorChanged = True
            profileMediaTypes = ('avatar', 'image',
                                 'banner', 'search_banner',
                                 'instanceLogo',
                                 'left_col_image', 'right_col_image')
            profileMediaTypesUploaded = {}
            for mType in profileMediaTypes:
                if debug:
                    print('DEBUG: profile update extracting ' + mType +
                          ' image or font from POST')
                mediaBytes, postBytes = \
                    extractMediaInFormPOST(postBytes, boundary, mType)
                if mediaBytes:
                    if debug:
                        print('DEBUG: profile update ' + mType +
                              ' image or font was found. ' +
                              str(len(mediaBytes)) + ' bytes')
                else:
                    if debug:
                        print('DEBUG: profile update, no ' + mType +
                              ' image or font was found in POST')
                    continue

                # Note: a .temp extension is used here so that at no
                # time is an image with metadata publicly exposed,
                # even for a few mS
                if mType == 'instanceLogo':
                    filenameBase = \
                        baseDir + '/accounts/login.temp'
                else:
                    filenameBase = \
                        baseDir + '/accounts/' + \
                        nickname + '@' + domain + \
                        '/' + mType + '.temp'

                filename, attachmentMediaType = \
                    saveMediaInFormPOST(mediaBytes, debug,
                                        filenameBase)
                if filename:
                    print('Profile update POST ' + mType +
                          ' media or font filename is ' + filename)
                else:
                    print('Profile update, no ' + mType +
                          ' media or font filename in POST')
                    continue

                postImageFilename = filename.replace('.temp', '')
                if debug:
                    print('DEBUG: POST ' + mType +
                          ' media removing metadata')
                # remove existing etag
                if os.path.isfile(postImageFilename + '.etag'):
                    try:
                        os.remove(postImageFilename + '.etag')
                    except BaseException:
                        pass
                removeMetaData(filename, postImageFilename)
                if os.path.isfile(postImageFilename):
                    print('profile update POST ' + mType +
                          ' image or font saved to ' + postImageFilename)
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
                baseDir + '/accounts/' + \
                nickname + '@' + domain + '.json'
            if os.path.isfile(actorFilename):
                actorJson = loadJson(actorFilename)
                if actorJson:
                    # update the avatar/image url file extension
                    uploads = profileMediaTypesUploaded.items()
                    for mType, lastPart in uploads:
                        repStr = '/' + lastPart
                        if mType == 'avatar':
                            lastPartOfUrl = \
                                actorJson['icon']['url'].split('/')[-1]
                            srchStr = '/' + lastPartOfUrl
                            actorJson['icon']['url'] = \
                                actorJson['icon']['url'].replace(srchStr,
                                                                 repStr)
                        elif mType == 'image':
                            lastPartOfUrl = \
                                actorJson['image']['url'].split('/')[-1]
                            srchStr = '/' + lastPartOfUrl
                            actorJson['image']['url'] = \
                                actorJson['image']['url'].replace(srchStr,
                                                                  repStr)

                    # set skill levels
                    skillCtr = 1
                    newSkills = {}
                    while skillCtr < 10:
                        skillName = \
                            fields.get('skillName' + str(skillCtr))
                        if not skillName:
                            skillCtr += 1
                            continue
                        skillValue = \
                            fields.get('skillValue' + str(skillCtr))
                        if not skillValue:
                            skillCtr += 1
                            continue
                        if not actorJson['skills'].get(skillName):
                            actorChanged = True
                        else:
                            if actorJson['skills'][skillName] != \
                               int(skillValue):
                                actorChanged = True
                        newSkills[skillName] = int(skillValue)
                        skillCtr += 1
                    if len(actorJson['skills'].items()) != \
                       len(newSkills.items()):
                        actorChanged = True
                    actorJson['skills'] = newSkills

                    # change password
                    if fields.get('password'):
                        if fields.get('passwordconfirm'):
                            if actorJson['password'] == \
                               fields['passwordconfirm']:
                                if len(actorJson['password']) > 2:
                                    # set password
                                    pwd = actorJson['password']
                                    storeBasicCredentials(baseDir,
                                                          nickname,
                                                          pwd)

                    # change displayed name
                    if fields.get('displayNickname'):
                        if fields['displayNickname'] != actorJson['name']:
                            actorJson['name'] = fields['displayNickname']
                            actorChanged = True
                    if fields.get('themeDropdown'):
                        setTheme(baseDir,
                                 fields['themeDropdown'])

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

                    # change instance title
                    if fields.get('instanceTitle'):
                        currInstanceTitle = \
                            getConfigParam(baseDir,
                                           'instanceTitle')
                        if fields['instanceTitle'] != currInstanceTitle:
                            setConfigParam(baseDir,
                                           'instanceTitle',
                                           fields['instanceTitle'])

                    # change YouTube alternate domain
                    if fields.get('ytdomain'):
                        currYTDomain = self.server.YTReplacementDomain
                        if fields['ytdomain'] != currYTDomain:
                            newYTDomain = fields['ytdomain']
                            if '://' in newYTDomain:
                                newYTDomain = newYTDomain.split('://')[1]
                            if '/' in newYTDomain:
                                newYTDomain = newYTDomain.split('/')[0]
                            if '.' in newYTDomain:
                                setConfigParam(baseDir,
                                               'youtubedomain',
                                               newYTDomain)
                                self.server.YTReplacementDomain = \
                                    newYTDomain
                    else:
                        setConfigParam(baseDir,
                                       'youtubedomain', '')
                        self.server.YTReplacementDomain = None

                    # change instance description
                    currInstanceDescriptionShort = \
                        getConfigParam(baseDir,
                                       'instanceDescriptionShort')
                    if fields.get('instanceDescriptionShort'):
                        if fields['instanceDescriptionShort'] != \
                           currInstanceDescriptionShort:
                            iDesc = fields['instanceDescriptionShort']
                            setConfigParam(baseDir,
                                           'instanceDescriptionShort',
                                           iDesc)
                    else:
                        if currInstanceDescriptionShort:
                            setConfigParam(baseDir,
                                           'instanceDescriptionShort', '')
                    currInstanceDescription = \
                        getConfigParam(baseDir,
                                       'instanceDescription')
                    if fields.get('instanceDescription'):
                        if fields['instanceDescription'] != \
                           currInstanceDescription:
                            setConfigParam(baseDir,
                                           'instanceDescription',
                                           fields['instanceDescription'])
                    else:
                        if currInstanceDescription:
                            setConfigParam(baseDir,
                                           'instanceDescription', '')

                    # change user bio
                    if fields.get('bio'):
                        if fields['bio'] != actorJson['summary']:
                            actorTags = {}
                            actorJson['summary'] = \
                                addHtmlTags(baseDir,
                                            httpPrefix,
                                            nickname,
                                            domainFull,
                                            fields['bio'], [], actorTags)
                            if actorTags:
                                actorJson['tag'] = []
                                for tagName, tag in actorTags.items():
                                    actorJson['tag'].append(tag)
                            actorChanged = True
                    else:
                        if actorJson['summary']:
                            actorJson['summary'] = ''
                            actorChanged = True

                    # change moderators list
                    if fields.get('moderators'):
                        adminNickname = \
                            getConfigParam(baseDir, 'admin')
                        if path.startswith('/users/' +
                                           adminNickname + '/'):
                            moderatorsFile = \
                                baseDir + \
                                '/accounts/moderators.txt'
                            clearModeratorStatus(baseDir)
                            if ',' in fields['moderators']:
                                # if the list was given as comma separated
                                modFile = open(moderatorsFile, "w+")
                                mods = fields['moderators'].split(',')
                                for modNick in mods:
                                    modNick = modNick.strip()
                                    modDir = baseDir + \
                                        '/accounts/' + modNick + \
                                        '@' + domain
                                    if os.path.isdir(modDir):
                                        modFile.write(modNick + '\n')
                                modFile.close()
                                mods = fields['moderators'].split(',')
                                for modNick in mods:
                                    modNick = modNick.strip()
                                    modDir = baseDir + \
                                        '/accounts/' + modNick + \
                                        '@' + domain
                                    if os.path.isdir(modDir):
                                        setRole(baseDir,
                                                modNick, domain,
                                                'instance', 'moderator')
                            else:
                                # nicknames on separate lines
                                modFile = open(moderatorsFile, "w+")
                                mods = fields['moderators'].split('\n')
                                for modNick in mods:
                                    modNick = modNick.strip()
                                    modDir = \
                                        baseDir + \
                                        '/accounts/' + modNick + \
                                        '@' + domain
                                    if os.path.isdir(modDir):
                                        modFile.write(modNick + '\n')
                                modFile.close()
                                mods = fields['moderators'].split('\n')
                                for modNick in mods:
                                    modNick = modNick.strip()
                                    modDir = \
                                        baseDir + \
                                        '/accounts/' + \
                                        modNick + '@' + \
                                        domain
                                    if os.path.isdir(modDir):
                                        setRole(baseDir,
                                                modNick, domain,
                                                'instance',
                                                'moderator')

                    # remove scheduled posts
                    if fields.get('removeScheduledPosts'):
                        if fields['removeScheduledPosts'] == 'on':
                            removeScheduledPosts(baseDir,
                                                 nickname, domain)

                    # approve followers
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
                        if fields['removeCustomFont'] == 'on':
                            fontExt = ('woff', 'woff2', 'otf', 'ttf')
                            for ext in fontExt:
                                if os.path.isfile(baseDir +
                                                  '/fonts/custom.' + ext):
                                    os.remove(baseDir +
                                              '/fonts/custom.' + ext)
                                if os.path.isfile(baseDir +
                                                  '/fonts/custom.' + ext +
                                                  '.etag'):
                                    os.remove(baseDir +
                                              '/fonts/custom.' + ext +
                                              '.etag')
                            currTheme = getTheme(baseDir)
                            if currTheme:
                                setTheme(baseDir, currTheme)

                    # change media instance status
                    if fields.get('mediaInstance'):
                        self.server.mediaInstance = False
                        self.server.defaultTimeline = 'inbox'
                        if fields['mediaInstance'] == 'on':
                            self.server.mediaInstance = True
                            self.server.blogsInstance = False
                            self.server.newsInstance = False
                            self.server.defaultTimeline = 'tlmedia'
                        setConfigParam(baseDir,
                                       "mediaInstance",
                                       self.server.mediaInstance)
                        setConfigParam(baseDir,
                                       "blogsInstance",
                                       self.server.blogsInstance)
                        setConfigParam(baseDir,
                                       "newsInstance",
                                       self.server.newsInstance)
                    else:
                        if self.server.mediaInstance:
                            self.server.mediaInstance = False
                            self.server.defaultTimeline = 'inbox'
                            setConfigParam(baseDir,
                                           "mediaInstance",
                                           self.server.mediaInstance)

                    # change news instance status
                    if fields.get('newsInstance'):
                        self.server.newsInstance = False
                        self.server.defaultTimeline = 'inbox'
                        if fields['mediaInstance'] == 'on':
                            self.server.newsInstance = True
                            self.server.blogsInstance = False
                            self.server.mediaInstance = False
                            self.server.defaultTimeline = 'tlnews'
                        setConfigParam(baseDir,
                                       "mediaInstance",
                                       self.server.mediaInstance)
                        setConfigParam(baseDir,
                                       "blogsInstance",
                                       self.server.blogsInstance)
                        setConfigParam(baseDir,
                                       "newsInstance",
                                       self.server.newsInstance)
                    else:
                        if self.server.newsInstance:
                            self.server.newsInstance = False
                            self.server.defaultTimeline = 'inbox'
                            setConfigParam(baseDir,
                                           "newsInstance",
                                           self.server.mediaInstance)

                    # change blog instance status
                    if fields.get('blogsInstance'):
                        self.server.blogsInstance = False
                        self.server.defaultTimeline = 'inbox'
                        if fields['blogsInstance'] == 'on':
                            self.server.blogsInstance = True
                            self.server.mediaInstance = False
                            self.server.newsInstance = False
                            self.server.defaultTimeline = 'tlblogs'
                        setConfigParam(baseDir,
                                       "blogsInstance",
                                       self.server.blogsInstance)
                        setConfigParam(baseDir,
                                       "mediaInstance",
                                       self.server.mediaInstance)
                        setConfigParam(baseDir,
                                       "newsInstance",
                                       self.server.newsInstance)
                    else:
                        if self.server.blogsInstance:
                            self.server.blogsInstance = False
                            self.server.defaultTimeline = 'inbox'
                            setConfigParam(baseDir,
                                           "blogsInstance",
                                           self.server.blogsInstance)

                    # only receive DMs from accounts you follow
                    followDMsFilename = \
                        baseDir + '/accounts/' + \
                        nickname + '@' + domain + \
                        '/.followDMs'
                    followDMsActive = False
                    if fields.get('followDMs'):
                        if fields['followDMs'] == 'on':
                            followDMsActive = True
                            with open(followDMsFilename, 'w+') as fFile:
                                fFile.write('\n')
                    if not followDMsActive:
                        if os.path.isfile(followDMsFilename):
                            os.remove(followDMsFilename)

                    # remove Twitter retweets
                    removeTwitterFilename = \
                        baseDir + '/accounts/' + \
                        nickname + '@' + domain + \
                        '/.removeTwitter'
                    removeTwitterActive = False
                    if fields.get('removeTwitter'):
                        if fields['removeTwitter'] == 'on':
                            removeTwitterActive = True
                            with open(removeTwitterFilename,
                                      'w+') as rFile:
                                rFile.write('\n')
                    if not removeTwitterActive:
                        if os.path.isfile(removeTwitterFilename):
                            os.remove(removeTwitterFilename)

                    # hide Like button
                    hideLikeButtonFile = \
                        baseDir + '/accounts/' + \
                        nickname + '@' + domain + \
                        '/.hideLikeButton'
                    notifyLikesFilename = \
                        baseDir + '/accounts/' + \
                        nickname + '@' + domain + \
                        '/.notifyLikes'
                    hideLikeButtonActive = False
                    if fields.get('hideLikeButton'):
                        if fields['hideLikeButton'] == 'on':
                            hideLikeButtonActive = True
                            with open(hideLikeButtonFile, 'w+') as rFile:
                                rFile.write('\n')
                            # remove notify likes selection
                            if os.path.isfile(notifyLikesFilename):
                                os.remove(notifyLikesFilename)
                    if not hideLikeButtonActive:
                        if os.path.isfile(hideLikeButtonFile):
                            os.remove(hideLikeButtonFile)

                    # notify about new Likes
                    notifyLikesActive = False
                    if fields.get('notifyLikes'):
                        if fields['notifyLikes'] == 'on' and \
                           not hideLikeButtonActive:
                            notifyLikesActive = True
                            with open(notifyLikesFilename, 'w+') as rFile:
                                rFile.write('\n')
                    if not notifyLikesActive:
                        if os.path.isfile(notifyLikesFilename):
                            os.remove(notifyLikesFilename)

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
                                    actorJson['type'] = 'Group'
                                    actorChanged = True
                        else:
                            # this account is a person (default)
                            if actorJson['type'] != 'Person':
                                actorJson['type'] = 'Person'
                                actorChanged = True

                    # grayscale theme
                    grayscale = False
                    if fields.get('grayscale'):
                        if fields['grayscale'] == 'on':
                            grayscale = True
                    if grayscale:
                        enableGrayscale(baseDir)
                    else:
                        disableGrayscale(baseDir)

                    # save filtered words list
                    filterFilename = \
                        baseDir + '/accounts/' + \
                        nickname + '@' + domain + \
                        '/filters.txt'
                    if fields.get('filteredWords'):
                        with open(filterFilename, 'w+') as filterfile:
                            filterfile.write(fields['filteredWords'])
                    else:
                        if os.path.isfile(filterFilename):
                            os.remove(filterFilename)

                    # word replacements
                    switchFilename = \
                        baseDir + '/accounts/' + \
                        nickname + '@' + domain + \
                        '/replacewords.txt'
                    if fields.get('switchWords'):
                        with open(switchFilename, 'w+') as switchfile:
                            switchfile.write(fields['switchWords'])
                    else:
                        if os.path.isfile(switchFilename):
                            os.remove(switchFilename)

                    # autogenerated tags
                    autoTagsFilename = \
                        baseDir + '/accounts/' + \
                        nickname + '@' + domain + \
                        '/autotags.txt'
                    if fields.get('autoTags'):
                        with open(autoTagsFilename, 'w+') as autoTagsFile:
                            autoTagsFile.write(fields['autoTags'])
                    else:
                        if os.path.isfile(autoTagsFilename):
                            os.remove(autoTagsFilename)

                    # autogenerated content warnings
                    autoCWFilename = \
                        baseDir + '/accounts/' + \
                        nickname + '@' + domain + \
                        '/autocw.txt'
                    if fields.get('autoCW'):
                        with open(autoCWFilename, 'w+') as autoCWFile:
                            autoCWFile.write(fields['autoCW'])
                    else:
                        if os.path.isfile(autoCWFilename):
                            os.remove(autoCWFilename)

                    # save blocked accounts list
                    blockedFilename = \
                        baseDir + '/accounts/' + \
                        nickname + '@' + domain + \
                        '/blocking.txt'
                    if fields.get('blocked'):
                        with open(blockedFilename, 'w+') as blockedfile:
                            blockedfile.write(fields['blocked'])
                    else:
                        if os.path.isfile(blockedFilename):
                            os.remove(blockedFilename)

                    # save allowed instances list
                    allowedInstancesFilename = \
                        baseDir + '/accounts/' + \
                        nickname + '@' + domain + \
                        '/allowedinstances.txt'
                    if fields.get('allowedInstances'):
                        with open(allowedInstancesFilename, 'w+') as aFile:
                            aFile.write(fields['allowedInstances'])
                    else:
                        if os.path.isfile(allowedInstancesFilename):
                            os.remove(allowedInstancesFilename)

                    # save git project names list
                    gitProjectsFilename = \
                        baseDir + '/accounts/' + \
                        nickname + '@' + domain + \
                        '/gitprojects.txt'
                    if fields.get('gitProjects'):
                        with open(gitProjectsFilename, 'w+') as aFile:
                            aFile.write(fields['gitProjects'].lower())
                    else:
                        if os.path.isfile(gitProjectsFilename):
                            os.remove(gitProjectsFilename)

                    # save actor json file within accounts
                    if actorChanged:
                        # update the context for the actor
                        actorJson['@context'] = [
                            'https://www.w3.org/ns/activitystreams',
                            'https://w3id.org/security/v1',
                            getDefaultPersonContext()
                        ]
                        randomizeActorImages(actorJson)
                        saveJson(actorJson, actorFilename)
                        webfingerUpdate(baseDir,
                                        nickname, domain,
                                        onionDomain,
                                        self.server.cachedWebfingers)
                        # also copy to the actors cache and
                        # personCache in memory
                        storePersonInCache(baseDir,
                                           actorJson['id'], actorJson,
                                           self.server.personCache,
                                           True)
                        # clear any cached images for this actor
                        idStr = actorJson['id'].replace('/', '-')
                        removeAvatarFromCache(baseDir, idStr)
                        # save the actor to the cache
                        actorCacheFilename = \
                            baseDir + '/cache/actors/' + \
                            actorJson['id'].replace('/', '#') + '.json'
                        saveJson(actorJson, actorCacheFilename)
                        # send profile update to followers
                        ccStr = 'https://www.w3.org/ns/' + \
                            'activitystreams#Public'
                        updateActorJson = {
                            'type': 'Update',
                            'actor': actorJson['id'],
                            'to': [actorJson['id'] + '/followers'],
                            'cc': [ccStr],
                            'object': actorJson
                        }
                        self._postToOutbox(updateActorJson,
                                           __version__, nickname)

                    # deactivate the account
                    if fields.get('deactivateThisAccount'):
                        if fields['deactivateThisAccount'] == 'on':
                            deactivateAccount(baseDir,
                                              nickname, domain)
                            self._clearLoginDetails(nickname,
                                                    callingDomain)
                            self.server.POSTbusy = False
                            return

        # redirect back to the profile screen
        if callingDomain.endswith('.onion') and \
           onionDomain:
            actorStr = \
                'http://' + onionDomain + usersPath
        elif (callingDomain.endswith('.i2p') and
              i2pDomain):
            actorStr = \
                'http://' + i2pDomain + usersPath
        self._redirect_headers(actorStr, cookie, callingDomain)
        self.server.POSTbusy = False

    def _progressiveWebAppManifest(self, callingDomain: str,
                                   GETstartTime, GETtimings: {}):
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
                    "src": "/logo152.png",
                    "type": "image/png",
                    "sizes": "152x152"
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
        self._set_headers('application/json', len(msg),
                          None, callingDomain)
        self._write(msg)
        if self.server.debug:
            print('Sent manifest: ' + callingDomain)
        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  'show logout', 'send manifest')

    def _getFavicon(self, callingDomain: str,
                    baseDir: str, debug: bool):
        """Return the favicon
        """
        favType = 'image/x-icon'
        favFilename = 'favicon.ico'
        if self._hasAccept(callingDomain):
            if 'image/webp' in self.headers['Accept']:
                favType = 'image/webp'
                favFilename = 'favicon.webp'
            if 'image/avif' in self.headers['Accept']:
                favType = 'image/avif'
                favFilename = 'favicon.avif'
        # custom favicon
        faviconFilename = baseDir + '/' + favFilename
        if not os.path.isfile(faviconFilename):
            # default favicon
            faviconFilename = \
                baseDir + '/img/icons/' + favFilename
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
                                   callingDomain)
            self._write(favBinary)
            if debug:
                print('Sent favicon from cache: ' + callingDomain)
            return
        else:
            if os.path.isfile(faviconFilename):
                with open(faviconFilename, 'rb') as favFile:
                    favBinary = favFile.read()
                    self._set_headers_etag(faviconFilename,
                                           favType,
                                           favBinary, None,
                                           callingDomain)
                    self._write(favBinary)
                    self.server.iconsCache[favFilename] = favBinary
                    if self.server.debug:
                        print('Sent favicon from file: ' + callingDomain)
                    return
        if debug:
            print('favicon not sent: ' + callingDomain)
        self._404()

    def _getFonts(self, callingDomain: str, path: str,
                  baseDir: str, debug: bool,
                  GETstartTime, GETtimings: {}):
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
                baseDir + '/fonts/' + fontStr
            if self._etag_exists(fontFilename):
                # The file has not changed
                self._304()
                return
            if self.server.fontsCache.get(fontStr):
                fontBinary = self.server.fontsCache[fontStr]
                self._set_headers_etag(fontFilename,
                                       fontType,
                                       fontBinary, None,
                                       callingDomain)
                self._write(fontBinary)
                if debug:
                    print('font sent from cache: ' +
                          path + ' ' + callingDomain)
                self._benchmarkGETtimings(GETstartTime, GETtimings,
                                          'hasAccept',
                                          'send font from cache')
                return
            else:
                if os.path.isfile(fontFilename):
                    with open(fontFilename, 'rb') as fontFile:
                        fontBinary = fontFile.read()
                        self._set_headers_etag(fontFilename,
                                               fontType,
                                               fontBinary, None,
                                               callingDomain)
                        self._write(fontBinary)
                        self.server.fontsCache[fontStr] = fontBinary
                    if debug:
                        print('font sent from file: ' +
                              path + ' ' + callingDomain)
                    self._benchmarkGETtimings(GETstartTime, GETtimings,
                                              'hasAccept',
                                              'send font from file')
                    return
        if debug:
            print('font not found: ' + path + ' ' + callingDomain)
        self._404()

    def _getRSS2feed(self, authorized: bool,
                     callingDomain: str, path: str,
                     baseDir: str, httpPrefix: str,
                     domain: str, port: int, proxyType: str,
                     GETstartTime, GETtimings: {},
                     debug: bool):
        """Returns an RSS2 feed for the blog
        """
        nickname = path.split('/blog/')[1]
        if '/' in nickname:
            nickname = nickname.split('/')[0]
        if not nickname.startswith('rss.'):
            if os.path.isdir(self.server.baseDir +
                             '/accounts/' + nickname + '@' + domain):
                if not self.server.session:
                    print('Starting new session during RSS request')
                    self.server.session = \
                        createSession(proxyType)
                    if not self.server.session:
                        print('ERROR: GET failed to create session ' +
                              'during RSS request')
                        self._404()
                        return

                msg = \
                    htmlBlogPageRSS2(authorized,
                                     self.server.session,
                                     baseDir,
                                     httpPrefix,
                                     self.server.translate,
                                     nickname,
                                     domain,
                                     port,
                                     maxPostsInRSSFeed, 1)
                if msg is not None:
                    msg = msg.encode('utf-8')
                    self._set_headers('text/xml', len(msg),
                                      None, callingDomain)
                    self._write(msg)
                    if debug:
                        print('Sent rss2 feed: ' +
                              path + ' ' + callingDomain)
                    self._benchmarkGETtimings(GETstartTime, GETtimings,
                                              'sharedInbox enabled',
                                              'blog rss2')
                    return
        if debug:
            print('Failed to get rss2 feed: ' +
                  path + ' ' + callingDomain)
        self._404()

    def _getNewswireFeed(self, authorized: bool,
                         callingDomain: str, path: str,
                         baseDir: str, httpPrefix: str,
                         domain: str, port: int, proxyType: str,
                         GETstartTime, GETtimings: {},
                         debug: bool):
        """Returns the newswire feed
        """
        if not self.server.session:
            print('Starting new session during RSS request')
            self.server.session = \
                createSession(proxyType)
        if not self.server.session:
            print('ERROR: GET failed to create session ' +
                  'during RSS request')
            self._404()
            return

        msg = getRSSfromDict(self.server.baseDir, self.server.newswire,
                             self.server.httpPrefix,
                             self.server.domainFull,
                             'Newswire', self.server.translate)
        if msg:
            msg = msg.encode('utf-8')
            self._set_headers('text/xml', len(msg),
                              None, callingDomain)
            self._write(msg)
            if debug:
                print('Sent rss2 newswire feed: ' +
                      path + ' ' + callingDomain)
            return
        if debug:
            print('Failed to get rss2 newswire feed: ' +
                  path + ' ' + callingDomain)
        self._404()

    def _getRSS3feed(self, authorized: bool,
                     callingDomain: str, path: str,
                     baseDir: str, httpPrefix: str,
                     domain: str, port: int, proxyType: str,
                     GETstartTime, GETtimings: {},
                     debug: bool):
        """Returns an RSS3 feed
        """
        nickname = path.split('/blog/')[1]
        if '/' in nickname:
            nickname = nickname.split('/')[0]
        if not nickname.startswith('rss.'):
            if os.path.isdir(baseDir +
                             '/accounts/' + nickname + '@' + domain):
                if not self.server.session:
                    print('Starting new session during RSS3 request')
                    self.server.session = \
                        createSession(proxyType)
                    if not self.server.session:
                        print('ERROR: GET failed to create session ' +
                              'during RSS3 request')
                        self._404()
                        return
                msg = \
                    htmlBlogPageRSS3(authorized,
                                     self.server.session,
                                     baseDir, httpPrefix,
                                     self.server.translate,
                                     nickname, domain, port,
                                     maxPostsInRSSFeed, 1)
                if msg is not None:
                    msg = msg.encode('utf-8')
                    self._set_headers('text/plain; charset=utf-8',
                                      len(msg), None, callingDomain)
                    self._write(msg)
                    if self.server.debug:
                        print('Sent rss3 feed: ' +
                              path + ' ' + callingDomain)
                    self._benchmarkGETtimings(GETstartTime, GETtimings,
                                              'sharedInbox enabled',
                                              'blog rss3')
                    return
        if debug:
            print('Failed to get rss3 feed: ' +
                  path + ' ' + callingDomain)
        self._404()

    def _showPersonOptions(self, callingDomain: str, path: str,
                           baseDir: str, httpPrefix: str,
                           domain: str, domainFull: str,
                           GETstartTime, GETtimings: {},
                           onionDomain: str, i2pDomain: str,
                           cookie: str, debug: bool):
        """Show person options screen
        """
        optionsStr = path.split('?options=')[1]
        originPathStr = path.split('?options=')[0]
        if ';' in optionsStr:
            pageNumber = 1
            optionsList = optionsStr.split(';')
            optionsActor = optionsList[0]
            optionsPageNumber = optionsList[1]
            optionsProfileUrl = optionsList[2]
            if optionsPageNumber.isdigit():
                pageNumber = int(optionsPageNumber)
            optionsLink = None
            if len(optionsList) > 3:
                optionsLink = optionsList[3]
            donateUrl = None
            PGPpubKey = None
            PGPfingerprint = None
            xmppAddress = None
            matrixAddress = None
            blogAddress = None
            toxAddress = None
            ssbAddress = None
            emailAddress = None
            actorJson = getPersonFromCache(baseDir,
                                           optionsActor,
                                           self.server.personCache,
                                           True)
            if actorJson:
                donateUrl = getDonationUrl(actorJson)
                xmppAddress = getXmppAddress(actorJson)
                matrixAddress = getMatrixAddress(actorJson)
                ssbAddress = getSSBAddress(actorJson)
                blogAddress = getBlogAddress(actorJson)
                toxAddress = getToxAddress(actorJson)
                emailAddress = getEmailAddress(actorJson)
                PGPpubKey = getPGPpubKey(actorJson)
                PGPfingerprint = getPGPfingerprint(actorJson)
            msg = htmlPersonOptions(self.server.translate,
                                    baseDir, domain,
                                    originPathStr,
                                    optionsActor,
                                    optionsProfileUrl,
                                    optionsLink,
                                    pageNumber, donateUrl,
                                    xmppAddress, matrixAddress,
                                    ssbAddress, blogAddress,
                                    toxAddress,
                                    PGPpubKey, PGPfingerprint,
                                    emailAddress).encode('utf-8')
            self._set_headers('text/html', len(msg),
                              cookie, callingDomain)
            self._write(msg)
            self._benchmarkGETtimings(GETstartTime, GETtimings,
                                      'registered devices done',
                                      'person options')
            return
        if callingDomain.endswith('.onion') and onionDomain:
            originPathStrAbsolute = \
                'http://' + onionDomain + originPathStr
        elif callingDomain.endswith('.i2p') and i2pDomain:
            originPathStrAbsolute = \
                'http://' + i2pDomain + originPathStr
        else:
            originPathStrAbsolute = \
                httpPrefix + '://' + domainFull + originPathStr
        self._redirect_headers(originPathStrAbsolute, cookie,
                               callingDomain)

    def _showMedia(self, callingDomain: str,
                   path: str, baseDir: str,
                   GETstartTime, GETtimings: {}):
        """Returns a media file
        """
        if self._pathIsImage(path) or \
           self._pathIsVideo(path) or \
           self._pathIsAudio(path):
            mediaStr = path.split('/media/')[1]
            mediaFilename = baseDir + '/media/' + mediaStr
            if os.path.isfile(mediaFilename):
                if self._etag_exists(mediaFilename):
                    # The file has not changed
                    self._304()
                    return

                mediaFileType = 'image/png'
                if mediaFilename.endswith('.png'):
                    mediaFileType = 'image/png'
                elif mediaFilename.endswith('.jpg'):
                    mediaFileType = 'image/jpeg'
                elif mediaFilename.endswith('.gif'):
                    mediaFileType = 'image/gif'
                elif mediaFilename.endswith('.webp'):
                    mediaFileType = 'image/webp'
                elif mediaFilename.endswith('.avif'):
                    mediaFileType = 'image/avif'
                elif mediaFilename.endswith('.mp4'):
                    mediaFileType = 'video/mp4'
                elif mediaFilename.endswith('.ogv'):
                    mediaFileType = 'video/ogv'
                elif mediaFilename.endswith('.mp3'):
                    mediaFileType = 'audio/mpeg'
                elif mediaFilename.endswith('.ogg'):
                    mediaFileType = 'audio/ogg'

                with open(mediaFilename, 'rb') as avFile:
                    mediaBinary = avFile.read()
                    self._set_headers_etag(mediaFilename, mediaFileType,
                                           mediaBinary, None,
                                           callingDomain)
                    self._write(mediaBinary)
                self._benchmarkGETtimings(GETstartTime, GETtimings,
                                          'show emoji done',
                                          'show media')
                return
        self._404()

    def _showEmoji(self, callingDomain: str, path: str,
                   baseDir: str,
                   GETstartTime, GETtimings: {}):
        """Returns an emoji image
        """
        if self._pathIsImage(path):
            emojiStr = path.split('/emoji/')[1]
            emojiFilename = baseDir + '/emoji/' + emojiStr
            if os.path.isfile(emojiFilename):
                if self._etag_exists(emojiFilename):
                    # The file has not changed
                    self._304()
                    return

                mediaImageType = 'png'
                if emojiFilename.endswith('.png'):
                    mediaImageType = 'png'
                elif emojiFilename.endswith('.jpg'):
                    mediaImageType = 'jpeg'
                elif emojiFilename.endswith('.webp'):
                    mediaImageType = 'webp'
                elif emojiFilename.endswith('.avif'):
                    mediaImageType = 'avif'
                else:
                    mediaImageType = 'gif'
                with open(emojiFilename, 'rb') as avFile:
                    mediaBinary = avFile.read()
                    self._set_headers_etag(emojiFilename,
                                           'image/' + mediaImageType,
                                           mediaBinary, None,
                                           callingDomain)
                    self._write(mediaBinary)
                self._benchmarkGETtimings(GETstartTime, GETtimings,
                                          'background shown done',
                                          'show emoji')
                return
        self._404()

    def _showIcon(self, callingDomain: str, path: str,
                  baseDir: str,
                  GETstartTime, GETtimings: {}):
        """Shows an icon
        """
        if path.endswith('.png'):
            mediaStr = path.split('/icons/')[1]
            mediaFilename = baseDir + '/img/icons/' + mediaStr
            if self._etag_exists(mediaFilename):
                # The file has not changed
                self._304()
                return
            if self.server.iconsCache.get(mediaStr):
                mediaBinary = self.server.iconsCache[mediaStr]
                self._set_headers_etag(mediaFilename,
                                       'image/png',
                                       mediaBinary, None,
                                       callingDomain)
                self._write(mediaBinary)
                return
            else:
                if os.path.isfile(mediaFilename):
                    with open(mediaFilename, 'rb') as avFile:
                        mediaBinary = avFile.read()
                        self._set_headers_etag(mediaFilename,
                                               'image/png',
                                               mediaBinary, None,
                                               callingDomain)
                        self._write(mediaBinary)
                        self.server.iconsCache[mediaStr] = mediaBinary
                    self._benchmarkGETtimings(GETstartTime, GETtimings,
                                              'show files done',
                                              'icon shown')
                    return
        self._404()

    def _showCachedAvatar(self, callingDomain: str, path: str,
                          baseDir: str,
                          GETstartTime, GETtimings: {}):
        """Shows an avatar image obtained from the cache
        """
        mediaFilename = baseDir + '/cache' + path
        if os.path.isfile(mediaFilename):
            if self._etag_exists(mediaFilename):
                # The file has not changed
                self._304()
                return
            with open(mediaFilename, 'rb') as avFile:
                mediaBinary = avFile.read()
                if mediaFilename.endswith('.png'):
                    self._set_headers_etag(mediaFilename,
                                           'image/png',
                                           mediaBinary, None,
                                           callingDomain)
                elif mediaFilename.endswith('.jpg'):
                    self._set_headers_etag(mediaFilename,
                                           'image/jpeg',
                                           mediaBinary, None,
                                           callingDomain)
                elif mediaFilename.endswith('.gif'):
                    self._set_headers_etag(mediaFilename,
                                           'image/gif',
                                           mediaBinary, None,
                                           callingDomain)
                elif mediaFilename.endswith('.webp'):
                    self._set_headers_etag(mediaFilename,
                                           'image/webp',
                                           mediaBinary, None,
                                           callingDomain)
                elif mediaFilename.endswith('.avif'):
                    self._set_headers_etag(mediaFilename,
                                           'image/avif',
                                           mediaBinary, None,
                                           callingDomain)
                else:
                    # default to jpeg
                    self._set_headers_etag(mediaFilename,
                                           'image/jpeg',
                                           mediaBinary, None,
                                           callingDomain)
                    # self._404()
                    return
                self._write(mediaBinary)
                self._benchmarkGETtimings(GETstartTime, GETtimings,
                                          'icon shown done',
                                          'avatar shown')
                return
        self._404()

    def _hashtagSearch(self, callingDomain: str,
                       path: str, cookie: str,
                       baseDir: str, httpPrefix: str,
                       domain: str, domainFull: str, port: int,
                       onionDomain: str, i2pDomain: str,
                       GETstartTime, GETtimings: {}):
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
        if isBlockedHashtag(baseDir, hashtag):
            msg = htmlHashtagBlocked(baseDir,
                                     self.server.translate).encode('utf-8')
            self._login_headers('text/html', len(msg), callingDomain)
            self._write(msg)
            self.server.GETbusy = False
            return
        nickname = None
        if '/users/' in path:
            actor = \
                httpPrefix + '://' + domainFull + path
            nickname = \
                getNicknameFromActor(actor)
        hashtagStr = \
            htmlHashtagSearch(nickname,
                              domain, port,
                              self.server.recentPostsCache,
                              self.server.maxRecentPosts,
                              self.server.translate,
                              baseDir, hashtag, pageNumber,
                              maxPostsInFeed, self.server.session,
                              self.server.cachedWebfingers,
                              self.server.personCache,
                              httpPrefix,
                              self.server.projectVersion,
                              self.server.YTReplacementDomain)
        if hashtagStr:
            msg = hashtagStr.encode('utf-8')
            self._set_headers('text/html', len(msg),
                              cookie, callingDomain)
            self._write(msg)
        else:
            originPathStr = path.split('/tags/')[0]
            originPathStrAbsolute = \
                httpPrefix + '://' + domainFull + originPathStr
            if callingDomain.endswith('.onion') and onionDomain:
                originPathStrAbsolute = \
                    'http://' + onionDomain + originPathStr
            elif (callingDomain.endswith('.i2p') and onionDomain):
                originPathStrAbsolute = \
                    'http://' + i2pDomain + originPathStr
            self._redirect_headers(originPathStrAbsolute + '/search',
                                   cookie, callingDomain)
        self.server.GETbusy = False
        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  'login shown done',
                                  'hashtag search')

    def _hashtagSearchRSS2(self, callingDomain: str,
                           path: str, cookie: str,
                           baseDir: str, httpPrefix: str,
                           domain: str, domainFull: str, port: int,
                           onionDomain: str, i2pDomain: str,
                           GETstartTime, GETtimings: {}):
        """Return an RSS 2 feed for a hashtag
        """
        hashtag = path.split('/tags/rss2/')[1]
        if isBlockedHashtag(baseDir, hashtag):
            self._400()
            self.server.GETbusy = False
            return
        nickname = None
        if '/users/' in path:
            actor = \
                httpPrefix + '://' + domainFull + path
            nickname = \
                getNicknameFromActor(actor)
        hashtagStr = \
            rssHashtagSearch(nickname,
                             domain, port,
                             self.server.recentPostsCache,
                             self.server.maxRecentPosts,
                             self.server.translate,
                             baseDir, hashtag,
                             maxPostsInFeed, self.server.session,
                             self.server.cachedWebfingers,
                             self.server.personCache,
                             httpPrefix,
                             self.server.projectVersion,
                             self.server.YTReplacementDomain)
        if hashtagStr:
            msg = hashtagStr.encode('utf-8')
            self._set_headers('text/xml', len(msg),
                              cookie, callingDomain)
            self._write(msg)
        else:
            originPathStr = path.split('/tags/rss2/')[0]
            originPathStrAbsolute = \
                httpPrefix + '://' + domainFull + originPathStr
            if callingDomain.endswith('.onion') and onionDomain:
                originPathStrAbsolute = \
                    'http://' + onionDomain + originPathStr
            elif (callingDomain.endswith('.i2p') and onionDomain):
                originPathStrAbsolute = \
                    'http://' + i2pDomain + originPathStr
            self._redirect_headers(originPathStrAbsolute + '/search',
                                   cookie, callingDomain)
        self.server.GETbusy = False
        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  'login shown done',
                                  'hashtag rss feed')

    def _announceButton(self, callingDomain: str, path: str,
                        baseDir: str,
                        cookie: str, proxyType: str,
                        httpPrefix: str,
                        domain: str, domainFull: str, port: int,
                        onionDomain: str, i2pDomain: str,
                        GETstartTime, GETtimings: {},
                        repeatPrivate: bool, debug: bool):
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
            self.server.GETbusy = False
            actorAbsolute = \
                httpPrefix + '://' + domainFull + actor
            if callingDomain.endswith('.onion') and onionDomain:
                actorAbsolute = 'http://' + onionDomain + actor
            elif (callingDomain.endswith('.i2p') and i2pDomain):
                actorAbsolute = 'http://' + i2pDomain + actor
            self._redirect_headers(actorAbsolute + '/' + timelineStr +
                                   '?page=' + str(pageNumber), cookie,
                                   callingDomain)
            return
        if not self.server.session:
            print('Starting new session during repeat button')
            self.server.session = createSession(proxyType)
            if not self.server.session:
                print('ERROR: GET failed to create session ' +
                      'during repeat button')
                self._404()
                self.server.GETbusy = False
                return
        self.server.actorRepeat = path.split('?actor=')[1]
        announceToStr = \
            httpPrefix + '://' + domainFull + '/users/' + \
            self.postToNickname + '/followers'
        if not repeatPrivate:
            announceToStr = 'https://www.w3.org/ns/activitystreams#Public'
        announceJson = \
            createAnnounce(self.server.session,
                           baseDir,
                           self.server.federationList,
                           self.postToNickname,
                           domain, port,
                           announceToStr,
                           None, httpPrefix,
                           repeatUrl, False, False,
                           self.server.sendThreads,
                           self.server.postLog,
                           self.server.personCache,
                           self.server.cachedWebfingers,
                           debug,
                           self.server.projectVersion)
        if announceJson:
            self._postToOutboxThread(announceJson)
        self.server.GETbusy = False
        actorAbsolute = httpPrefix + '://' + domainFull + actor
        if callingDomain.endswith('.onion') and onionDomain:
            actorAbsolute = 'http://' + onionDomain + actor
        elif callingDomain.endswith('.i2p') and i2pDomain:
            actorAbsolute = 'http://' + i2pDomain + actor
        self._redirect_headers(actorAbsolute + '/' +
                               timelineStr + '?page=' +
                               str(pageNumber) +
                               timelineBookmark, cookie, callingDomain)
        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  'emoji search shown done',
                                  'show announce')

    def _undoAnnounceButton(self, callingDomain: str, path: str,
                            baseDir: str,
                            cookie: str, proxyType: str,
                            httpPrefix: str,
                            domain: str, domainFull: str, port: int,
                            onionDomain: str, i2pDomain: str,
                            GETstartTime, GETtimings: {},
                            repeatPrivate: bool, debug: bool):
        """Undo announce/repeat button was pressed
        """
        pageNumber = 1
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
            self.server.GETbusy = False
            actorAbsolute = httpPrefix + '://' + domainFull + actor
            if callingDomain.endswith('.onion') and onionDomain:
                actorAbsolute = 'http://' + onionDomain + actor
            elif (callingDomain.endswith('.i2p') and i2pDomain):
                actorAbsolute = 'http://' + i2pDomain + actor
            self._redirect_headers(actorAbsolute + '/' +
                                   timelineStr + '?page=' +
                                   str(pageNumber), cookie,
                                   callingDomain)
            return
        if not self.server.session:
            print('Starting new session during undo repeat')
            self.server.session = createSession(proxyType)
            if not self.server.session:
                print('ERROR: GET failed to create session ' +
                      'during undo repeat')
                self._404()
                self.server.GETbusy = False
                return
        undoAnnounceActor = \
            httpPrefix + '://' + domainFull + \
            '/users/' + self.postToNickname
        unRepeatToStr = 'https://www.w3.org/ns/activitystreams#Public'
        newUndoAnnounce = {
            "@context": "https://www.w3.org/ns/activitystreams",
            'actor': undoAnnounceActor,
            'type': 'Undo',
            'cc': [undoAnnounceActor+'/followers'],
            'to': [unRepeatToStr],
            'object': {
                'actor': undoAnnounceActor,
                'cc': [undoAnnounceActor+'/followers'],
                'object': repeatUrl,
                'to': [unRepeatToStr],
                'type': 'Announce'
            }
        }
        self._postToOutboxThread(newUndoAnnounce)
        self.server.GETbusy = False
        actorAbsolute = httpPrefix + '://' + domainFull + actor
        if callingDomain.endswith('.onion') and onionDomain:
            actorAbsolute = 'http://' + onionDomain + actor
        elif (callingDomain.endswith('.i2p') and i2pDomain):
            actorAbsolute = 'http://' + i2pDomain + actor
        self._redirect_headers(actorAbsolute + '/' +
                               timelineStr + '?page=' +
                               str(pageNumber) +
                               timelineBookmark, cookie, callingDomain)
        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  'show announce done',
                                  'unannounce')

    def _followApproveButton(self, callingDomain: str, path: str,
                             cookie: str,
                             baseDir: str, httpPrefix: str,
                             domain: str, domainFull: str, port: int,
                             onionDomain: str, i2pDomain: str,
                             GETstartTime, GETtimings: {},
                             proxyType: str, debug: bool):
        """Follow approve button was pressed
        """
        originPathStr = path.split('/followapprove=')[0]
        followerNickname = originPathStr.replace('/users/', '')
        followingHandle = path.split('/followapprove=')[1]
        if '@' in followingHandle:
            if not self.server.session:
                print('Starting new session during follow approval')
                self.server.session = createSession(proxyType)
                if not self.server.session:
                    print('ERROR: GET failed to create session ' +
                          'during follow approval')
                    self._404()
                    self.server.GETbusy = False
                    return
            manualApproveFollowRequest(self.server.session,
                                       baseDir, httpPrefix,
                                       followerNickname,
                                       domain, port,
                                       followingHandle,
                                       self.server.federationList,
                                       self.server.sendThreads,
                                       self.server.postLog,
                                       self.server.cachedWebfingers,
                                       self.server.personCache,
                                       debug,
                                       self.server.projectVersion)
        originPathStrAbsolute = \
            httpPrefix + '://' + domainFull + originPathStr
        if callingDomain.endswith('.onion') and onionDomain:
            originPathStrAbsolute = \
                'http://' + onionDomain + originPathStr
        elif (callingDomain.endswith('.i2p') and i2pDomain):
            originPathStrAbsolute = \
                'http://' + i2pDomain + originPathStr
        self._redirect_headers(originPathStrAbsolute,
                               cookie, callingDomain)
        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  'unannounce done',
                                  'follow approve shown')
        self.server.GETbusy = False

    def _newswireVote(self, callingDomain: str, path: str,
                      cookie: str,
                      baseDir: str, httpPrefix: str,
                      domain: str, domainFull: str, port: int,
                      onionDomain: str, i2pDomain: str,
                      GETstartTime, GETtimings: {},
                      proxyType: str, debug: bool,
                      newswire: {}):
        """Vote for a newswire item
        """
        originPathStr = path.split('/newswirevote=')[0]
        dateStr = \
            path.split('/newswirevote=')[1].replace('T', ' ') + '+00:00'
        nickname = originPathStr.split('/users/')[1]
        if '/' in nickname:
            nickname = nickname.split('/')[0]
        if newswire.get(dateStr):
            if isModerator(baseDir, nickname):
                if 'vote:' + nickname not in newswire[dateStr][2]:
                    newswire[dateStr][2].append('vote:' + nickname)
                    filename = newswire[dateStr][3]
                    if filename:
                        saveJson(newswire[dateStr][2],
                                 filename + '.votes')

        originPathStrAbsolute = \
            httpPrefix + '://' + domainFull + originPathStr + '/' + \
            self.server.defaultTimeline
        if callingDomain.endswith('.onion') and onionDomain:
            originPathStrAbsolute = \
                'http://' + onionDomain + originPathStr
        elif (callingDomain.endswith('.i2p') and i2pDomain):
            originPathStrAbsolute = \
                'http://' + i2pDomain + originPathStr
        self._redirect_headers(originPathStrAbsolute,
                               cookie, callingDomain)
        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  'unannounce done',
                                  'vote for newswite item')
        self.server.GETbusy = False

    def _newswireUnvote(self, callingDomain: str, path: str,
                        cookie: str,
                        baseDir: str, httpPrefix: str,
                        domain: str, domainFull: str, port: int,
                        onionDomain: str, i2pDomain: str,
                        GETstartTime, GETtimings: {},
                        proxyType: str, debug: bool,
                        newswire: {}):
        """Remove vote for a newswire item
        """
        originPathStr = path.split('/newswireunvote=')[0]
        dateStr = \
            path.split('/newswireunvote=')[1].replace('T', ' ') + '+00:00'
        nickname = originPathStr.split('/users/')[1]
        if '/' in nickname:
            nickname = nickname.split('/')[0]
        if newswire.get(dateStr):
            if isModerator(baseDir, nickname):
                if 'vote:' + nickname in newswire[dateStr][2]:
                    newswire[dateStr][2].remove('vote:' + nickname)
                    filename = newswire[dateStr][3]
                    if filename:
                        saveJson(newswire[dateStr][2],
                                 filename + '.votes')

        originPathStrAbsolute = \
            httpPrefix + '://' + domainFull + originPathStr + '/' + \
            self.server.defaultTimeline
        if callingDomain.endswith('.onion') and onionDomain:
            originPathStrAbsolute = \
                'http://' + onionDomain + originPathStr
        elif (callingDomain.endswith('.i2p') and i2pDomain):
            originPathStrAbsolute = \
                'http://' + i2pDomain + originPathStr
        self._redirect_headers(originPathStrAbsolute,
                               cookie, callingDomain)
        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  'unannounce done',
                                  'unvote for newswite item')
        self.server.GETbusy = False

    def _followDenyButton(self, callingDomain: str, path: str,
                          cookie: str,
                          baseDir: str, httpPrefix: str,
                          domain: str, domainFull: str, port: int,
                          onionDomain: str, i2pDomain: str,
                          GETstartTime, GETtimings: {},
                          proxyType: str, debug: bool):
        """Follow deny button was pressed
        """
        originPathStr = path.split('/followdeny=')[0]
        followerNickname = originPathStr.replace('/users/', '')
        followingHandle = path.split('/followdeny=')[1]
        if '@' in followingHandle:
            manualDenyFollowRequest(self.server.session,
                                    baseDir, httpPrefix,
                                    followerNickname,
                                    domain, port,
                                    followingHandle,
                                    self.server.federationList,
                                    self.server.sendThreads,
                                    self.server.postLog,
                                    self.server.cachedWebfingers,
                                    self.server.personCache,
                                    debug,
                                    self.server.projectVersion)
        originPathStrAbsolute = \
            httpPrefix + '://' + domainFull + originPathStr
        if callingDomain.endswith('.onion') and onionDomain:
            originPathStrAbsolute = \
                'http://' + onionDomain + originPathStr
        elif callingDomain.endswith('.i2p') and i2pDomain:
            originPathStrAbsolute = \
                'http://' + i2pDomain + originPathStr
        self._redirect_headers(originPathStrAbsolute,
                               cookie, callingDomain)
        self.server.GETbusy = False
        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  'follow approve done',
                                  'follow deny shown')

    def _likeButton(self, callingDomain: str, path: str,
                    baseDir: str, httpPrefix: str,
                    domain: str, domainFull: str,
                    onionDomain: str, i2pDomain: str,
                    GETstartTime, GETtimings: {},
                    proxyType: str, cookie: str,
                    debug: str):
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
            self.server.GETbusy = False
            actorAbsolute = \
                httpPrefix + '://' + domainFull + actor
            if callingDomain.endswith('.onion') and onionDomain:
                actorAbsolute = 'http://' + onionDomain + actor
            elif (callingDomain.endswith('.i2p') and i2pDomain):
                actorAbsolute = 'http://' + i2pDomain + actor
            self._redirect_headers(actorAbsolute + '/' + timelineStr +
                                   '?page=' + str(pageNumber) +
                                   timelineBookmark, cookie,
                                   callingDomain)
            return
        if not self.server.session:
            print('Starting new session during like')
            self.server.session = createSession(proxyType)
            if not self.server.session:
                print('ERROR: GET failed to create session during like')
                self._404()
                self.server.GETbusy = False
                return
        likeActor = \
            httpPrefix + '://' + \
            domainFull + '/users/' + self.postToNickname
        actorLiked = path.split('?actor=')[1]
        if '?' in actorLiked:
            actorLiked = actorLiked.split('?')[0]
        likeJson = {
            "@context": "https://www.w3.org/ns/activitystreams",
            'type': 'Like',
            'actor': likeActor,
            'to': [actorLiked],
            'object': likeUrl
        }
        # directly like the post file
        likedPostFilename = locatePost(baseDir,
                                       self.postToNickname,
                                       domain,
                                       likeUrl)
        if likedPostFilename:
            if debug:
                print('Updating likes for ' + likedPostFilename)
            updateLikesCollection(self.server.recentPostsCache,
                                  baseDir,
                                  likedPostFilename, likeUrl,
                                  likeActor, domain,
                                  debug)
        else:
            print('WARN: unable to locate file for liked post ' +
                  likeUrl)
        # send out the like to followers
        self._postToOutbox(likeJson, self.server.projectVersion)
        self.server.GETbusy = False
        actorAbsolute = \
            httpPrefix + '://' + domainFull + actor
        if callingDomain.endswith('.onion') and onionDomain:
            actorAbsolute = 'http://' + onionDomain + actor
        elif (callingDomain.endswith('.i2p') and i2pDomain):
            actorAbsolute = 'http://' + i2pDomain + actor
        self._redirect_headers(actorAbsolute + '/' + timelineStr +
                               '?page=' + str(pageNumber) +
                               timelineBookmark, cookie,
                               callingDomain)
        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  'follow deny done',
                                  'like shown')

    def _undoLikeButton(self, callingDomain: str, path: str,
                        baseDir: str, httpPrefix: str,
                        domain: str, domainFull: str,
                        onionDomain: str, i2pDomain: str,
                        GETstartTime, GETtimings: {},
                        proxyType: str, cookie: str,
                        debug: str):
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
            self.server.GETbusy = False
            actorAbsolute = \
                httpPrefix + '://' + domainFull + actor
            if callingDomain.endswith('.onion') and onionDomain:
                actorAbsolute = 'http://' + onionDomain + actor
            elif (callingDomain.endswith('.i2p') and onionDomain):
                actorAbsolute = 'http://' + i2pDomain + actor
            self._redirect_headers(actorAbsolute + '/' + timelineStr +
                                   '?page=' + str(pageNumber), cookie,
                                   callingDomain)
            return
        if not self.server.session:
            print('Starting new session during undo like')
            self.server.session = createSession(proxyType)
            if not self.server.session:
                print('ERROR: GET failed to create session ' +
                      'during undo like')
                self._404()
                self.server.GETbusy = False
                return
        undoActor = \
            httpPrefix + '://' + domainFull + '/users/' + self.postToNickname
        actorLiked = path.split('?actor=')[1]
        if '?' in actorLiked:
            actorLiked = actorLiked.split('?')[0]
        undoLikeJson = {
            "@context": "https://www.w3.org/ns/activitystreams",
            'type': 'Undo',
            'actor': undoActor,
            'to': [actorLiked],
            'object': {
                'type': 'Like',
                'actor': undoActor,
                'to': [actorLiked],
                'object': likeUrl
            }
        }
        # directly undo the like within the post file
        likedPostFilename = locatePost(baseDir,
                                       self.postToNickname,
                                       domain, likeUrl)
        if likedPostFilename:
            if debug:
                print('Removing likes for ' + likedPostFilename)
            undoLikesCollectionEntry(self.server.recentPostsCache,
                                     baseDir,
                                     likedPostFilename, likeUrl,
                                     undoActor, domain, debug)
        # send out the undo like to followers
        self._postToOutbox(undoLikeJson, self.server.projectVersion)
        self.server.GETbusy = False
        actorAbsolute = httpPrefix + '://' + domainFull + actor
        if callingDomain.endswith('.onion') and onionDomain:
            actorAbsolute = 'http://' + onionDomain + actor
        elif callingDomain.endswith('.i2p') and i2pDomain:
            actorAbsolute = 'http://' + i2pDomain + actor
        self._redirect_headers(actorAbsolute + '/' + timelineStr +
                               '?page=' + str(pageNumber) +
                               timelineBookmark, cookie,
                               callingDomain)
        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  'like shown done',
                                  'unlike shown')

    def _bookmarkButton(self, callingDomain: str, path: str,
                        baseDir: str, httpPrefix: str,
                        domain: str, domainFull: str, port: int,
                        onionDomain: str, i2pDomain: str,
                        GETstartTime, GETtimings: {},
                        proxyType: str, cookie: str,
                        debug: str):
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
            self.server.GETbusy = False
            actorAbsolute = \
                httpPrefix + '://' + domainFull + actor
            if callingDomain.endswith('.onion') and onionDomain:
                actorAbsolute = 'http://' + onionDomain + actor
            elif callingDomain.endswith('.i2p') and i2pDomain:
                actorAbsolute = 'http://' + i2pDomain + actor
            self._redirect_headers(actorAbsolute + '/' + timelineStr +
                                   '?page=' + str(pageNumber), cookie,
                                   callingDomain)
            return
        if not self.server.session:
            print('Starting new session during bookmark')
            self.server.session = createSession(proxyType)
            if not self.server.session:
                print('ERROR: GET failed to create session ' +
                      'during bookmark')
                self._404()
                self.server.GETbusy = False
                return
        bookmarkActor = \
            httpPrefix + '://' + domainFull + '/users/' + self.postToNickname
        ccList = []
        bookmark(self.server.recentPostsCache,
                 self.server.session,
                 baseDir,
                 self.server.federationList,
                 self.postToNickname,
                 domain, port,
                 ccList,
                 httpPrefix,
                 bookmarkUrl, bookmarkActor, False,
                 self.server.sendThreads,
                 self.server.postLog,
                 self.server.personCache,
                 self.server.cachedWebfingers,
                 self.server.debug,
                 self.server.projectVersion)
        # self._postToOutbox(bookmarkJson, self.server.projectVersion)
        self.server.GETbusy = False
        actorAbsolute = \
            httpPrefix + '://' + domainFull + actor
        if callingDomain.endswith('.onion') and onionDomain:
            actorAbsolute = 'http://' + onionDomain + actor
        elif callingDomain.endswith('.i2p') and i2pDomain:
            actorAbsolute = 'http://' + i2pDomain + actor
        self._redirect_headers(actorAbsolute + '/' + timelineStr +
                               '?page=' + str(pageNumber) +
                               timelineBookmark, cookie,
                               callingDomain)
        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  'unlike shown done',
                                  'bookmark shown')

    def _undoBookmarkButton(self, callingDomain: str, path: str,
                            baseDir: str, httpPrefix: str,
                            domain: str, domainFull: str, port: int,
                            onionDomain: str, i2pDomain: str,
                            GETstartTime, GETtimings: {},
                            proxyType: str, cookie: str,
                            debug: str):
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
            self.server.GETbusy = False
            actorAbsolute = \
                httpPrefix + '://' + domainFull + actor
            if callingDomain.endswith('.onion') and onionDomain:
                actorAbsolute = 'http://' + onionDomain + actor
            elif callingDomain.endswith('.i2p') and i2pDomain:
                actorAbsolute = 'http://' + i2pDomain + actor
            self._redirect_headers(actorAbsolute + '/' + timelineStr +
                                   '?page=' + str(pageNumber), cookie,
                                   callingDomain)
            return
        if not self.server.session:
            print('Starting new session during undo bookmark')
            self.server.session = createSession(proxyType)
            if not self.server.session:
                print('ERROR: GET failed to create session ' +
                      'during undo bookmark')
                self._404()
                self.server.GETbusy = False
                return
        undoActor = \
            httpPrefix + '://' + domainFull + '/users/' + self.postToNickname
        ccList = []
        undoBookmark(self.server.recentPostsCache,
                     self.server.session,
                     baseDir,
                     self.server.federationList,
                     self.postToNickname,
                     domain, port,
                     ccList,
                     httpPrefix,
                     bookmarkUrl, undoActor, False,
                     self.server.sendThreads,
                     self.server.postLog,
                     self.server.personCache,
                     self.server.cachedWebfingers,
                     debug,
                     self.server.projectVersion)
        # self._postToOutbox(undoBookmarkJson, self.server.projectVersion)
        self.server.GETbusy = False
        actorAbsolute = \
            httpPrefix + '://' + domainFull + actor
        if callingDomain.endswith('.onion') and onionDomain:
            actorAbsolute = 'http://' + onionDomain + actor
        elif callingDomain.endswith('.i2p') and i2pDomain:
            actorAbsolute = 'http://' + i2pDomain + actor
        self._redirect_headers(actorAbsolute + '/' + timelineStr +
                               '?page=' + str(pageNumber) +
                               timelineBookmark, cookie,
                               callingDomain)
        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  'bookmark shown done',
                                  'unbookmark shown')

    def _deleteButton(self, callingDomain: str, path: str,
                      baseDir: str, httpPrefix: str,
                      domain: str, domainFull: str, port: int,
                      onionDomain: str, i2pDomain: str,
                      GETstartTime, GETtimings: {},
                      proxyType: str, cookie: str,
                      debug: str):
        """Delete button is pressed
        """
        if not cookie:
            print('ERROR: no cookie given when deleting')
            self._400()
            self.server.GETbusy = False
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
            httpPrefix + '://' + domainFull + usersPath
        if self.server.allowDeletion or \
           deleteUrl.startswith(actor):
            if self.server.debug:
                print('DEBUG: deleteUrl=' + deleteUrl)
                print('DEBUG: actor=' + actor)
            if actor not in deleteUrl:
                # You can only delete your own posts
                self.server.GETbusy = False
                if callingDomain.endswith('.onion') and onionDomain:
                    actor = 'http://' + onionDomain + usersPath
                elif callingDomain.endswith('.i2p') and i2pDomain:
                    actor = 'http://' + i2pDomain + usersPath
                self._redirect_headers(actor + '/' + timelineStr,
                                       cookie, callingDomain)
                return
            self.postToNickname = getNicknameFromActor(actor)
            if not self.postToNickname:
                print('WARN: unable to find nickname in ' + actor)
                self.server.GETbusy = False
                if callingDomain.endswith('.onion') and onionDomain:
                    actor = 'http://' + onionDomain + usersPath
                elif callingDomain.endswith('.i2p') and i2pDomain:
                    actor = 'http://' + i2pDomain + usersPath
                self._redirect_headers(actor + '/' + timelineStr,
                                       cookie, callingDomain)
                return
            if not self.server.session:
                print('Starting new session during delete')
                self.server.session = createSession(proxyType)
                if not self.server.session:
                    print('ERROR: GET failed to create session ' +
                          'during delete')
                    self._404()
                    self.server.GETbusy = False
                    return

            deleteStr = \
                htmlDeletePost(self.server.recentPostsCache,
                               self.server.maxRecentPosts,
                               self.server.translate, pageNumber,
                               self.server.session, baseDir,
                               deleteUrl, httpPrefix,
                               __version__, self.server.cachedWebfingers,
                               self.server.personCache, callingDomain,
                               self.server.TYReplacementDomain)
            if deleteStr:
                self._set_headers('text/html', len(deleteStr),
                                  cookie, callingDomain)
                self._write(deleteStr.encode('utf-8'))
                self.server.GETbusy = False
                return
        self.server.GETbusy = False
        if callingDomain.endswith('.onion') and onionDomain:
            actor = 'http://' + onionDomain + usersPath
        elif (callingDomain.endswith('.i2p') and i2pDomain):
            actor = 'http://' + i2pDomain + usersPath
        self._redirect_headers(actor + '/' + timelineStr,
                               cookie, callingDomain)
        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  'unbookmark shown done',
                                  'delete shown')

    def _muteButton(self, callingDomain: str, path: str,
                    baseDir: str, httpPrefix: str,
                    domain: str, domainFull: str, port: int,
                    onionDomain: str, i2pDomain: str,
                    GETstartTime, GETtimings: {},
                    proxyType: str, cookie: str,
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
        actor = \
            httpPrefix + '://' + domainFull + path.split('?mute=')[0]
        nickname = getNicknameFromActor(actor)
        mutePost(baseDir, nickname, domain,
                 muteUrl, self.server.recentPostsCache)
        self.server.GETbusy = False
        if callingDomain.endswith('.onion') and onionDomain:
            actor = \
                'http://' + onionDomain + \
                path.split('?mute=')[0]
        elif (callingDomain.endswith('.i2p') and i2pDomain):
            actor = \
                'http://' + i2pDomain + \
                path.split('?mute=')[0]
        self._redirect_headers(actor + '/' +
                               timelineStr + timelineBookmark,
                               cookie, callingDomain)
        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  'delete shown done',
                                  'post muted')

    def _undoMuteButton(self, callingDomain: str, path: str,
                        baseDir: str, httpPrefix: str,
                        domain: str, domainFull: str, port: int,
                        onionDomain: str, i2pDomain: str,
                        GETstartTime, GETtimings: {},
                        proxyType: str, cookie: str,
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
        actor = \
            httpPrefix + '://' + domainFull + path.split('?unmute=')[0]
        nickname = getNicknameFromActor(actor)
        unmutePost(baseDir, nickname, domain,
                   muteUrl, self.server.recentPostsCache)
        self.server.GETbusy = False
        if callingDomain.endswith('.onion') and onionDomain:
            actor = \
                'http://' + onionDomain + path.split('?unmute=')[0]
        elif callingDomain.endswith('.i2p') and i2pDomain:
            actor = \
                'http://' + i2pDomain + path.split('?unmute=')[0]
        self._redirect_headers(actor + '/' + timelineStr +
                               timelineBookmark,
                               cookie, callingDomain)
        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  'post muted done',
                                  'unmute activated')

    def _showRepliesToPost(self, authorized: bool,
                           callingDomain: str, path: str,
                           baseDir: str, httpPrefix: str,
                           domain: str, domainFull: str, port: int,
                           onionDomain: str, i2pDomain: str,
                           GETstartTime, GETtimings: {},
                           proxyType: str, cookie: str,
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
            baseDir + '/accounts/' + nickname + '@' + domain + '/' + boxname
        postRepliesFilename = \
            postDir + '/' + \
            httpPrefix + ':##' + domainFull + '#users#' + \
            nickname + '#statuses#' + statusNumber + '.replies'
        if not os.path.isfile(postRepliesFilename):
            # There are no replies,
            # so show empty collection
            contextStr = \
                'https://www.w3.org/ns/activitystreams'

            firstStr = \
                httpPrefix + '://' + domainFull + '/users/' + nickname + \
                '/statuses/' + statusNumber + '/replies?page=true'

            idStr = \
                httpPrefix + '://' + domainFull + '/users/' + nickname + \
                '/statuses/' + statusNumber + '/replies'

            lastStr = \
                httpPrefix + '://' + domainFull + '/users/' + nickname + \
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
                if not self.server.session:
                    print('DEBUG: creating new session during get replies')
                    self.server.session = createSession(proxyType)
                    if not self.server.session:
                        print('ERROR: GET failed to create session ' +
                              'during get replies')
                        self._404()
                        self.server.GETbusy = False
                        return
                recentPostsCache = self.server.recentPostsCache
                maxRecentPosts = self.server.maxRecentPosts
                translate = self.server.translate
                session = self.server.session
                cachedWebfingers = self.server.cachedWebfingers
                personCache = self.server.personCache
                projectVersion = self.server.projectVersion
                ytDomain = self.server.YTReplacementDomain
                msg = \
                    htmlPostReplies(recentPostsCache,
                                    maxRecentPosts,
                                    translate,
                                    baseDir,
                                    session,
                                    cachedWebfingers,
                                    personCache,
                                    nickname,
                                    domain,
                                    port,
                                    repliesJson,
                                    httpPrefix,
                                    projectVersion,
                                    ytDomain)
                msg = msg.encode('utf-8')
                self._set_headers('text/html', len(msg),
                                  cookie, callingDomain)
                self._write(msg)
            else:
                if self._fetchAuthenticated():
                    msg = json.dumps(repliesJson, ensure_ascii=False)
                    msg = msg.encode('utf-8')
                    protocolStr = 'application/json'
                    self._set_headers(protocolStr, len(msg), None,
                                      callingDomain)
                    self._write(msg)
                else:
                    self._404()
            self.server.GETbusy = False
            return True
        else:
            # replies exist. Itterate through the
            # text file containing message ids
            contextStr = 'https://www.w3.org/ns/activitystreams'

            idStr = \
                httpPrefix + '://' + domainFull + \
                '/users/' + nickname + '/statuses/' + \
                statusNumber + '?page=true'

            partOfStr = \
                httpPrefix + '://' + domainFull + \
                '/users/' + nickname + '/statuses/' + statusNumber

            repliesJson = {
                '@context': contextStr,
                'id': idStr,
                'orderedItems': [
                ],
                'partOf': partOfStr,
                'type': 'OrderedCollectionPage'
            }

            # populate the items list with replies
            populateRepliesJson(baseDir, nickname, domain,
                                postRepliesFilename,
                                authorized, repliesJson)

            # send the replies json
            if self._requestHTTP():
                if not self.server.session:
                    print('DEBUG: creating new session ' +
                          'during get replies 2')
                    self.server.session = createSession(proxyType)
                    if not self.server.session:
                        print('ERROR: GET failed to ' +
                              'create session ' +
                              'during get replies 2')
                        self._404()
                        self.server.GETbusy = False
                        return
                recentPostsCache = self.server.recentPostsCache
                maxRecentPosts = self.server.maxRecentPosts
                translate = self.server.translate
                session = self.server.session
                cachedWebfingers = self.server.cachedWebfingers
                personCache = self.server.personCache
                projectVersion = self.server.projectVersion
                ytDomain = self.server.YTReplacementDomain
                msg = \
                    htmlPostReplies(recentPostsCache,
                                    maxRecentPosts,
                                    translate,
                                    baseDir,
                                    session,
                                    cachedWebfingers,
                                    personCache,
                                    nickname,
                                    domain,
                                    port,
                                    repliesJson,
                                    httpPrefix,
                                    projectVersion,
                                    ytDomain)
                msg = msg.encode('utf-8')
                self._set_headers('text/html', len(msg),
                                  cookie, callingDomain)
                self._write(msg)
                self._benchmarkGETtimings(GETstartTime,
                                          GETtimings,
                                          'individual post done',
                                          'post replies done')
            else:
                if self._fetchAuthenticated():
                    msg = json.dumps(repliesJson,
                                     ensure_ascii=False)
                    msg = msg.encode('utf-8')
                    protocolStr = 'application/json'
                    self._set_headers(protocolStr, len(msg),
                                      None, callingDomain)
                    self._write(msg)
                else:
                    self._404()
            self.server.GETbusy = False
            return True
        return False

    def _showRoles(self, authorized: bool,
                   callingDomain: str, path: str,
                   baseDir: str, httpPrefix: str,
                   domain: str, domainFull: str, port: int,
                   onionDomain: str, i2pDomain: str,
                   GETstartTime, GETtimings: {},
                   proxyType: str, cookie: str,
                   debug: str) -> bool:
        """Show roles within profile screen
        """
        namedStatus = path.split('/users/')[1]
        if '/' not in namedStatus:
            return False

        postSections = namedStatus.split('/')
        nickname = postSections[0]
        actorFilename = \
            baseDir + '/accounts/' + nickname + '@' + domain + '.json'
        if not os.path.isfile(actorFilename):
            return False

        actorJson = loadJson(actorFilename)
        if not actorJson:
            return False

        if actorJson.get('roles'):
            if self._requestHTTP():
                getPerson = \
                    personLookup(domain, path.replace('/roles', ''),
                                 baseDir)
                if getPerson:
                    defaultTimeline = \
                        self.server.defaultTimeline
                    recentPostsCache = \
                        self.server.recentPostsCache
                    cachedWebfingers = \
                        self.server.cachedWebfingers
                    YTReplacementDomain = \
                        self.server.YTReplacementDomain
                    msg = \
                        htmlProfile(defaultTimeline,
                                    recentPostsCache,
                                    self.server.maxRecentPosts,
                                    self.server.translate,
                                    self.server.projectVersion,
                                    baseDir, httpPrefix, True,
                                    getPerson, 'roles',
                                    self.server.session,
                                    cachedWebfingers,
                                    self.server.personCache,
                                    YTReplacementDomain,
                                    actorJson['roles'],
                                    None, None)
                    msg = msg.encode('utf-8')
                    self._set_headers('text/html', len(msg),
                                      cookie, callingDomain)
                    self._write(msg)
                    self._benchmarkGETtimings(GETstartTime, GETtimings,
                                              'post replies done',
                                              'show roles')
            else:
                if self._fetchAuthenticated():
                    msg = json.dumps(actorJson['roles'],
                                     ensure_ascii=False)
                    msg = msg.encode('utf-8')
                    self._set_headers('application/json', len(msg),
                                      None, callingDomain)
                    self._write(msg)
                else:
                    self._404()
            self.server.GETbusy = False
            return True
        return False

    def _showSkills(self, authorized: bool,
                    callingDomain: str, path: str,
                    baseDir: str, httpPrefix: str,
                    domain: str, domainFull: str, port: int,
                    onionDomain: str, i2pDomain: str,
                    GETstartTime, GETtimings: {},
                    proxyType: str, cookie: str,
                    debug: str) -> bool:
        """Show skills on the profile screen
        """
        namedStatus = path.split('/users/')[1]
        if '/' in namedStatus:
            postSections = namedStatus.split('/')
            nickname = postSections[0]
            actorFilename = \
                baseDir + '/accounts/' + \
                nickname + '@' + domain + '.json'
            if os.path.isfile(actorFilename):
                actorJson = loadJson(actorFilename)
                if actorJson:
                    if actorJson.get('skills'):
                        if self._requestHTTP():
                            getPerson = \
                                personLookup(domain,
                                             path.replace('/skills', ''),
                                             baseDir)
                            if getPerson:
                                defaultTimeline =  \
                                    self.server.defaultTimeline
                                recentPostsCache = \
                                    self.server.recentPostsCache
                                cachedWebfingers = \
                                    self.server.cachedWebfingers
                                YTReplacementDomain = \
                                    self.server.YTReplacementDomain
                                msg = \
                                    htmlProfile(defaultTimeline,
                                                recentPostsCache,
                                                self.server.maxRecentPosts,
                                                self.server.translate,
                                                self.server.projectVersion,
                                                baseDir, httpPrefix, True,
                                                getPerson, 'skills',
                                                self.server.session,
                                                cachedWebfingers,
                                                self.server.personCache,
                                                YTReplacementDomain,
                                                actorJson['skills'],
                                                None, None)
                                msg = msg.encode('utf-8')
                                self._set_headers('text/html', len(msg),
                                                  cookie, callingDomain)
                                self._write(msg)
                                self._benchmarkGETtimings(GETstartTime,
                                                          GETtimings,
                                                          'post roles done',
                                                          'show skills')
                        else:
                            if self._fetchAuthenticated():
                                msg = json.dumps(actorJson['skills'],
                                                 ensure_ascii=False)
                                msg = msg.encode('utf-8')
                                self._set_headers('application/json',
                                                  len(msg), None,
                                                  callingDomain)
                                self._write(msg)
                            else:
                                self._404()
                        self.server.GETbusy = False
                        return True
        actor = path.replace('/skills', '')
        actorAbsolute = httpPrefix + '://' + domainFull + actor
        if callingDomain.endswith('.onion') and onionDomain:
            actorAbsolute = 'http://' + onionDomain + actor
        elif callingDomain.endswith('.i2p') and i2pDomain:
            actorAbsolute = 'http://' + i2pDomain + actor
        self._redirect_headers(actorAbsolute, cookie, callingDomain)
        self.server.GETbusy = False
        return True

    def _showIndividualAtPost(self, authorized: bool,
                              callingDomain: str, path: str,
                              baseDir: str, httpPrefix: str,
                              domain: str, domainFull: str, port: int,
                              onionDomain: str, i2pDomain: str,
                              GETstartTime, GETtimings: {},
                              proxyType: str, cookie: str,
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

        namedStatus = path.split('/@')[1]
        if '/' not in namedStatus:
            # show actor
            nickname = namedStatus
        else:
            postSections = namedStatus.split('/')
            if len(postSections) == 2:
                nickname = postSections[0]
                statusNumber = postSections[1]
                if len(statusNumber) > 10 and statusNumber.isdigit():
                    postFilename = \
                        baseDir + '/accounts/' + \
                        nickname + '@' + \
                        domain + '/outbox/' + \
                        httpPrefix + ':##' + \
                        domainFull + '#users#' + \
                        nickname + '#statuses#' + \
                        statusNumber + '.json'
                    if os.path.isfile(postFilename):
                        postJsonObject = loadJson(postFilename)
                        loadedPost = False
                        if postJsonObject:
                            loadedPost = True
                        else:
                            postJsonObject = {}
                        if loadedPost:
                            # Only authorized viewers get to see likes
                            # on posts. Otherwize marketers could gain
                            # more social graph info
                            if not authorized:
                                pjo = postJsonObject
                                self._removePostInteractions(pjo)
                            if self._requestHTTP():
                                recentPostsCache = \
                                    self.server.recentPostsCache
                                maxRecentPosts = \
                                    self.server.maxRecentPosts
                                translate = \
                                    self.server.translate
                                cachedWebfingers = \
                                    self.server.cachedWebfingers
                                personCache = \
                                    self.server.personCache
                                projectVersion = \
                                    self.server.projectVersion
                                ytDomain = \
                                    self.server.YTReplacementDomain
                                msg = \
                                    htmlIndividualPost(recentPostsCache,
                                                       maxRecentPosts,
                                                       translate,
                                                       self.server.session,
                                                       cachedWebfingers,
                                                       personCache,
                                                       nickname,
                                                       domain,
                                                       port,
                                                       authorized,
                                                       postJsonObject,
                                                       httpPrefix,
                                                       projectVersion,
                                                       likedBy,
                                                       ytDomain)
                                msg = msg.encode('utf-8')
                                self._set_headers('text/html', len(msg),
                                                  cookie, callingDomain)
                                self._write(msg)
                            else:
                                if self._fetchAuthenticated():
                                    msg = json.dumps(postJsonObject,
                                                     ensure_ascii=False)
                                    msg = msg.encode('utf-8')
                                    self._set_headers('application/json',
                                                      len(msg),
                                                      None, callingDomain)
                                    self._write(msg)
                                else:
                                    self._404()
                        self.server.GETbusy = False
                        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                                  'new post done',
                                                  'individual post shown')
                        return True
                    else:
                        self._404()
                        self.server.GETbusy = False
                        return True
        return False

    def _showIndividualPost(self, authorized: bool,
                            callingDomain: str, path: str,
                            baseDir: str, httpPrefix: str,
                            domain: str, domainFull: str, port: int,
                            onionDomain: str, i2pDomain: str,
                            GETstartTime, GETtimings: {},
                            proxyType: str, cookie: str,
                            debug: str) -> bool:
        """Shows an individual post
        """
        likedBy = None
        if '?likedBy=' in path:
            likedBy = path.split('?likedBy=')[1].strip()
            if '?' in likedBy:
                likedBy = likedBy.split('?')[0]
            path = path.split('?likedBy=')[0]
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
            baseDir + '/accounts/' + \
            nickname + '@' + \
            domain + '/outbox/' + \
            httpPrefix + ':##' + \
            domainFull + '#users#' + \
            nickname + '#statuses#' + \
            statusNumber + '.json'
        if os.path.isfile(postFilename):
            postJsonObject = loadJson(postFilename)
            if not postJsonObject:
                self.send_response(429)
                self.end_headers()
                self.server.GETbusy = False
                return True
            else:
                # Only authorized viewers get to see likes
                # on posts
                # Otherwize marketers could gain more social
                # graph info
                if not authorized:
                    pjo = postJsonObject
                    self._removePostInteractions(pjo)

                if self._requestHTTP():
                    recentPostsCache = \
                        self.server.recentPostsCache
                    maxRecentPosts = \
                        self.server.maxRecentPosts
                    translate = \
                        self.server.translate
                    cachedWebfingers = \
                        self.server.cachedWebfingers
                    personCache = \
                        self.server.personCache
                    projectVersion = \
                        self.server.projectVersion
                    ytDomain = \
                        self.server.YTReplacementDomain
                    msg = \
                        htmlIndividualPost(recentPostsCache,
                                           maxRecentPosts,
                                           translate,
                                           baseDir,
                                           self.server.session,
                                           cachedWebfingers,
                                           personCache,
                                           nickname,
                                           domain,
                                           port,
                                           authorized,
                                           postJsonObject,
                                           httpPrefix,
                                           projectVersion,
                                           likedBy,
                                           ytDomain)
                    msg = msg.encode('utf-8')
                    self._set_headers('text/html', len(msg),
                                      cookie, callingDomain)
                    self._write(msg)
                    self._benchmarkGETtimings(GETstartTime,
                                              GETtimings,
                                              'show skills ' +
                                              'done',
                                              'show status')
                else:
                    if self._fetchAuthenticated():
                        msg = json.dumps(postJsonObject,
                                         ensure_ascii=False)
                        msg = msg.encode('utf-8')
                        self._set_headers('application/json',
                                          len(msg),
                                          None, callingDomain)
                        self._write(msg)
                    else:
                        self._404()
            self.server.GETbusy = False
            return True
        else:
            self._404()
            self.server.GETbusy = False
            return True
        return False

    def _showInbox(self, authorized: bool,
                   callingDomain: str, path: str,
                   baseDir: str, httpPrefix: str,
                   domain: str, domainFull: str, port: int,
                   onionDomain: str, i2pDomain: str,
                   GETstartTime, GETtimings: {},
                   proxyType: str, cookie: str,
                   debug: str,
                   recentPostsCache: {}, session,
                   defaultTimeline: str,
                   maxRecentPosts: int,
                   translate: {},
                   cachedWebfingers: {},
                   personCache: {},
                   allowDeletion: bool,
                   projectVersion: str,
                   YTReplacementDomain: str) -> bool:
        """Shows the inbox timeline
        """
        if '/users/' in path:
            if authorized:
                inboxFeed = \
                    personBoxJson(recentPostsCache,
                                  session,
                                  baseDir,
                                  domain,
                                  port,
                                  path,
                                  httpPrefix,
                                  maxPostsInFeed, 'inbox',
                                  authorized)
                if inboxFeed:
                    if GETstartTime:
                        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                                  'show status done',
                                                  'show inbox json')
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
                                              baseDir,
                                              domain,
                                              port,
                                              path + '?page=1',
                                              httpPrefix,
                                              maxPostsInFeed, 'inbox',
                                              authorized)
                            if GETstartTime:
                                self._benchmarkGETtimings(GETstartTime,
                                                          GETtimings,
                                                          'show status done',
                                                          'show inbox page')
                        msg = htmlInbox(defaultTimeline,
                                        recentPostsCache,
                                        maxRecentPosts,
                                        translate,
                                        pageNumber, maxPostsInFeed,
                                        session,
                                        baseDir,
                                        cachedWebfingers,
                                        personCache,
                                        nickname,
                                        domain,
                                        port,
                                        inboxFeed,
                                        allowDeletion,
                                        httpPrefix,
                                        projectVersion,
                                        self._isMinimal(nickname),
                                        YTReplacementDomain,
                                        self.server.newswire)
                        if GETstartTime:
                            self._benchmarkGETtimings(GETstartTime, GETtimings,
                                                      'show status done',
                                                      'show inbox html')

                        if msg:
                            msg = msg.encode('utf-8')
                            self._set_headers('text/html', len(msg),
                                              cookie, callingDomain)
                            self._write(msg)

                        if GETstartTime:
                            self._benchmarkGETtimings(GETstartTime, GETtimings,
                                                      'show status done',
                                                      'show inbox')
                    else:
                        # don't need authenticated fetch here because
                        # there is already the authorization check
                        msg = json.dumps(inboxFeed, ensure_ascii=False)
                        msg = msg.encode('utf-8')
                        self._set_headers('application/json', len(msg),
                                          None, callingDomain)
                        self._write(msg)
                    self.server.GETbusy = False
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
            self.server.GETbusy = False
            return True
        return False

    def _showDMs(self, authorized: bool,
                 callingDomain: str, path: str,
                 baseDir: str, httpPrefix: str,
                 domain: str, domainFull: str, port: int,
                 onionDomain: str, i2pDomain: str,
                 GETstartTime, GETtimings: {},
                 proxyType: str, cookie: str,
                 debug: str) -> bool:
        """Shows the DMs timeline
        """
        if '/users/' in path:
            if authorized:
                inboxDMFeed = \
                    personBoxJson(self.server.recentPostsCache,
                                  self.server.session,
                                  baseDir,
                                  domain,
                                  port,
                                  path,
                                  httpPrefix,
                                  maxPostsInFeed, 'dm',
                                  authorized)
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
                                              baseDir,
                                              domain,
                                              port,
                                              path + '?page=1',
                                              httpPrefix,
                                              maxPostsInFeed, 'dm',
                                              authorized)
                        msg = \
                            htmlInboxDMs(self.server.defaultTimeline,
                                         self.server.recentPostsCache,
                                         self.server.maxRecentPosts,
                                         self.server.translate,
                                         pageNumber, maxPostsInFeed,
                                         self.server.session,
                                         baseDir,
                                         self.server.cachedWebfingers,
                                         self.server.personCache,
                                         nickname,
                                         domain,
                                         port,
                                         inboxDMFeed,
                                         self.server.allowDeletion,
                                         httpPrefix,
                                         self.server.projectVersion,
                                         self._isMinimal(nickname),
                                         self.server.YTReplacementDomain,
                                         self.server.newswire)
                        msg = msg.encode('utf-8')
                        self._set_headers('text/html', len(msg),
                                          cookie, callingDomain)
                        self._write(msg)
                        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                                  'show inbox done',
                                                  'show dms')
                    else:
                        # don't need authenticated fetch here because
                        # there is already the authorization check
                        msg = json.dumps(inboxDMFeed, ensure_ascii=False)
                        msg = msg.encode('utf-8')
                        self._set_headers('application/json',
                                          len(msg),
                                          None, callingDomain)
                        self._write(msg)
                    self.server.GETbusy = False
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
            self.server.GETbusy = False
            return True
        return False

    def _showReplies(self, authorized: bool,
                     callingDomain: str, path: str,
                     baseDir: str, httpPrefix: str,
                     domain: str, domainFull: str, port: int,
                     onionDomain: str, i2pDomain: str,
                     GETstartTime, GETtimings: {},
                     proxyType: str, cookie: str,
                     debug: str) -> bool:
        """Shows the replies timeline
        """
        if '/users/' in path:
            if authorized:
                inboxRepliesFeed = \
                    personBoxJson(self.server.recentPostsCache,
                                  self.server.session,
                                  baseDir,
                                  domain,
                                  port,
                                  path,
                                  httpPrefix,
                                  maxPostsInFeed, 'tlreplies',
                                  True)
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
                                          baseDir,
                                          domain,
                                          port,
                                          path + '?page=1',
                                          httpPrefix,
                                          maxPostsInFeed, 'tlreplies',
                                          True)
                    msg = \
                        htmlInboxReplies(self.server.defaultTimeline,
                                         self.server.recentPostsCache,
                                         self.server.maxRecentPosts,
                                         self.server.translate,
                                         pageNumber, maxPostsInFeed,
                                         self.server.session,
                                         baseDir,
                                         self.server.cachedWebfingers,
                                         self.server.personCache,
                                         nickname,
                                         domain,
                                         port,
                                         inboxRepliesFeed,
                                         self.server.allowDeletion,
                                         httpPrefix,
                                         self.server.projectVersion,
                                         self._isMinimal(nickname),
                                         self.server.YTReplacementDomain,
                                         self.server.newswire)
                    msg = msg.encode('utf-8')
                    self._set_headers('text/html', len(msg),
                                      cookie, callingDomain)
                    self._write(msg)
                    self._benchmarkGETtimings(GETstartTime, GETtimings,
                                              'show dms done',
                                              'show replies 2')
                else:
                    # don't need authenticated fetch here because there is
                    # already the authorization check
                    msg = json.dumps(inboxRepliesFeed,
                                     ensure_ascii=False)
                    msg = msg.encode('utf-8')
                    self._set_headers('application/json', len(msg),
                                      None, callingDomain)
                    self._write(msg)
                self.server.GETbusy = False
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
            self.server.GETbusy = False
            return True
        return False

    def _showMediaTimeline(self, authorized: bool,
                           callingDomain: str, path: str,
                           baseDir: str, httpPrefix: str,
                           domain: str, domainFull: str, port: int,
                           onionDomain: str, i2pDomain: str,
                           GETstartTime, GETtimings: {},
                           proxyType: str, cookie: str,
                           debug: str) -> bool:
        """Shows the media timeline
        """
        if '/users/' in path:
            if authorized:
                inboxMediaFeed = \
                    personBoxJson(self.server.recentPostsCache,
                                  self.server.session,
                                  baseDir,
                                  domain,
                                  port,
                                  path,
                                  httpPrefix,
                                  maxPostsInMediaFeed, 'tlmedia',
                                  True)
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
                                          baseDir,
                                          domain,
                                          port,
                                          path + '?page=1',
                                          httpPrefix,
                                          maxPostsInMediaFeed, 'tlmedia',
                                          True)
                    msg = \
                        htmlInboxMedia(self.server.defaultTimeline,
                                       self.server.recentPostsCache,
                                       self.server.maxRecentPosts,
                                       self.server.translate,
                                       pageNumber, maxPostsInMediaFeed,
                                       self.server.session,
                                       baseDir,
                                       self.server.cachedWebfingers,
                                       self.server.personCache,
                                       nickname,
                                       domain,
                                       port,
                                       inboxMediaFeed,
                                       self.server.allowDeletion,
                                       httpPrefix,
                                       self.server.projectVersion,
                                       self._isMinimal(nickname),
                                       self.server.YTReplacementDomain,
                                       self.server.newswire)
                    msg = msg.encode('utf-8')
                    self._set_headers('text/html', len(msg),
                                      cookie, callingDomain)
                    self._write(msg)
                    self._benchmarkGETtimings(GETstartTime, GETtimings,
                                              'show replies 2 done',
                                              'show media 2')
                else:
                    # don't need authenticated fetch here because there is
                    # already the authorization check
                    msg = json.dumps(inboxMediaFeed,
                                     ensure_ascii=False)
                    msg = msg.encode('utf-8')
                    self._set_headers('application/json', len(msg),
                                      None, callingDomain)
                    self._write(msg)
                self.server.GETbusy = False
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
            self.server.GETbusy = False
            return True
        return False

    def _showBlogsTimeline(self, authorized: bool,
                           callingDomain: str, path: str,
                           baseDir: str, httpPrefix: str,
                           domain: str, domainFull: str, port: int,
                           onionDomain: str, i2pDomain: str,
                           GETstartTime, GETtimings: {},
                           proxyType: str, cookie: str,
                           debug: str) -> bool:
        """Shows the blogs timeline
        """
        if '/users/' in path:
            if authorized:
                inboxBlogsFeed = \
                    personBoxJson(self.server.recentPostsCache,
                                  self.server.session,
                                  baseDir,
                                  domain,
                                  port,
                                  path,
                                  httpPrefix,
                                  maxPostsInBlogsFeed, 'tlblogs',
                                  True)
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
                                          baseDir,
                                          domain,
                                          port,
                                          path + '?page=1',
                                          httpPrefix,
                                          maxPostsInBlogsFeed, 'tlblogs',
                                          True)
                    msg = \
                        htmlInboxBlogs(self.server.defaultTimeline,
                                       self.server.recentPostsCache,
                                       self.server.maxRecentPosts,
                                       self.server.translate,
                                       pageNumber, maxPostsInBlogsFeed,
                                       self.server.session,
                                       baseDir,
                                       self.server.cachedWebfingers,
                                       self.server.personCache,
                                       nickname,
                                       domain,
                                       port,
                                       inboxBlogsFeed,
                                       self.server.allowDeletion,
                                       httpPrefix,
                                       self.server.projectVersion,
                                       self._isMinimal(nickname),
                                       self.server.YTReplacementDomain,
                                       self.server.newswire)
                    msg = msg.encode('utf-8')
                    self._set_headers('text/html', len(msg),
                                      cookie, callingDomain)
                    self._write(msg)
                    self._benchmarkGETtimings(GETstartTime, GETtimings,
                                              'show media 2 done',
                                              'show blogs 2')
                else:
                    # don't need authenticated fetch here because there is
                    # already the authorization check
                    msg = json.dumps(inboxBlogsFeed,
                                     ensure_ascii=False)
                    msg = msg.encode('utf-8')
                    self._set_headers('application/json',
                                      len(msg),
                                      None, callingDomain)
                    self._write(msg)
                self.server.GETbusy = False
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
            self.server.GETbusy = False
            return True
        return False

    def _showSharesTimeline(self, authorized: bool,
                            callingDomain: str, path: str,
                            baseDir: str, httpPrefix: str,
                            domain: str, domainFull: str, port: int,
                            onionDomain: str, i2pDomain: str,
                            GETstartTime, GETtimings: {},
                            proxyType: str, cookie: str,
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
                    msg = \
                        htmlShares(self.server.defaultTimeline,
                                   self.server.recentPostsCache,
                                   self.server.maxRecentPosts,
                                   self.server.translate,
                                   pageNumber, maxPostsInFeed,
                                   self.server.session,
                                   baseDir,
                                   self.server.cachedWebfingers,
                                   self.server.personCache,
                                   nickname,
                                   domain,
                                   port,
                                   self.server.allowDeletion,
                                   httpPrefix,
                                   self.server.projectVersion,
                                   self.server.YTReplacementDomain,
                                   self.server.newswire)
                    msg = msg.encode('utf-8')
                    self._set_headers('text/html', len(msg),
                                      cookie, callingDomain)
                    self._write(msg)
                    self._benchmarkGETtimings(GETstartTime, GETtimings,
                                              'show blogs 2 done',
                                              'show shares 2')
                    self.server.GETbusy = False
                    return True
        # not the shares timeline
        if debug:
            print('DEBUG: GET access to shares timeline is unauthorized')
        self.send_response(405)
        self.end_headers()
        self.server.GETbusy = False
        return True

    def _showBookmarksTimeline(self, authorized: bool,
                               callingDomain: str, path: str,
                               baseDir: str, httpPrefix: str,
                               domain: str, domainFull: str, port: int,
                               onionDomain: str, i2pDomain: str,
                               GETstartTime, GETtimings: {},
                               proxyType: str, cookie: str,
                               debug: str) -> bool:
        """Shows the bookmarks timeline
        """
        if '/users/' in path:
            if authorized:
                bookmarksFeed = \
                    personBoxJson(self.server.recentPostsCache,
                                  self.server.session,
                                  baseDir,
                                  domain,
                                  port,
                                  path,
                                  httpPrefix,
                                  maxPostsInFeed, 'tlbookmarks',
                                  authorized)
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
                                              baseDir,
                                              domain,
                                              port,
                                              path + '?page=1',
                                              httpPrefix,
                                              maxPostsInFeed,
                                              'tlbookmarks',
                                              authorized)
                        msg = \
                            htmlBookmarks(self.server.defaultTimeline,
                                          self.server.recentPostsCache,
                                          self.server.maxRecentPosts,
                                          self.server.translate,
                                          pageNumber, maxPostsInFeed,
                                          self.server.session,
                                          baseDir,
                                          self.server.cachedWebfingers,
                                          self.server.personCache,
                                          nickname,
                                          domain,
                                          port,
                                          bookmarksFeed,
                                          self.server.allowDeletion,
                                          httpPrefix,
                                          self.server.projectVersion,
                                          self._isMinimal(nickname),
                                          self.server.YTReplacementDomain,
                                          self.server.newswire)
                        msg = msg.encode('utf-8')
                        self._set_headers('text/html', len(msg),
                                          cookie, callingDomain)
                        self._write(msg)
                        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                                  'show shares 2 done',
                                                  'show bookmarks 2')
                    else:
                        # don't need authenticated fetch here because
                        # there is already the authorization check
                        msg = json.dumps(bookmarksFeed,
                                         ensure_ascii=False)
                        msg = msg.encode('utf-8')
                        self._set_headers('application/json', len(msg),
                                          None, callingDomain)
                        self._write(msg)
                    self.server.GETbusy = False
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
        self.server.GETbusy = False
        return True

    def _showEventsTimeline(self, authorized: bool,
                            callingDomain: str, path: str,
                            baseDir: str, httpPrefix: str,
                            domain: str, domainFull: str, port: int,
                            onionDomain: str, i2pDomain: str,
                            GETstartTime, GETtimings: {},
                            proxyType: str, cookie: str,
                            debug: str) -> bool:
        """Shows the events timeline
        """
        if '/users/' in path:
            if authorized:
                # convert /events to /tlevents
                if path.endswith('/events') or \
                   '/events?page=' in path:
                    path = path.replace('/events', '/tlevents')
                eventsFeed = \
                    personBoxJson(self.server.recentPostsCache,
                                  self.server.session,
                                  baseDir,
                                  domain,
                                  port,
                                  path,
                                  httpPrefix,
                                  maxPostsInFeed, 'tlevents',
                                  authorized)
                print('eventsFeed: ' + str(eventsFeed))
                if eventsFeed:
                    if self._requestHTTP():
                        nickname = path.replace('/users/', '')
                        nickname = nickname.replace('/tlevents', '')
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
                            eventsFeed = \
                                personBoxJson(self.server.recentPostsCache,
                                              self.server.session,
                                              baseDir,
                                              domain,
                                              port,
                                              path + '?page=1',
                                              httpPrefix,
                                              maxPostsInFeed,
                                              'tlevents',
                                              authorized)
                        msg = \
                            htmlEvents(self.server.defaultTimeline,
                                       self.server.recentPostsCache,
                                       self.server.maxRecentPosts,
                                       self.server.translate,
                                       pageNumber, maxPostsInFeed,
                                       self.server.session,
                                       baseDir,
                                       self.server.cachedWebfingers,
                                       self.server.personCache,
                                       nickname,
                                       domain,
                                       port,
                                       eventsFeed,
                                       self.server.allowDeletion,
                                       httpPrefix,
                                       self.server.projectVersion,
                                       self._isMinimal(nickname),
                                       self.server.YTReplacementDomain,
                                       self.server.newswire)
                        msg = msg.encode('utf-8')
                        self._set_headers('text/html', len(msg),
                                          cookie, callingDomain)
                        self._write(msg)
                        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                                  'show bookmarks 2 done',
                                                  'show events')
                    else:
                        # don't need authenticated fetch here because
                        # there is already the authorization check
                        msg = json.dumps(eventsFeed,
                                         ensure_ascii=False)
                        msg = msg.encode('utf-8')
                        self._set_headers('application/json', len(msg),
                                          None, callingDomain)
                        self._write(msg)
                    self.server.GETbusy = False
                    return True
            else:
                if debug:
                    nickname = path.replace('/users/', '')
                    nickname = nickname.replace('/tlevents', '')
                    print('DEBUG: ' + nickname +
                          ' was not authorized to access ' + path)
        if debug:
            print('DEBUG: GET access to events is unauthorized')
        self.send_response(405)
        self.end_headers()
        self.server.GETbusy = False
        return True

    def _showOutboxTimeline(self, authorized: bool,
                            callingDomain: str, path: str,
                            baseDir: str, httpPrefix: str,
                            domain: str, domainFull: str, port: int,
                            onionDomain: str, i2pDomain: str,
                            GETstartTime, GETtimings: {},
                            proxyType: str, cookie: str,
                            debug: str) -> bool:
        """Shows the outbox timeline
        """
        # get outbox feed for a person
        outboxFeed = \
            personBoxJson(self.server.recentPostsCache,
                          self.server.session,
                          baseDir, domain,
                          port, path,
                          httpPrefix,
                          maxPostsInFeed, 'outbox',
                          authorized)
        if outboxFeed:
            if self._requestHTTP():
                nickname = \
                    path.replace('/users/', '').replace('/outbox', '')
                pageNumber = 1
                if '?page=' in nickname:
                    pageNumber = nickname.split('?page=')[1]
                    nickname = nickname.split('?page=')[0]
                    if pageNumber.isdigit():
                        pageNumber = int(pageNumber)
                    else:
                        pageNumber = 1
                if 'page=' not in path:
                    # if a page wasn't specified then show the first one
                    outboxFeed = \
                        personBoxJson(self.server.recentPostsCache,
                                      self.server.session,
                                      baseDir,
                                      domain,
                                      port,
                                      path + '?page=1',
                                      httpPrefix,
                                      maxPostsInFeed, 'outbox',
                                      authorized)
                msg = \
                    htmlOutbox(self.server.defaultTimeline,
                               self.server.recentPostsCache,
                               self.server.maxRecentPosts,
                               self.server.translate,
                               pageNumber, maxPostsInFeed,
                               self.server.session,
                               baseDir,
                               self.server.cachedWebfingers,
                               self.server.personCache,
                               nickname,
                               domain,
                               port,
                               outboxFeed,
                               self.server.allowDeletion,
                               httpPrefix,
                               self.server.projectVersion,
                               self._isMinimal(nickname),
                               self.server.YTReplacementDomain,
                               self.server.newswire)
                msg = msg.encode('utf-8')
                self._set_headers('text/html', len(msg),
                                  cookie, callingDomain)
                self._write(msg)
                self._benchmarkGETtimings(GETstartTime, GETtimings,
                                          'show events done',
                                          'show outbox')
            else:
                if self._fetchAuthenticated():
                    msg = json.dumps(outboxFeed,
                                     ensure_ascii=False)
                    msg = msg.encode('utf-8')
                    self._set_headers('application/json', len(msg),
                                      None, callingDomain)
                    self._write(msg)
                else:
                    self._404()
            self.server.GETbusy = False
            return True
        return False

    def _showModTimeline(self, authorized: bool,
                         callingDomain: str, path: str,
                         baseDir: str, httpPrefix: str,
                         domain: str, domainFull: str, port: int,
                         onionDomain: str, i2pDomain: str,
                         GETstartTime, GETtimings: {},
                         proxyType: str, cookie: str,
                         debug: str) -> bool:
        """Shows the moderation timeline
        """
        if '/users/' in path:
            if authorized:
                moderationFeed = \
                    personBoxJson(self.server.recentPostsCache,
                                  self.server.session,
                                  baseDir,
                                  domain,
                                  port,
                                  path,
                                  httpPrefix,
                                  maxPostsInFeed, 'moderation',
                                  True)
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
                                              baseDir,
                                              domain,
                                              port,
                                              path + '?page=1',
                                              httpPrefix,
                                              maxPostsInFeed, 'moderation',
                                              True)
                        msg = \
                            htmlModeration(self.server.defaultTimeline,
                                           self.server.recentPostsCache,
                                           self.server.maxRecentPosts,
                                           self.server.translate,
                                           pageNumber, maxPostsInFeed,
                                           self.server.session,
                                           baseDir,
                                           self.server.cachedWebfingers,
                                           self.server.personCache,
                                           nickname,
                                           domain,
                                           port,
                                           moderationFeed,
                                           True,
                                           httpPrefix,
                                           self.server.projectVersion,
                                           self.server.YTReplacementDomain,
                                           self.server.newswire)
                        msg = msg.encode('utf-8')
                        self._set_headers('text/html', len(msg),
                                          cookie, callingDomain)
                        self._write(msg)
                        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                                  'show outbox done',
                                                  'show moderation')
                    else:
                        # don't need authenticated fetch here because
                        # there is already the authorization check
                        msg = json.dumps(moderationFeed,
                                         ensure_ascii=False)
                        msg = msg.encode('utf-8')
                        self._set_headers('application/json', len(msg),
                                          None, callingDomain)
                        self._write(msg)
                    self.server.GETbusy = False
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
        self.server.GETbusy = False
        return True

    def _showSharesFeed(self, authorized: bool,
                        callingDomain: str, path: str,
                        baseDir: str, httpPrefix: str,
                        domain: str, domainFull: str, port: int,
                        onionDomain: str, i2pDomain: str,
                        GETstartTime, GETtimings: {},
                        proxyType: str, cookie: str,
                        debug: str) -> bool:
        """Shows the shares feed
        """
        shares = \
            getSharesFeedForPerson(baseDir, domain, port, path,
                                   httpPrefix, sharesPerPage)
        if shares:
            if self._requestHTTP():
                pageNumber = 1
                if '?page=' not in path:
                    searchPath = path
                    # get a page of shares, not the summary
                    shares = \
                        getSharesFeedForPerson(baseDir, domain, port,
                                               path + '?page=true',
                                               httpPrefix,
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
                                 searchPath.replace('/shares', ''),
                                 baseDir)
                if getPerson:
                    if not self.server.session:
                        print('Starting new session during profile')
                        self.server.session = createSession(proxyType)
                        if not self.server.session:
                            print('ERROR: GET failed to create session ' +
                                  'during profile')
                            self._404()
                            self.server.GETbusy = False
                            return True
                    msg = \
                        htmlProfile(self.server.defaultTimeline,
                                    self.server.recentPostsCache,
                                    self.server.maxRecentPosts,
                                    self.server.translate,
                                    self.server.projectVersion,
                                    baseDir, httpPrefix,
                                    authorized,
                                    getPerson, 'shares',
                                    self.server.session,
                                    self.server.cachedWebfingers,
                                    self.server.personCache,
                                    self.server.YTReplacementDomain,
                                    shares,
                                    pageNumber, sharesPerPage)
                    msg = msg.encode('utf-8')
                    self._set_headers('text/html', len(msg),
                                      cookie, callingDomain)
                    self._write(msg)
                    self._benchmarkGETtimings(GETstartTime, GETtimings,
                                              'show moderation done',
                                              'show profile 2')
                    self.server.GETbusy = False
                    return True
            else:
                if self._fetchAuthenticated():
                    msg = json.dumps(shares,
                                     ensure_ascii=False)
                    msg = msg.encode('utf-8')
                    self._set_headers('application/json', len(msg),
                                      None, callingDomain)
                    self._write(msg)
                else:
                    self._404()
                self.server.GETbusy = False
                return True
        return False

    def _showFollowingFeed(self, authorized: bool,
                           callingDomain: str, path: str,
                           baseDir: str, httpPrefix: str,
                           domain: str, domainFull: str, port: int,
                           onionDomain: str, i2pDomain: str,
                           GETstartTime, GETtimings: {},
                           proxyType: str, cookie: str,
                           debug: str) -> bool:
        """Shows the following feed
        """
        following = \
            getFollowingFeed(baseDir, domain, port, path,
                             httpPrefix, authorized, followsPerPage)
        if following:
            if self._requestHTTP():
                pageNumber = 1
                if '?page=' not in path:
                    searchPath = path
                    # get a page of following, not the summary
                    following = \
                        getFollowingFeed(baseDir,
                                         domain,
                                         port,
                                         path + '?page=true',
                                         httpPrefix,
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
                                 baseDir)
                if getPerson:
                    if not self.server.session:
                        print('Starting new session during following')
                        self.server.session = createSession(proxyType)
                        if not self.server.session:
                            print('ERROR: GET failed to create session ' +
                                  'during following')
                            self._404()
                            self.server.GETbusy = False
                            return True

                    msg = \
                        htmlProfile(self.server.defaultTimeline,
                                    self.server.recentPostsCache,
                                    self.server.maxRecentPosts,
                                    self.server.translate,
                                    self.server.projectVersion,
                                    baseDir, httpPrefix,
                                    authorized,
                                    getPerson, 'following',
                                    self.server.session,
                                    self.server.cachedWebfingers,
                                    self.server.personCache,
                                    self.server.YTReplacementDomain,
                                    following,
                                    pageNumber,
                                    followsPerPage).encode('utf-8')
                    self._set_headers('text/html',
                                      len(msg), cookie, callingDomain)
                    self._write(msg)
                    self.server.GETbusy = False
                    self._benchmarkGETtimings(GETstartTime, GETtimings,
                                              'show profile 2 done',
                                              'show profile 3')
                    return True
            else:
                if self._fetchAuthenticated():
                    msg = json.dumps(following,
                                     ensure_ascii=False).encode('utf-8')
                    self._set_headers('application/json', len(msg),
                                      None, callingDomain)
                    self._write(msg)
                else:
                    self._404()
                self.server.GETbusy = False
                return True
        return False

    def _showFollowersFeed(self, authorized: bool,
                           callingDomain: str, path: str,
                           baseDir: str, httpPrefix: str,
                           domain: str, domainFull: str, port: int,
                           onionDomain: str, i2pDomain: str,
                           GETstartTime, GETtimings: {},
                           proxyType: str, cookie: str,
                           debug: str) -> bool:
        """Shows the followers feed
        """
        followers = \
            getFollowingFeed(baseDir, domain, port, path, httpPrefix,
                             authorized, followsPerPage, 'followers')
        if followers:
            if self._requestHTTP():
                pageNumber = 1
                if '?page=' not in path:
                    searchPath = path
                    # get a page of followers, not the summary
                    followers = \
                        getFollowingFeed(baseDir,
                                         domain,
                                         port,
                                         path + '?page=1',
                                         httpPrefix,
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
                                 baseDir)
                if getPerson:
                    if not self.server.session:
                        print('Starting new session during following2')
                        self.server.session = createSession(proxyType)
                        if not self.server.session:
                            print('ERROR: GET failed to create session ' +
                                  'during following2')
                            self._404()
                            self.server.GETbusy = False
                            return True
                    msg = \
                        htmlProfile(self.server.defaultTimeline,
                                    self.server.recentPostsCache,
                                    self.server.maxRecentPosts,
                                    self.server.translate,
                                    self.server.projectVersion,
                                    baseDir,
                                    httpPrefix,
                                    authorized,
                                    getPerson, 'followers',
                                    self.server.session,
                                    self.server.cachedWebfingers,
                                    self.server.personCache,
                                    self.server.YTReplacementDomain,
                                    followers,
                                    pageNumber,
                                    followsPerPage).encode('utf-8')
                    self._set_headers('text/html', len(msg),
                                      cookie, callingDomain)
                    self._write(msg)
                    self.server.GETbusy = False
                    self._benchmarkGETtimings(GETstartTime, GETtimings,
                                              'show profile 3 done',
                                              'show profile 4')
                    return True
            else:
                if self._fetchAuthenticated():
                    msg = json.dumps(followers,
                                     ensure_ascii=False).encode('utf-8')
                    self._set_headers('application/json', len(msg),
                                      None, callingDomain)
                    self._write(msg)
                else:
                    self._404()
            self.server.GETbusy = False
            return True
        return False

    def _showPersonProfile(self, authorized: bool,
                           callingDomain: str, path: str,
                           baseDir: str, httpPrefix: str,
                           domain: str, domainFull: str, port: int,
                           onionDomain: str, i2pDomain: str,
                           GETstartTime, GETtimings: {},
                           proxyType: str, cookie: str,
                           debug: str) -> bool:
        """Shows the profile for a person
        """
        # look up a person
        getPerson = personLookup(domain, path, baseDir)
        if getPerson:
            if self._requestHTTP():
                if not self.server.session:
                    print('Starting new session during person lookup')
                    self.server.session = createSession(proxyType)
                    if not self.server.session:
                        print('ERROR: GET failed to create session ' +
                              'during person lookup')
                        self._404()
                        self.server.GETbusy = False
                        return True
                msg = \
                    htmlProfile(self.server.defaultTimeline,
                                self.server.recentPostsCache,
                                self.server.maxRecentPosts,
                                self.server.translate,
                                self.server.projectVersion,
                                baseDir,
                                httpPrefix,
                                authorized,
                                getPerson, 'posts',
                                self.server.session,
                                self.server.cachedWebfingers,
                                self.server.personCache,
                                self.server.YTReplacementDomain,
                                None, None).encode('utf-8')
                self._set_headers('text/html', len(msg),
                                  cookie, callingDomain)
                self._write(msg)
                self._benchmarkGETtimings(GETstartTime, GETtimings,
                                          'show profile 4 done',
                                          'show profile posts')
            else:
                if self._fetchAuthenticated():
                    msg = json.dumps(getPerson,
                                     ensure_ascii=False).encode('utf-8')
                    self._set_headers('application/json', len(msg),
                                      None, callingDomain)
                    self._write(msg)
                else:
                    self._404()
            self.server.GETbusy = False
            return True
        return False

    def _showBlogPage(self, authorized: bool,
                      callingDomain: str, path: str,
                      baseDir: str, httpPrefix: str,
                      domain: str, domainFull: str, port: int,
                      onionDomain: str, i2pDomain: str,
                      GETstartTime, GETtimings: {},
                      proxyType: str, cookie: str,
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
        if not self.server.session:
            print('Starting new session during blog page')
            self.server.session = createSession(proxyType)
            if not self.server.session:
                print('ERROR: GET failed to create session ' +
                      'during blog page')
                self._404()
                return True
        msg = htmlBlogPage(authorized,
                           self.server.session,
                           baseDir,
                           httpPrefix,
                           translate,
                           nickname,
                           domain, port,
                           maxPostsInBlogsFeed, pageNumber)
        if msg is not None:
            msg = msg.encode('utf-8')
            self._set_headers('text/html', len(msg),
                              cookie, callingDomain)
            self._write(msg)
            self._benchmarkGETtimings(GETstartTime, GETtimings,
                                      'blog view done', 'blog page')
            return True
        self._404()
        return True

    def _redirectToLoginScreen(self, callingDomain: str, path: str,
                               httpPrefix: str, domainFull: str,
                               onionDomain: str, i2pDomain: str,
                               GETstartTime, GETtimings: {},
                               authorized: bool, debug: bool):
        """Redirects to the login screen if necessary
        """
        divertToLoginScreen = False
        if '/media/' not in path and \
           '/sharefiles/' not in path and \
           '/statuses/' not in path and \
           '/emoji/' not in path and \
           '/tags/' not in path and \
           '/avatars/' not in path and \
           '/fonts/' not in path and \
           '/icons/' not in path:
            divertToLoginScreen = True
            if path.startswith('/users/'):
                nickStr = path.split('/users/')[1]
                if '/' not in nickStr and '?' not in nickStr:
                    divertToLoginScreen = False
                else:
                    if path.endswith('/following') or \
                       '/following?page=' in path or \
                       path.endswith('/followers') or \
                       '/followers?page=' in path or \
                       path.endswith('/skills') or \
                       path.endswith('/roles') or \
                       path.endswith('/shares'):
                        divertToLoginScreen = False

        if divertToLoginScreen and not authorized:
            if debug:
                print('DEBUG: divertToLoginScreen=' +
                      str(divertToLoginScreen))
                print('DEBUG: authorized=' + str(authorized))
                print('DEBUG: path=' + path)
            if callingDomain.endswith('.onion') and onionDomain:
                self._redirect_headers('http://' +
                                       onionDomain + '/login',
                                       None, callingDomain)
            elif callingDomain.endswith('.i2p') and i2pDomain:
                self._redirect_headers('http://' +
                                       i2pDomain + '/login',
                                       None, callingDomain)
            else:
                self._redirect_headers(httpPrefix + '://' +
                                       domainFull +
                                       '/login', None, callingDomain)
            self._benchmarkGETtimings(GETstartTime, GETtimings,
                                      'robots txt',
                                      'show login screen')
            return True
        return False

    def _getStyleSheet(self, callingDomain: str, path: str,
                       GETstartTime, GETtimings: {}) -> bool:
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
                    with open(path, 'r') as cssfile:
                        css = cssfile.read()
                        break
                except Exception as e:
                    print(e)
                    time.sleep(1)
                    tries += 1
            msg = css.encode('utf-8')
            self._set_headers('text/css', len(msg),
                              None, callingDomain)
            self._write(msg)
            self._benchmarkGETtimings(GETstartTime, GETtimings,
                                      'show login screen done',
                                      'show profile.css')
            return True
        self._404()
        return True

    def _showQRcode(self, callingDomain: str, path: str,
                    baseDir: str, domain: str, port: int,
                    GETstartTime, GETtimings: {}) -> bool:
        """Shows a QR code for an account
        """
        nickname = getNicknameFromActor(path)
        savePersonQrcode(baseDir, nickname, domain, port)
        qrFilename = \
            baseDir + '/accounts/' + nickname + '@' + domain + '/qrcode.png'
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
                except Exception as e:
                    print(e)
                    time.sleep(1)
                    tries += 1
            if mediaBinary:
                self._set_headers_etag(qrFilename, 'image/png',
                                       mediaBinary, None,
                                       callingDomain)
                self._write(mediaBinary)
                self._benchmarkGETtimings(GETstartTime, GETtimings,
                                          'login screen logo done',
                                          'account qrcode')
                return True
        self._404()
        return True

    def _searchScreenBanner(self, callingDomain: str, path: str,
                            baseDir: str, domain: str, port: int,
                            GETstartTime, GETtimings: {}) -> bool:
        """Shows a banner image on the search screen
        """
        nickname = getNicknameFromActor(path)
        bannerFilename = \
            baseDir + '/accounts/' + \
            nickname + '@' + domain + '/search_banner.png'
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
                except Exception as e:
                    print(e)
                    time.sleep(1)
                    tries += 1
            if mediaBinary:
                self._set_headers_etag(bannerFilename, 'image/png',
                                       mediaBinary, None,
                                       callingDomain)
                self._write(mediaBinary)
                self._benchmarkGETtimings(GETstartTime, GETtimings,
                                          'account qrcode done',
                                          'search screen banner')
                return True
        self._404()
        return True

    def _columImage(self, side: str, callingDomain: str, path: str,
                    baseDir: str, domain: str, port: int,
                    GETstartTime, GETtimings: {}) -> bool:
        """Shows an image at the top of the left/right column
        """
        nickname = getNicknameFromActor(path)
        if not nickname:
            self._404()
            return True
        bannerFilename = \
            baseDir + '/accounts/' + \
            nickname + '@' + domain + '/' + side + '_col_image.png'
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
                except Exception as e:
                    print(e)
                    time.sleep(1)
                    tries += 1
            if mediaBinary:
                self._set_headers_etag(bannerFilename, 'image/png',
                                       mediaBinary, None,
                                       callingDomain)
                self._write(mediaBinary)
                self._benchmarkGETtimings(GETstartTime, GETtimings,
                                          'account qrcode done',
                                          side + ' col image')
                return True
        self._404()
        return True

    def _showBackgroundImage(self, callingDomain: str, path: str,
                             baseDir: str,
                             GETstartTime, GETtimings: {}) -> bool:
        """Show a background image
        """
        for ext in ('webp', 'gif', 'jpg', 'png', 'avif'):
            for bg in ('follow', 'options', 'login'):
                # follow screen background image
                if path.endswith('/' + bg + '-background.' + ext):
                    bgFilename = \
                        baseDir + '/accounts/' + \
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
                            except Exception as e:
                                print(e)
                                time.sleep(1)
                                tries += 1
                        if bgBinary:
                            if ext == 'jpg':
                                ext = 'jpeg'
                            self._set_headers_etag(bgFilename,
                                                   'image/' + ext,
                                                   bgBinary, None,
                                                   callingDomain)
                            self._write(bgBinary)
                            self._benchmarkGETtimings(GETstartTime,
                                                      GETtimings,
                                                      'search screen ' +
                                                      'banner done',
                                                      'background shown')
                            return True
        self._404()
        return True

    def _showShareImage(self, callingDomain: str, path: str,
                        baseDir: str,
                        GETstartTime, GETtimings: {}) -> bool:
        """Show a shared item image
        """
        if self._pathIsImage(path):
            mediaStr = path.split('/sharefiles/')[1]
            mediaFilename = \
                baseDir + '/sharefiles/' + mediaStr
            if os.path.isfile(mediaFilename):
                if self._etag_exists(mediaFilename):
                    # The file has not changed
                    self._304()
                    return True

                mediaFileType = 'png'
                if mediaFilename.endswith('.png'):
                    mediaFileType = 'png'
                elif mediaFilename.endswith('.jpg'):
                    mediaFileType = 'jpeg'
                elif mediaFilename.endswith('.webp'):
                    mediaFileType = 'webp'
                elif mediaFilename.endswith('.avif'):
                    mediaFileType = 'avif'
                else:
                    mediaFileType = 'gif'
                with open(mediaFilename, 'rb') as avFile:
                    mediaBinary = avFile.read()
                    self._set_headers_etag(mediaFilename,
                                           'image/' + mediaFileType,
                                           mediaBinary, None,
                                           callingDomain)
                    self._write(mediaBinary)
                self._benchmarkGETtimings(GETstartTime, GETtimings,
                                          'show media done',
                                          'share files shown')
                return True
        self._404()
        return True

    def _showAvatarOrBackground(self, callingDomain: str, path: str,
                                baseDir: str, domain: str,
                                GETstartTime, GETtimings: {}) -> bool:
        """Shows an avatar or profile background image
        """
        if '/users/' in path:
            if self._pathIsImage(path):
                avatarStr = path.split('/users/')[1]
                if '/' in avatarStr and '.temp.' not in path:
                    avatarNickname = avatarStr.split('/')[0]
                    avatarFile = avatarStr.split('/')[1]
                    # remove any numbers, eg. avatar123.png becomes avatar.png
                    if avatarFile.startswith('avatar'):
                        avatarFile = 'avatar.' + avatarFile.split('.')[1]
                    elif avatarFile.startswith('image'):
                        avatarFile = 'image.' + avatarFile.split('.')[1]
                    avatarFilename = \
                        baseDir + '/accounts/' + \
                        avatarNickname + '@' + domain + '/' + avatarFile
                    if os.path.isfile(avatarFilename):
                        if self._etag_exists(avatarFilename):
                            # The file has not changed
                            self._304()
                            return True
                        mediaImageType = 'png'
                        if avatarFile.endswith('.png'):
                            mediaImageType = 'png'
                        elif avatarFile.endswith('.jpg'):
                            mediaImageType = 'jpeg'
                        elif avatarFile.endswith('.gif'):
                            mediaImageType = 'gif'
                        elif avatarFile.endswith('.avif'):
                            mediaImageType = 'avif'
                        else:
                            mediaImageType = 'webp'
                        with open(avatarFilename, 'rb') as avFile:
                            mediaBinary = avFile.read()
                            self._set_headers_etag(avatarFilename,
                                                   'image/' + mediaImageType,
                                                   mediaBinary, None,
                                                   callingDomain)
                            self._write(mediaBinary)
                        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                                  'icon shown done',
                                                  'avatar background shown')
                        return True
        return False

    def _confirmDeleteEvent(self, callingDomain: str, path: str,
                            baseDir: str, httpPrefix: str, cookie: str,
                            translate: {}, domainFull: str,
                            onionDomain: str, i2pDomain: str,
                            GETstartTime, GETtimings: {}) -> bool:
        """Confirm whether to delete a calendar event
        """
        postId = path.split('?id=')[1]
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
        msg = htmlCalendarDeleteConfirm(translate,
                                        baseDir,
                                        path,
                                        httpPrefix,
                                        domainFull,
                                        postId, postTime,
                                        postYear, postMonth, postDay,
                                        callingDomain)
        if not msg:
            actor = \
                httpPrefix + '://' + \
                domainFull + \
                path.split('/eventdelete')[0]
            if callingDomain.endswith('.onion') and onionDomain:
                actor = \
                    'http://' + onionDomain + \
                    path.split('/eventdelete')[0]
            elif callingDomain.endswith('.i2p') and i2pDomain:
                actor = \
                    'http://' + i2pDomain + \
                    path.split('/eventdelete')[0]
            self._redirect_headers(actor + '/calendar',
                                   cookie, callingDomain)
            self._benchmarkGETtimings(GETstartTime, GETtimings,
                                      'calendar shown done',
                                      'calendar delete shown')
            return True
        msg = msg.encode('utf-8')
        self._set_headers('text/html', len(msg),
                          cookie, callingDomain)
        self._write(msg)
        self.server.GETbusy = False
        return True

    def _showNewPost(self, callingDomain: str, path: str,
                     mediaInstance: bool, translate: {},
                     baseDir: str, httpPrefix: str,
                     inReplyToUrl: str, replyToList: [],
                     shareDescription: str, replyPageNumber: int,
                     domain: str, domainFull: str,
                     GETstartTime, GETtimings: {}, cookie) -> bool:
        """Shows the new post screen
        """
        isNewPostEndpoint = False
        if '/users/' in path and '/new' in path:
            # Various types of new post in the web interface
            newPostEnd = ('newpost', 'newblog', 'newunlisted',
                          'newfollowers', 'newdm', 'newreminder',
                          'newevent', 'newreport', 'newquestion',
                          'newshare')
            for postType in newPostEnd:
                if path.endswith('/' + postType):
                    isNewPostEndpoint = True
                    break
        if isNewPostEndpoint:
            nickname = getNicknameFromActor(path)
            msg = htmlNewPost(mediaInstance,
                              translate,
                              baseDir,
                              httpPrefix,
                              path, inReplyToUrl,
                              replyToList,
                              shareDescription,
                              replyPageNumber,
                              nickname, domain,
                              domainFull).encode('utf-8')
            if not msg:
                print('Error replying to ' + inReplyToUrl)
                self._404()
                self.server.GETbusy = False
                return True
            self._set_headers('text/html', len(msg),
                              cookie, callingDomain)
            self._write(msg)
            self.server.GETbusy = False
            self._benchmarkGETtimings(GETstartTime, GETtimings,
                                      'unmute activated done',
                                      'new post made')
            return True
        return False

    def _editProfile(self, callingDomain: str, path: str,
                     translate: {}, baseDir: str,
                     httpPrefix: str, domain: str, port: int,
                     cookie: str) -> bool:
        """Show the edit profile screen
        """
        if '/users/' in path and path.endswith('/editprofile'):
            msg = htmlEditProfile(translate,
                                  baseDir,
                                  path, domain,
                                  port,
                                  httpPrefix).encode('utf-8')
            if msg:
                self._set_headers('text/html', len(msg),
                                  cookie, callingDomain)
                self._write(msg)
            else:
                self._404()
            self.server.GETbusy = False
            return True
        return False

    def _editLinks(self, callingDomain: str, path: str,
                   translate: {}, baseDir: str,
                   httpPrefix: str, domain: str, port: int,
                   cookie: str) -> bool:
        """Show the links from the left column
        """
        if '/users/' in path and path.endswith('/editlinks'):
            msg = htmlEditLinks(translate,
                                baseDir,
                                path, domain,
                                port,
                                httpPrefix).encode('utf-8')
            if msg:
                self._set_headers('text/html', len(msg),
                                  cookie, callingDomain)
                self._write(msg)
            else:
                self._404()
            self.server.GETbusy = False
            return True
        return False

    def _editNewswire(self, callingDomain: str, path: str,
                      translate: {}, baseDir: str,
                      httpPrefix: str, domain: str, port: int,
                      cookie: str) -> bool:
        """Show the newswire from the right column
        """
        if '/users/' in path and path.endswith('/editnewswire'):
            msg = htmlEditNewswire(translate,
                                   baseDir,
                                   path, domain,
                                   port,
                                   httpPrefix).encode('utf-8')
            if msg:
                self._set_headers('text/html', len(msg),
                                  cookie, callingDomain)
                self._write(msg)
            else:
                self._404()
            self.server.GETbusy = False
            return True
        return False

    def _editEvent(self, callingDomain: str, path: str,
                   httpPrefix: str, domain: str, domainFull: str,
                   baseDir: str, translate: {},
                   mediaInstance: bool,
                   cookie: str) -> bool:
        """Show edit event screen
        """
        messageId = path.split('?editeventpost=')[1]
        if '?' in messageId:
            messageId = messageId.split('?')[0]
        actor = path.split('?actor=')[1]
        if '?' in actor:
            actor = actor.split('?')[0]
        nickname = getNicknameFromActor(path)
        if nickname == actor:
            # postUrl = \
            #     httpPrefix + '://' + \
            #     domainFull + '/users/' + nickname + \
            #     '/statuses/' + messageId
            msg = None
            # TODO
            # htmlEditEvent(mediaInstance,
            #               translate,
            #               baseDir,
            #               httpPrefix,
            #               path,
            #               nickname, domain,
            #               postUrl)
            if msg:
                msg = msg.encode('utf-8')
                self._set_headers('text/html', len(msg),
                                  cookie, callingDomain)
                self._write(msg)
                self.server.GETbusy = False
                return True
        return False

    def do_GET(self):
        callingDomain = self.server.domainFull
        if self.headers.get('Host'):
            callingDomain = self.headers['Host']
            if self.server.onionDomain:
                if callingDomain != self.server.domain and \
                   callingDomain != self.server.domainFull and \
                   callingDomain != self.server.onionDomain:
                    print('GET domain blocked: ' + callingDomain)
                    self._400()
                    return
            else:
                if callingDomain != self.server.domain and \
                   callingDomain != self.server.domainFull:
                    print('GET domain blocked: ' + callingDomain)
                    self._400()
                    return

        GETstartTime = time.time()
        GETtimings = {}

        self._benchmarkGETtimings(GETstartTime, GETtimings, None, 'start')

        # Since fediverse crawlers are quite active,
        # make returning info to them high priority
        # get nodeinfo endpoint
        if self._nodeinfo(callingDomain):
            return

        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  'start', '_nodeinfo(callingDomain)')

        # minimal mastodon api
        if self._mastoApi(callingDomain):
            return

        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  '_nodeinfo(callingDomain)',
                                  '_mastoApi(callingDomain)')

        if self.path == '/logout':
            msg = \
                htmlLogin(self.server.translate,
                          self.server.baseDir, False).encode('utf-8')
            self._logout_headers('text/html', len(msg), callingDomain)
            self._write(msg)
            self._benchmarkGETtimings(GETstartTime, GETtimings,
                                      '_nodeinfo(callingDomain)',
                                      'logout')
            return

        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  '_nodeinfo(callingDomain)',
                                  'show logout')

        # replace https://domain/@nick with https://domain/users/nick
        if self.path.startswith('/@'):
            self.path = self.path.replace('/@', '/users/')

        # redirect music to #nowplaying list
        if self.path == '/music' or self.path == '/nowplaying':
            self.path = '/tags/nowplaying'

        if self.server.debug:
            print('DEBUG: GET from ' + self.server.baseDir +
                  ' path: ' + self.path + ' busy: ' +
                  str(self.server.GETbusy))

        if self.server.debug:
            print(str(self.headers))

        cookie = None
        if self.headers.get('Cookie'):
            cookie = self.headers['Cookie']

        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  'show logout', 'get cookie')

        # manifest for progressive web apps
        if '/manifest.json' in self.path:
            self._progressiveWebAppManifest(callingDomain,
                                            GETstartTime, GETtimings)
            return

        # favicon image
        if 'favicon.ico' in self.path:
            self._getFavicon(callingDomain, self.server.baseDir,
                             self.server.debug)
            return

        # check authorization
        authorized = self._isAuthorized()
        if self.server.debug:
            if authorized:
                print('GET Authorization granted')
            else:
                print('GET Not authorized')

        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  'show logout', 'isAuthorized')

        if not self.server.session:
            print('Starting new session during GET')
            self.server.session = createSession(self.server.proxyType)
            if not self.server.session:
                print('ERROR: GET failed to create session duing GET')
                self._404()
                self._benchmarkGETtimings(GETstartTime, GETtimings,
                                          'isAuthorized', 'session fail')
                return

        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  'isAuthorized', 'create session')

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

        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  'create session', 'hasAccept')

        # get fonts
        if '/fonts/' in self.path:
            self._getFonts(callingDomain, self.path,
                           self.server.baseDir, self.server.debug,
                           GETstartTime, GETtimings)
            return

        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  'hasAccept', 'fonts')

        # treat shared inbox paths consistently
        if self.path == '/sharedInbox' or \
           self.path == '/users/inbox' or \
           self.path == '/actor/inbox' or \
           self.path == '/users/'+self.server.domain:
            # if shared inbox is not enabled
            if not self.server.enableSharedInbox:
                self._503()
                return

            self.path = '/inbox'

        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  'fonts', 'sharedInbox enabled')

        if self.path == '/newswire.xml':
            self._getNewswireFeed(authorized,
                                  callingDomain, self.path,
                                  self.server.baseDir,
                                  self.server.httpPrefix,
                                  self.server.domain,
                                  self.server.port,
                                  self.server.proxyType,
                                  GETstartTime, GETtimings,
                                  self.server.debug)
            return

        # RSS 2.0
        if self.path.startswith('/blog/') and \
           self.path.endswith('/rss.xml'):
            self._getRSS2feed(authorized,
                              callingDomain, self.path,
                              self.server.baseDir,
                              self.server.httpPrefix,
                              self.server.domain,
                              self.server.port,
                              self.server.proxyType,
                              GETstartTime, GETtimings,
                              self.server.debug)
            return

        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  'sharedInbox enabled', 'rss2 done')

        # RSS 3.0
        if self.path.startswith('/blog/') and \
           self.path.endswith('/rss.txt'):
            self._getRSS3feed(authorized,
                              callingDomain, self.path,
                              self.server.baseDir,
                              self.server.httpPrefix,
                              self.server.domain,
                              self.server.port,
                              self.server.proxyType,
                              GETstartTime, GETtimings,
                              self.server.debug)
            return

        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  'sharedInbox enabled', 'rss3 done')

        # show the main blog page
        if htmlGET and (self.path == '/blog' or
                        self.path == '/blog/' or
                        self.path == '/blogs' or
                        self.path == '/blogs/'):
            if '/rss.xml' not in self.path:
                if not self.server.session:
                    print('Starting new session during blog view')
                    self.server.session = \
                        createSession(self.server.proxyType)
                    if not self.server.session:
                        print('ERROR: GET failed to create session ' +
                              'during blog view')
                        self._404()
                        return
                msg = htmlBlogView(authorized,
                                   self.server.session,
                                   self.server.baseDir,
                                   self.server.httpPrefix,
                                   self.server.translate,
                                   self.server.domain,
                                   self.server.port,
                                   maxPostsInBlogsFeed)
                if msg is not None:
                    msg = msg.encode('utf-8')
                    self._set_headers('text/html', len(msg),
                                      cookie, callingDomain)
                    self._write(msg)
                    self._benchmarkGETtimings(GETstartTime, GETtimings,
                                              'rss3 done', 'blog view')
                    return
                self._404()
                return

        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  'rss3 done', 'blog view done')

        # show a particular page of blog entries
        # for a particular account
        if htmlGET and self.path.startswith('/blog/'):
            if '/rss.xml' not in self.path:
                if self._showBlogPage(authorized,
                                      callingDomain, self.path,
                                      self.server.baseDir,
                                      self.server.httpPrefix,
                                      self.server.domain,
                                      self.server.domainFull,
                                      self.server.port,
                                      self.server.onionDomain,
                                      self.server.i2pDomain,
                                      GETstartTime, GETtimings,
                                      self.server.proxyType,
                                      cookie, self.server.translate,
                                      self.server.debug):
                    return

        # list of registered devices for e2ee
        # see https://github.com/tootsuite/mastodon/pull/13820
        if authorized and '/users/' in self.path:
            if self.path.endswith('/collections/devices'):
                nickname = self.path.split('/users/')
                if '/' in nickname:
                    nickname = nickname.split('/')[0]
                devJson = E2EEdevicesCollection(self.server.baseDir,
                                                nickname,
                                                self.server.domain,
                                                self.server.domainFull,
                                                self.server.httpPrefix)
                msg = json.dumps(devJson,
                                 ensure_ascii=False).encode('utf-8')
                self._set_headers('application/json',
                                  len(msg),
                                  None, callingDomain)
                self._write(msg)
                self._benchmarkGETtimings(GETstartTime, GETtimings,
                                          'blog page',
                                          'registered devices')
                return

        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  'blog view done',
                                  'registered devices done')

        if htmlGET and '/users/' in self.path:
            # show the person options screen with view/follow/block/report
            if '?options=' in self.path:
                self._showPersonOptions(callingDomain, self.path,
                                        self.server.baseDir,
                                        self.server.httpPrefix,
                                        self.server.domain,
                                        self.server.domainFull,
                                        GETstartTime, GETtimings,
                                        self.server.onionDomain,
                                        self.server.i2pDomain,
                                        cookie, self.server.debug)
                return

            self._benchmarkGETtimings(GETstartTime, GETtimings,
                                      'registered devices done',
                                      'person options done')
            # show blog post
            blogFilename, nickname = \
                self._pathContainsBlogLink(self.server.baseDir,
                                           self.server.httpPrefix,
                                           self.server.domain,
                                           self.server.domainFull,
                                           self.path)
            if blogFilename and nickname:
                postJsonObject = loadJson(blogFilename)
                if isBlogPost(postJsonObject):
                    msg = htmlBlogPost(authorized,
                                       self.server.baseDir,
                                       self.server.httpPrefix,
                                       self.server.translate,
                                       nickname, self.server.domain,
                                       self.server.domainFull,
                                       postJsonObject)
                    if msg is not None:
                        msg = msg.encode('utf-8')
                        self._set_headers('text/html', len(msg),
                                          cookie, callingDomain)
                        self._write(msg)
                        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                                  'person options done',
                                                  'blog post 2')
                        return
                    self._404()
                    return

        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  'person options done',
                                  'blog post 2 done')

        # remove a shared item
        if htmlGET and '?rmshare=' in self.path:
            shareName = self.path.split('?rmshare=')[1]
            shareName = urllib.parse.unquote_plus(shareName.strip())
            usersPath = self.path.split('?rmshare=')[0]
            actor = \
                self.server.httpPrefix + '://' + \
                self.server.domainFull + usersPath
            msg = htmlRemoveSharedItem(self.server.translate,
                                       self.server.baseDir,
                                       actor, shareName,
                                       callingDomain).encode('utf-8')
            if not msg:
                if callingDomain.endswith('.onion') and \
                   self.server.onionDomain:
                    actor = 'http://' + self.server.onionDomain + usersPath
                elif (callingDomain.endswith('.i2p') and
                      self.server.i2pDomain):
                    actor = 'http://' + self.server.i2pDomain + usersPath
                self._redirect_headers(actor + '/tlshares',
                                       cookie, callingDomain)
                return
            self._set_headers('text/html', len(msg),
                              cookie, callingDomain)
            self._write(msg)
            self._benchmarkGETtimings(GETstartTime, GETtimings,
                                      'blog post 2 done',
                                      'remove shared item')
            return

        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  'blog post 2 done',
                                  'remove shared item done')

        if self.path.startswith('/terms'):
            if callingDomain.endswith('.onion') and \
               self.server.onionDomain:
                msg = htmlTermsOfService(self.server.baseDir, 'http',
                                         self.server.onionDomain)
            elif (callingDomain.endswith('.i2p') and
                  self.server.i2pDomain):
                msg = htmlTermsOfService(self.server.baseDir, 'http',
                                         self.server.i2pDomain)
            else:
                msg = htmlTermsOfService(self.server.baseDir,
                                         self.server.httpPrefix,
                                         self.server.domainFull)
            msg = msg.encode('utf-8')
            self._login_headers('text/html', len(msg), callingDomain)
            self._write(msg)
            self._benchmarkGETtimings(GETstartTime, GETtimings,
                                      'blog post 2 done',
                                      'terms of service shown')
            return

        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  'blog post 2 done',
                                  'terms of service done')

        # show a list of who you are following
        if htmlGET and authorized and '/users/' in self.path and \
           self.path.endswith('/followingaccounts'):
            nickname = getNicknameFromActor(self.path)
            followingFilename = \
                self.server.baseDir + '/accounts/' + \
                nickname + '@' + self.server.domain + '/following.txt'
            if not os.path.isfile(followingFilename):
                self._404()
                return
            msg = htmlFollowingList(self.server.baseDir, followingFilename)
            self._login_headers('text/html', len(msg), callingDomain)
            self._write(msg.encode('utf-8'))
            self._benchmarkGETtimings(GETstartTime, GETtimings,
                                      'terms of service done',
                                      'following accounts shown')
            return

        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  'terms of service done',
                                  'following accounts done')

        if self.path.endswith('/about'):
            if callingDomain.endswith('.onion'):
                msg = \
                    htmlAbout(self.server.baseDir, 'http',
                              self.server.onionDomain,
                              None)
            elif callingDomain.endswith('.i2p'):
                msg = \
                    htmlAbout(self.server.baseDir, 'http',
                              self.server.i2pDomain,
                              None)
            else:
                msg = \
                    htmlAbout(self.server.baseDir,
                              self.server.httpPrefix,
                              self.server.domainFull,
                              self.server.onionDomain)
            msg = msg.encode('utf-8')
            self._login_headers('text/html', len(msg), callingDomain)
            self._write(msg)
            self._benchmarkGETtimings(GETstartTime, GETtimings,
                                      'following accounts done',
                                      'show about screen')
            return

        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  'following accounts done',
                                  'show about screen done')

        # send robots.txt if asked
        if self._robotsTxt():
            return

        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  'show about screen done',
                                  'robots txt')

        # if not authorized then show the login screen
        if htmlGET and self.path != '/login' and \
           not self._pathIsImage(self.path) and self.path != '/':
            if self._redirectToLoginScreen(callingDomain, self.path,
                                           self.server.httpPrefix,
                                           self.server.domainFull,
                                           self.server.onionDomain,
                                           self.server.i2pDomain,
                                           GETstartTime, GETtimings,
                                           authorized, self.server.debug):
                return

        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  'robots txt',
                                  'show login screen done')

        # get css
        # Note that this comes before the busy flag to avoid conflicts
        if self.path.endswith('.css'):
            if self._getStyleSheet(callingDomain, self.path,
                                   GETstartTime, GETtimings):
                return

        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  'show login screen done',
                                  'profile.css done')

        # manifest images used to create a home screen icon
        # when selecting "add to home screen" in browsers
        # which support progressive web apps
        if self.path == '/logo72.png' or \
           self.path == '/logo96.png' or \
           self.path == '/logo128.png' or \
           self.path == '/logo144.png' or \
           self.path == '/logo152.png' or \
           self.path == '/logo192.png' or \
           self.path == '/logo256.png' or \
           self.path == '/logo512.png':
            mediaFilename = \
                self.server.baseDir + '/img' + self.path
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
                    except Exception as e:
                        print(e)
                        time.sleep(1)
                        tries += 1
                if mediaBinary:
                    self._set_headers_etag(mediaFilename,
                                           'image/png',
                                           mediaBinary, cookie,
                                           callingDomain)
                    self._write(mediaBinary)
                    self._benchmarkGETtimings(GETstartTime, GETtimings,
                                              'profile.css done',
                                              'manifest logo shown')
                    return
            self._404()
            return

        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  'profile.css done',
                                  'manifest logo done')

        # manifest images used to show example screenshots
        # for use by app stores
        if self.path == '/screenshot1.jpg' or \
           self.path == '/screenshot2.jpg':
            screenFilename = \
                self.server.baseDir + '/img' + self.path
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
                    except Exception as e:
                        print(e)
                        time.sleep(1)
                        tries += 1
                if mediaBinary:
                    self._set_headers_etag(screenFilename,
                                           'image/png',
                                           mediaBinary, cookie,
                                           callingDomain)
                    self._write(mediaBinary)
                    self._benchmarkGETtimings(GETstartTime, GETtimings,
                                              'manifest logo done',
                                              'show screenshot')
                    return
            self._404()
            return

        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  'manifest logo done',
                                  'show screenshot done')

        # image on login screen or qrcode
        if self.path == '/login.png' or \
           self.path == '/login.gif' or \
           self.path == '/login.webp' or \
           self.path == '/login.avif' or \
           self.path == '/login.jpeg' or \
           self.path == '/login.jpg' or \
           self.path == '/qrcode.png':
            iconFilename = \
                self.server.baseDir + '/accounts' + self.path
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
                    except Exception as e:
                        print(e)
                        time.sleep(1)
                        tries += 1
                if mediaBinary:
                    self._set_headers_etag(iconFilename,
                                           'image/png',
                                           mediaBinary, cookie,
                                           callingDomain)
                    self._write(mediaBinary)
                    self._benchmarkGETtimings(GETstartTime, GETtimings,
                                              'show screenshot done',
                                              'login screen logo')
                    return
            self._404()
            return

        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  'show screenshot done',
                                  'login screen logo done')

        # QR code for account handle
        if '/users/' in self.path and \
           self.path.endswith('/qrcode.png'):
            if self._showQRcode(callingDomain, self.path,
                                self.server.baseDir,
                                self.server.domain,
                                self.server.port,
                                GETstartTime, GETtimings):
                return

        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  'login screen logo done',
                                  'account qrcode done')

        # search screen banner image
        if '/users/' in self.path:
            if self.path.endswith('/search_banner.png'):
                if self._searchScreenBanner(callingDomain, self.path,
                                            self.server.baseDir,
                                            self.server.domain,
                                            self.server.port,
                                            GETstartTime, GETtimings):
                    return

            if self.path.endswith('/left_col_image.png'):
                if self._columImage('left', callingDomain, self.path,
                                    self.server.baseDir,
                                    self.server.domain,
                                    self.server.port,
                                    GETstartTime, GETtimings):
                    return

            if self.path.endswith('/right_col_image.png'):
                if self._columImage('right', callingDomain, self.path,
                                    self.server.baseDir,
                                    self.server.domain,
                                    self.server.port,
                                    GETstartTime, GETtimings):
                    return

        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  'account qrcode done',
                                  'search screen banner done')

        if '-background.' in self.path:
            if self._showBackgroundImage(callingDomain, self.path,
                                         self.server.baseDir,
                                         GETstartTime, GETtimings):
                return

        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  'search screen banner done',
                                  'background shown done')

        # emoji images
        if '/emoji/' in self.path:
            self._showEmoji(callingDomain, self.path,
                            self.server.baseDir,
                            GETstartTime, GETtimings)
            return

        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  'background shown done',
                                  'show emoji done')

        # show media
        # Note that this comes before the busy flag to avoid conflicts
        if '/media/' in self.path:
            self._showMedia(callingDomain,
                            self.path, self.server.baseDir,
                            GETstartTime, GETtimings)
            return

        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  'show emoji done',
                                  'show media done')

        # show shared item images
        # Note that this comes before the busy flag to avoid conflicts
        if '/sharefiles/' in self.path:
            if self._showShareImage(callingDomain, self.path,
                                    self.server.baseDir,
                                    GETstartTime, GETtimings):
                return

        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  'show media done',
                                  'share files done')

        # icon images
        # Note that this comes before the busy flag to avoid conflicts
        if self.path.startswith('/icons/'):
            self._showIcon(callingDomain, self.path,
                           self.server.baseDir,
                           GETstartTime, GETtimings)
            return

        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  'show files done',
                                  'icon shown done')

        # cached avatar images
        # Note that this comes before the busy flag to avoid conflicts
        if self.path.startswith('/avatars/'):
            self._showCachedAvatar(callingDomain, self.path,
                                   self.server.baseDir,
                                   GETstartTime, GETtimings)
            return

        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  'icon shown done',
                                  'avatar shown done')

        # show avatar or background image
        # Note that this comes before the busy flag to avoid conflicts
        if self._showAvatarOrBackground(callingDomain, self.path,
                                        self.server.baseDir,
                                        self.server.domain,
                                        GETstartTime, GETtimings):
            return

        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  'icon shown done',
                                  'avatar background shown done')

        # This busy state helps to avoid flooding
        # Resources which are expected to be called from a web page
        # should be above this
        if self.server.GETbusy:
            currTimeGET = int(time.time())
            if currTimeGET - self.server.lastGET == 0:
                if self.server.debug:
                    print('DEBUG: GET Busy')
                self.send_response(429)
                self.end_headers()
                return
            self.server.lastGET = currTimeGET
        self.server.GETbusy = True

        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  'avatar background shown done',
                                  'GET busy time')

        if not self._permittedDir(self.path):
            if self.server.debug:
                print('DEBUG: GET Not permitted')
            self._404()
            self.server.GETbusy = False
            return

        # get webfinger endpoint for a person
        if self._webfinger(callingDomain):
            self.server.GETbusy = False
            self._benchmarkGETtimings(GETstartTime, GETtimings,
                                      'GET busy time',
                                      'webfinger called')
            return

        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  'GET busy time',
                                  'permitted directory')

        if self.path.startswith('/login') or \
           (self.path == '/' and not authorized):
            # request basic auth
            msg = htmlLogin(self.server.translate,
                            self.server.baseDir).encode('utf-8')
            self._login_headers('text/html', len(msg), callingDomain)
            self._write(msg)
            self.server.GETbusy = False
            self._benchmarkGETtimings(GETstartTime, GETtimings,
                                      'permitted directory',
                                      'login shown')
            return

        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  'permitted directory',
                                  'login shown done')

        # hashtag search
        if self.path.startswith('/tags/') or \
           (authorized and '/tags/' in self.path):
            if self.path.startswith('/tags/rss2/'):
                self._hashtagSearchRSS2(callingDomain,
                                        self.path, cookie,
                                        self.server.baseDir,
                                        self.server.httpPrefix,
                                        self.server.domain,
                                        self.server.domainFull,
                                        self.server.port,
                                        self.server.onionDomain,
                                        self.server.i2pDomain,
                                        GETstartTime, GETtimings)
                return
            self._hashtagSearch(callingDomain,
                                self.path, cookie,
                                self.server.baseDir,
                                self.server.httpPrefix,
                                self.server.domain,
                                self.server.domainFull,
                                self.server.port,
                                self.server.onionDomain,
                                self.server.i2pDomain,
                                GETstartTime, GETtimings)
            return

        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  'login shown done',
                                  'hashtag search done')

        # show or hide buttons in the web interface
        if htmlGET and '/users/' in self.path and \
           self.path.endswith('/minimal') and \
           authorized:
            nickname = self.path.split('/users/')[1]
            if '/' in nickname:
                nickname = nickname.split('/')[0]
                self._setMinimal(nickname, not self._isMinimal(nickname))
                if not (self.server.mediaInstance or
                        self.server.blogsInstance or
                        self.server.newsInstance):
                    self.path = '/users/' + nickname + '/inbox'
                else:
                    if self.server.blogsInstance:
                        self.path = '/users/' + nickname + '/tlblogs'
                    elif self.server.mediaInstance:
                        self.path = '/users/' + nickname + '/tlmedia'
                    else:
                        self.path = '/users/' + nickname + '/tlnews'

        # search for a fediverse address, shared item or emoji
        # from the web interface by selecting search icon
        if htmlGET and '/users/' in self.path:
            if self.path.endswith('/search') or \
               '/search?' in self.path:
                if '?' in self.path:
                    self.path = self.path.split('?')[0]
                # show the search screen
                msg = htmlSearch(self.server.translate,
                                 self.server.baseDir, self.path,
                                 self.server.domain).encode('utf-8')
                self._set_headers('text/html', len(msg), cookie, callingDomain)
                self._write(msg)
                self.server.GETbusy = False
                self._benchmarkGETtimings(GETstartTime, GETtimings,
                                          'hashtag search done',
                                          'search screen shown')
                return

        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  'hashtag search done',
                                  'search screen shown done')

        # Show the calendar for a user
        if htmlGET and '/users/' in self.path:
            if '/calendar' in self.path:
                # show the calendar screen
                msg = htmlCalendar(self.server.translate,
                                   self.server.baseDir, self.path,
                                   self.server.httpPrefix,
                                   self.server.domainFull).encode('utf-8')
                self._set_headers('text/html', len(msg), cookie, callingDomain)
                self._write(msg)
                self.server.GETbusy = False
                self._benchmarkGETtimings(GETstartTime, GETtimings,
                                          'search screen shown done',
                                          'calendar shown')
                return

        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  'search screen shown done',
                                  'calendar shown done')

        # Show confirmation for deleting a calendar event
        if htmlGET and '/users/' in self.path:
            if '/eventdelete' in self.path and \
               '?time=' in self.path and \
               '?id=' in self.path:
                if self._confirmDeleteEvent(callingDomain, self.path,
                                            self.server.baseDir,
                                            self.server.httpPrefix,
                                            cookie,
                                            self.server.translate,
                                            self.server.domainFull,
                                            self.server.onionDomain,
                                            self.server.i2pDomain,
                                            GETstartTime, GETtimings):
                    return

        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  'calendar shown done',
                                  'calendar delete shown done')

        # search for emoji by name
        if htmlGET and '/users/' in self.path:
            if self.path.endswith('/searchemoji'):
                # show the search screen
                msg = htmlSearchEmojiTextEntry(self.server.translate,
                                               self.server.baseDir,
                                               self.path).encode('utf-8')
                self._set_headers('text/html', len(msg),
                                  cookie, callingDomain)
                self._write(msg)
                self.server.GETbusy = False
                self._benchmarkGETtimings(GETstartTime, GETtimings,
                                          'calendar delete shown done',
                                          'emoji search shown')
                return

        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  'calendar delete shown done',
                                  'emoji search shown done')

        repeatPrivate = False
        if htmlGET and '?repeatprivate=' in self.path:
            repeatPrivate = True
            self.path = self.path.replace('?repeatprivate=', '?repeat=')
        # announce/repeat button was pressed
        if htmlGET and '?repeat=' in self.path:
            self._announceButton(callingDomain, self.path,
                                 self.server.baseDir,
                                 cookie, self.server.proxyType,
                                 self.server.httpPrefix,
                                 self.server.domain,
                                 self.server.domainFull,
                                 self.server.port,
                                 self.server.onionDomain,
                                 self.server.i2pDomain,
                                 GETstartTime, GETtimings,
                                 repeatPrivate,
                                 self.server.debug)
            return

        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  'emoji search shown done',
                                  'show announce done')

        if htmlGET and '?unrepeatprivate=' in self.path:
            self.path = self.path.replace('?unrepeatprivate=', '?unrepeat=')

        # undo an announce/repeat from the web interface
        if htmlGET and '?unrepeat=' in self.path:
            self._undoAnnounceButton(callingDomain, self.path,
                                     self.server.baseDir,
                                     cookie, self.server.proxyType,
                                     self.server.httpPrefix,
                                     self.server.domain,
                                     self.server.domainFull,
                                     self.server.port,
                                     self.server.onionDomain,
                                     self.server.i2pDomain,
                                     GETstartTime, GETtimings,
                                     repeatPrivate,
                                     self.server.debug)
            return

        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  'show announce done',
                                  'unannounce done')

        # send a newswire moderation vote from the web interface
        if authorized and '/newswirevote=' in self.path and \
           self.path.startswith('/users/'):
            self._newswireVote(callingDomain, self.path,
                               cookie,
                               self.server.baseDir,
                               self.server.httpPrefix,
                               self.server.domain,
                               self.server.domainFull,
                               self.server.port,
                               self.server.onionDomain,
                               self.server.i2pDomain,
                               GETstartTime, GETtimings,
                               self.server.proxyType,
                               self.server.debug,
                               self.server.newswire)
            return

        # send a newswire moderation unvote from the web interface
        if authorized and '/newswireunvote=' in self.path and \
           self.path.startswith('/users/'):
            self._newswireUnvote(callingDomain, self.path,
                                 cookie,
                                 self.server.baseDir,
                                 self.server.httpPrefix,
                                 self.server.domain,
                                 self.server.domainFull,
                                 self.server.port,
                                 self.server.onionDomain,
                                 self.server.i2pDomain,
                                 GETstartTime, GETtimings,
                                 self.server.proxyType,
                                 self.server.debug,
                                 self.server.newswire)
            return

        # send a follow request approval from the web interface
        if authorized and '/followapprove=' in self.path and \
           self.path.startswith('/users/'):
            self._followApproveButton(callingDomain, self.path,
                                      cookie,
                                      self.server.baseDir,
                                      self.server.httpPrefix,
                                      self.server.domain,
                                      self.server.domainFull,
                                      self.server.port,
                                      self.server.onionDomain,
                                      self.server.i2pDomain,
                                      GETstartTime, GETtimings,
                                      self.server.proxyType,
                                      self.server.debug)
            return

        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  'unannounce done',
                                  'follow approve done')

        # deny a follow request from the web interface
        if authorized and '/followdeny=' in self.path and \
           self.path.startswith('/users/'):
            self._followDenyButton(callingDomain, self.path,
                                   cookie,
                                   self.server.baseDir,
                                   self.server.httpPrefix,
                                   self.server.domain,
                                   self.server.domainFull,
                                   self.server.port,
                                   self.server.onionDomain,
                                   self.server.i2pDomain,
                                   GETstartTime, GETtimings,
                                   self.server.proxyType,
                                   self.server.debug)
            return

        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  'follow approve done',
                                  'follow deny done')

        # like from the web interface icon
        if htmlGET and '?like=' in self.path:
            self._likeButton(callingDomain, self.path,
                             self.server.baseDir,
                             self.server.httpPrefix,
                             self.server.domain,
                             self.server.domainFull,
                             self.server.onionDomain,
                             self.server.i2pDomain,
                             GETstartTime, GETtimings,
                             self.server.proxyType,
                             cookie,
                             self.server.debug)
            return

        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  'follow deny done',
                                  'like shown done')

        # undo a like from the web interface icon
        if htmlGET and '?unlike=' in self.path:
            self._undoLikeButton(callingDomain, self.path,
                                 self.server.baseDir,
                                 self.server.httpPrefix,
                                 self.server.domain,
                                 self.server.domainFull,
                                 self.server.onionDomain,
                                 self.server.i2pDomain,
                                 GETstartTime, GETtimings,
                                 self.server.proxyType,
                                 cookie, self.server.debug)
            return

        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  'like shown done',
                                  'unlike shown done')

        # bookmark from the web interface icon
        if htmlGET and '?bookmark=' in self.path:
            self._bookmarkButton(callingDomain, self.path,
                                 self.server.baseDir,
                                 self.server.httpPrefix,
                                 self.server.domain,
                                 self.server.domainFull,
                                 self.server.port,
                                 self.server.onionDomain,
                                 self.server.i2pDomain,
                                 GETstartTime, GETtimings,
                                 self.server.proxyType,
                                 cookie, self.server.debug)
            return

        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  'unlike shown done',
                                  'bookmark shown done')

        # undo a bookmark from the web interface icon
        if htmlGET and '?unbookmark=' in self.path:
            self._undoBookmarkButton(callingDomain, self.path,
                                     self.server.baseDir,
                                     self.server.httpPrefix,
                                     self.server.domain,
                                     self.server.domainFull,
                                     self.server.port,
                                     self.server.onionDomain,
                                     self.server.i2pDomain,
                                     GETstartTime, GETtimings,
                                     self.server.proxyType, cookie,
                                     self.server.debug)
            return

        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  'bookmark shown done',
                                  'unbookmark shown done')

        # delete button is pressed on a post
        if htmlGET and '?delete=' in self.path:
            self._deleteButton(callingDomain, self.path,
                               self.server.baseDir,
                               self.server.httpPrefix,
                               self.server.domain,
                               self.server.domainFull,
                               self.server.port,
                               self.server.onionDomain,
                               self.server.i2pDomain,
                               GETstartTime, GETtimings,
                               self.server.proxyType, cookie,
                               self.server.debug)
            return

        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  'unbookmark shown done',
                                  'delete shown done')

        # The mute button is pressed
        if htmlGET and '?mute=' in self.path:
            self._muteButton(callingDomain, self.path,
                             self.server.baseDir,
                             self.server.httpPrefix,
                             self.server.domain,
                             self.server.domainFull,
                             self.server.port,
                             self.server.onionDomain,
                             self.server.i2pDomain,
                             GETstartTime, GETtimings,
                             self.server.proxyType, cookie,
                             self.server.debug)
            return

        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  'delete shown done',
                                  'post muted done')

        # unmute a post from the web interface icon
        if htmlGET and '?unmute=' in self.path:
            self._undoMuteButton(callingDomain, self.path,
                                 self.server.baseDir,
                                 self.server.httpPrefix,
                                 self.server.domain,
                                 self.server.domainFull,
                                 self.server.port,
                                 self.server.onionDomain,
                                 self.server.i2pDomain,
                                 GETstartTime, GETtimings,
                                 self.server.proxyType, cookie,
                                 self.server.debug)
            return

        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  'post muted done',
                                  'unmute activated done')

        # reply from the web interface icon
        inReplyToUrl = None
#        replyWithDM = False
        replyToList = []
        replyPageNumber = 1
        shareDescription = None
#        replytoActor = None
        if htmlGET:
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
                if '?' in inReplyToUrl:
                    mentionsList = inReplyToUrl.split('?')
                    for m in mentionsList:
                        if m.startswith('mention='):
                            replyHandle = m.replace('mention=', '')
                            if m.replace('mention=', '') not in replyToList:
                                replyToList.append(m.replace('mention=', ''))
                        if m.startswith('page='):
                            replyPageStr = m.replace('page=', '')
                            if replyPageStr.isdigit():
                                replyPageNumber = int(replyPageStr)
#                        if m.startswith('actor='):
#                            replytoActor = m.replace('actor=', '')
                    inReplyToUrl = mentionsList[0]
                    if inReplyToUrl.startswith('sharedesc:'):
                        shareDescription = \
                            inReplyToUrl.replace('sharedesc:', '')
                        shareDescription = \
                            urllib.parse.unquote_plus(shareDescription.strip())
                self.path = self.path.split('?replydm=')[0]+'/newdm'
                if self.server.debug:
                    print('DEBUG: replydm path ' + self.path)

            # Edit a blog post
            if authorized and \
               '/tlblogs' in self.path and \
               '?editblogpost=' in self.path and \
               '?actor=' in self.path:
                messageId = self.path.split('?editblogpost=')[1]
                if '?' in messageId:
                    messageId = messageId.split('?')[0]
                actor = self.path.split('?actor=')[1]
                if '?' in actor:
                    actor = actor.split('?')[0]
                nickname = getNicknameFromActor(self.path)
                if nickname == actor:
                    postUrl = \
                        self.server.httpPrefix + '://' + \
                        self.server.domainFull + '/users/' + nickname + \
                        '/statuses/' + messageId
                    msg = htmlEditBlog(self.server.mediaInstance,
                                       self.server.translate,
                                       self.server.baseDir,
                                       self.server.httpPrefix,
                                       self.path,
                                       replyPageNumber,
                                       nickname, self.server.domain,
                                       postUrl)
                    if msg:
                        msg = msg.encode('utf-8')
                        self._set_headers('text/html', len(msg),
                                          cookie, callingDomain)
                        self._write(msg)
                        self.server.GETbusy = False
                        return

            # Edit an event
            if authorized and \
               '/tlevents' in self.path and \
               '?editeventpost=' in self.path and \
               '?actor=' in self.path:
                if self._editEvent(callingDomain, self.path,
                                   self.server.httpPrefix,
                                   self.server.domain,
                                   self.server.domainFull,
                                   self.server.baseDir,
                                   self.server.translate,
                                   self.server.mediaInstance,
                                   cookie):
                    return

            # edit profile in web interface
            if self._editProfile(callingDomain, self.path,
                                 self.server.translate,
                                 self.server.baseDir,
                                 self.server.httpPrefix,
                                 self.server.domain,
                                 self.server.port,
                                 cookie):
                return

            # edit links from the left column of the timeline in web interface
            if self._editLinks(callingDomain, self.path,
                               self.server.translate,
                               self.server.baseDir,
                               self.server.httpPrefix,
                               self.server.domain,
                               self.server.port,
                               cookie):
                return

            # edit newswire from the right column of the timeline
            if self._editNewswire(callingDomain, self.path,
                                  self.server.translate,
                                  self.server.baseDir,
                                  self.server.httpPrefix,
                                  self.server.domain,
                                  self.server.port,
                                  cookie):
                return

            if self._showNewPost(callingDomain, self.path,
                                 self.server.mediaInstance,
                                 self.server.translate,
                                 self.server.baseDir,
                                 self.server.httpPrefix,
                                 inReplyToUrl, replyToList,
                                 shareDescription, replyPageNumber,
                                 self.server.domain,
                                 self.server.domainFull,
                                 GETstartTime, GETtimings,
                                 cookie):
                return

        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  'unmute activated done',
                                  'new post done')

        # get an individual post from the path /@nickname/statusnumber
        if self._showIndividualAtPost(authorized,
                                      callingDomain, self.path,
                                      self.server.baseDir,
                                      self.server.httpPrefix,
                                      self.server.domain,
                                      self.server.domainFull,
                                      self.server.port,
                                      self.server.onionDomain,
                                      self.server.i2pDomain,
                                      GETstartTime, GETtimings,
                                      self.server.proxyType,
                                      cookie, self.server.debug):
            return

        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  'new post done',
                                  'individual post done')

        # get replies to a post /users/nickname/statuses/number/replies
        if self.path.endswith('/replies') or '/replies?page=' in self.path:
            if self._showRepliesToPost(authorized,
                                       callingDomain, self.path,
                                       self.server.baseDir,
                                       self.server.httpPrefix,
                                       self.server.domain,
                                       self.server.domainFull,
                                       self.server.port,
                                       self.server.onionDomain,
                                       self.server.i2pDomain,
                                       GETstartTime, GETtimings,
                                       self.server.proxyType, cookie,
                                       self.server.debug):
                return

        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  'individual post done',
                                  'post replies done')

        if self.path.endswith('/roles') and '/users/' in self.path:
            if self._showRoles(authorized,
                               callingDomain, self.path,
                               self.server.baseDir,
                               self.server.httpPrefix,
                               self.server.domain,
                               self.server.domainFull,
                               self.server.port,
                               self.server.onionDomain,
                               self.server.i2pDomain,
                               GETstartTime, GETtimings,
                               self.server.proxyType,
                               cookie, self.server.debug):
                return

        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  'post replies done',
                                  'show roles done')

        # show skills on the profile page
        if self.path.endswith('/skills') and '/users/' in self.path:
            if self._showSkills(authorized,
                                callingDomain, self.path,
                                self.server.baseDir,
                                self.server.httpPrefix,
                                self.server.domain,
                                self.server.domainFull,
                                self.server.port,
                                self.server.onionDomain,
                                self.server.i2pDomain,
                                GETstartTime, GETtimings,
                                self.server.proxyType,
                                cookie, self.server.debug):
                return

        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  'post roles done',
                                  'show skills done')

        # get an individual post from the path
        # /users/nickname/statuses/number
        if '/statuses/' in self.path and '/users/' in self.path:
            if self._showIndividualPost(authorized,
                                        callingDomain, self.path,
                                        self.server.baseDir,
                                        self.server.httpPrefix,
                                        self.server.domain,
                                        self.server.domainFull,
                                        self.server.port,
                                        self.server.onionDomain,
                                        self.server.i2pDomain,
                                        GETstartTime, GETtimings,
                                        self.server.proxyType,
                                        cookie, self.server.debug):
                return

        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  'show skills done',
                                  'show status done')

        # get the inbox timeline for a given person
        if self.path.endswith('/inbox') or '/inbox?page=' in self.path:
            if self._showInbox(authorized,
                               callingDomain, self.path,
                               self.server.baseDir,
                               self.server.httpPrefix,
                               self.server.domain,
                               self.server.domainFull,
                               self.server.port,
                               self.server.onionDomain,
                               self.server.i2pDomain,
                               GETstartTime, GETtimings,
                               self.server.proxyType,
                               cookie, self.server.debug,
                               self.server.recentPostsCache,
                               self.server.session,
                               self.server.defaultTimeline,
                               self.server.maxRecentPosts,
                               self.server.translate,
                               self.server.cachedWebfingers,
                               self.server.personCache,
                               self.server.allowDeletion,
                               self.server.projectVersion,
                               self.server.YTReplacementDomain):
                return

        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  'show status done',
                                  'show inbox done')

        # get the direct messages timeline for a given person
        if self.path.endswith('/dm') or '/dm?page=' in self.path:
            if self._showDMs(authorized,
                             callingDomain, self.path,
                             self.server.baseDir,
                             self.server.httpPrefix,
                             self.server.domain,
                             self.server.domainFull,
                             self.server.port,
                             self.server.onionDomain,
                             self.server.i2pDomain,
                             GETstartTime, GETtimings,
                             self.server.proxyType,
                             cookie, self.server.debug):
                return

        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  'show inbox done',
                                  'show dms done')

        # get the replies timeline for a given person
        if self.path.endswith('/tlreplies') or '/tlreplies?page=' in self.path:
            if self._showReplies(authorized,
                                 callingDomain, self.path,
                                 self.server.baseDir,
                                 self.server.httpPrefix,
                                 self.server.domain,
                                 self.server.domainFull,
                                 self.server.port,
                                 self.server.onionDomain,
                                 self.server.i2pDomain,
                                 GETstartTime, GETtimings,
                                 self.server.proxyType,
                                 cookie, self.server.debug):
                return

        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  'show dms done',
                                  'show replies 2 done')

        # get the media timeline for a given person
        if self.path.endswith('/tlmedia') or '/tlmedia?page=' in self.path:
            if self._showMediaTimeline(authorized,
                                       callingDomain, self.path,
                                       self.server.baseDir,
                                       self.server.httpPrefix,
                                       self.server.domain,
                                       self.server.domainFull,
                                       self.server.port,
                                       self.server.onionDomain,
                                       self.server.i2pDomain,
                                       GETstartTime, GETtimings,
                                       self.server.proxyType,
                                       cookie, self.server.debug):
                return

        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  'show replies 2 done',
                                  'show media 2 done')

        # get the blogs for a given person
        if self.path.endswith('/tlblogs') or '/tlblogs?page=' in self.path:
            if self._showBlogsTimeline(authorized,
                                       callingDomain, self.path,
                                       self.server.baseDir,
                                       self.server.httpPrefix,
                                       self.server.domain,
                                       self.server.domainFull,
                                       self.server.port,
                                       self.server.onionDomain,
                                       self.server.i2pDomain,
                                       GETstartTime, GETtimings,
                                       self.server.proxyType,
                                       cookie, self.server.debug):
                return

        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  'show media 2 done',
                                  'show blogs 2 done')

        # get the shared items timeline for a given person
        if self.path.endswith('/tlshares') or '/tlshares?page=' in self.path:
            if self._showSharesTimeline(authorized,
                                        callingDomain, self.path,
                                        self.server.baseDir,
                                        self.server.httpPrefix,
                                        self.server.domain,
                                        self.server.domainFull,
                                        self.server.port,
                                        self.server.onionDomain,
                                        self.server.i2pDomain,
                                        GETstartTime, GETtimings,
                                        self.server.proxyType,
                                        cookie, self.server.debug):
                return

        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  'show blogs 2 done',
                                  'show shares 2 done')

        # get the bookmarks timeline for a given person
        if self.path.endswith('/tlbookmarks') or \
           '/tlbookmarks?page=' in self.path or \
           self.path.endswith('/bookmarks') or \
           '/bookmarks?page=' in self.path:
            if self._showBookmarksTimeline(authorized,
                                           callingDomain, self.path,
                                           self.server.baseDir,
                                           self.server.httpPrefix,
                                           self.server.domain,
                                           self.server.domainFull,
                                           self.server.port,
                                           self.server.onionDomain,
                                           self.server.i2pDomain,
                                           GETstartTime, GETtimings,
                                           self.server.proxyType,
                                           cookie, self.server.debug):
                return

        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  'show shares 2 done',
                                  'show bookmarks 2 done')

        # get the events for a given person
        if self.path.endswith('/tlevents') or \
           '/tlevents?page=' in self.path or \
           self.path.endswith('/events') or \
           '/events?page=' in self.path:
            if self._showEventsTimeline(authorized,
                                        callingDomain, self.path,
                                        self.server.baseDir,
                                        self.server.httpPrefix,
                                        self.server.domain,
                                        self.server.domainFull,
                                        self.server.port,
                                        self.server.onionDomain,
                                        self.server.i2pDomain,
                                        GETstartTime, GETtimings,
                                        self.server.proxyType,
                                        cookie, self.server.debug):
                return

        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  'show bookmarks 2 done',
                                  'show events done')

        # outbox timeline
        if self._showOutboxTimeline(authorized,
                                    callingDomain, self.path,
                                    self.server.baseDir,
                                    self.server.httpPrefix,
                                    self.server.domain,
                                    self.server.domainFull,
                                    self.server.port,
                                    self.server.onionDomain,
                                    self.server.i2pDomain,
                                    GETstartTime, GETtimings,
                                    self.server.proxyType,
                                    cookie, self.server.debug):
            return

        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  'show events done',
                                  'show outbox done')

        # get the moderation feed for a moderator
        if self.path.endswith('/moderation') or \
           '/moderation?page=' in self.path:
            if self._showModTimeline(authorized,
                                     callingDomain, self.path,
                                     self.server.baseDir,
                                     self.server.httpPrefix,
                                     self.server.domain,
                                     self.server.domainFull,
                                     self.server.port,
                                     self.server.onionDomain,
                                     self.server.i2pDomain,
                                     GETstartTime, GETtimings,
                                     self.server.proxyType,
                                     cookie, self.server.debug):
                return

        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  'show outbox done',
                                  'show moderation done')

        if self._showSharesFeed(authorized,
                                callingDomain, self.path,
                                self.server.baseDir,
                                self.server.httpPrefix,
                                self.server.domain,
                                self.server.domainFull,
                                self.server.port,
                                self.server.onionDomain,
                                self.server.i2pDomain,
                                GETstartTime, GETtimings,
                                self.server.proxyType,
                                cookie, self.server.debug):
            return

        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  'show moderation done',
                                  'show profile 2 done')

        if self._showFollowingFeed(authorized,
                                   callingDomain, self.path,
                                   self.server.baseDir,
                                   self.server.httpPrefix,
                                   self.server.domain,
                                   self.server.domainFull,
                                   self.server.port,
                                   self.server.onionDomain,
                                   self.server.i2pDomain,
                                   GETstartTime, GETtimings,
                                   self.server.proxyType,
                                   cookie, self.server.debug):
            return

        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  'show profile 2 done',
                                  'show profile 3 done')

        if self._showFollowersFeed(authorized,
                                   callingDomain, self.path,
                                   self.server.baseDir,
                                   self.server.httpPrefix,
                                   self.server.domain,
                                   self.server.domainFull,
                                   self.server.port,
                                   self.server.onionDomain,
                                   self.server.i2pDomain,
                                   GETstartTime, GETtimings,
                                   self.server.proxyType,
                                   cookie, self.server.debug):
            return

        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  'show profile 3 done',
                                  'show profile 4 done')

        # look up a person
        if self._showPersonProfile(authorized,
                                   callingDomain, self.path,
                                   self.server.baseDir,
                                   self.server.httpPrefix,
                                   self.server.domain,
                                   self.server.domainFull,
                                   self.server.port,
                                   self.server.onionDomain,
                                   self.server.i2pDomain,
                                   GETstartTime, GETtimings,
                                   self.server.proxyType,
                                   cookie, self.server.debug):
            return

        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  'show profile 4 done',
                                  'show profile posts done')

        # check that a json file was requested
        if not self.path.endswith('.json'):
            if self.server.debug:
                print('DEBUG: GET Not json: ' + self.path +
                      ' ' + self.server.baseDir)
            self._404()
            self.server.GETbusy = False
            return

        if not self._fetchAuthenticated():
            if self.server.debug:
                print('WARN: Unauthenticated GET')
            self._404()
            self.server.GETbusy = False
            return

        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  'show profile posts done',
                                  'authenticated fetch')

        # check that the file exists
        filename = self.server.baseDir + self.path
        if os.path.isfile(filename):
            with open(filename, 'r', encoding='utf-8') as File:
                content = File.read()
                contentJson = json.loads(content)
                msg = json.dumps(contentJson,
                                 ensure_ascii=False).encode('utf-8')
                self._set_headers('application/json',
                                  len(msg),
                                  None, callingDomain)
                self._write(msg)
                self._benchmarkGETtimings(GETstartTime, GETtimings,
                                          'authenticated fetch',
                                          'arbitrary json')
        else:
            if self.server.debug:
                print('DEBUG: GET Unknown file')
            self._404()
        self.server.GETbusy = False

        self._benchmarkGETtimings(GETstartTime, GETtimings,
                                  'arbitrary json', 'end benchmarks')

    def do_HEAD(self):
        callingDomain = self.server.domainFull
        if self.headers.get('Host'):
            callingDomain = self.headers['Host']
            if self.server.onionDomain:
                if callingDomain != self.server.domain and \
                   callingDomain != self.server.domainFull and \
                   callingDomain != self.server.onionDomain:
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
            if self._pathIsImage(self.path) or \
               self._pathIsVideo(self.path) or \
               self._pathIsAudio(self.path):
                mediaStr = self.path.split('/media/')[1]
                mediaFilename = \
                    self.server.baseDir + '/media/' + mediaStr
                if os.path.isfile(mediaFilename):
                    checkPath = mediaFilename
                    fileLength = os.path.getsize(mediaFilename)
                    mediaTagFilename = mediaFilename + '.etag'
                    if os.path.isfile(mediaTagFilename):
                        try:
                            with open(mediaTagFilename, 'r') as etagFile:
                                etag = etagFile.read()
                        except BaseException:
                            pass
                    else:
                        with open(mediaFilename, 'rb') as avFile:
                            mediaBinary = avFile.read()
                            etag = sha1(mediaBinary).hexdigest()  # nosec
                            try:
                                with open(mediaTagFilename, 'w+') as etagFile:
                                    etagFile.write(etag)
                            except BaseException:
                                pass

        mediaFileType = 'application/json'
        if checkPath.endswith('.png'):
            mediaFileType = 'image/png'
        elif checkPath.endswith('.jpg'):
            mediaFileType = 'image/jpeg'
        elif checkPath.endswith('.gif'):
            mediaFileType = 'image/gif'
        elif checkPath.endswith('.webp'):
            mediaFileType = 'image/webp'
        elif checkPath.endswith('.avif'):
            mediaFileType = 'image/avif'
        elif checkPath.endswith('.mp4'):
            mediaFileType = 'video/mp4'
        elif checkPath.endswith('.ogv'):
            mediaFileType = 'video/ogv'
        elif checkPath.endswith('.mp3'):
            mediaFileType = 'audio/mpeg'
        elif checkPath.endswith('.ogg'):
            mediaFileType = 'audio/ogg'

        self._set_headers_head(mediaFileType, fileLength,
                               etag, callingDomain)

    def _receiveNewPostProcess(self, postType: str, path: str, headers: {},
                               length: int, postBytes, boundary: str,
                               callingDomain: str, cookie: str,
                               authorized: bool) -> int:
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
                      headers['Content-Type'])
            nickname = None
            nicknameStr = path.split('/users/')[1]
            if '/' in nicknameStr:
                nickname = nicknameStr.split('/')[0]
            else:
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
                self.server.baseDir + '/accounts/' + \
                nickname + '@' + self.server.domain + '/upload.temp'

            filename, attachmentMediaType = \
                saveMediaInFormPOST(mediaBytes, self.server.debug,
                                    filenameBase)
            if self.server.debug:
                if filename:
                    print('DEBUG: POST media filename is ' + filename)
                else:
                    print('DEBUG: no media filename in POST')

            if filename:
                if filename.endswith('.png') or \
                   filename.endswith('.jpg') or \
                   filename.endswith('.webp') or \
                   filename.endswith('.avif') or \
                   filename.endswith('.gif'):
                    if self.server.debug:
                        print('DEBUG: POST media removing metadata')
                    postImageFilename = filename.replace('.temp', '')
                    removeMetaData(filename, postImageFilename)
                    if os.path.isfile(postImageFilename):
                        print('POST media saved to ' + postImageFilename)
                    else:
                        print('ERROR: POST media could not be saved to ' +
                              postImageFilename)
                else:
                    if os.path.isfile(filename):
                        os.rename(filename, filename.replace('.temp', ''))

            fields = \
                extractTextFieldsInPOST(postBytes, boundary,
                                        self.server.debug)
            if self.server.debug:
                if fields:
                    print('DEBUG: text field extracted from POST ' +
                          str(fields))
                else:
                    print('WARN: no text fields could be extracted from POST')

            # process the received text fields from the POST
            if not fields.get('message') and \
               not fields.get('imageDescription'):
                return -1
            if fields.get('submitPost'):
                if fields['submitPost'] != 'Submit':
                    return -1
            else:
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

            # Store a file which contains the time in seconds
            # since epoch when an attempt to post something was made.
            # This is then used for active monthly users counts
            lastUsedFilename = \
                self.server.baseDir + '/accounts/' + \
                nickname + '@' + self.server.domain + '/.lastUsed'
            try:
                lastUsedFile = open(lastUsedFilename, 'w+')
                if lastUsedFile:
                    lastUsedFile.write(str(int(time.time())))
                    lastUsedFile.close()
            except BaseException:
                pass

            mentionsStr = ''
            if fields.get('mentions'):
                mentionsStr = fields['mentions'].strip() + ' '
            if not fields.get('commentsEnabled'):
                commentsEnabled = False
            else:
                commentsEnabled = True
            if not fields.get('privateEvent'):
                privateEvent = False
            else:
                privateEvent = True

            if postType == 'newpost':
                messageJson = \
                    createPublicPost(self.server.baseDir,
                                     nickname,
                                     self.server.domain,
                                     self.server.port,
                                     self.server.httpPrefix,
                                     mentionsStr + fields['message'],
                                     False, False, False, commentsEnabled,
                                     filename, attachmentMediaType,
                                     fields['imageDescription'],
                                     self.server.useBlurHash,
                                     fields['replyTo'], fields['replyTo'],
                                     fields['subject'], fields['schedulePost'],
                                     fields['eventDate'], fields['eventTime'],
                                     fields['location'])
                if messageJson:
                    if fields['schedulePost']:
                        return 1

                    if self._postToOutbox(messageJson, __version__, nickname):
                        populateReplies(self.server.baseDir,
                                        self.server.httpPrefix,
                                        self.server.domainFull,
                                        messageJson,
                                        self.server.maxReplies,
                                        self.server.debug)
                        return 1
                    else:
                        return -1
            elif postType == 'newblog':
                messageJson = \
                    createBlogPost(self.server.baseDir, nickname,
                                   self.server.domain, self.server.port,
                                   self.server.httpPrefix,
                                   fields['message'],
                                   False, False, False, commentsEnabled,
                                   filename, attachmentMediaType,
                                   fields['imageDescription'],
                                   self.server.useBlurHash,
                                   fields['replyTo'], fields['replyTo'],
                                   fields['subject'], fields['schedulePost'],
                                   fields['eventDate'], fields['eventTime'],
                                   fields['location'])
                if messageJson:
                    if fields['schedulePost']:
                        return 1
                    if self._postToOutbox(messageJson, __version__, nickname):
                        populateReplies(self.server.baseDir,
                                        self.server.httpPrefix,
                                        self.server.domainFull,
                                        messageJson,
                                        self.server.maxReplies,
                                        self.server.debug)
                        return 1
                    else:
                        return -1
            elif postType == 'editblogpost':
                print('Edited blog post received')
                postFilename = \
                    locatePost(self.server.baseDir,
                               nickname, self.server.domain,
                               fields['postUrl'])
                if os.path.isfile(postFilename):
                    postJsonObject = loadJson(postFilename)
                    if postJsonObject:
                        cachedFilename = \
                            self.server.baseDir + '/accounts/' + \
                            nickname + '@' + self.server.domain + \
                            '/postcache/' + \
                            fields['postUrl'].replace('/', '#') + '.html'
                        if os.path.isfile(cachedFilename):
                            print('Edited blog post, removing cached html')
                            try:
                                os.remove(cachedFilename)
                            except BaseException:
                                pass
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
                            addHtmlTags(self.server.baseDir,
                                        self.server.httpPrefix,
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
                            replaceEmojiFromTags(fields['message'],
                                                 tags, 'content')

                        postJsonObject['object']['content'] = fields['message']

                        imgDescription = ''
                        if fields.get('imageDescription'):
                            imgDescription = fields['imageDescription']

                        if filename:
                            postJsonObject['object'] = \
                                attachMedia(self.server.baseDir,
                                            self.server.httpPrefix,
                                            self.server.domain,
                                            self.server.port,
                                            postJsonObject['object'],
                                            filename,
                                            attachmentMediaType,
                                            imgDescription,
                                            self.server.useBlurHash)

                        replaceYouTube(postJsonObject,
                                       self.server.YTReplacementDomain)
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
                messageJson = \
                    createUnlistedPost(self.server.baseDir,
                                       nickname,
                                       self.server.domain, self.server.port,
                                       self.server.httpPrefix,
                                       mentionsStr + fields['message'],
                                       False, False, False, commentsEnabled,
                                       filename, attachmentMediaType,
                                       fields['imageDescription'],
                                       self.server.useBlurHash,
                                       fields['replyTo'],
                                       fields['replyTo'],
                                       fields['subject'],
                                       fields['schedulePost'],
                                       fields['eventDate'],
                                       fields['eventTime'],
                                       fields['location'])
                if messageJson:
                    if fields['schedulePost']:
                        return 1
                    if self._postToOutbox(messageJson, __version__, nickname):
                        populateReplies(self.server.baseDir,
                                        self.server.httpPrefix,
                                        self.server.domain,
                                        messageJson,
                                        self.server.maxReplies,
                                        self.server.debug)
                        return 1
                    else:
                        return -1
            elif postType == 'newfollowers':
                messageJson = \
                    createFollowersOnlyPost(self.server.baseDir,
                                            nickname,
                                            self.server.domain,
                                            self.server.port,
                                            self.server.httpPrefix,
                                            mentionsStr + fields['message'],
                                            True, False, False,
                                            commentsEnabled,
                                            filename, attachmentMediaType,
                                            fields['imageDescription'],
                                            self.server.useBlurHash,
                                            fields['replyTo'],
                                            fields['replyTo'],
                                            fields['subject'],
                                            fields['schedulePost'],
                                            fields['eventDate'],
                                            fields['eventTime'],
                                            fields['location'])
                if messageJson:
                    if fields['schedulePost']:
                        return 1
                    if self._postToOutbox(messageJson, __version__, nickname):
                        populateReplies(self.server.baseDir,
                                        self.server.httpPrefix,
                                        self.server.domain,
                                        messageJson,
                                        self.server.maxReplies,
                                        self.server.debug)
                        return 1
                    else:
                        return -1
            elif postType == 'newevent':
                # A Mobilizon-type event is posted

                # if there is no image dscription then make it the same
                # as the event title
                if not fields.get('imageDescription'):
                    fields['imageDescription'] = fields['subject']
                # Events are public by default, with opt-in
                # followers only status
                if not fields.get('followersOnlyEvent'):
                    fields['followersOnlyEvent'] = False

                if not fields.get('anonymousParticipationEnabled'):
                    anonymousParticipationEnabled = False
                else:
                    anonymousParticipationEnabled = True
                maximumAttendeeCapacity = 999999
                if fields.get('maximumAttendeeCapacity'):
                    maximumAttendeeCapacity = \
                        int(fields['maximumAttendeeCapacity'])

                messageJson = \
                    createEventPost(self.server.baseDir,
                                    nickname,
                                    self.server.domain,
                                    self.server.port,
                                    self.server.httpPrefix,
                                    mentionsStr + fields['message'],
                                    privateEvent,
                                    False, False, commentsEnabled,
                                    filename, attachmentMediaType,
                                    fields['imageDescription'],
                                    self.server.useBlurHash,
                                    fields['subject'],
                                    fields['schedulePost'],
                                    fields['eventDate'],
                                    fields['eventTime'],
                                    fields['location'],
                                    fields['category'],
                                    fields['joinMode'],
                                    fields['endDate'],
                                    fields['endTime'],
                                    maximumAttendeeCapacity,
                                    fields['repliesModerationOption'],
                                    anonymousParticipationEnabled,
                                    fields['eventStatus'],
                                    fields['ticketUrl'])
                if messageJson:
                    if fields['schedulePost']:
                        return 1
                    if self._postToOutbox(messageJson, __version__, nickname):
                        return 1
                    else:
                        return -1
            elif postType == 'newdm':
                messageJson = None
                print('A DM was posted')
                if '@' in mentionsStr:
                    messageJson = \
                        createDirectMessagePost(self.server.baseDir,
                                                nickname,
                                                self.server.domain,
                                                self.server.port,
                                                self.server.httpPrefix,
                                                mentionsStr +
                                                fields['message'],
                                                True, False, False,
                                                commentsEnabled,
                                                filename, attachmentMediaType,
                                                fields['imageDescription'],
                                                self.server.useBlurHash,
                                                fields['replyTo'],
                                                fields['replyTo'],
                                                fields['subject'],
                                                True, fields['schedulePost'],
                                                fields['eventDate'],
                                                fields['eventTime'],
                                                fields['location'])
                if messageJson:
                    if fields['schedulePost']:
                        return 1
                    print('Sending new DM to ' +
                          str(messageJson['object']['to']))
                    if self._postToOutbox(messageJson, __version__, nickname):
                        populateReplies(self.server.baseDir,
                                        self.server.httpPrefix,
                                        self.server.domain,
                                        messageJson,
                                        self.server.maxReplies,
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
                messageJson = \
                    createDirectMessagePost(self.server.baseDir,
                                            nickname,
                                            self.server.domain,
                                            self.server.port,
                                            self.server.httpPrefix,
                                            mentionsStr + fields['message'],
                                            True, False, False, False,
                                            filename, attachmentMediaType,
                                            fields['imageDescription'],
                                            self.server.useBlurHash,
                                            None, None,
                                            fields['subject'],
                                            True, fields['schedulePost'],
                                            fields['eventDate'],
                                            fields['eventTime'],
                                            fields['location'])
                if messageJson:
                    if fields['schedulePost']:
                        return 1
                    print('DEBUG: new reminder to ' +
                          str(messageJson['object']['to']))
                    if self._postToOutbox(messageJson, __version__, nickname):
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
                messageJson = \
                    createReportPost(self.server.baseDir,
                                     nickname,
                                     self.server.domain, self.server.port,
                                     self.server.httpPrefix,
                                     mentionsStr + fields['message'],
                                     True, False, False, True,
                                     filename, attachmentMediaType,
                                     fields['imageDescription'],
                                     self.server.useBlurHash,
                                     self.server.debug, fields['subject'])
                if messageJson:
                    if self._postToOutbox(messageJson, __version__, nickname):
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
                messageJson = \
                    createQuestionPost(self.server.baseDir,
                                       nickname,
                                       self.server.domain,
                                       self.server.port,
                                       self.server.httpPrefix,
                                       fields['message'], qOptions,
                                       False, False, False,
                                       commentsEnabled,
                                       filename, attachmentMediaType,
                                       fields['imageDescription'],
                                       self.server.useBlurHash,
                                       fields['subject'],
                                       int(fields['duration']))
                if messageJson:
                    if self.server.debug:
                        print('DEBUG: new Question')
                    if self._postToOutbox(messageJson, __version__, nickname):
                        return 1
                return -1
            elif postType == 'newshare':
                if not fields.get('itemType'):
                    return -1
                if not fields.get('category'):
                    return -1
                if not fields.get('location'):
                    return -1
                if not fields.get('duration'):
                    return -1
                if attachmentMediaType:
                    if attachmentMediaType != 'image':
                        return -1
                durationStr = fields['duration']
                if durationStr:
                    if ' ' not in durationStr:
                        durationStr = durationStr + ' days'
                addShare(self.server.baseDir,
                         self.server.httpPrefix,
                         nickname,
                         self.server.domain, self.server.port,
                         fields['subject'],
                         fields['message'],
                         filename,
                         fields['itemType'],
                         fields['category'],
                         fields['location'],
                         durationStr,
                         self.server.debug)
                if filename:
                    if os.path.isfile(filename):
                        os.remove(filename)
                self.postToNickname = nickname
                return 1
        return -1

    def _receiveNewPost(self, postType: str, path: str,
                        callingDomain: str, cookie: str,
                        authorized: bool) -> int:
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
            while (self.server.newPostThread[newPostThreadName].isAlive() and
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
                except SocketError as e:
                    if e.errno == errno.ECONNRESET:
                        print('WARN: POST postBytes ' +
                              'connection reset by peer')
                    else:
                        print('WARN: POST postBytes socket error')
                    return None
                except ValueError as e:
                    print('ERROR: POST postBytes rfile.read failed')
                    print(e)
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
                                            authorized)
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
        except SocketError as e:
            if e.errno == errno.ECONNRESET:
                print('WARN: handle POST messageBytes ' +
                      'connection reset by peer')
            else:
                print('WARN: handle POST messageBytes socket error')
            return {}
        except ValueError as e:
            print('ERROR: handle POST messageBytes rfile.read failed')
            print(e)
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
        except SocketError as e:
            if e.errno == errno.ECONNRESET:
                print('WARN: POST messageBytes ' +
                      'connection reset by peer')
            else:
                print('WARN: POST messageBytes socket error')
            return {}
        except ValueError as e:
            print('ERROR: POST messageBytes rfile.read failed')
            print(e)
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
            personDir = self.server.baseDir + '/accounts/' + handle
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
            # return the list of devices for this handle
            msg = \
                json.dumps(devicesList,
                           ensure_ascii=False).encode('utf-8')
            self._set_headers('application/json',
                              len(msg),
                              None, callingDomain)
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
                E2EEaddDevice(self.server.baseDir,
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
        POSTtimings = []

        if not self.server.session:
            print('Starting new session from POST')
            self.server.session = \
                createSession(self.server.proxyType)
            if not self.server.session:
                print('ERROR: POST failed to create session during POST')
                self._404()
                return

        if self.server.debug:
            print('DEBUG: POST to ' + self.server.baseDir +
                  ' path: ' + self.path + ' busy: ' +
                  str(self.server.POSTbusy))
        if self.server.POSTbusy:
            currTimePOST = int(time.time())
            if currTimePOST - self.server.lastPOST == 0:
                self.send_response(429)
                self.end_headers()
                return
            self.server.lastPOST = currTimePOST

        callingDomain = self.server.domainFull
        if self.headers.get('Host'):
            callingDomain = self.headers['Host']
            if self.server.onionDomain:
                if callingDomain != self.server.domain and \
                   callingDomain != self.server.domainFull and \
                   callingDomain != self.server.onionDomain:
                    print('POST domain blocked: ' + callingDomain)
                    self._400()
                    return
            else:
                if callingDomain != self.server.domain and \
                   callingDomain != self.server.domainFull:
                    print('POST domain blocked: ' + callingDomain)
                    self._400()
                    return

        self.server.POSTbusy = True
        if not self.headers.get('Content-type'):
            print('Content-type header missing')
            self._400()
            self.server.POSTbusy = False
            return

        # remove any trailing slashes from the path
        if not self.path.endswith('confirm'):
            self.path = self.path.replace('/outbox/', '/outbox')
            self.path = self.path.replace('/tlblogs/', '/tlblogs')
            self.path = self.path.replace('/tlevents/', '/tlevents')
            self.path = self.path.replace('/inbox/', '/inbox')
            self.path = self.path.replace('/shares/', '/shares')
            self.path = self.path.replace('/sharedInbox/', '/sharedInbox')

        if self.path == '/inbox':
            if not self.server.enableSharedInbox:
                self._503()
                self.server.POSTbusy = False
                return

        cookie = None
        if self.headers.get('Cookie'):
            cookie = self.headers['Cookie']

        # check authorization
        authorized = self._isAuthorized()
        if not authorized:
            print('POST Not authorized')
            print(str(self.headers))

        if self.path.startswith('/api/v1/crypto/'):
            self._cryptoAPI(self.path, authorized)
            self.server.POSTbusy = False
            return

        # if this is a POST to the outbox then check authentication
        self.outboxAuthenticated = False
        self.postToNickname = None

        self._benchmarkPOSTtimings(POSTstartTime, POSTtimings, 1)

        # login screen
        if self.path.startswith('/login'):
            self._loginScreen(self.path, callingDomain, cookie,
                              self.server.baseDir, self.server.httpPrefix,
                              self.server.domain, self.server.domainFull,
                              self.server.port,
                              self.server.onionDomain, self.server.i2pDomain,
                              self.server.debug)
            return

        self._benchmarkPOSTtimings(POSTstartTime, POSTtimings, 2)

        # update of profile/avatar from web interface,
        # after selecting Edit button then Submit
        if authorized and self.path.endswith('/profiledata'):
            self._profileUpdate(callingDomain, cookie, authorized, self.path,
                                self.server.baseDir, self.server.httpPrefix,
                                self.server.domain,
                                self.server.domainFull,
                                self.server.onionDomain,
                                self.server.i2pDomain, self.server.debug)
            return

        if authorized and self.path.endswith('/linksdata'):
            self._linksUpdate(callingDomain, cookie, authorized, self.path,
                              self.server.baseDir, self.server.httpPrefix,
                              self.server.domain,
                              self.server.domainFull,
                              self.server.onionDomain,
                              self.server.i2pDomain, self.server.debug,
                              self.server.defaultTimeline)
            return

        if authorized and self.path.endswith('/newswiredata'):
            self._newswireUpdate(callingDomain, cookie, authorized, self.path,
                                 self.server.baseDir, self.server.httpPrefix,
                                 self.server.domain,
                                 self.server.domainFull,
                                 self.server.onionDomain,
                                 self.server.i2pDomain, self.server.debug,
                                 self.server.defaultTimeline)
            return

        self._benchmarkPOSTtimings(POSTstartTime, POSTtimings, 3)

        # moderator action buttons
        if authorized and '/users/' in self.path and \
           self.path.endswith('/moderationaction'):
            self._moderatorActions(self.path, callingDomain, cookie,
                                   self.server.baseDir,
                                   self.server.httpPrefix,
                                   self.server.domain,
                                   self.server.domainFull,
                                   self.server.port,
                                   self.server.onionDomain,
                                   self.server.i2pDomain,
                                   self.server.debug)
            return

        self._benchmarkPOSTtimings(POSTstartTime, POSTtimings, 4)

        searchForEmoji = False
        if self.path.endswith('/searchhandleemoji'):
            searchForEmoji = True
            self.path = self.path.replace('/searchhandleemoji',
                                          '/searchhandle')
            if self.server.debug:
                print('DEBUG: searching for emoji')
                print('authorized: ' + str(authorized))

        self._benchmarkPOSTtimings(POSTstartTime, POSTtimings, 5)

        self._benchmarkPOSTtimings(POSTstartTime, POSTtimings, 6)

        # a search was made
        if ((authorized or searchForEmoji) and
            (self.path.endswith('/searchhandle') or
             '/searchhandle?page=' in self.path)):
            self._receiveSearchQuery(callingDomain, cookie,
                                     authorized, self.path,
                                     self.server.baseDir,
                                     self.server.httpPrefix,
                                     self.server.domain,
                                     self.server.domainFull,
                                     self.server.port,
                                     searchForEmoji,
                                     self.server.onionDomain,
                                     self.server.i2pDomain,
                                     self.server.debug)
            return

        self._benchmarkPOSTtimings(POSTstartTime, POSTtimings, 7)

        if authorized:
            # a vote/question/poll is posted
            if self.path.endswith('/question') or \
               '/question?page=' in self.path:
                self._receiveVote(callingDomain, cookie,
                                  authorized, self.path,
                                  self.server.baseDir,
                                  self.server.httpPrefix,
                                  self.server.domain,
                                  self.server.domainFull,
                                  self.server.onionDomain,
                                  self.server.i2pDomain,
                                  self.server.debug)
                return

            # removes a shared item
            if self.path.endswith('/rmshare'):
                self._removeShare(callingDomain, cookie,
                                  authorized, self.path,
                                  self.server.baseDir,
                                  self.server.httpPrefix,
                                  self.server.domain,
                                  self.server.domainFull,
                                  self.server.onionDomain,
                                  self.server.i2pDomain,
                                  self.server.debug)
                return

            self._benchmarkPOSTtimings(POSTstartTime, POSTtimings, 8)

            # removes a post
            if self.path.endswith('/rmpost'):
                print('ERROR: attempt to remove post was not authorized. ' +
                      self.path)
                self._400()
                self.server.POSTbusy = False
                return
            if self.path.endswith('/rmpost'):
                self._removePost(callingDomain, cookie,
                                 authorized, self.path,
                                 self.server.baseDir,
                                 self.server.httpPrefix,
                                 self.server.domain,
                                 self.server.domainFull,
                                 self.server.onionDomain,
                                 self.server.i2pDomain,
                                 self.server.debug)
                return

            self._benchmarkPOSTtimings(POSTstartTime, POSTtimings, 9)

            # decision to follow in the web interface is confirmed
            if self.path.endswith('/followconfirm'):
                self._followConfirm(callingDomain, cookie,
                                    authorized, self.path,
                                    self.server.baseDir,
                                    self.server.httpPrefix,
                                    self.server.domain,
                                    self.server.domainFull,
                                    self.server.port,
                                    self.server.onionDomain,
                                    self.server.i2pDomain,
                                    self.server.debug)
                return

            self._benchmarkPOSTtimings(POSTstartTime, POSTtimings, 10)

            # decision to unfollow in the web interface is confirmed
            if self.path.endswith('/unfollowconfirm'):
                self._unfollowConfirm(callingDomain, cookie,
                                      authorized, self.path,
                                      self.server.baseDir,
                                      self.server.httpPrefix,
                                      self.server.domain,
                                      self.server.domainFull,
                                      self.server.port,
                                      self.server.onionDomain,
                                      self.server.i2pDomain,
                                      self.server.debug)
                return

            self._benchmarkPOSTtimings(POSTstartTime, POSTtimings, 11)

            # decision to unblock in the web interface is confirmed
            if self.path.endswith('/unblockconfirm'):
                self._unblockConfirm(callingDomain, cookie,
                                     authorized, self.path,
                                     self.server.baseDir,
                                     self.server.httpPrefix,
                                     self.server.domain,
                                     self.server.domainFull,
                                     self.server.port,
                                     self.server.onionDomain,
                                     self.server.i2pDomain,
                                     self.server.debug)
                return

            self._benchmarkPOSTtimings(POSTstartTime, POSTtimings, 12)

            # decision to block in the web interface is confirmed
            if self.path.endswith('/blockconfirm'):
                self._blockConfirm(callingDomain, cookie,
                                   authorized, self.path,
                                   self.server.baseDir,
                                   self.server.httpPrefix,
                                   self.server.domain,
                                   self.server.domainFull,
                                   self.server.port,
                                   self.server.onionDomain,
                                   self.server.i2pDomain,
                                   self.server.debug)
                return

            self._benchmarkPOSTtimings(POSTstartTime, POSTtimings, 13)

            # an option was chosen from person options screen
            # view/follow/block/report
            if self.path.endswith('/personoptions'):
                self._personOptions(self.path,
                                    callingDomain, cookie,
                                    self.server.baseDir,
                                    self.server.httpPrefix,
                                    self.server.domain,
                                    self.server.domainFull,
                                    self.server.port,
                                    self.server.onionDomain,
                                    self.server.i2pDomain,
                                    self.server.debug)
                return

        self._benchmarkPOSTtimings(POSTstartTime, POSTtimings, 14)

        # receive different types of post created by htmlNewPost
        postTypes = ("newpost", "newblog", "newunlisted", "newfollowers",
                     "newdm", "newreport", "newshare", "newquestion",
                     "editblogpost", "newreminder", "newevent")
        for currPostType in postTypes:
            if not authorized:
                break

            postRedirect = self.server.defaultTimeline
            if currPostType == 'newshare':
                postRedirect = 'shares'
            elif currPostType == 'newevent':
                postRedirect = 'tlevents'

            pageNumber = \
                self._receiveNewPost(currPostType, self.path,
                                     callingDomain, cookie,
                                     authorized)
            if pageNumber:
                nickname = self.path.split('/users/')[1]
                if '/' in nickname:
                    nickname = nickname.split('/')[0]

                if callingDomain.endswith('.onion') and \
                   self.server.onionDomain:
                    self._redirect_headers('http://' +
                                           self.server.onionDomain +
                                           '/users/' + nickname +
                                           '/' + postRedirect +
                                           '?page=' + str(pageNumber), cookie,
                                           callingDomain)
                elif (callingDomain.endswith('.i2p') and
                      self.server.i2pDomain):
                    self._redirect_headers('http://' +
                                           self.server.i2pDomain +
                                           '/users/' + nickname +
                                           '/' + postRedirect +
                                           '?page=' + str(pageNumber), cookie,
                                           callingDomain)
                else:
                    self._redirect_headers(self.server.httpPrefix + '://' +
                                           self.server.domainFull +
                                           '/users/' + nickname +
                                           '/' + postRedirect +
                                           '?page=' + str(pageNumber), cookie,
                                           callingDomain)
                self.server.POSTbusy = False
                return

        self._benchmarkPOSTtimings(POSTstartTime, POSTtimings, 15)

        if self.path.endswith('/outbox') or self.path.endswith('/shares'):
            if '/users/' in self.path:
                if authorized:
                    self.outboxAuthenticated = True
                    pathUsersSection = self.path.split('/users/')[1]
                    self.postToNickname = pathUsersSection.split('/')[0]
            if not self.outboxAuthenticated:
                self.send_response(405)
                self.end_headers()
                self.server.POSTbusy = False
                return

        self._benchmarkPOSTtimings(POSTstartTime, POSTtimings, 16)

        # check that the post is to an expected path
        if not (self.path.endswith('/outbox') or
                self.path.endswith('/inbox') or
                self.path.endswith('/shares') or
                self.path.endswith('/moderationaction') or
                self.path == '/sharedInbox'):
            print('Attempt to POST to invalid path ' + self.path)
            self._400()
            self.server.POSTbusy = False
            return

        self._benchmarkPOSTtimings(POSTstartTime, POSTtimings, 17)

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
           '/users/' in self.path:
            self._receiveImage(length, callingDomain, cookie,
                               authorized, self.path,
                               self.server.baseDir,
                               self.server.httpPrefix,
                               self.server.domain,
                               self.server.domainFull,
                               self.server.onionDomain,
                               self.server.i2pDomain,
                               self.server.debug)
            return

        # refuse to receive non-json content
        if self.headers['Content-type'] != 'application/json' and \
           self.headers['Content-type'] != 'application/activity+json':
            print("POST is not json: " + self.headers['Content-type'])
            if self.server.debug:
                print(str(self.headers))
                length = int(self.headers['Content-length'])
                if length < self.server.maxPostLength:
                    try:
                        unknownPost = self.rfile.read(length).decode('utf-8')
                    except SocketError as e:
                        if e.errno == errno.ECONNRESET:
                            print('WARN: POST unknownPost ' +
                                  'connection reset by peer')
                        else:
                            print('WARN: POST unknownPost socket error')
                        self.send_response(400)
                        self.end_headers()
                        self.server.POSTbusy = False
                        return
                    except ValueError as e:
                        print('ERROR: POST unknownPost rfile.read failed')
                        print(e)
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

        self._benchmarkPOSTtimings(POSTstartTime, POSTtimings, 18)

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
        except SocketError as e:
            if e.errno == errno.ECONNRESET:
                print('WARN: POST messageBytes ' +
                      'connection reset by peer')
            else:
                print('WARN: POST messageBytes socket error')
            self.send_response(400)
            self.end_headers()
            self.server.POSTbusy = False
            return
        except ValueError as e:
            print('ERROR: POST messageBytes rfile.read failed')
            print(e)
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

        # convert the raw bytes to json
        messageJson = json.loads(messageBytes)

        self._benchmarkPOSTtimings(POSTstartTime, POSTtimings, 19)

        # https://www.w3.org/TR/activitypub/#object-without-create
        if self.outboxAuthenticated:
            if self._postToOutbox(messageJson, __version__):
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

        self._benchmarkPOSTtimings(POSTstartTime, POSTtimings, 20)

        # check the necessary properties are available
        if self.server.debug:
            print('DEBUG: Check message has params')

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

        self._benchmarkPOSTtimings(POSTstartTime, POSTtimings, 21)

        if not self.headers.get('signature'):
            if 'keyId=' not in self.headers['signature']:
                if self.server.debug:
                    print('DEBUG: POST to inbox has no keyId in ' +
                          'header signature parameter')
                self.send_response(403)
                self.end_headers()
                self.server.POSTbusy = False
                return

        self._benchmarkPOSTtimings(POSTstartTime, POSTtimings, 22)

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

        self._benchmarkPOSTtimings(POSTstartTime, POSTtimings, 23)

        if self.server.debug:
            print('DEBUG: POST saving to inbox queue')
        if '/users/' in self.path:
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
                print('DEBUG: POST to shared inbox')
                queueStatus = \
                    self._updateInboxQueue('inbox', messageJson, messageBytes)
                if queueStatus >= 0 and queueStatus <= 3:
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
            print('ERROR: ' + str(cls) + ", " + str(e))
            pass
        else:
            return HTTPServer.handle_error(self, request, client_address)


def runPostsQueue(baseDir: str, sendThreads: [], debug: bool) -> None:
    """Manages the threads used to send posts
    """
    while True:
        time.sleep(1)
        removeDormantThreads(baseDir, sendThreads, debug)


def runSharesExpire(versionNumber: str, baseDir: str) -> None:
    """Expires shares as needed
    """
    while True:
        time.sleep(120)
        expireShares(baseDir)


def runPostsWatchdog(projectVersion: str, httpd) -> None:
    """This tries to keep the posts thread running even if it dies
    """
    print('Starting posts queue watchdog')
    postsQueueOriginal = httpd.thrPostsQueue.clone(runPostsQueue)
    httpd.thrPostsQueue.start()
    while True:
        time.sleep(20)
        if not httpd.thrPostsQueue.isAlive():
            httpd.thrPostsQueue.kill()
            httpd.thrPostsQueue = postsQueueOriginal.clone(runPostsQueue)
            httpd.thrPostsQueue.start()
            print('Restarting posts queue...')


def runSharesExpireWatchdog(projectVersion: str, httpd) -> None:
    """This tries to keep the shares expiry thread running even if it dies
    """
    print('Starting shares expiry watchdog')
    sharesExpireOriginal = httpd.thrSharesExpire.clone(runSharesExpire)
    httpd.thrSharesExpire.start()
    while True:
        time.sleep(20)
        if not httpd.thrSharesExpire.isAlive():
            httpd.thrSharesExpire.kill()
            httpd.thrSharesExpire = sharesExpireOriginal.clone(runSharesExpire)
            httpd.thrSharesExpire.start()
            print('Restarting shares expiry...')


def loadTokens(baseDir: str, tokensDict: {}, tokensLookup: {}) -> None:
    for subdir, dirs, files in os.walk(baseDir + '/accounts'):
        for handle in dirs:
            if '@' in handle:
                tokenFilename = baseDir + '/accounts/' + handle + '/.token'
                if not os.path.isfile(tokenFilename):
                    continue
                nickname = handle.split('@')[0]
                token = None
                try:
                    with open(tokenFilename, 'r') as fp:
                        token = fp.read()
                except Exception as e:
                    print('WARN: Unable to read token for ' +
                          nickname + ' ' + str(e))
                if not token:
                    continue
                tokensDict[nickname] = token
                tokensLookup[token] = nickname


def runDaemon(newsInstance: bool,
              blogsInstance: bool,
              mediaInstance: bool,
              maxRecentPosts: int,
              enableSharedInbox: bool, registration: bool,
              language: str, projectVersion: str,
              instanceId: str, clientToServer: bool,
              baseDir: str, domain: str,
              onionDomain: str, i2pDomain: str,
              YTReplacementDomain: str,
              port=80, proxyPort=80, httpPrefix='https',
              fedList=[], maxMentions=10, maxEmoji=10,
              authenticatedFetch=False,
              proxyType=None, maxReplies=64,
              domainMaxPostsPerDay=8640, accountMaxPostsPerDay=864,
              allowDeletion=False, debug=False, unitTest=False,
              instanceOnlySkillsSearch=False, sendThreads=[],
              useBlurHash=False,
              manualFollowerApproval=True) -> None:
    if len(domain) == 0:
        domain = 'localhost'
    if '.' not in domain:
        if domain != 'localhost':
            print('Invalid domain: ' + domain)
            return

    if unitTest:
        serverAddress = (domain, proxyPort)
        pubHandler = partial(PubServerUnitTest)
    else:
        serverAddress = ('', proxyPort)
        pubHandler = partial(PubServer)

    if not os.path.isdir(baseDir + '/accounts'):
        print('Creating accounts directory')
        os.mkdir(baseDir + '/accounts')

    try:
        httpd = EpicyonServer(serverAddress, pubHandler)
    except Exception as e:
        if e.errno == 98:
            print('ERROR: HTTP server address is already in use. ' +
                  str(serverAddress))
            return False

        print('ERROR: HTTP server failed to start. ' + str(e))
        return False

    httpd.unitTest = unitTest
    httpd.YTReplacementDomain = YTReplacementDomain

    # newswire storing rss feeds
    httpd.newswire = {}

    # This counter is used to update the list of blocked domains in memory.
    # It helps to avoid touching the disk and so improves flooding resistance
    httpd.blocklistUpdateCtr = 0
    httpd.blocklistUpdateInterval = 100
    httpd.domainBlocklist = getDomainBlocklist(baseDir)

    httpd.manualFollowerApproval = manualFollowerApproval
    httpd.onionDomain = onionDomain
    httpd.i2pDomain = i2pDomain
    httpd.useBlurHash = useBlurHash
    httpd.mediaInstance = mediaInstance
    httpd.blogsInstance = blogsInstance
    httpd.newsInstance = newsInstance
    httpd.defaultTimeline = 'inbox'
    if mediaInstance:
        httpd.defaultTimeline = 'tlmedia'
    if blogsInstance:
        httpd.defaultTimeline = 'tlblogs'
    if newsInstance:
        httpd.defaultTimeline = 'tlnews'

    # load translations dictionary
    httpd.translate = {}
    httpd.systemLanguage = 'en'
    if not unitTest:
        if not os.path.isdir(baseDir + '/translations'):
            print('ERROR: translations directory not found')
            return
        if not language:
            systemLanguage = locale.getdefaultlocale()[0]
        else:
            systemLanguage = language
        if not systemLanguage:
            systemLanguage = 'en'
        if '_' in systemLanguage:
            systemLanguage = systemLanguage.split('_')[0]
        while '/' in systemLanguage:
            systemLanguage = systemLanguage.split('/')[1]
        if '.' in systemLanguage:
            systemLanguage = systemLanguage.split('.')[0]
        translationsFile = baseDir + '/translations/' + \
            systemLanguage + '.json'
        if not os.path.isfile(translationsFile):
            systemLanguage = 'en'
            translationsFile = baseDir + '/translations/' + \
                systemLanguage + '.json'
        print('System language: ' + systemLanguage)
        httpd.systemLanguage = systemLanguage
        httpd.translate = loadJson(translationsFile)
        if not httpd.translate:
            print('ERROR: no translations loaded from ' + translationsFile)
            sys.exit()

    if registration == 'open':
        httpd.registration = True
    else:
        httpd.registration = False
    httpd.enableSharedInbox = enableSharedInbox
    httpd.outboxThread = {}
    httpd.newPostThread = {}
    httpd.projectVersion = projectVersion
    httpd.authenticatedFetch = authenticatedFetch
    # max POST size of 30M
    httpd.maxPostLength = 1024 * 1024 * 30
    httpd.maxMediaSize = httpd.maxPostLength
    # Maximum text length is 32K - enough for a blog post
    httpd.maxMessageLength = 32000
    # Maximum overall number of posts per box
    httpd.maxPostsInBox = 32000
    httpd.domain = domain
    httpd.port = port
    httpd.domainFull = domain
    if port:
        if port != 80 and port != 443:
            if ':' not in domain:
                httpd.domainFull = domain + ':' + str(port)
    saveDomainQrcode(baseDir, httpPrefix, httpd.domainFull)
    httpd.httpPrefix = httpPrefix
    httpd.debug = debug
    httpd.federationList = fedList.copy()
    httpd.baseDir = baseDir
    httpd.instanceId = instanceId
    httpd.personCache = {}
    httpd.cachedWebfingers = {}
    httpd.proxyType = proxyType
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
    httpd.maxReplies = maxReplies
    httpd.tokens = {}
    httpd.tokensLookup = {}
    loadTokens(baseDir, httpd.tokens, httpd.tokensLookup)
    httpd.instanceOnlySkillsSearch = instanceOnlySkillsSearch
    # contains threads used to send posts to followers
    httpd.followersThreads = []

    if not os.path.isdir(baseDir + '/accounts/inbox@' + domain):
        print('Creating shared inbox: inbox@' + domain)
        createSharedInbox(baseDir, 'inbox', domain, port, httpPrefix)

    if not os.path.isdir(baseDir + '/cache'):
        os.mkdir(baseDir + '/cache')
    if not os.path.isdir(baseDir + '/cache/actors'):
        print('Creating actors cache')
        os.mkdir(baseDir + '/cache/actors')
    if not os.path.isdir(baseDir + '/cache/announce'):
        print('Creating announce cache')
        os.mkdir(baseDir + '/cache/announce')
    if not os.path.isdir(baseDir + '/cache/avatars'):
        print('Creating avatars cache')
        os.mkdir(baseDir + '/cache/avatars')

    archiveDir = baseDir + '/archive'
    if not os.path.isdir(archiveDir):
        print('Creating archive')
        os.mkdir(archiveDir)

    print('Creating cache expiry thread')
    httpd.thrCache = \
        threadWithTrace(target=expireCache,
                        args=(baseDir, httpd.personCache,
                              httpd.httpPrefix,
                              archiveDir,
                              httpd.maxPostsInBox), daemon=True)
    httpd.thrCache.start()

    print('Creating posts queue')
    httpd.thrPostsQueue = \
        threadWithTrace(target=runPostsQueue,
                        args=(baseDir, httpd.sendThreads, debug), daemon=True)
    if not unitTest:
        httpd.thrPostsWatchdog = \
            threadWithTrace(target=runPostsWatchdog,
                            args=(projectVersion, httpd), daemon=True)
        httpd.thrPostsWatchdog.start()
    else:
        httpd.thrPostsQueue.start()

    print('Creating expire thread for shared items')
    httpd.thrSharesExpire = \
        threadWithTrace(target=runSharesExpire,
                        args=(__version__, baseDir), daemon=True)
    if not unitTest:
        httpd.thrSharesExpireWatchdog = \
            threadWithTrace(target=runSharesExpireWatchdog,
                            args=(projectVersion, httpd), daemon=True)
        httpd.thrSharesExpireWatchdog.start()
    else:
        httpd.thrSharesExpire.start()

    httpd.recentPostsCache = {}
    httpd.maxRecentPosts = maxRecentPosts
    httpd.iconsCache = {}
    httpd.fontsCache = {}

    print('Creating inbox queue')
    httpd.thrInboxQueue = \
        threadWithTrace(target=runInboxQueue,
                        args=(httpd.recentPostsCache, httpd.maxRecentPosts,
                              projectVersion,
                              baseDir, httpPrefix, httpd.sendThreads,
                              httpd.postLog, httpd.cachedWebfingers,
                              httpd.personCache, httpd.inboxQueue,
                              domain, onionDomain, i2pDomain, port, proxyType,
                              httpd.federationList,
                              maxReplies,
                              domainMaxPostsPerDay, accountMaxPostsPerDay,
                              allowDeletion, debug, maxMentions, maxEmoji,
                              httpd.translate, unitTest,
                              httpd.YTReplacementDomain), daemon=True)

    print('Creating scheduled post thread')
    httpd.thrPostSchedule = \
        threadWithTrace(target=runPostSchedule,
                        args=(baseDir, httpd, 20), daemon=True)

    print('Creating newswire thread')
    httpd.thrNewswireDaemon = \
        threadWithTrace(target=runNewswireDaemon,
                        args=(baseDir, httpd, 'newswire'), daemon=True)

    # flags used when restarting the inbox queue
    httpd.restartInboxQueueInProgress = False
    httpd.restartInboxQueue = False

    if not unitTest:
        print('Creating inbox queue watchdog')
        httpd.thrWatchdog = \
            threadWithTrace(target=runInboxQueueWatchdog,
                            args=(projectVersion, httpd), daemon=True)
        httpd.thrWatchdog.start()

        print('Creating scheduled post watchdog')
        httpd.thrWatchdogSchedule = \
            threadWithTrace(target=runPostScheduleWatchdog,
                            args=(projectVersion, httpd), daemon=True)
        httpd.thrWatchdogSchedule.start()

        print('Creating newswire watchdog')
        httpd.thrNewswireWatchdog = \
            threadWithTrace(target=runNewswireWatchdog,
                            args=(projectVersion, httpd), daemon=True)
        httpd.thrNewswireWatchdog.start()
    else:
        httpd.thrInboxQueue.start()
        httpd.thrPostSchedule.start()

    if clientToServer:
        print('Running ActivityPub client on ' +
              domain + ' port ' + str(proxyPort))
    else:
        print('Running ActivityPub server on ' +
              domain + ' port ' + str(proxyPort))
    httpd.serve_forever()
