__filename__ = "epicyon.py"
__author__ = "Bob Mottram"
__license__ = "AGPL3+"
__version__ = "1.2.0"
__maintainer__ = "Bob Mottram"
__email__ = "bob@libreserver.org"
__status__ = "Production"
__module_group__ = "Commandline Interface"

import os
import shutil
import sys
import time
import argparse
import getpass
from person import getActorJson
from person import createPerson
from person import createGroup
from person import setProfileImage
from person import removeAccount
from person import activateAccount
from person import deactivateAccount
from skills import setSkillLevel
from roles import setRole
from webfinger import webfingerHandle
from bookmarks import sendBookmarkViaServer
from bookmarks import sendUndoBookmarkViaServer
from posts import getInstanceActorKey
from posts import sendMuteViaServer
from posts import sendUndoMuteViaServer
from posts import c2sBoxJson
from posts import downloadFollowCollection
from posts import getPublicPostDomains
from posts import getPublicPostDomainsBlocked
from posts import sendBlockViaServer
from posts import sendUndoBlockViaServer
from posts import createPublicPost
from posts import deleteAllPosts
from posts import archivePosts
from posts import sendPostViaServer
from posts import getPublicPostsOfPerson
from posts import getUserUrl
from posts import checkDomains
from session import createSession
from session import getJson
from newswire import getRSS
from filters import addFilter
from filters import removeFilter
from pprint import pprint
from daemon import runDaemon
from follow import getFollowRequestsViaServer
from follow import getFollowingViaServer
from follow import getFollowersViaServer
from follow import clearFollows
from follow import followerOfPerson
from follow import sendFollowRequestViaServer
from follow import sendUnfollowRequestViaServer
from tests import testSharedItemsFederation
from tests import testGroupFollow
from tests import testPostMessageBetweenServers
from tests import testFollowBetweenServers
from tests import testClientToServer
from tests import testUpdateActor
from tests import runAllTests
from auth import storeBasicCredentials
from auth import createPassword
from utils import removeDomainPort
from utils import getPortFromDomain
from utils import hasUsersPath
from utils import getFullDomain
from utils import setConfigParam
from utils import getConfigParam
from utils import getDomainFromActor
from utils import getNicknameFromActor
from utils import followPerson
from utils import validNickname
from utils import getProtocolPrefixes
from utils import acctDir
from media import archiveMedia
from media import getAttachmentMediaType
from delete import sendDeleteViaServer
from like import sendLikeViaServer
from like import sendUndoLikeViaServer
from skills import sendSkillViaServer
from availability import setAvailability
from availability import sendAvailabilityViaServer
from manualapprove import manualDenyFollowRequest
from manualapprove import manualApproveFollowRequest
from shares import sendShareViaServer
from shares import sendUndoShareViaServer
from shares import sendWantedViaServer
from shares import sendUndoWantedViaServer
from shares import addShare
from theme import setTheme
from announce import sendAnnounceViaServer
from socnet import instancesGraph
from migrate import migrateAccounts
from desktop_client import runDesktopClient


def str2bool(v) -> bool:
    """Returns true if the given value is a boolean
    """
    if isinstance(v, bool):
        return v
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')


parser = argparse.ArgumentParser(description='ActivityPub Server')
parser.add_argument('--userAgentBlocks', type=str,
                    default=None,
                    help='List of blocked user agents, separated by commas')
parser.add_argument('--libretranslate', dest='libretranslateUrl', type=str,
                    default=None,
                    help='URL for LibreTranslate service')
parser.add_argument('--conversationId', dest='conversationId', type=str,
                    default=None,
                    help='Conversation Id which can be added ' +
                    'when sending a post')
parser.add_argument('--libretranslateApiKey',
                    dest='libretranslateApiKey', type=str,
                    default=None,
                    help='API key for LibreTranslate service')
parser.add_argument('--defaultCurrency', dest='defaultCurrency', type=str,
                    default=None,
                    help='Default currency EUR/GBP/USD...')
parser.add_argument('-n', '--nickname', dest='nickname', type=str,
                    default=None,
                    help='Nickname of the account to use')
parser.add_argument('--screenreader', dest='screenreader', type=str,
                    default=None,
                    help='Name of the screen reader: espeak/picospeaker')
parser.add_argument('--fol', '--follow', dest='follow', type=str,
                    default=None,
                    help='Handle of account to follow. eg. nickname@domain')
parser.add_argument('--unfol', '--unfollow', dest='unfollow', type=str,
                    default=None,
                    help='Handle of account stop following. ' +
                    'eg. nickname@domain')
parser.add_argument('-d', '--domain', dest='domain', type=str,
                    default=None,
                    help='Domain name of the server')
parser.add_argument('--notificationType', '--notifyType',
                    dest='notificationType', type=str,
                    default='notify-send',
                    help='Type of desktop notification command: ' +
                    'notify-send/zenity/osascript/New-BurntToastNotification')
parser.add_argument('-o', '--onion', dest='onion', type=str,
                    default=None,
                    help='Onion domain name of the server if ' +
                    'primarily on clearnet')
parser.add_argument('--i2pDomain', dest='i2pDomain', type=str,
                    default=None,
                    help='i2p domain name of the server if ' +
                    'primarily on clearnet')
parser.add_argument('-p', '--port', dest='port', type=int,
                    default=None,
                    help='Port number to run on')
parser.add_argument('--postsPerSource',
                    dest='maxNewswirePostsPerSource', type=int,
                    default=4,
                    help='Maximum newswire posts per feed or account')
parser.add_argument('--dormantMonths',
                    dest='dormantMonths', type=int,
                    default=3,
                    help='How many months does a followed account need to ' +
                    'be unseen for before being considered dormant')
parser.add_argument('--defaultReplyIntervalHours',
                    dest='defaultReplyIntervalHours', type=int,
                    default=1000,
                    help='How many hours after publication of a post ' +
                    'are replies to it permitted')
parser.add_argument('--sendThreadsTimeoutMins',
                    dest='sendThreadsTimeoutMins', type=int,
                    default=30,
                    help='How many minutes before a thread to send out ' +
                    'posts expires')
parser.add_argument('--maxNewswirePosts',
                    dest='maxNewswirePosts', type=int,
                    default=20,
                    help='Maximum newswire posts in the right column')
parser.add_argument('--maxFeedSize',
                    dest='maxNewswireFeedSizeKb', type=int,
                    default=10240,
                    help='Maximum newswire rss/atom feed size in K')
parser.add_argument('--maxFeedItemSizeKb',
                    dest='maxFeedItemSizeKb', type=int,
                    default=2048,
                    help='Maximum size of an individual rss/atom ' +
                    'feed item in K')
parser.add_argument('--maxMirroredArticles',
                    dest='maxMirroredArticles', type=int,
                    default=100,
                    help='Maximum number of news articles to mirror.' +
                    ' Set to zero for indefinite mirroring.')
parser.add_argument('--maxNewsPosts',
                    dest='maxNewsPosts', type=int,
                    default=0,
                    help='Maximum number of news timeline posts to keep. ' +
                    'Zero for no expiry.')
parser.add_argument('--maxFollowers',
                    dest='maxFollowers', type=int,
                    default=2000,
                    help='Maximum number of followers per account. ' +
                    'Zero for no limit.')
parser.add_argument('--followers',
                    dest='followers', type=str,
                    default='',
                    help='Show list of followers for the given actor')
parser.add_argument('--postcache', dest='maxRecentPosts', type=int,
                    default=512,
                    help='The maximum number of recent posts to store in RAM')
parser.add_argument('--proxy', dest='proxyPort', type=int, default=None,
                    help='Proxy port number to run on')
parser.add_argument('--path', dest='baseDir',
                    type=str, default=os.getcwd(),
                    help='Directory in which to store posts')
parser.add_argument('--ytdomain', dest='YTReplacementDomain',
                    type=str, default=None,
                    help='Domain used to replace youtube.com')
parser.add_argument('--twitterdomain', dest='twitterReplacementDomain',
                    type=str, default=None,
                    help='Domain used to replace twitter.com')
parser.add_argument('--language', dest='language',
                    type=str, default=None,
                    help='Language code, eg. en/fr/de/es')
parser.add_argument('-a', '--addaccount', dest='addaccount',
                    type=str, default=None,
                    help='Adds a new account')
parser.add_argument('-g', '--addgroup', dest='addgroup',
                    type=str, default=None,
                    help='Adds a new group')
parser.add_argument('--activate', dest='activate',
                    type=str, default=None,
                    help='Activate a previously deactivated account')
parser.add_argument('--deactivate', dest='deactivate',
                    type=str, default=None,
                    help='Deactivate an account')
parser.add_argument('-r', '--rmaccount', dest='rmaccount',
                    type=str, default=None,
                    help='Remove an account')
parser.add_argument('--rmgroup', dest='rmgroup',
                    type=str, default=None,
                    help='Remove a group')
parser.add_argument('--pass', '--password', dest='password',
                    type=str, default=None,
                    help='Set a password for an account')
parser.add_argument('--chpass', '--changepassword',
                    nargs='+', dest='changepassword',
                    help='Change the password for an account')
parser.add_argument('--actor', dest='actor', type=str,
                    default=None,
                    help='Show the json actor the given handle')
parser.add_argument('--posts', dest='posts', type=str,
                    default=None,
                    help='Show posts for the given handle')
parser.add_argument('--postDomains', dest='postDomains', type=str,
                    default=None,
                    help='Show domains referenced in public '
                    'posts for the given handle')
parser.add_argument('--postDomainsBlocked', dest='postDomainsBlocked',
                    type=str, default=None,
                    help='Show blocked domains referenced in public '
                    'posts for the given handle')
parser.add_argument('--checkDomains', dest='checkDomains', type=str,
                    default=None,
                    help='Check domains of non-mutual followers for '
                    'domains which are globally blocked by this instance')
parser.add_argument('--socnet', dest='socnet', type=str,
                    default=None,
                    help='Show dot diagram for social network '
                    'of federated instances')
parser.add_argument('--postsraw', dest='postsraw', type=str,
                    default=None,
                    help='Show raw json of posts for the given handle')
parser.add_argument('--json', dest='json', type=str, default=None,
                    help='Show the json for a given activitypub url')
parser.add_argument('--rss', dest='rss', type=str, default=None,
                    help='Show an rss feed for a given url')
parser.add_argument('-f', '--federate', nargs='+', dest='federationList',
                    help='Specify federation list separated by spaces')
parser.add_argument('--federateshares', nargs='+',
                    dest='sharedItemsFederatedDomains',
                    help='Specify federation list for shared items, ' +
                    'separated by spaces')
parser.add_argument("--following", "--followingList",
                    dest='followingList',
                    type=str2bool, nargs='?',
                    const=True, default=False,
                    help="Get the following list. Use nickname and " +
                    "domain options to specify the account")
parser.add_argument("--followersList",
                    dest='followersList',
                    type=str2bool, nargs='?',
                    const=True, default=False,
                    help="Get the followers list. Use nickname and " +
                    "domain options to specify the account")
parser.add_argument("--followRequestsList",
                    dest='followRequestsList',
                    type=str2bool, nargs='?',
                    const=True, default=False,
                    help="Get the follow requests list. Use nickname and " +
                    "domain options to specify the account")
parser.add_argument("--repliesEnabled", "--commentsEnabled",
                    dest='commentsEnabled',
                    type=str2bool, nargs='?',
                    const=True, default=True,
                    help="Enable replies to a post")
parser.add_argument("--showPublishAsIcon",
                    dest='showPublishAsIcon',
                    type=str2bool, nargs='?',
                    const=True, default=True,
                    help="Whether to show newswire publish " +
                    "as an icon or a button")
parser.add_argument("--fullWidthTimelineButtonHeader",
                    dest='fullWidthTimelineButtonHeader',
                    type=str2bool, nargs='?',
                    const=True, default=False,
                    help="Whether to show the timeline " +
                    "button header containing inbox and outbox " +
                    "as the full width of the screen")
parser.add_argument("--iconsAsButtons",
                    dest='iconsAsButtons',
                    type=str2bool, nargs='?',
                    const=True, default=False,
                    help="Show header icons as buttons")
parser.add_argument("--logLoginFailures",
                    dest='logLoginFailures',
                    type=str2bool, nargs='?',
                    const=True, default=False,
                    help="Whether to log longin failures")
parser.add_argument("--rssIconAtTop",
                    dest='rssIconAtTop',
                    type=str2bool, nargs='?',
                    const=True, default=True,
                    help="Whether to show the rss icon at teh top or bottom" +
                    "of the timeline")
parser.add_argument("--lowBandwidth",
                    dest='lowBandwidth',
                    type=str2bool, nargs='?',
                    const=True, default=True,
                    help="Whether to use low bandwidth images")
parser.add_argument("--publishButtonAtTop",
                    dest='publishButtonAtTop',
                    type=str2bool, nargs='?',
                    const=True, default=False,
                    help="Whether to show the publish button at the top of " +
                    "the newswire column")
parser.add_argument("--allowLocalNetworkAccess",
                    dest='allowLocalNetworkAccess',
                    type=str2bool, nargs='?',
                    const=True, default=False,
                    help="Whether to allow access to local network " +
                    "addresses. This might be useful when deploying in " +
                    "a mesh network")
parser.add_argument("--verifyAllSignatures",
                    dest='verifyAllSignatures',
                    type=str2bool, nargs='?',
                    const=True, default=False,
                    help="Whether to require that all incoming " +
                    "posts have valid jsonld signatures")
parser.add_argument("--brochMode",
                    dest='brochMode',
                    type=str2bool, nargs='?',
                    const=True, default=False,
                    help="Enable broch mode")
parser.add_argument("--nodeinfoaccounts",
                    dest='showNodeInfoAccounts',
                    type=str2bool, nargs='?',
                    const=True, default=False,
                    help="Show numbers of accounts within nodeinfo metadata")
parser.add_argument("--nodeinfoversion",
                    dest='showNodeInfoVersion',
                    type=str2bool, nargs='?',
                    const=True, default=False,
                    help="Show version number within nodeinfo metadata")
parser.add_argument("--noKeyPress",
                    dest='noKeyPress',
                    type=str2bool, nargs='?',
                    const=True, default=False,
                    help="Notification daemon does not wait for keypresses")
parser.add_argument("--notifyShowNewPosts",
                    dest='notifyShowNewPosts',
                    type=str2bool, nargs='?',
                    const=True, default=False,
                    help="Desktop client shows/speaks new posts " +
                    "as they arrive")
parser.add_argument("--noapproval", type=str2bool, nargs='?',
                    const=True, default=False,
                    help="Allow followers without approval")
parser.add_argument("--mediainstance", type=str2bool, nargs='?',
                    const=True, default=False,
                    help="Media Instance - favor media over text")
parser.add_argument("--dateonly", type=str2bool, nargs='?',
                    const=True, default=False,
                    help="Only show the date at the bottom of posts")
parser.add_argument("--blogsinstance", type=str2bool, nargs='?',
                    const=True, default=False,
                    help="Blogs Instance - favor blogs over microblogging")
parser.add_argument("--newsinstance", type=str2bool, nargs='?',
                    const=True, default=False,
                    help="News Instance - favor news over microblogging")
parser.add_argument("--positivevoting", type=str2bool, nargs='?',
                    const=True, default=False,
                    help="On newswire, whether moderators vote " +
                    "positively for or veto against items")
parser.add_argument("--debug", type=str2bool, nargs='?',
                    const=True, default=False,
                    help="Show debug messages")
parser.add_argument("--notificationSounds", type=str2bool, nargs='?',
                    const=True, default=True,
                    help="Play notification sounds")
parser.add_argument("--secureMode", type=str2bool, nargs='?',
                    const=True, default=False,
                    help="Requires all GET requests to be signed, " +
                    "so that the sender can be identifies and " +
                    "blocked  if neccessary")
parser.add_argument("--instanceOnlySkillsSearch", type=str2bool, nargs='?',
                    const=True, default=False,
                    help="Skills searches only return " +
                    "results from this instance")
parser.add_argument("--http", type=str2bool, nargs='?',
                    const=True, default=False,
                    help="Use http only")
parser.add_argument("--gnunet", type=str2bool, nargs='?',
                    const=True, default=False,
                    help="Use gnunet protocol only")
parser.add_argument("--dat", type=str2bool, nargs='?',
                    const=True, default=False,
                    help="Use dat protocol only")
parser.add_argument("--hyper", type=str2bool, nargs='?',
                    const=True, default=False,
                    help="Use hypercore protocol only")
parser.add_argument("--i2p", type=str2bool, nargs='?',
                    const=True, default=False,
                    help="Use i2p protocol only")
parser.add_argument("--tor", type=str2bool, nargs='?',
                    const=True, default=False,
                    help="Route via Tor")
parser.add_argument("--migrations", type=str2bool, nargs='?',
                    const=True, default=False,
                    help="Migrate moved accounts")
parser.add_argument("--tests", type=str2bool, nargs='?',
                    const=True, default=False,
                    help="Run unit tests")
parser.add_argument("--testsnetwork", type=str2bool, nargs='?',
                    const=True, default=False,
                    help="Run network unit tests")
parser.add_argument("--testdata", type=str2bool, nargs='?',
                    const=True, default=False,
                    help="Generate some data for testing purposes")
parser.add_argument('--icon', '--avatar', dest='avatar', type=str,
                    default=None,
                    help='Set the avatar filename for an account')
parser.add_argument('--image', '--background', dest='backgroundImage',
                    type=str, default=None,
                    help='Set the profile background image for an account')
parser.add_argument('--archive', dest='archive', type=str,
                    default=None,
                    help='Archive old files to the given directory')
parser.add_argument('--archiveweeks', dest='archiveWeeks', type=int,
                    default=4,
                    help='Specify the number of weeks after which ' +
                    'media will be archived')
parser.add_argument('--maxposts', dest='archiveMaxPosts', type=int,
                    default=32000,
                    help='Maximum number of posts in in/outbox')
parser.add_argument('--minimumvotes', dest='minimumvotes', type=int,
                    default=1,
                    help='Minimum number of votes to remove or add' +
                    ' a newswire item')
parser.add_argument('--maxLikeCount', dest='maxLikeCount', type=int,
                    default=10,
                    help='Maximum number of likes displayed on a post')
parser.add_argument('--votingtime', dest='votingtime', type=int,
                    default=1440,
                    help='Time to vote on newswire items in minutes')
parser.add_argument('--message', dest='message', type=str,
                    default=None,
                    help='Message content')
parser.add_argument('--delete', dest='delete', type=str,
                    default=None,
                    help='Delete a specified post')
parser.add_argument("--allowdeletion", type=str2bool, nargs='?',
                    const=True, default=False,
                    help="Do not allow deletions")
parser.add_argument('--repeat', '--announce', dest='announce', type=str,
                    default=None,
                    help='Announce/repeat a url')
parser.add_argument('--box', type=str,
                    default=None,
                    help='Returns the json for a given timeline, ' +
                    'with authentication')
parser.add_argument('--page', '--pageNumber', dest='pageNumber', type=int,
                    default=1,
                    help='Page number when using the --box option')
parser.add_argument('--favorite', '--like', dest='like', type=str,
                    default=None, help='Like a url')
parser.add_argument('--undolike', '--unlike', dest='undolike', type=str,
                    default=None, help='Undo a like of a url')
parser.add_argument('--bookmark', '--bm', dest='bookmark', type=str,
                    default=None,
                    help='Bookmark the url of a post')
parser.add_argument('--unbookmark', '--unbm', dest='unbookmark', type=str,
                    default=None,
                    help='Undo a bookmark given the url of a post')
parser.add_argument('--sendto', dest='sendto', type=str,
                    default=None, help='Address to send a post to')
parser.add_argument('--attach', dest='attach', type=str,
                    default=None, help='File to attach to a post')
parser.add_argument('--imagedescription', dest='imageDescription', type=str,
                    default=None, help='Description of an attached image')
parser.add_argument('--city', dest='city', type=str,
                    default='London, England',
                    help='Spoofed city for image metadata misdirection')
parser.add_argument('--warning', '--warn', '--cwsubject', '--subject',
                    dest='subject', type=str, default=None,
                    help='Subject of content warning')
parser.add_argument('--reply', '--replyto', dest='replyto', type=str,
                    default=None, help='Url of post to reply to')
parser.add_argument("--followersonly", type=str2bool, nargs='?',
                    const=True, default=True,
                    help="Send to followers only")
parser.add_argument("--followerspending", type=str2bool, nargs='?',
                    const=True, default=False,
                    help="Show a list of followers pending")
parser.add_argument('--approve', dest='approve', type=str, default=None,
                    help='Approve a follow request')
parser.add_argument('--deny', dest='deny', type=str, default=None,
                    help='Deny a follow request')
parser.add_argument("-c", "--client", type=str2bool, nargs='?',
                    const=True, default=False,
                    help="Use as an ActivityPub client")
parser.add_argument('--maxreplies', dest='maxReplies', type=int, default=64,
                    help='Maximum number of replies to a post')
parser.add_argument('--maxMentions', '--hellthread', dest='maxMentions',
                    type=int, default=10,
                    help='Maximum number of mentions within a post')
parser.add_argument('--maxEmoji', '--maxemoji', dest='maxEmoji',
                    type=int, default=10,
                    help='Maximum number of emoji within a post')
parser.add_argument('--role', dest='role', type=str, default=None,
                    help='Set a role for a person')
parser.add_argument('--skill', dest='skill', type=str, default=None,
                    help='Set a skill for a person')
parser.add_argument('--level', dest='skillLevelPercent', type=int,
                    default=None,
                    help='Set a skill level for a person as a ' +
                    'percentage, or zero to remove')
parser.add_argument('--status', '--availability', dest='availability',
                    type=str, default=None,
                    help='Set an availability status')
parser.add_argument('--desktop', dest='desktop',
                    type=str, default=None,
                    help='Run desktop client')
parser.add_argument('--block', dest='block', type=str, default=None,
                    help='Block a particular address')
parser.add_argument('--unblock', dest='unblock', type=str, default=None,
                    help='Remove a block on a particular address')
parser.add_argument('--mute', dest='mute', type=str, default=None,
                    help='Mute a particular post URL')
parser.add_argument('--unmute', dest='unmute', type=str, default=None,
                    help='Unmute a particular post URL')
parser.add_argument('--filter', dest='filterStr', type=str, default=None,
                    help='Adds a word or phrase which if present will ' +
                    'cause a message to be ignored')
parser.add_argument('--unfilter', dest='unfilterStr', type=str, default=None,
                    help='Remove a filter on a particular word or phrase')
parser.add_argument('--domainmax', dest='domainMaxPostsPerDay', type=int,
                    default=8640,
                    help='Maximum number of received posts ' +
                    'from a domain per day')
parser.add_argument('--accountmax', dest='accountMaxPostsPerDay', type=int,
                    default=8640,
                    help='Maximum number of received posts ' +
                    'from an account per day')
parser.add_argument('--itemName', dest='itemName', type=str,
                    default=None,
                    help='Name of an item being shared')
parser.add_argument('--undoItemName', dest='undoItemName', type=str,
                    default=None,
                    help='Name of an shared item to remove')
parser.add_argument('--wantedItemName', dest='wantedItemName', type=str,
                    default=None,
                    help='Name of a wanted item')
parser.add_argument('--undoWantedItemName', dest='undoWantedItemName',
                    type=str, default=None,
                    help='Name of a wanted item to remove')
parser.add_argument('--summary', dest='summary', type=str,
                    default=None,
                    help='Description of an item being shared')
parser.add_argument('--itemImage', dest='itemImage', type=str,
                    default=None,
                    help='Filename of an image for an item being shared')
parser.add_argument('--itemQty', dest='itemQty', type=float,
                    default=1,
                    help='Quantity of items being shared')
parser.add_argument('--itemPrice', dest='itemPrice', type=str,
                    default="0.00",
                    help='Total price of items being shared')
parser.add_argument('--itemCurrency', dest='itemCurrency', type=str,
                    default="EUR",
                    help='Currency of items being shared')
parser.add_argument('--itemType', dest='itemType', type=str,
                    default=None,
                    help='Type of item being shared')
parser.add_argument('--itemCategory', dest='itemCategory', type=str,
                    default=None,
                    help='Category of item being shared')
parser.add_argument('--location', dest='location', type=str, default=None,
                    help='Location/City of item being shared')
parser.add_argument('--duration', dest='duration', type=str, default=None,
                    help='Duration for which to share an item')
parser.add_argument('--registration', dest='registration', type=str,
                    default='open',
                    help='Whether new registrations are open or closed')
parser.add_argument("--nosharedinbox", type=str2bool, nargs='?',
                    const=True, default=False,
                    help='Disable shared inbox')
parser.add_argument('--maxregistrations', dest='maxRegistrations',
                    type=int, default=10,
                    help='The maximum number of new registrations')
parser.add_argument("--resetregistrations", type=str2bool, nargs='?',
                    const=True, default=False,
                    help="Reset the number of remaining registrations")

args = parser.parse_args()

debug = False
if args.debug:
    debug = True
else:
    if os.path.isfile('debug'):
        debug = True

if args.tests:
    runAllTests()
    sys.exit()
if args.testsnetwork:
    print('Network Tests')
    baseDir = os.getcwd()
    testSharedItemsFederation(baseDir)
    testGroupFollow(baseDir)
    testPostMessageBetweenServers(baseDir)
    testFollowBetweenServers(baseDir)
    testClientToServer(baseDir)
    testUpdateActor(baseDir)
    print('All tests succeeded')
    sys.exit()

httpPrefix = 'https'
if args.http or args.i2p:
    httpPrefix = 'http'
elif args.gnunet:
    httpPrefix = 'gnunet'

baseDir = args.baseDir
if baseDir.endswith('/'):
    print("--path option should not end with '/'")
    sys.exit()

# automatic translations
if args.libretranslateUrl:
    if '://' in args.libretranslateUrl and \
       '.' in args.libretranslateUrl:
        setConfigParam(baseDir, 'libretranslateUrl', args.libretranslateUrl)
if args.libretranslateApiKey:
    setConfigParam(baseDir, 'libretranslateApiKey', args.libretranslateApiKey)

if args.posts:
    if not args.domain:
        originDomain = getConfigParam(baseDir, 'domain')
    else:
        originDomain = args.domain
    if debug:
        print('originDomain: ' + str(originDomain))
    if '@' not in args.posts:
        if '/users/' in args.posts:
            postsNickname = getNicknameFromActor(args.posts)
            postsDomain, postsPort = getDomainFromActor(args.posts)
            args.posts = \
                getFullDomain(postsNickname + '@' + postsDomain, postsPort)
        else:
            print('Syntax: --posts nickname@domain')
            sys.exit()
    if not args.http:
        args.port = 443
    nickname = args.posts.split('@')[0]
    domain = args.posts.split('@')[1]
    proxyType = None
    if args.tor or domain.endswith('.onion'):
        proxyType = 'tor'
        if domain.endswith('.onion'):
            args.port = 80
    elif args.i2p or domain.endswith('.i2p'):
        proxyType = 'i2p'
        if domain.endswith('.i2p'):
            args.port = 80
    elif args.gnunet:
        proxyType = 'gnunet'
    if not args.language:
        args.language = 'en'
    signingPrivateKeyPem = getInstanceActorKey(baseDir, originDomain)
    getPublicPostsOfPerson(baseDir, nickname, domain, False, True,
                           proxyType, args.port, httpPrefix, debug,
                           __version__, args.language,
                           signingPrivateKeyPem, originDomain)
    sys.exit()

if args.postDomains:
    if '@' not in args.postDomains:
        if '/users/' in args.postDomains:
            postsNickname = getNicknameFromActor(args.postDomains)
            postsDomain, postsPort = getDomainFromActor(args.postDomains)
            args.postDomains = \
                getFullDomain(postsNickname + '@' + postsDomain, postsPort)
        else:
            print('Syntax: --postDomains nickname@domain')
            sys.exit()
    if not args.http:
        args.port = 443
    nickname = args.postDomains.split('@')[0]
    domain = args.postDomains.split('@')[1]
    proxyType = None
    if args.tor or domain.endswith('.onion'):
        proxyType = 'tor'
        if domain.endswith('.onion'):
            args.port = 80
    elif args.i2p or domain.endswith('.i2p'):
        proxyType = 'i2p'
        if domain.endswith('.i2p'):
            args.port = 80
    elif args.gnunet:
        proxyType = 'gnunet'
    wordFrequency = {}
    domainList = []
    if not args.language:
        args.language = 'en'
    signingPrivateKeyPem = None
    if not args.domain:
        originDomain = getConfigParam(baseDir, 'domain')
    else:
        originDomain = args.domain
    if args.secureMode:
        signingPrivateKeyPem = getInstanceActorKey(baseDir, originDomain)
    domainList = getPublicPostDomains(None,
                                      baseDir, nickname, domain,
                                      originDomain,
                                      proxyType, args.port,
                                      httpPrefix, debug,
                                      __version__,
                                      wordFrequency, domainList,
                                      args.language,
                                      signingPrivateKeyPem)
    for postDomain in domainList:
        print(postDomain)
    sys.exit()

if args.postDomainsBlocked:
    # Domains which were referenced in public posts by a
    # given handle but which are globally blocked on this instance
    if '@' not in args.postDomainsBlocked:
        if '/users/' in args.postDomainsBlocked:
            postsNickname = getNicknameFromActor(args.postDomainsBlocked)
            postsDomain, postsPort = \
                getDomainFromActor(args.postDomainsBlocked)
            args.postDomainsBlocked = \
                getFullDomain(postsNickname + '@' + postsDomain, postsPort)
        else:
            print('Syntax: --postDomainsBlocked nickname@domain')
            sys.exit()
    if not args.http:
        args.port = 443
    nickname = args.postDomainsBlocked.split('@')[0]
    domain = args.postDomainsBlocked.split('@')[1]
    proxyType = None
    if args.tor or domain.endswith('.onion'):
        proxyType = 'tor'
        if domain.endswith('.onion'):
            args.port = 80
    elif args.i2p or domain.endswith('.i2p'):
        proxyType = 'i2p'
        if domain.endswith('.i2p'):
            args.port = 80
    elif args.gnunet:
        proxyType = 'gnunet'
    wordFrequency = {}
    domainList = []
    if not args.language:
        args.language = 'en'
    signingPrivateKeyPem = None
    if args.secureMode:
        signingPrivateKeyPem = getInstanceActorKey(baseDir, domain)
    domainList = getPublicPostDomainsBlocked(None,
                                             baseDir, nickname, domain,
                                             proxyType, args.port,
                                             httpPrefix, debug,
                                             __version__,
                                             wordFrequency, domainList,
                                             args.language,
                                             signingPrivateKeyPem)
    for postDomain in domainList:
        print(postDomain)
    sys.exit()

if args.checkDomains:
    # Domains which were referenced in public posts by a
    # given handle but which are globally blocked on this instance
    if '@' not in args.checkDomains:
        if '/users/' in args.checkDomains:
            postsNickname = getNicknameFromActor(args.posts)
            postsDomain, postsPort = getDomainFromActor(args.posts)
            args.checkDomains = \
                getFullDomain(postsNickname + '@' + postsDomain, postsPort)
        else:
            print('Syntax: --checkDomains nickname@domain')
            sys.exit()
    if not args.http:
        args.port = 443
    nickname = args.checkDomains.split('@')[0]
    domain = args.checkDomains.split('@')[1]
    proxyType = None
    if args.tor or domain.endswith('.onion'):
        proxyType = 'tor'
        if domain.endswith('.onion'):
            args.port = 80
    elif args.i2p or domain.endswith('.i2p'):
        proxyType = 'i2p'
        if domain.endswith('.i2p'):
            args.port = 80
    elif args.gnunet:
        proxyType = 'gnunet'
    maxBlockedDomains = 0
    if not args.language:
        args.language = 'en'
    signingPrivateKeyPem = None
    if args.secureMode:
        signingPrivateKeyPem = getInstanceActorKey(baseDir, domain)
    checkDomains(None,
                 baseDir, nickname, domain,
                 proxyType, args.port,
                 httpPrefix, debug,
                 __version__,
                 maxBlockedDomains, False, args.language,
                 signingPrivateKeyPem)
    sys.exit()

if args.socnet:
    if ',' not in args.socnet:
        print('Syntax: '
              '--socnet nick1@domain1,nick2@domain2,nick3@domain3')
        sys.exit()

    if not args.http:
        args.port = 443
    proxyType = 'tor'
    if not args.language:
        args.language = 'en'
    if not args.domain:
        args.domain = getConfigParam(baseDir, 'domain')
    domain = ''
    if args.domain:
        domain = args.domain
    signingPrivateKeyPem = None
    if args.secureMode:
        signingPrivateKeyPem = getInstanceActorKey(baseDir, domain)
    dotGraph = instancesGraph(baseDir, args.socnet,
                              proxyType, args.port,
                              httpPrefix, debug,
                              __version__, args.language,
                              signingPrivateKeyPem)
    try:
        with open('socnet.dot', 'w+') as fp:
            fp.write(dotGraph)
            print('Saved to socnet.dot')
    except BaseException:
        pass
    sys.exit()

if args.postsraw:
    if not args.domain:
        originDomain = getConfigParam(baseDir, 'domain')
    else:
        originDomain = args.domain
    if debug:
        print('originDomain: ' + str(originDomain))
    if '@' not in args.postsraw:
        print('Syntax: --postsraw nickname@domain')
        sys.exit()
    if not args.http:
        args.port = 443
    nickname = args.postsraw.split('@')[0]
    domain = args.postsraw.split('@')[1]
    proxyType = None
    if args.tor or domain.endswith('.onion'):
        proxyType = 'tor'
    elif args.i2p or domain.endswith('.i2p'):
        proxyType = 'i2p'
    elif args.gnunet:
        proxyType = 'gnunet'
    if not args.language:
        args.language = 'en'
    signingPrivateKeyPem = getInstanceActorKey(baseDir, originDomain)
    getPublicPostsOfPerson(baseDir, nickname, domain, False, False,
                           proxyType, args.port, httpPrefix, debug,
                           __version__, args.language,
                           signingPrivateKeyPem, originDomain)
    sys.exit()

if args.json:
    session = createSession(None)
    profileStr = 'https://www.w3.org/ns/activitystreams'
    asHeader = {
        'Accept': 'application/ld+json; profile="' + profileStr + '"'
    }
    if not args.domain:
        args.domain = getConfigParam(baseDir, 'domain')
    domain = ''
    if args.domain:
        domain = args.domain
    signingPrivateKeyPem = getInstanceActorKey(baseDir, domain)
    if debug:
        print('baseDir: ' + str(baseDir))
        if signingPrivateKeyPem:
            print('Obtained instance actor signing key')
        else:
            print('Did not obtain instance actor key for ' + domain)
    testJson = getJson(signingPrivateKeyPem, session, args.json, asHeader,
                       None, debug, __version__, httpPrefix, domain)
    pprint(testJson)
    sys.exit()

# create cache for actors
if not os.path.isdir(baseDir + '/cache'):
    os.mkdir(baseDir + '/cache')
if not os.path.isdir(baseDir + '/cache/actors'):
    print('Creating actors cache')
    os.mkdir(baseDir + '/cache/actors')
if not os.path.isdir(baseDir + '/cache/announce'):
    print('Creating announce cache')
    os.mkdir(baseDir + '/cache/announce')

# set the theme in config.json
themeName = getConfigParam(baseDir, 'theme')
if not themeName:
    setConfigParam(baseDir, 'theme', 'default')
    themeName = 'default'

if not args.mediainstance:
    mediaInstance = getConfigParam(baseDir, 'mediaInstance')
    if mediaInstance is not None:
        args.mediainstance = mediaInstance
        if args.mediainstance:
            args.blogsinstance = False
            args.newsinstance = False

if not args.newsinstance:
    newsInstance = getConfigParam(baseDir, 'newsInstance')
    if newsInstance is not None:
        args.newsinstance = newsInstance
        if args.newsinstance:
            args.blogsinstance = False
            args.mediainstance = False

if not args.blogsinstance:
    blogsInstance = getConfigParam(baseDir, 'blogsInstance')
    if blogsInstance is not None:
        args.blogsinstance = blogsInstance
        if args.blogsinstance:
            args.mediainstance = False
            args.newsinstance = False

# set the instance title in config.json
title = getConfigParam(baseDir, 'instanceTitle')
if not title:
    setConfigParam(baseDir, 'instanceTitle', 'Epicyon')

# set the instance description in config.json
descFull = getConfigParam(baseDir, 'instanceDescription')
if not descFull:
    setConfigParam(baseDir, 'instanceDescription',
                   'Just another ActivityPub server')

# set the short instance description in config.json
descShort = getConfigParam(baseDir, 'instanceDescriptionShort')
if not descShort:
    setConfigParam(baseDir, 'instanceDescriptionShort',
                   'Just another ActivityPub server')

if args.domain:
    domain = args.domain
    setConfigParam(baseDir, 'domain', domain)

if args.rss:
    session = createSession(None)
    testRSS = getRSS(baseDir, domain, session, args.rss,
                     False, False, 1000, 1000, 1000, 1000)
    pprint(testRSS)
    sys.exit()

if args.onion:
    if not args.onion.endswith('.onion'):
        print(args.onion + ' does not look like an onion domain')
        sys.exit()
    if '://' in args.onion:
        args.onion = args.onion.split('://')[1]
    onionDomain = args.onion
    setConfigParam(baseDir, 'onion', onionDomain)

i2pDomain = None
if args.i2pDomain:
    if not args.i2pDomain.endswith('.i2p'):
        print(args.i2pDomain + ' does not look like an i2p domain')
        sys.exit()
    if '://' in args.i2pDomain:
        args.onion = args.onion.split('://')[1]
    i2pDomain = args.i2pDomain
    setConfigParam(baseDir, 'i2pDomain', i2pDomain)

if not args.language:
    languageCode = getConfigParam(baseDir, 'language')
    if languageCode:
        args.language = languageCode
    else:
        args.language = 'en'

# maximum number of new registrations
if not args.maxRegistrations:
    maxRegistrations = getConfigParam(baseDir, 'maxRegistrations')
    if not maxRegistrations:
        maxRegistrations = 10
        setConfigParam(baseDir, 'maxRegistrations', str(maxRegistrations))
    else:
        maxRegistrations = int(maxRegistrations)
else:
    maxRegistrations = args.maxRegistrations
    setConfigParam(baseDir, 'maxRegistrations', str(maxRegistrations))

# if this is the initial run then allow new registrations
if not getConfigParam(baseDir, 'registration'):
    if args.registration.lower() == 'open':
        setConfigParam(baseDir, 'registration', 'open')
        setConfigParam(baseDir, 'maxRegistrations', str(maxRegistrations))
        setConfigParam(baseDir, 'registrationsRemaining',
                       str(maxRegistrations))

if args.resetregistrations:
    setConfigParam(baseDir, 'registrationsRemaining', str(maxRegistrations))
    print('Number of new registrations reset to ' + str(maxRegistrations))

# unique ID for the instance
instanceId = getConfigParam(baseDir, 'instanceId')
if not instanceId:
    instanceId = createPassword(32)
    setConfigParam(baseDir, 'instanceId', instanceId)
    print('Instance ID: ' + instanceId)

# get domain name from configuration
configDomain = getConfigParam(baseDir, 'domain')
if configDomain:
    domain = configDomain
else:
    domain = 'localhost'

# get onion domain name from configuration
configOnionDomain = getConfigParam(baseDir, 'onion')
if configOnionDomain:
    onionDomain = configOnionDomain
else:
    onionDomain = None

# get i2p domain name from configuration
configi2pDomain = getConfigParam(baseDir, 'i2pDomain')
if configi2pDomain:
    i2pDomain = configi2pDomain
else:
    i2pDomain = None

# get port number from configuration
configPort = getConfigParam(baseDir, 'port')
if configPort:
    port = configPort
else:
    if domain.endswith('.onion') or \
       domain.endswith('.i2p'):
        port = 80
    else:
        port = 443

configProxyPort = getConfigParam(baseDir, 'proxyPort')
if configProxyPort:
    proxyPort = configProxyPort
else:
    proxyPort = port

nickname = None
if args.nickname:
    nickname = nickname

federationList = []
if args.federationList:
    if len(args.federationList) == 1:
        if not (args.federationList[0].lower() == 'any' or
                args.federationList[0].lower() == 'all' or
                args.federationList[0].lower() == '*'):
            for federationDomain in args.federationList:
                if '@' in federationDomain:
                    print(federationDomain +
                          ': Federate with domains, not individual accounts')
                    sys.exit()
            federationList = args.federationList.copy()
        setConfigParam(baseDir, 'federationList', federationList)
else:
    configFederationList = getConfigParam(baseDir, 'federationList')
    if configFederationList:
        federationList = configFederationList

proxyType = None
if args.tor or domain.endswith('.onion'):
    proxyType = 'tor'
elif args.i2p or domain.endswith('.i2p'):
    proxyType = 'i2p'
elif args.gnunet:
    proxyType = 'gnunet'

if args.approve:
    if not args.nickname:
        print('Specify a nickname with the --nickname option')
        sys.exit()
    if '@' not in args.approve:
        print('syntax: --approve nick@domain')
        sys.exit()
    session = createSession(proxyType)
    sendThreads = []
    postLog = []
    cachedWebfingers = {}
    personCache = {}
    if not domain:
        domain = getConfigParam(baseDir, 'domain')
    signingPrivateKeyPem = None
    if args.secureMode:
        signingPrivateKeyPem = getInstanceActorKey(baseDir, domain)
    manualApproveFollowRequest(session, baseDir,
                               httpPrefix,
                               args.nickname, domain, port,
                               args.approve,
                               federationList,
                               sendThreads, postLog,
                               cachedWebfingers, personCache,
                               debug, __version__,
                               signingPrivateKeyPem)
    sys.exit()

if args.deny:
    if not args.nickname:
        print('Specify a nickname with the --nickname option')
        sys.exit()
    if '@' not in args.deny:
        print('syntax: --deny nick@domain')
        sys.exit()
    session = createSession(proxyType)
    sendThreads = []
    postLog = []
    cachedWebfingers = {}
    personCache = {}
    if not domain:
        domain = getConfigParam(baseDir, 'domain')
    signingPrivateKeyPem = None
    if args.secureMode:
        signingPrivateKeyPem = getInstanceActorKey(baseDir, domain)
    manualDenyFollowRequest(session, baseDir,
                            httpPrefix,
                            args.nickname, domain, port,
                            args.deny,
                            federationList,
                            sendThreads, postLog,
                            cachedWebfingers, personCache,
                            debug, __version__,
                            signingPrivateKeyPem)
    sys.exit()

if args.followerspending:
    if not args.nickname:
        print('Specify a nickname with the --nickname option')
        sys.exit()

    accountsDir = acctDir(baseDir, args.nickname, domain)
    approveFollowsFilename = accountsDir + '/followrequests.txt'
    approveCtr = 0
    if os.path.isfile(approveFollowsFilename):
        with open(approveFollowsFilename, 'r') as approvefile:
            for approve in approvefile:
                print(approve.replace('\n', '').replace('\r', ''))
                approveCtr += 1
    if approveCtr == 0:
        print('There are no follow requests pending approval.')
    sys.exit()


if args.message:
    if not args.nickname:
        print('Specify a nickname with the --nickname option')
        sys.exit()

    if not args.password:
        args.password = getpass.getpass('Password: ')
        if not args.password:
            print('Specify a password with the --password option')
            sys.exit()
    args.password = args.password.replace('\n', '')

    session = createSession(proxyType)
    if not args.sendto:
        print('Specify an account to sent to: --sendto [nickname@domain]')
        sys.exit()
    if '@' not in args.sendto and \
       not args.sendto.lower().endswith('public') and \
       not args.sendto.lower().endswith('followers'):
        print('syntax: --sendto [nickname@domain]')
        print('        --sendto public')
        print('        --sendto followers')
        sys.exit()
    if '@' in args.sendto:
        toNickname = args.sendto.split('@')[0]
        toDomain = args.sendto.split('@')[1]
        toDomain = toDomain.replace('\n', '').replace('\r', '')
        toPort = 443
        if ':' in toDomain:
            toPort = getPortFromDomain(toDomain)
            toDomain = removeDomainPort(toDomain)
    else:
        if args.sendto.endswith('followers'):
            toNickname = None
            toDomain = 'followers'
            toPort = port
        else:
            toNickname = None
            toDomain = 'public'
            toPort = port

    ccUrl = None
    sendMessage = args.message
    followersOnly = args.followersonly
    clientToServer = args.client
    attachedImageDescription = args.imageDescription
    city = 'London, England'
    sendThreads = []
    postLog = []
    personCache = {}
    cachedWebfingers = {}
    subject = args.subject
    attach = args.attach
    mediaType = None
    if attach:
        mediaType = getAttachmentMediaType(attach)
    replyTo = args.replyto
    followersOnly = False
    isArticle = False
    if not domain:
        domain = getConfigParam(baseDir, 'domain')
    signingPrivateKeyPem = None
    if args.secureMode:
        signingPrivateKeyPem = getInstanceActorKey(baseDir, domain)
    print('Sending post to ' + args.sendto)

    sendPostViaServer(signingPrivateKeyPem, __version__,
                      baseDir, session, args.nickname, args.password,
                      domain, port,
                      toNickname, toDomain, toPort, ccUrl,
                      httpPrefix, sendMessage, followersOnly,
                      args.commentsEnabled, attach, mediaType,
                      attachedImageDescription, city,
                      cachedWebfingers, personCache, isArticle,
                      args.language, args.lowBandwidth, args.debug,
                      replyTo, replyTo, args.conversationId, subject)
    for i in range(10):
        # TODO detect send success/fail
        time.sleep(1)
    sys.exit()

if args.announce:
    if not args.nickname:
        print('Specify a nickname with the --nickname option')
        sys.exit()

    if not args.password:
        args.password = getpass.getpass('Password: ')
        if not args.password:
            print('Specify a password with the --password option')
            sys.exit()
    args.password = args.password.replace('\n', '')

    session = createSession(proxyType)
    personCache = {}
    cachedWebfingers = {}
    if not domain:
        domain = getConfigParam(baseDir, 'domain')
    signingPrivateKeyPem = None
    if args.secureMode:
        signingPrivateKeyPem = getInstanceActorKey(baseDir, domain)
    print('Sending announce/repeat of ' + args.announce)

    sendAnnounceViaServer(baseDir, session, args.nickname, args.password,
                          domain, port,
                          httpPrefix, args.announce,
                          cachedWebfingers, personCache,
                          True, __version__, signingPrivateKeyPem)
    for i in range(10):
        # TODO detect send success/fail
        time.sleep(1)
    sys.exit()

if args.box:
    if not domain:
        print('Specify a domain with the --domain option')
        sys.exit()

    if not args.nickname:
        print('Specify a nickname with the --nickname option')
        sys.exit()

    if not args.password:
        args.password = getpass.getpass('Password: ')
        if not args.password:
            print('Specify a password with the --password option')
            sys.exit()
    args.password = args.password.replace('\n', '')

    proxyType = None
    if args.tor or domain.endswith('.onion'):
        proxyType = 'tor'
        if domain.endswith('.onion'):
            args.port = 80
    elif args.i2p or domain.endswith('.i2p'):
        proxyType = 'i2p'
        if domain.endswith('.i2p'):
            args.port = 80
    elif args.gnunet:
        proxyType = 'gnunet'
    if not domain:
        domain = getConfigParam(baseDir, 'domain')
    signingPrivateKeyPem = None
    if args.secureMode:
        signingPrivateKeyPem = getInstanceActorKey(baseDir, domain)

    session = createSession(proxyType)
    boxJson = c2sBoxJson(baseDir, session,
                         args.nickname, args.password,
                         domain, port, httpPrefix,
                         args.box, args.pageNumber,
                         args.debug, signingPrivateKeyPem)
    if boxJson:
        pprint(boxJson)
    else:
        print('Box not found: ' + args.box)
    sys.exit()

if args.itemName:
    if not args.password:
        args.password = getpass.getpass('Password: ')
        if not args.password:
            print('Specify a password with the --password option')
            sys.exit()
    args.password = args.password.replace('\n', '')

    if not args.nickname:
        print('Specify a nickname with the --nickname option')
        sys.exit()

    if not args.summary:
        print('Specify a description for your shared item ' +
              'with the --summary option')
        sys.exit()

    if not args.itemQty:
        print('Specify a quantity of shared items with the --itemQty option')
        sys.exit()

    if not args.itemType:
        print('Specify a type of shared item with the --itemType option')
        sys.exit()

    if not args.itemCategory:
        print('Specify a category of shared item ' +
              'with the --itemCategory option')
        sys.exit()

    if not args.location:
        print('Specify a location or city where the shared ' +
              'item resides with the --location option')
        sys.exit()

    if not args.duration:
        print('Specify a duration to share the object ' +
              'with the --duration option')
        sys.exit()

    session = createSession(proxyType)
    personCache = {}
    cachedWebfingers = {}
    if not domain:
        domain = getConfigParam(baseDir, 'domain')
    signingPrivateKeyPem = None
    if args.secureMode:
        signingPrivateKeyPem = getInstanceActorKey(baseDir, domain)
    print('Sending shared item: ' + args.itemName)

    sendShareViaServer(baseDir, session,
                       args.nickname, args.password,
                       domain, port,
                       httpPrefix,
                       args.itemName,
                       args.summary,
                       args.itemImage,
                       args.itemQty,
                       args.itemType,
                       args.itemCategory,
                       args.location,
                       args.duration,
                       cachedWebfingers, personCache,
                       debug, __version__,
                       args.itemPrice, args.itemCurrency,
                       signingPrivateKeyPem)
    for i in range(10):
        # TODO detect send success/fail
        time.sleep(1)
    sys.exit()

if args.undoItemName:
    if not args.password:
        args.password = getpass.getpass('Password: ')
        if not args.password:
            print('Specify a password with the --password option')
            sys.exit()
    args.password = args.password.replace('\n', '')

    if not args.nickname:
        print('Specify a nickname with the --nickname option')
        sys.exit()

    session = createSession(proxyType)
    personCache = {}
    cachedWebfingers = {}
    if not domain:
        domain = getConfigParam(baseDir, 'domain')
    signingPrivateKeyPem = None
    if args.secureMode:
        signingPrivateKeyPem = getInstanceActorKey(baseDir, domain)
    print('Sending undo of shared item: ' + args.undoItemName)

    sendUndoShareViaServer(baseDir, session,
                           args.nickname, args.password,
                           domain, port,
                           httpPrefix,
                           args.undoItemName,
                           cachedWebfingers, personCache,
                           debug, __version__, signingPrivateKeyPem)
    for i in range(10):
        # TODO detect send success/fail
        time.sleep(1)
    sys.exit()

if args.wantedItemName:
    if not args.password:
        args.password = getpass.getpass('Password: ')
        if not args.password:
            print('Specify a password with the --password option')
            sys.exit()
    args.password = args.password.replace('\n', '')

    if not args.nickname:
        print('Specify a nickname with the --nickname option')
        sys.exit()

    if not args.summary:
        print('Specify a description for your shared item ' +
              'with the --summary option')
        sys.exit()

    if not args.itemQty:
        print('Specify a quantity of shared items with the --itemQty option')
        sys.exit()

    if not args.itemType:
        print('Specify a type of shared item with the --itemType option')
        sys.exit()

    if not args.itemCategory:
        print('Specify a category of shared item ' +
              'with the --itemCategory option')
        sys.exit()

    if not args.location:
        print('Specify a location or city where the wanted ' +
              'item resides with the --location option')
        sys.exit()

    if not args.duration:
        print('Specify a duration to share the object ' +
              'with the --duration option')
        sys.exit()

    session = createSession(proxyType)
    personCache = {}
    cachedWebfingers = {}
    if not domain:
        domain = getConfigParam(baseDir, 'domain')
    signingPrivateKeyPem = None
    if args.secureMode:
        signingPrivateKeyPem = getInstanceActorKey(baseDir, domain)
    print('Sending wanted item: ' + args.wantedItemName)

    sendWantedViaServer(baseDir, session,
                        args.nickname, args.password,
                        domain, port,
                        httpPrefix,
                        args.wantedItemName,
                        args.summary,
                        args.itemImage,
                        args.itemQty,
                        args.itemType,
                        args.itemCategory,
                        args.location,
                        args.duration,
                        cachedWebfingers, personCache,
                        debug, __version__,
                        args.itemPrice, args.itemCurrency,
                        signingPrivateKeyPem)
    for i in range(10):
        # TODO detect send success/fail
        time.sleep(1)
    sys.exit()

if args.undoWantedItemName:
    if not args.password:
        args.password = getpass.getpass('Password: ')
        if not args.password:
            print('Specify a password with the --password option')
            sys.exit()
    args.password = args.password.replace('\n', '')

    if not args.nickname:
        print('Specify a nickname with the --nickname option')
        sys.exit()

    session = createSession(proxyType)
    personCache = {}
    cachedWebfingers = {}
    if not domain:
        domain = getConfigParam(baseDir, 'domain')
    signingPrivateKeyPem = None
    if args.secureMode:
        signingPrivateKeyPem = getInstanceActorKey(baseDir, domain)
    print('Sending undo of wanted item: ' + args.undoWantedItemName)

    sendUndoWantedViaServer(baseDir, session,
                            args.nickname, args.password,
                            domain, port,
                            httpPrefix,
                            args.undoWantedItemName,
                            cachedWebfingers, personCache,
                            debug, __version__, signingPrivateKeyPem)
    for i in range(10):
        # TODO detect send success/fail
        time.sleep(1)
    sys.exit()

if args.like:
    if not args.nickname:
        print('Specify a nickname with the --nickname option')
        sys.exit()

    if not args.password:
        args.password = getpass.getpass('Password: ')
        if not args.password:
            print('Specify a password with the --password option')
            sys.exit()
    args.password = args.password.replace('\n', '')

    session = createSession(proxyType)
    personCache = {}
    cachedWebfingers = {}
    if not domain:
        domain = getConfigParam(baseDir, 'domain')
    signingPrivateKeyPem = None
    if args.secureMode:
        signingPrivateKeyPem = getInstanceActorKey(baseDir, domain)
    print('Sending like of ' + args.like)

    sendLikeViaServer(baseDir, session,
                      args.nickname, args.password,
                      domain, port,
                      httpPrefix, args.like,
                      cachedWebfingers, personCache,
                      True, __version__, signingPrivateKeyPem)
    for i in range(10):
        # TODO detect send success/fail
        time.sleep(1)
    sys.exit()

if args.undolike:
    if not args.nickname:
        print('Specify a nickname with the --nickname option')
        sys.exit()

    if not args.password:
        args.password = getpass.getpass('Password: ')
        if not args.password:
            print('Specify a password with the --password option')
            sys.exit()
    args.password = args.password.replace('\n', '')

    session = createSession(proxyType)
    personCache = {}
    cachedWebfingers = {}
    if not domain:
        domain = getConfigParam(baseDir, 'domain')
    signingPrivateKeyPem = None
    if args.secureMode:
        signingPrivateKeyPem = getInstanceActorKey(baseDir, domain)
    print('Sending undo like of ' + args.undolike)

    sendUndoLikeViaServer(baseDir, session,
                          args.nickname, args.password,
                          domain, port,
                          httpPrefix, args.undolike,
                          cachedWebfingers, personCache,
                          True, __version__,
                          signingPrivateKeyPem)
    for i in range(10):
        # TODO detect send success/fail
        time.sleep(1)
    sys.exit()

if args.bookmark:
    if not args.nickname:
        print('Specify a nickname with the --nickname option')
        sys.exit()

    if not args.password:
        args.password = getpass.getpass('Password: ')
        if not args.password:
            print('Specify a password with the --password option')
            sys.exit()
    args.password = args.password.replace('\n', '')

    session = createSession(proxyType)
    personCache = {}
    cachedWebfingers = {}
    if not domain:
        domain = getConfigParam(baseDir, 'domain')
    signingPrivateKeyPem = None
    if args.secureMode:
        signingPrivateKeyPem = getInstanceActorKey(baseDir, domain)
    print('Sending bookmark of ' + args.bookmark)

    sendBookmarkViaServer(baseDir, session,
                          args.nickname, args.password,
                          domain, port,
                          httpPrefix, args.bookmark,
                          cachedWebfingers, personCache,
                          True, __version__,
                          signingPrivateKeyPem)
    for i in range(10):
        # TODO detect send success/fail
        time.sleep(1)
    sys.exit()

if args.unbookmark:
    if not args.nickname:
        print('Specify a nickname with the --nickname option')
        sys.exit()

    if not args.password:
        args.password = getpass.getpass('Password: ')
        if not args.password:
            print('Specify a password with the --password option')
            sys.exit()
    args.password = args.password.replace('\n', '')

    session = createSession(proxyType)
    personCache = {}
    cachedWebfingers = {}
    if not domain:
        domain = getConfigParam(baseDir, 'domain')
    signingPrivateKeyPem = None
    if args.secureMode:
        signingPrivateKeyPem = getInstanceActorKey(baseDir, domain)
    print('Sending undo bookmark of ' + args.unbookmark)

    sendUndoBookmarkViaServer(baseDir, session,
                              args.nickname, args.password,
                              domain, port,
                              httpPrefix, args.unbookmark,
                              cachedWebfingers, personCache,
                              True, __version__, signingPrivateKeyPem)
    for i in range(10):
        # TODO detect send success/fail
        time.sleep(1)
    sys.exit()

if args.delete:
    if not args.nickname:
        print('Specify a nickname with the --nickname option')
        sys.exit()

    if not args.password:
        args.password = getpass.getpass('Password: ')
        if not args.password:
            print('Specify a password with the --password option')
            sys.exit()
    args.password = args.password.replace('\n', '')

    session = createSession(proxyType)
    personCache = {}
    cachedWebfingers = {}
    if not domain:
        domain = getConfigParam(baseDir, 'domain')
    signingPrivateKeyPem = None
    if args.secureMode:
        signingPrivateKeyPem = getInstanceActorKey(baseDir, domain)
    print('Sending delete request of ' + args.delete)

    sendDeleteViaServer(baseDir, session,
                        args.nickname, args.password,
                        domain, port,
                        httpPrefix, args.delete,
                        cachedWebfingers, personCache,
                        True, __version__, signingPrivateKeyPem)
    for i in range(10):
        # TODO detect send success/fail
        time.sleep(1)
    sys.exit()

if args.follow:
    # follow via c2s protocol
    if '.' not in args.follow:
        print("This doesn't look like a fediverse handle")
        sys.exit()
    if not args.nickname:
        print('Please specify the nickname for the account with --nickname')
        sys.exit()
    if not args.password:
        args.password = getpass.getpass('Password: ')
        if not args.password:
            print('Specify a password with the --password option')
            sys.exit()
    args.password = args.password.replace('\n', '')

    followNickname = getNicknameFromActor(args.follow)
    if not followNickname:
        print('Unable to find nickname in ' + args.follow)
        sys.exit()
    followDomain, followPort = getDomainFromActor(args.follow)

    session = createSession(proxyType)
    personCache = {}
    cachedWebfingers = {}
    followHttpPrefix = httpPrefix
    if args.follow.startswith('https'):
        followHttpPrefix = 'https'
    if not domain:
        domain = getConfigParam(baseDir, 'domain')
    signingPrivateKeyPem = None
    if args.secureMode:
        signingPrivateKeyPem = getInstanceActorKey(baseDir, domain)

    sendFollowRequestViaServer(baseDir, session,
                               args.nickname, args.password,
                               domain, port,
                               followNickname, followDomain, followPort,
                               httpPrefix,
                               cachedWebfingers, personCache,
                               debug, __version__, signingPrivateKeyPem)
    for t in range(20):
        time.sleep(1)
        # TODO some method to know if it worked
    print('Ok')
    sys.exit()

if args.unfollow:
    # unfollow via c2s protocol
    if '.' not in args.follow:
        print("This doesn't look like a fediverse handle")
        sys.exit()
    if not args.nickname:
        print('Please specify the nickname for the account with --nickname')
        sys.exit()
    if not args.password:
        args.password = getpass.getpass('Password: ')
        if not args.password:
            print('Specify a password with the --password option')
            sys.exit()
    args.password = args.password.replace('\n', '')

    followNickname = getNicknameFromActor(args.unfollow)
    if not followNickname:
        print('WARN: unable to find nickname in ' + args.unfollow)
        sys.exit()
    followDomain, followPort = getDomainFromActor(args.unfollow)

    session = createSession(proxyType)
    personCache = {}
    cachedWebfingers = {}
    followHttpPrefix = httpPrefix
    if args.follow.startswith('https'):
        followHttpPrefix = 'https'
    if not domain:
        domain = getConfigParam(baseDir, 'domain')
    signingPrivateKeyPem = None
    if args.secureMode:
        signingPrivateKeyPem = getInstanceActorKey(baseDir, domain)

    sendUnfollowRequestViaServer(baseDir, session,
                                 args.nickname, args.password,
                                 domain, port,
                                 followNickname, followDomain, followPort,
                                 httpPrefix,
                                 cachedWebfingers, personCache,
                                 debug, __version__, signingPrivateKeyPem)
    for t in range(20):
        time.sleep(1)
        # TODO some method to know if it worked
    print('Ok')
    sys.exit()

if args.followingList:
    # following list via c2s protocol
    if not args.nickname:
        print('Please specify the nickname for the account with --nickname')
        sys.exit()
    if not args.password:
        args.password = getpass.getpass('Password: ')
        if not args.password:
            print('Specify a password with the --password option')
            sys.exit()
    args.password = args.password.replace('\n', '')

    session = createSession(proxyType)
    personCache = {}
    cachedWebfingers = {}
    followHttpPrefix = httpPrefix
    if not domain:
        domain = getConfigParam(baseDir, 'domain')
    signingPrivateKeyPem = None
    if args.secureMode:
        signingPrivateKeyPem = getInstanceActorKey(baseDir, domain)

    followingJson = \
        getFollowingViaServer(baseDir, session,
                              args.nickname, args.password,
                              domain, port,
                              httpPrefix, args.pageNumber,
                              cachedWebfingers, personCache,
                              debug, __version__, signingPrivateKeyPem)
    if followingJson:
        pprint(followingJson)
    sys.exit()

if args.followersList:
    # following list via c2s protocol
    if not args.nickname:
        print('Please specify the nickname for the account with --nickname')
        sys.exit()
    if not args.password:
        args.password = getpass.getpass('Password: ')
        if not args.password:
            print('Specify a password with the --password option')
            sys.exit()
    args.password = args.password.replace('\n', '')

    session = createSession(proxyType)
    personCache = {}
    cachedWebfingers = {}
    followHttpPrefix = httpPrefix
    if not domain:
        domain = getConfigParam(baseDir, 'domain')
    signingPrivateKeyPem = None
    if args.secureMode:
        signingPrivateKeyPem = getInstanceActorKey(baseDir, domain)

    followersJson = \
        getFollowersViaServer(baseDir, session,
                              args.nickname, args.password,
                              domain, port,
                              httpPrefix, args.pageNumber,
                              cachedWebfingers, personCache,
                              debug, __version__,
                              signingPrivateKeyPem)
    if followersJson:
        pprint(followersJson)
    sys.exit()

if args.followRequestsList:
    # follow requests list via c2s protocol
    if not args.nickname:
        print('Please specify the nickname for the account with --nickname')
        sys.exit()
    if not args.password:
        args.password = getpass.getpass('Password: ')
        if not args.password:
            print('Specify a password with the --password option')
            sys.exit()
    args.password = args.password.replace('\n', '')

    session = createSession(proxyType)
    personCache = {}
    cachedWebfingers = {}
    followHttpPrefix = httpPrefix
    if not domain:
        domain = getConfigParam(baseDir, 'domain')
    signingPrivateKeyPem = None
    if args.secureMode:
        signingPrivateKeyPem = getInstanceActorKey(baseDir, domain)

    followRequestsJson = \
        getFollowRequestsViaServer(baseDir, session,
                                   args.nickname, args.password,
                                   domain, port,
                                   httpPrefix, args.pageNumber,
                                   cachedWebfingers, personCache,
                                   debug, __version__, signingPrivateKeyPem)
    if followRequestsJson:
        pprint(followRequestsJson)
    sys.exit()

nickname = 'admin'
if args.domain:
    domain = args.domain
    setConfigParam(baseDir, 'domain', domain)
if args.port:
    port = args.port
    setConfigParam(baseDir, 'port', port)
if args.proxyPort:
    proxyPort = args.proxyPort
    setConfigParam(baseDir, 'proxyPort', proxyPort)
if args.gnunet:
    httpPrefix = 'gnunet'
if args.dat or args.hyper:
    httpPrefix = 'hyper'
if args.i2p:
    httpPrefix = 'http'

if args.migrations:
    cachedWebfingers = {}
    if args.http or domain.endswith('.onion'):
        httpPrefix = 'http'
        port = 80
        proxyType = 'tor'
    elif domain.endswith('.i2p'):
        httpPrefix = 'http'
        port = 80
        proxyType = 'i2p'
    elif args.gnunet:
        httpPrefix = 'gnunet'
        port = 80
        proxyType = 'gnunet'
    else:
        httpPrefix = 'https'
        port = 443
    session = createSession(proxyType)
    if not domain:
        domain = getConfigParam(baseDir, 'domain')
    signingPrivateKeyPem = None
    if args.secureMode:
        signingPrivateKeyPem = getInstanceActorKey(baseDir, domain)
    ctr = migrateAccounts(baseDir, session,
                          httpPrefix, cachedWebfingers,
                          True, signingPrivateKeyPem)
    if ctr == 0:
        print('No followed accounts have moved')
    else:
        print(str(ctr) + ' followed accounts were migrated')
    sys.exit()

if args.actor:
    if not domain:
        domain = getConfigParam(baseDir, 'domain')
    signingPrivateKeyPem = getInstanceActorKey(baseDir, domain)
    if debug:
        print('baseDir: ' + str(baseDir))
        if signingPrivateKeyPem:
            print('Obtained instance actor signing key')
        else:
            print('Did not obtain instance actor key for ' + domain)
    getActorJson(domain, args.actor, args.http, args.gnunet,
                 debug, False, signingPrivateKeyPem)
    sys.exit()

if args.followers:
    originalActor = args.followers
    if '/@' in args.followers or \
       '/users/' in args.followers or \
       args.followers.startswith('http') or \
       args.followers.startswith('hyper'):
        # format: https://domain/@nick
        prefixes = getProtocolPrefixes()
        for prefix in prefixes:
            args.followers = args.followers.replace(prefix, '')
        args.followers = args.followers.replace('/@', '/users/')
        if not hasUsersPath(args.followers):
            print('Expected actor format: ' +
                  'https://domain/@nick or https://domain/users/nick')
            sys.exit()
        if '/users/' in args.followers:
            nickname = args.followers.split('/users/')[1]
            nickname = nickname.replace('\n', '').replace('\r', '')
            domain = args.followers.split('/users/')[0]
        elif '/profile/' in args.followers:
            nickname = args.followers.split('/profile/')[1]
            nickname = nickname.replace('\n', '').replace('\r', '')
            domain = args.followers.split('/profile/')[0]
        elif '/channel/' in args.followers:
            nickname = args.followers.split('/channel/')[1]
            nickname = nickname.replace('\n', '').replace('\r', '')
            domain = args.followers.split('/channel/')[0]
        elif '/accounts/' in args.followers:
            nickname = args.followers.split('/accounts/')[1]
            nickname = nickname.replace('\n', '').replace('\r', '')
            domain = args.followers.split('/accounts/')[0]
        elif '/u/' in args.followers:
            nickname = args.followers.split('/u/')[1]
            nickname = nickname.replace('\n', '').replace('\r', '')
            domain = args.followers.split('/u/')[0]
        elif '/c/' in args.followers:
            nickname = args.followers.split('/c/')[1]
            nickname = nickname.replace('\n', '').replace('\r', '')
            domain = args.followers.split('/c/')[0]
    else:
        # format: @nick@domain
        if '@' not in args.followers:
            print('Syntax: --actor nickname@domain')
            sys.exit()
        if args.followers.startswith('@'):
            args.followers = args.followers[1:]
        if '@' not in args.followers:
            print('Syntax: --actor nickname@domain')
            sys.exit()
        nickname = args.followers.split('@')[0]
        domain = args.followers.split('@')[1]
        domain = domain.replace('\n', '').replace('\r', '')
    cachedWebfingers = {}
    if args.http or domain.endswith('.onion'):
        httpPrefix = 'http'
        port = 80
        proxyType = 'tor'
    elif domain.endswith('.i2p'):
        httpPrefix = 'http'
        port = 80
        proxyType = 'i2p'
    elif args.gnunet:
        httpPrefix = 'gnunet'
        port = 80
        proxyType = 'gnunet'
    else:
        httpPrefix = 'https'
        port = 443
    session = createSession(proxyType)
    if nickname == 'inbox':
        nickname = domain

    hostDomain = None
    if args.domain:
        hostDomain = args.domain
    handle = nickname + '@' + domain
    signingPrivateKeyPem = None
    if args.secureMode:
        signingPrivateKeyPem = getInstanceActorKey(baseDir, domain)
    wfRequest = webfingerHandle(session, handle,
                                httpPrefix, cachedWebfingers,
                                hostDomain, __version__, debug, False,
                                signingPrivateKeyPem)
    if not wfRequest:
        print('Unable to webfinger ' + handle)
        sys.exit()
    if not isinstance(wfRequest, dict):
        print('Webfinger for ' + handle + ' did not return a dict. ' +
              str(wfRequest))
        sys.exit()

    personUrl = None
    if wfRequest.get('errors'):
        print('wfRequest error: ' + str(wfRequest['errors']))
        if hasUsersPath(args.followers):
            personUrl = originalActor
        else:
            sys.exit()

    profileStr = 'https://www.w3.org/ns/activitystreams'
    asHeader = {
        'Accept': 'application/activity+json; profile="' + profileStr + '"'
    }
    if not personUrl:
        personUrl = getUserUrl(wfRequest)
    if nickname == domain:
        personUrl = personUrl.replace('/users/', '/actor/')
        personUrl = personUrl.replace('/accounts/', '/actor/')
        personUrl = personUrl.replace('/channel/', '/actor/')
        personUrl = personUrl.replace('/profile/', '/actor/')
        personUrl = personUrl.replace('/u/', '/actor/')
        personUrl = personUrl.replace('/c/', '/actor/')
    if not personUrl:
        # try single user instance
        personUrl = httpPrefix + '://' + domain
        profileStr = 'https://www.w3.org/ns/activitystreams'
        asHeader = {
            'Accept': 'application/ld+json; profile="' + profileStr + '"'
        }
    if '/channel/' in personUrl or '/accounts/' in personUrl:
        profileStr = 'https://www.w3.org/ns/activitystreams'
        asHeader = {
            'Accept': 'application/ld+json; profile="' + profileStr + '"'
        }
    signingPrivateKeyPem = None
    if args.secureMode:
        signingPrivateKeyPem = getInstanceActorKey(baseDir, domain)
    followersList = \
        downloadFollowCollection(signingPrivateKeyPem,
                                 'followers', session,
                                 httpPrefix, personUrl, 1, 3)
    if followersList:
        for actor in followersList:
            print(actor)
    sys.exit()

if args.addaccount:
    if '@' in args.addaccount:
        nickname = args.addaccount.split('@')[0]
        domain = args.addaccount.split('@')[1]
    else:
        nickname = args.addaccount
        if not args.domain or not getConfigParam(baseDir, 'domain'):
            print('Use the --domain option to set the domain name')
            sys.exit()

    configuredDomain = getConfigParam(baseDir, 'domain')
    if configuredDomain:
        if domain != configuredDomain:
            print('The account domain is expected to be ' + configuredDomain)
            sys.exit()

    if not validNickname(domain, nickname):
        print(nickname + ' is a reserved name. Use something different.')
        sys.exit()

    if not args.password:
        args.password = getpass.getpass('Password: ')
        if not args.password:
            print('Specify a password with the --password option')
            sys.exit()
    args.password = args.password.replace('\n', '')
    if len(args.password.strip()) < 8:
        print('Password should be at least 8 characters')
        sys.exit()
    accountDir = acctDir(baseDir, nickname, domain)
    if os.path.isdir(accountDir):
        print('Account already exists')
        sys.exit()
    if os.path.isdir(baseDir + '/deactivated/' + nickname + '@' + domain):
        print('Account is deactivated')
        sys.exit()
    if domain.endswith('.onion') or \
       domain.endswith('.i2p'):
        port = 80
        httpPrefix = 'http'
    createPerson(baseDir, nickname, domain, port, httpPrefix,
                 True, not args.noapproval, args.password.strip())
    if os.path.isdir(accountDir):
        print('Account created for ' + nickname + '@' + domain)
    else:
        print('Account creation failed')
    sys.exit()

if args.addgroup:
    if '@' in args.addgroup:
        nickname = args.addgroup.split('@')[0]
        domain = args.addgroup.split('@')[1]
    else:
        nickname = args.addgroup
        if not args.domain or not getConfigParam(baseDir, 'domain'):
            print('Use the --domain option to set the domain name')
            sys.exit()
    if nickname.startswith('!'):
        # remove preceding group indicator
        nickname = nickname[1:]
    if not validNickname(domain, nickname):
        print(nickname + ' is a reserved name. Use something different.')
        sys.exit()
    if not args.password:
        args.password = getpass.getpass('Password: ')
        if not args.password:
            print('Specify a password with the --password option')
            sys.exit()
    args.password = args.password.replace('\n', '')
    if len(args.password.strip()) < 8:
        print('Password should be at least 8 characters')
        sys.exit()
    accountDir = acctDir(baseDir, nickname, domain)
    if os.path.isdir(accountDir):
        print('Group already exists')
        sys.exit()
    createGroup(baseDir, nickname, domain, port, httpPrefix,
                True, args.password.strip())
    if os.path.isdir(accountDir):
        print('Group created for ' + nickname + '@' + domain)
    else:
        print('Group creation failed')
    sys.exit()

if args.rmgroup:
    args.rmaccount = args.rmgroup

if args.deactivate:
    args.rmaccount = args.deactivate

if args.rmaccount:
    if '@' in args.rmaccount:
        nickname = args.rmaccount.split('@')[0]
        domain = args.rmaccount.split('@')[1]
    else:
        nickname = args.rmaccount
        if not args.domain or not getConfigParam(baseDir, 'domain'):
            print('Use the --domain option to set the domain name')
            sys.exit()
        if args.domain:
            domain = args.domain
        else:
            domain = getConfigParam(baseDir, 'domain')

    configuredDomain = getConfigParam(baseDir, 'domain')
    if configuredDomain:
        if domain != configuredDomain:
            print('The account domain is expected to be ' + configuredDomain)
            sys.exit()

    if args.deactivate:
        if deactivateAccount(baseDir, nickname, domain):
            print('Account for ' + nickname + '@' + domain +
                  ' was deactivated')
        else:
            print('Account for ' + nickname + '@' + domain + ' was not found')
        sys.exit()
    if removeAccount(baseDir, nickname, domain, port):
        if not args.rmgroup:
            print('Account for ' + nickname + '@' + domain + ' was removed')
        else:
            print('Group ' + nickname + '@' + domain + ' was removed')
        sys.exit()

if args.activate:
    if '@' in args.activate:
        nickname = args.activate.split('@')[0]
        domain = args.activate.split('@')[1]
    else:
        nickname = args.activate
        if not args.domain or not getConfigParam(baseDir, 'domain'):
            print('Use the --domain option to set the domain name')
            sys.exit()
    if activateAccount(baseDir, nickname, domain):
        print('Account for ' + nickname + '@' + domain + ' was activated')
    else:
        print('Deactivated account for ' + nickname + '@' + domain +
              ' was not found')
    sys.exit()

if args.changepassword:
    if len(args.changepassword) != 2:
        print('--changepassword [nickname] [new password]')
        sys.exit()
    if '@' in args.changepassword[0]:
        nickname = args.changepassword[0].split('@')[0]
        domain = args.changepassword[0].split('@')[1]
    else:
        nickname = args.changepassword[0]
        if not args.domain or not getConfigParam(baseDir, 'domain'):
            print('Use the --domain option to set the domain name')
            sys.exit()
    newPassword = args.changepassword[1]
    if len(newPassword) < 8:
        print('Password should be at least 8 characters')
        sys.exit()
    accountDir = acctDir(baseDir, nickname, domain)
    if not os.path.isdir(accountDir):
        print('Account ' + nickname + '@' + domain + ' not found')
        sys.exit()
    passwordFile = baseDir + '/accounts/passwords'
    if os.path.isfile(passwordFile):
        if nickname + ':' in open(passwordFile).read():
            storeBasicCredentials(baseDir, nickname, newPassword)
            print('Password for ' + nickname + ' was changed')
        else:
            print(nickname + ' is not in the passwords file')
    else:
        print('Passwords file not found')
    sys.exit()

if args.archive:
    if args.archive.lower().endswith('null') or \
       args.archive.lower().endswith('delete') or \
       args.archive.lower().endswith('none'):
        args.archive = None
        print('Archiving with deletion of old posts...')
    else:
        print('Archiving to ' + args.archive + '...')
    archiveMedia(baseDir, args.archive, args.archiveWeeks)
    archivePosts(baseDir, httpPrefix, args.archive, {}, args.archiveMaxPosts)
    print('Archiving complete')
    sys.exit()

if not args.domain and not domain:
    print('Specify a domain with --domain [name]')
    sys.exit()

if args.avatar:
    if not os.path.isfile(args.avatar):
        print(args.avatar + ' is not an image filename')
        sys.exit()
    if not args.nickname:
        print('Specify a nickname with --nickname [name]')
        sys.exit()
    city = 'London, England'
    if setProfileImage(baseDir, httpPrefix, args.nickname, domain,
                       port, args.avatar, 'avatar', '128x128', city):
        print('Avatar added for ' + args.nickname)
    else:
        print('Avatar was not added for ' + args.nickname)
    sys.exit()

if args.backgroundImage:
    if not os.path.isfile(args.backgroundImage):
        print(args.backgroundImage + ' is not an image filename')
        sys.exit()
    if not args.nickname:
        print('Specify a nickname with --nickname [name]')
        sys.exit()
    city = 'London, England'
    if setProfileImage(baseDir, httpPrefix, args.nickname, domain,
                       port, args.backgroundImage, 'background',
                       '256x256', city):
        print('Background image added for ' + args.nickname)
    else:
        print('Background image was not added for ' + args.nickname)
    sys.exit()

if args.skill:
    if not nickname:
        print('Specify a nickname with the --nickname option')
        sys.exit()

    if not args.password:
        args.password = getpass.getpass('Password: ')
        if not args.password:
            print('Specify a password with the --password option')
            sys.exit()
    args.password = args.password.replace('\n', '')

    if not args.skillLevelPercent:
        print('Specify a skill level in the range 0-100')
        sys.exit()

    if int(args.skillLevelPercent) < 0 or \
       int(args.skillLevelPercent) > 100:
        print('Skill level should be a percentage in the range 0-100')
        sys.exit()

    session = createSession(proxyType)
    personCache = {}
    cachedWebfingers = {}
    if not domain:
        domain = getConfigParam(baseDir, 'domain')
    signingPrivateKeyPem = None
    if args.secureMode:
        signingPrivateKeyPem = getInstanceActorKey(baseDir, domain)
    print('Sending ' + args.skill + ' skill level ' +
          str(args.skillLevelPercent) + ' for ' + nickname)

    sendSkillViaServer(baseDir, session,
                       nickname, args.password,
                       domain, port,
                       httpPrefix,
                       args.skill, args.skillLevelPercent,
                       cachedWebfingers, personCache,
                       True, __version__, signingPrivateKeyPem)
    for i in range(10):
        # TODO detect send success/fail
        time.sleep(1)
    sys.exit()

if args.availability:
    if not nickname:
        print('Specify a nickname with the --nickname option')
        sys.exit()

    if not args.password:
        args.password = getpass.getpass('Password: ')
        if not args.password:
            print('Specify a password with the --password option')
            sys.exit()
    args.password = args.password.replace('\n', '')

    session = createSession(proxyType)
    personCache = {}
    cachedWebfingers = {}
    if not domain:
        domain = getConfigParam(baseDir, 'domain')
    signingPrivateKeyPem = None
    if args.secureMode:
        signingPrivateKeyPem = getInstanceActorKey(baseDir, domain)
    print('Sending availability status of ' + nickname +
          ' as ' + args.availability)

    sendAvailabilityViaServer(baseDir, session, nickname, args.password,
                              domain, port,
                              httpPrefix,
                              args.availability,
                              cachedWebfingers, personCache,
                              True, __version__, signingPrivateKeyPem)
    for i in range(10):
        # TODO detect send success/fail
        time.sleep(1)
    sys.exit()

if args.desktop:
    # Announce posts as they arrive in your inbox using text-to-speech
    if args.desktop.startswith('@'):
        args.desktop = args.desktop[1:]
    if '@' not in args.desktop:
        print('Specify the handle to notify: nickname@domain')
        sys.exit()
    nickname = args.desktop.split('@')[0]
    domain = args.desktop.split('@')[1]

    if not nickname:
        print('Specify a nickname with the --nickname option')
        sys.exit()

    if not args.password:
        args.password = getpass.getpass('Password: ')
        if not args.password:
            print('Specify a password with the --password option')
            sys.exit()

    args.password = args.password.replace('\n', '')

    proxyType = None
    if args.tor or domain.endswith('.onion'):
        proxyType = 'tor'
        if domain.endswith('.onion'):
            args.port = 80
    elif args.i2p or domain.endswith('.i2p'):
        proxyType = 'i2p'
        if domain.endswith('.i2p'):
            args.port = 80
    elif args.gnunet:
        proxyType = 'gnunet'

    # only store inbox posts if we are not running as a daemon
    storeInboxPosts = not args.noKeyPress

    runDesktopClient(baseDir, proxyType, httpPrefix,
                     nickname, domain, port, args.password,
                     args.screenreader, args.language,
                     args.notificationSounds,
                     args.notificationType,
                     args.noKeyPress,
                     storeInboxPosts,
                     args.notifyShowNewPosts,
                     args.language,
                     args.debug, args.lowBandwidth)
    sys.exit()

if federationList:
    print('Federating with: ' + str(federationList))
if args.sharedItemsFederatedDomains:
    print('Federating shared items with: ' +
          args.sharedItemsFederatedDomains)

sharedItemsFederatedDomains = []
if args.sharedItemsFederatedDomains:
    sharedItemsFederatedDomainsStr = args.sharedItemsFederatedDomains
    setConfigParam(baseDir, 'sharedItemsFederatedDomains',
                   sharedItemsFederatedDomainsStr)
else:
    sharedItemsFederatedDomainsStr = \
        getConfigParam(baseDir, 'sharedItemsFederatedDomains')
if sharedItemsFederatedDomainsStr:
    sharedItemsFederatedDomainsList = sharedItemsFederatedDomainsStr.split(',')
    for sharedFederatedDomain in sharedItemsFederatedDomainsList:
        sharedItemsFederatedDomains.append(sharedFederatedDomain.strip())

if args.block:
    if not nickname:
        print('Specify a nickname with the --nickname option')
        sys.exit()

    if not args.password:
        args.password = getpass.getpass('Password: ')
        if not args.password:
            print('Specify a password with the --password option')
            sys.exit()
    args.password = args.password.replace('\n', '')

    if '@' in args.block:
        blockedDomain = args.block.split('@')[1]
        blockedDomain = blockedDomain.replace('\n', '').replace('\r', '')
        blockedNickname = args.block.split('@')[0]
        blockedActor = httpPrefix + '://' + blockedDomain + \
            '/users/' + blockedNickname
        args.block = blockedActor
    else:
        if '/users/' not in args.block:
            print(args.block + ' does not look like an actor url')
            sys.exit()

    session = createSession(proxyType)
    personCache = {}
    cachedWebfingers = {}
    if not domain:
        domain = getConfigParam(baseDir, 'domain')
    signingPrivateKeyPem = None
    if args.secureMode:
        signingPrivateKeyPem = getInstanceActorKey(baseDir, domain)
    print('Sending block of ' + args.block)

    sendBlockViaServer(baseDir, session, nickname, args.password,
                       domain, port,
                       httpPrefix, args.block,
                       cachedWebfingers, personCache,
                       True, __version__, signingPrivateKeyPem)
    for i in range(10):
        # TODO detect send success/fail
        time.sleep(1)
    sys.exit()

if args.mute:
    if not nickname:
        print('Specify a nickname with the --nickname option')
        sys.exit()

    if not args.password:
        args.password = getpass.getpass('Password: ')
        if not args.password:
            print('Specify a password with the --password option')
            sys.exit()
    args.password = args.password.replace('\n', '')

    session = createSession(proxyType)
    personCache = {}
    cachedWebfingers = {}
    if not domain:
        domain = getConfigParam(baseDir, 'domain')
    signingPrivateKeyPem = None
    if args.secureMode:
        signingPrivateKeyPem = getInstanceActorKey(baseDir, domain)
    print('Sending mute of ' + args.mute)

    sendMuteViaServer(baseDir, session, nickname, args.password,
                      domain, port,
                      httpPrefix, args.mute,
                      cachedWebfingers, personCache,
                      True, __version__, signingPrivateKeyPem)
    for i in range(10):
        # TODO detect send success/fail
        time.sleep(1)
    sys.exit()

if args.unmute:
    if not nickname:
        print('Specify a nickname with the --nickname option')
        sys.exit()

    if not args.password:
        args.password = getpass.getpass('Password: ')
        if not args.password:
            print('Specify a password with the --password option')
            sys.exit()
    args.password = args.password.replace('\n', '')

    session = createSession(proxyType)
    personCache = {}
    cachedWebfingers = {}
    if not domain:
        domain = getConfigParam(baseDir, 'domain')
    signingPrivateKeyPem = None
    if args.secureMode:
        signingPrivateKeyPem = getInstanceActorKey(baseDir, domain)
    print('Sending undo mute of ' + args.unmute)

    sendUndoMuteViaServer(baseDir, session, nickname, args.password,
                          domain, port,
                          httpPrefix, args.unmute,
                          cachedWebfingers, personCache,
                          True, __version__, signingPrivateKeyPem)
    for i in range(10):
        # TODO detect send success/fail
        time.sleep(1)
    sys.exit()

if args.unblock:
    if not nickname:
        print('Specify a nickname with the --nickname option')
        sys.exit()

    if not args.password:
        args.password = getpass.getpass('Password: ')
        if not args.password:
            print('Specify a password with the --password option')
            sys.exit()
    args.password = args.password.replace('\n', '')

    if '@' in args.unblock:
        blockedDomain = args.unblock.split('@')[1]
        blockedDomain = blockedDomain.replace('\n', '').replace('\r', '')
        blockedNickname = args.unblock.split('@')[0]
        blockedActor = httpPrefix + '://' + blockedDomain + \
            '/users/' + blockedNickname
        args.unblock = blockedActor
    else:
        if '/users/' not in args.unblock:
            print(args.unblock + ' does not look like an actor url')
            sys.exit()

    session = createSession(proxyType)
    personCache = {}
    cachedWebfingers = {}
    if not domain:
        domain = getConfigParam(baseDir, 'domain')
    signingPrivateKeyPem = None
    if args.secureMode:
        signingPrivateKeyPem = getInstanceActorKey(baseDir, domain)
    print('Sending undo block of ' + args.unblock)

    sendUndoBlockViaServer(baseDir, session, nickname, args.password,
                           domain, port,
                           httpPrefix, args.unblock,
                           cachedWebfingers, personCache,
                           True, __version__, signingPrivateKeyPem)
    for i in range(10):
        # TODO detect send success/fail
        time.sleep(1)
    sys.exit()

if args.filterStr:
    if not args.nickname:
        print('Please specify a nickname')
        sys.exit()
    if addFilter(baseDir, args.nickname, domain, args.filterStr):
        print('Filter added to ' + args.nickname + ': ' + args.filterStr)
    sys.exit()

if args.unfilterStr:
    if not args.nickname:
        print('Please specify a nickname')
        sys.exit()
    if removeFilter(baseDir, args.nickname, domain, args.unfilterStr):
        print('Filter removed from ' + args.nickname + ': ' + args.unfilterStr)
    sys.exit()

if args.testdata:
    args.language = 'en'
    city = 'London, England'
    nickname = 'testuser567'
    password = 'boringpassword'
    print('Generating some test data for user: ' + nickname)

    if os.path.isdir(baseDir + '/tags'):
        shutil.rmtree(baseDir + '/tags')
    if os.path.isdir(baseDir + '/accounts'):
        shutil.rmtree(baseDir + '/accounts')
    if os.path.isdir(baseDir + '/keys'):
        shutil.rmtree(baseDir + '/keys')
    if os.path.isdir(baseDir + '/media'):
        shutil.rmtree(baseDir + '/media')
    if os.path.isdir(baseDir + '/sharefiles'):
        shutil.rmtree(baseDir + '/sharefiles')
    if os.path.isdir(baseDir + '/wfendpoints'):
        shutil.rmtree(baseDir + '/wfendpoints')

    setConfigParam(baseDir, 'registrationsRemaining',
                   str(maxRegistrations))

    createPerson(baseDir, 'maxboardroom', domain, port, httpPrefix,
                 True, False, password)
    createPerson(baseDir, 'ultrapancake', domain, port, httpPrefix,
                 True, False, password)
    createPerson(baseDir, 'drokk', domain, port, httpPrefix,
                 True, False, password)
    createPerson(baseDir, 'sausagedog', domain, port, httpPrefix,
                 True, False, password)

    createPerson(baseDir, nickname, domain, port, httpPrefix,
                 True, False, 'likewhateveryouwantscoob')
    setSkillLevel(baseDir, nickname, domain, 'testing', 60)
    setSkillLevel(baseDir, nickname, domain, 'typing', 50)
    setRole(baseDir, nickname, domain, 'admin')
    setAvailability(baseDir, nickname, domain, 'busy')

    addShare(baseDir,
             httpPrefix, nickname, domain, port,
             "spanner",
             "It's a spanner",
             "img/shares1.png",
             1, "tool",
             "mechanical",
             "City", "0", "GBP",
             "2 months",
             debug, city, args.language, {}, 'shares', args.lowBandwidth)
    addShare(baseDir,
             httpPrefix, nickname, domain, port,
             "witch hat",
             "Spooky",
             "img/shares2.png",
             1, "hat",
             "clothing",
             "City", "0", "GBP",
             "3 months",
             debug, city, args.language, {}, 'shares', args.lowBandwidth)

    deleteAllPosts(baseDir, nickname, domain, 'inbox')
    deleteAllPosts(baseDir, nickname, domain, 'outbox')

    testFollowersOnly = False
    testSaveToFile = True
    testC2S = False
    testCommentsEnabled = True
    testAttachImageFilename = None
    testMediaType = None
    testImageDescription = None
    testCity = 'London, England'
    testInReplyTo = None
    testInReplyToAtomUri = None
    testSubject = None
    testSchedulePost = False
    testEventDate = None
    testEventTime = None
    testLocation = None
    testIsArticle = False
    conversationId = None
    lowBandwidth = False

    createPublicPost(baseDir, nickname, domain, port, httpPrefix,
                     "like this is totally just a #test man",
                     testFollowersOnly,
                     testSaveToFile,
                     testC2S,
                     testCommentsEnabled,
                     testAttachImageFilename,
                     testMediaType, testImageDescription, testCity,
                     testInReplyTo, testInReplyToAtomUri,
                     testSubject, testSchedulePost,
                     testEventDate, testEventTime, testLocation,
                     testIsArticle, args.language, conversationId,
                     lowBandwidth)
    createPublicPost(baseDir, nickname, domain, port, httpPrefix,
                     "Zoiks!!!",
                     testFollowersOnly,
                     testSaveToFile,
                     testC2S,
                     testCommentsEnabled,
                     testAttachImageFilename,
                     testMediaType, testImageDescription, testCity,
                     testInReplyTo, testInReplyToAtomUri,
                     testSubject, testSchedulePost,
                     testEventDate, testEventTime, testLocation,
                     testIsArticle, args.language, conversationId,
                     lowBandwidth)
    createPublicPost(baseDir, nickname, domain, port, httpPrefix,
                     "Hey scoob we need like a hundred more #milkshakes",
                     testFollowersOnly,
                     testSaveToFile,
                     testC2S,
                     testCommentsEnabled,
                     testAttachImageFilename,
                     testMediaType, testImageDescription, testCity,
                     testInReplyTo, testInReplyToAtomUri,
                     testSubject, testSchedulePost,
                     testEventDate, testEventTime, testLocation,
                     testIsArticle, args.language, conversationId,
                     lowBandwidth)
    createPublicPost(baseDir, nickname, domain, port, httpPrefix,
                     "Getting kinda spooky around here",
                     testFollowersOnly,
                     testSaveToFile,
                     testC2S,
                     testCommentsEnabled,
                     testAttachImageFilename,
                     testMediaType, testImageDescription, testCity,
                     'someone', testInReplyToAtomUri,
                     testSubject, testSchedulePost,
                     testEventDate, testEventTime, testLocation,
                     testIsArticle, args.language, conversationId,
                     lowBandwidth)
    createPublicPost(baseDir, nickname, domain, port, httpPrefix,
                     "And they would have gotten away with it too" +
                     "if it wasn't for those pesky hackers",
                     testFollowersOnly,
                     testSaveToFile,
                     testC2S,
                     testCommentsEnabled,
                     'img/logo.png', 'image/png',
                     'Description of image', testCity,
                     testInReplyTo, testInReplyToAtomUri,
                     testSubject, testSchedulePost,
                     testEventDate, testEventTime, testLocation,
                     testIsArticle, args.language, conversationId,
                     lowBandwidth)
    createPublicPost(baseDir, nickname, domain, port, httpPrefix,
                     "man these centralized sites are like the worst!",
                     testFollowersOnly,
                     testSaveToFile,
                     testC2S,
                     testCommentsEnabled,
                     testAttachImageFilename,
                     testMediaType, testImageDescription, testCity,
                     testInReplyTo, testInReplyToAtomUri,
                     testSubject, testSchedulePost,
                     testEventDate, testEventTime, testLocation,
                     testIsArticle, args.language, conversationId,
                     lowBandwidth)
    createPublicPost(baseDir, nickname, domain, port, httpPrefix,
                     "another mystery solved #test",
                     testFollowersOnly,
                     testSaveToFile,
                     testC2S,
                     testCommentsEnabled,
                     testAttachImageFilename,
                     testMediaType, testImageDescription, testCity,
                     testInReplyTo, testInReplyToAtomUri,
                     testSubject, testSchedulePost,
                     testEventDate, testEventTime, testLocation,
                     testIsArticle, args.language, conversationId,
                     lowBandwidth)
    createPublicPost(baseDir, nickname, domain, port, httpPrefix,
                     "let's go bowling",
                     testFollowersOnly,
                     testSaveToFile,
                     testC2S,
                     testCommentsEnabled,
                     testAttachImageFilename,
                     testMediaType, testImageDescription, testCity,
                     testInReplyTo, testInReplyToAtomUri,
                     testSubject, testSchedulePost,
                     testEventDate, testEventTime, testLocation,
                     testIsArticle, args.language, conversationId,
                     lowBandwidth)
    domainFull = domain + ':' + str(port)
    clearFollows(baseDir, nickname, domain)
    followPerson(baseDir, nickname, domain, 'maxboardroom', domainFull,
                 federationList, False, False)
    followPerson(baseDir, nickname, domain, 'ultrapancake', domainFull,
                 federationList, False, False)
    followPerson(baseDir, nickname, domain, 'sausagedog', domainFull,
                 federationList, False, False)
    followPerson(baseDir, nickname, domain, 'drokk', domainFull,
                 federationList, False, False)
    followerOfPerson(baseDir, nickname, domain, 'drokk', domainFull,
                     federationList, False, False)
    followerOfPerson(baseDir, nickname, domain, 'maxboardroom', domainFull,
                     federationList, False, False)
    setConfigParam(baseDir, 'admin', nickname)

# set a lower bound to the maximum mentions
# so that it can't be accidentally set to zero and disable replies
if args.maxMentions < 4:
    args.maxMentions = 4

registration = getConfigParam(baseDir, 'registration')
if not registration:
    registration = False

minimumvotes = getConfigParam(baseDir, 'minvotes')
if minimumvotes:
    args.minimumvotes = int(minimumvotes)

votingtime = getConfigParam(baseDir, 'votingtime')
if votingtime:
    args.votingtime = votingtime

# only show the date at the bottom of posts
dateonly = getConfigParam(baseDir, 'dateonly')
if dateonly:
    args.dateonly = dateonly

# set the maximum number of newswire posts per account or rss feed
maxNewswirePostsPerSource = \
    getConfigParam(baseDir, 'maxNewswirePostsPerSource')
if maxNewswirePostsPerSource:
    args.maxNewswirePostsPerSource = int(maxNewswirePostsPerSource)

# set the maximum number of newswire posts appearing in the right column
maxNewswirePosts = \
    getConfigParam(baseDir, 'maxNewswirePosts')
if maxNewswirePosts:
    args.maxNewswirePosts = int(maxNewswirePosts)

# set the maximum size of a newswire rss/atom feed in Kilobytes
maxNewswireFeedSizeKb = \
    getConfigParam(baseDir, 'maxNewswireFeedSizeKb')
if maxNewswireFeedSizeKb:
    args.maxNewswireFeedSizeKb = int(maxNewswireFeedSizeKb)

maxMirroredArticles = \
    getConfigParam(baseDir, 'maxMirroredArticles')
if maxMirroredArticles is not None:
    args.maxMirroredArticles = int(maxMirroredArticles)

maxNewsPosts = \
    getConfigParam(baseDir, 'maxNewsPosts')
if maxNewsPosts is not None:
    args.maxNewsPosts = int(maxNewsPosts)

maxFollowers = \
    getConfigParam(baseDir, 'maxFollowers')
if maxFollowers is not None:
    args.maxFollowers = int(maxFollowers)

maxFeedItemSizeKb = \
    getConfigParam(baseDir, 'maxFeedItemSizeKb')
if maxFeedItemSizeKb is not None:
    args.maxFeedItemSizeKb = int(maxFeedItemSizeKb)

dormantMonths = \
    getConfigParam(baseDir, 'dormantMonths')
if dormantMonths is not None:
    args.dormantMonths = int(dormantMonths)

sendThreadsTimeoutMins = \
    getConfigParam(baseDir, 'sendThreadsTimeoutMins')
if sendThreadsTimeoutMins is not None:
    args.sendThreadsTimeoutMins = int(sendThreadsTimeoutMins)

maxLikeCount = \
    getConfigParam(baseDir, 'maxLikeCount')
if maxLikeCount is not None:
    args.maxLikeCount = int(maxLikeCount)

showPublishAsIcon = \
    getConfigParam(baseDir, 'showPublishAsIcon')
if showPublishAsIcon is not None:
    args.showPublishAsIcon = bool(showPublishAsIcon)

iconsAsButtons = \
    getConfigParam(baseDir, 'iconsAsButtons')
if iconsAsButtons is not None:
    args.iconsAsButtons = bool(iconsAsButtons)

rssIconAtTop = \
    getConfigParam(baseDir, 'rssIconAtTop')
if rssIconAtTop is not None:
    args.rssIconAtTop = bool(rssIconAtTop)

publishButtonAtTop = \
    getConfigParam(baseDir, 'publishButtonAtTop')
if publishButtonAtTop is not None:
    args.publishButtonAtTop = bool(publishButtonAtTop)

fullWidthTimelineButtonHeader = \
    getConfigParam(baseDir, 'fullWidthTimelineButtonHeader')
if fullWidthTimelineButtonHeader is not None:
    args.fullWidthTimelineButtonHeader = bool(fullWidthTimelineButtonHeader)

allowLocalNetworkAccess = \
    getConfigParam(baseDir, 'allowLocalNetworkAccess')
if allowLocalNetworkAccess is not None:
    args.allowLocalNetworkAccess = bool(allowLocalNetworkAccess)

verifyAllSignatures = \
    getConfigParam(baseDir, 'verifyAllSignatures')
if verifyAllSignatures is not None:
    args.verifyAllSignatures = bool(verifyAllSignatures)

brochMode = \
    getConfigParam(baseDir, 'brochMode')
if brochMode is not None:
    args.brochMode = bool(brochMode)

logLoginFailures = \
    getConfigParam(baseDir, 'logLoginFailures')
if logLoginFailures is not None:
    args.logLoginFailures = bool(logLoginFailures)

showNodeInfoAccounts = \
    getConfigParam(baseDir, 'showNodeInfoAccounts')
if showNodeInfoAccounts is not None:
    args.showNodeInfoAccounts = bool(showNodeInfoAccounts)

showNodeInfoVersion = \
    getConfigParam(baseDir, 'showNodeInfoVersion')
if showNodeInfoVersion is not None:
    args.showNodeInfoVersion = bool(showNodeInfoVersion)

lowBandwidth = \
    getConfigParam(baseDir, 'lowBandwidth')
if lowBandwidth is not None:
    args.lowBandwidth = bool(lowBandwidth)

userAgentsBlocked = []
if args.userAgentBlocks:
    userAgentsBlockedStr = args.userAgentBlocks
    setConfigParam(baseDir, 'userAgentsBlocked', userAgentsBlockedStr)
else:
    userAgentsBlockedStr = \
        getConfigParam(baseDir, 'userAgentsBlocked')
if userAgentsBlockedStr:
    agentBlocksList = userAgentsBlockedStr.split(',')
    for agentBlockStr in agentBlocksList:
        userAgentsBlocked.append(agentBlockStr.strip())

city = \
    getConfigParam(baseDir, 'city')
if city is not None:
    args.city = city

YTDomain = getConfigParam(baseDir, 'youtubedomain')
if YTDomain:
    if '://' in YTDomain:
        YTDomain = YTDomain.split('://')[1]
    if '/' in YTDomain:
        YTDomain = YTDomain.split('/')[0]
    if '.' in YTDomain:
        args.YTReplacementDomain = YTDomain

twitterDomain = getConfigParam(baseDir, 'twitterdomain')
if twitterDomain:
    if '://' in twitterDomain:
        twitterDomain = twitterDomain.split('://')[1]
    if '/' in twitterDomain:
        twitterDomain = twitterDomain.split('/')[0]
    if '.' in twitterDomain:
        args.twitterReplacementDomain = twitterDomain

if setTheme(baseDir, themeName, domain,
            args.allowLocalNetworkAccess, args.language):
    print('Theme set to ' + themeName)

# whether new registrations are open or closed
if args.registration:
    if args.registration.lower() == 'open':
        registration = getConfigParam(baseDir, 'registration')
        if not registration:
            setConfigParam(baseDir, 'registrationsRemaining',
                           str(maxRegistrations))
        else:
            if registration != 'open':
                setConfigParam(baseDir, 'registrationsRemaining',
                               str(maxRegistrations))
        setConfigParam(baseDir, 'registration', 'open')
        print('New registrations open')
    else:
        setConfigParam(baseDir, 'registration', 'closed')
        print('New registrations closed')

defaultCurrency = getConfigParam(baseDir, 'defaultCurrency')
if not defaultCurrency:
    setConfigParam(baseDir, 'defaultCurrency', 'EUR')
if args.defaultCurrency:
    if args.defaultCurrency == args.defaultCurrency.upper():
        setConfigParam(baseDir, 'defaultCurrency', args.defaultCurrency)
        print('Default currency set to ' + args.defaultCurrency)

if __name__ == "__main__":
    runDaemon(args.defaultReplyIntervalHours,
              args.lowBandwidth, args.maxLikeCount,
              sharedItemsFederatedDomains,
              userAgentsBlocked,
              args.logLoginFailures,
              args.city,
              args.showNodeInfoAccounts,
              args.showNodeInfoVersion,
              args.brochMode,
              args.verifyAllSignatures,
              args.sendThreadsTimeoutMins,
              args.dormantMonths,
              args.maxNewswirePosts,
              args.allowLocalNetworkAccess,
              args.maxFeedItemSizeKb,
              args.publishButtonAtTop,
              args.rssIconAtTop,
              args.iconsAsButtons,
              args.fullWidthTimelineButtonHeader,
              args.showPublishAsIcon,
              args.maxFollowers,
              args.maxNewsPosts,
              args.maxMirroredArticles,
              args.maxNewswireFeedSizeKb,
              args.maxNewswirePostsPerSource,
              args.dateonly,
              args.votingtime,
              args.positivevoting,
              args.minimumvotes,
              args.newsinstance,
              args.blogsinstance, args.mediainstance,
              args.maxRecentPosts,
              not args.nosharedinbox,
              registration, args.language, __version__,
              instanceId, args.client, baseDir,
              domain, onionDomain, i2pDomain,
              args.YTReplacementDomain,
              args.twitterReplacementDomain,
              port, proxyPort, httpPrefix,
              federationList, args.maxMentions,
              args.maxEmoji, args.secureMode,
              proxyType, args.maxReplies,
              args.domainMaxPostsPerDay,
              args.accountMaxPostsPerDay,
              args.allowdeletion, debug, False,
              args.instanceOnlySkillsSearch, [],
              not args.noapproval)
