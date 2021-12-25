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
from session import downloadHtml
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
from reaction import sendReactionViaServer
from reaction import sendUndoReactionViaServer
from reaction import validEmojiContent
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
parser.add_argument('--content_license_url', type=str,
                    default='https://creativecommons.org/licenses/by/4.0',
                    help='Url of the license used for the instance content')
parser.add_argument('--lists_enabled', type=str,
                    default=None,
                    help='Names of content warning lists enabled. ' +
                    'See the cwlists directory')
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
                    dest='max_newswire_postsPerSource', type=int,
                    default=4,
                    help='Maximum newswire posts per feed or account')
parser.add_argument('--dormant_months',
                    dest='dormant_months', type=int,
                    default=3,
                    help='How many months does a followed account need to ' +
                    'be unseen for before being considered dormant')
parser.add_argument('--default_reply_interval_hrs',
                    dest='default_reply_interval_hrs', type=int,
                    default=1000,
                    help='How many hours after publication of a post ' +
                    'are replies to it permitted')
parser.add_argument('--send_threads_timeout_mins',
                    dest='send_threads_timeout_mins', type=int,
                    default=30,
                    help='How many minutes before a thread to send out ' +
                    'posts expires')
parser.add_argument('--max_newswire_posts',
                    dest='max_newswire_posts', type=int,
                    default=20,
                    help='Maximum newswire posts in the right column')
parser.add_argument('--maxFeedSize',
                    dest='max_newswire_feed_size_kb', type=int,
                    default=10240,
                    help='Maximum newswire rss/atom feed size in K')
parser.add_argument('--max_feed_item_size_kb',
                    dest='max_feed_item_size_kb', type=int,
                    default=2048,
                    help='Maximum size of an individual rss/atom ' +
                    'feed item in K')
parser.add_argument('--max_mirrored_articles',
                    dest='max_mirrored_articles', type=int,
                    default=100,
                    help='Maximum number of news articles to mirror.' +
                    ' Set to zero for indefinite mirroring.')
parser.add_argument('--max_news_posts',
                    dest='max_news_posts', type=int,
                    default=0,
                    help='Maximum number of news timeline posts to keep. ' +
                    'Zero for no expiry.')
parser.add_argument('--max_followers',
                    dest='max_followers', type=int,
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
parser.add_argument('--path', dest='base_dir',
                    type=str, default=os.getcwd(),
                    help='Directory in which to store posts')
parser.add_argument('--ytdomain', dest='yt_replace_domain',
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
parser.add_argument('--htmlpost', dest='htmlpost', type=str, default=None,
                    help='Show the html for a given activitypub url')
parser.add_argument('--rss', dest='rss', type=str, default=None,
                    help='Show an rss feed for a given url')
parser.add_argument('-f', '--federate', nargs='+', dest='federationList',
                    help='Specify federation list separated by spaces')
parser.add_argument('--federateshares', nargs='+',
                    dest='shared_items_federated_domains',
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
parser.add_argument("--show_publish_as_icon",
                    dest='show_publish_as_icon',
                    type=str2bool, nargs='?',
                    const=True, default=True,
                    help="Whether to show newswire publish " +
                    "as an icon or a button")
parser.add_argument("--full_width_tl_button_header",
                    dest='full_width_tl_button_header',
                    type=str2bool, nargs='?',
                    const=True, default=False,
                    help="Whether to show the timeline " +
                    "button header containing inbox and outbox " +
                    "as the full width of the screen")
parser.add_argument("--icons_as_buttons",
                    dest='icons_as_buttons',
                    type=str2bool, nargs='?',
                    const=True, default=False,
                    help="Show header icons as buttons")
parser.add_argument("--log_login_failures",
                    dest='log_login_failures',
                    type=str2bool, nargs='?',
                    const=True, default=False,
                    help="Whether to log longin failures")
parser.add_argument("--rss_icon_at_top",
                    dest='rss_icon_at_top',
                    type=str2bool, nargs='?',
                    const=True, default=True,
                    help="Whether to show the rss icon at teh top or bottom" +
                    "of the timeline")
parser.add_argument("--low_bandwidth",
                    dest='low_bandwidth',
                    type=str2bool, nargs='?',
                    const=True, default=True,
                    help="Whether to use low bandwidth images")
parser.add_argument("--publish_button_at_top",
                    dest='publish_button_at_top',
                    type=str2bool, nargs='?',
                    const=True, default=False,
                    help="Whether to show the publish button at the top of " +
                    "the newswire column")
parser.add_argument("--allow_local_network_access",
                    dest='allow_local_network_access',
                    type=str2bool, nargs='?',
                    const=True, default=False,
                    help="Whether to allow access to local network " +
                    "addresses. This might be useful when deploying in " +
                    "a mesh network")
parser.add_argument("--verify_all_signatures",
                    dest='verify_all_signatures',
                    type=str2bool, nargs='?',
                    const=True, default=False,
                    help="Whether to require that all incoming " +
                    "posts have valid jsonld signatures")
parser.add_argument("--broch_mode",
                    dest='broch_mode',
                    type=str2bool, nargs='?',
                    const=True, default=False,
                    help="Enable broch mode")
parser.add_argument("--nodeinfoaccounts",
                    dest='show_node_info_accounts',
                    type=str2bool, nargs='?',
                    const=True, default=False,
                    help="Show numbers of accounts within nodeinfo metadata")
parser.add_argument("--nodeinfoversion",
                    dest='show_node_info_version',
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
parser.add_argument('--max_like_count', dest='max_like_count', type=int,
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
parser.add_argument('--react', '--reaction', dest='react', type=str,
                    default=None, help='Reaction url')
parser.add_argument('--emoji', type=str,
                    default=None, help='Reaction emoji')
parser.add_argument('--undoreact', '--undoreaction', dest='undoreact',
                    type=str,
                    default=None, help='Reaction url')
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
    base_dir = os.getcwd()
    testSharedItemsFederation(base_dir)
    testGroupFollow(base_dir)
    testPostMessageBetweenServers(base_dir)
    testFollowBetweenServers(base_dir)
    testClientToServer(base_dir)
    testUpdateActor(base_dir)
    print('All tests succeeded')
    sys.exit()

http_prefix = 'https'
if args.http or args.i2p:
    http_prefix = 'http'
elif args.gnunet:
    http_prefix = 'gnunet'

base_dir = args.base_dir
if base_dir.endswith('/'):
    print("--path option should not end with '/'")
    sys.exit()

# automatic translations
if args.libretranslateUrl:
    if '://' in args.libretranslateUrl and \
       '.' in args.libretranslateUrl:
        setConfigParam(base_dir, 'libretranslateUrl', args.libretranslateUrl)
if args.libretranslateApiKey:
    setConfigParam(base_dir, 'libretranslateApiKey', args.libretranslateApiKey)

if args.posts:
    if not args.domain:
        originDomain = getConfigParam(base_dir, 'domain')
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
    signingPrivateKeyPem = getInstanceActorKey(base_dir, originDomain)
    getPublicPostsOfPerson(base_dir, nickname, domain, False, True,
                           proxyType, args.port, http_prefix, debug,
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
        originDomain = getConfigParam(base_dir, 'domain')
    else:
        originDomain = args.domain
    if args.secureMode:
        signingPrivateKeyPem = getInstanceActorKey(base_dir, originDomain)
    domainList = getPublicPostDomains(None,
                                      base_dir, nickname, domain,
                                      originDomain,
                                      proxyType, args.port,
                                      http_prefix, debug,
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
        signingPrivateKeyPem = getInstanceActorKey(base_dir, domain)
    domainList = getPublicPostDomainsBlocked(None,
                                             base_dir, nickname, domain,
                                             proxyType, args.port,
                                             http_prefix, debug,
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
        signingPrivateKeyPem = getInstanceActorKey(base_dir, domain)
    checkDomains(None,
                 base_dir, nickname, domain,
                 proxyType, args.port,
                 http_prefix, debug,
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
        args.domain = getConfigParam(base_dir, 'domain')
    domain = ''
    if args.domain:
        domain = args.domain
    signingPrivateKeyPem = None
    if args.secureMode:
        signingPrivateKeyPem = getInstanceActorKey(base_dir, domain)
    dotGraph = instancesGraph(base_dir, args.socnet,
                              proxyType, args.port,
                              http_prefix, debug,
                              __version__, args.language,
                              signingPrivateKeyPem)
    try:
        with open('socnet.dot', 'w+') as fp:
            fp.write(dotGraph)
            print('Saved to socnet.dot')
    except OSError:
        print('EX: commandline unable to write socnet.dot')
    sys.exit()

if args.postsraw:
    if not args.domain:
        originDomain = getConfigParam(base_dir, 'domain')
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
    signingPrivateKeyPem = getInstanceActorKey(base_dir, originDomain)
    getPublicPostsOfPerson(base_dir, nickname, domain, False, False,
                           proxyType, args.port, http_prefix, debug,
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
        args.domain = getConfigParam(base_dir, 'domain')
    domain = ''
    if args.domain:
        domain = args.domain
    signingPrivateKeyPem = getInstanceActorKey(base_dir, domain)
    if debug:
        print('base_dir: ' + str(base_dir))
        if signingPrivateKeyPem:
            print('Obtained instance actor signing key')
        else:
            print('Did not obtain instance actor key for ' + domain)
    testJson = getJson(signingPrivateKeyPem, session, args.json, asHeader,
                       None, debug, __version__, http_prefix, domain)
    if testJson:
        pprint(testJson)
    sys.exit()

if args.htmlpost:
    session = createSession(None)
    profileStr = 'https://www.w3.org/ns/activitystreams'
    asHeader = {
        'Accept': 'text/html; profile="' + profileStr + '"'
    }
    if not args.domain:
        args.domain = getConfigParam(base_dir, 'domain')
    domain = ''
    if args.domain:
        domain = args.domain
    signingPrivateKeyPem = getInstanceActorKey(base_dir, domain)
    if debug:
        print('base_dir: ' + str(base_dir))
        if signingPrivateKeyPem:
            print('Obtained instance actor signing key')
        else:
            print('Did not obtain instance actor key for ' + domain)
    testHtml = downloadHtml(signingPrivateKeyPem, session, args.htmlpost,
                            asHeader, None, debug, __version__,
                            http_prefix, domain)
    if testHtml:
        print(testHtml)
    sys.exit()

# create cache for actors
if not os.path.isdir(base_dir + '/cache'):
    os.mkdir(base_dir + '/cache')
if not os.path.isdir(base_dir + '/cache/actors'):
    print('Creating actors cache')
    os.mkdir(base_dir + '/cache/actors')
if not os.path.isdir(base_dir + '/cache/announce'):
    print('Creating announce cache')
    os.mkdir(base_dir + '/cache/announce')

# set the theme in config.json
themeName = getConfigParam(base_dir, 'theme')
if not themeName:
    setConfigParam(base_dir, 'theme', 'default')
    themeName = 'default'

if not args.mediainstance:
    mediaInstance = getConfigParam(base_dir, 'mediaInstance')
    if mediaInstance is not None:
        args.mediainstance = mediaInstance
        if args.mediainstance:
            args.blogsinstance = False
            args.newsinstance = False

if not args.newsinstance:
    newsInstance = getConfigParam(base_dir, 'newsInstance')
    if newsInstance is not None:
        args.newsinstance = newsInstance
        if args.newsinstance:
            args.blogsinstance = False
            args.mediainstance = False

if not args.blogsinstance:
    blogsInstance = getConfigParam(base_dir, 'blogsInstance')
    if blogsInstance is not None:
        args.blogsinstance = blogsInstance
        if args.blogsinstance:
            args.mediainstance = False
            args.newsinstance = False

# set the instance title in config.json
title = getConfigParam(base_dir, 'instanceTitle')
if not title:
    setConfigParam(base_dir, 'instanceTitle', 'Epicyon')

# set the instance description in config.json
descFull = getConfigParam(base_dir, 'instanceDescription')
if not descFull:
    setConfigParam(base_dir, 'instanceDescription',
                   'Just another ActivityPub server')

# set the short instance description in config.json
descShort = getConfigParam(base_dir, 'instanceDescriptionShort')
if not descShort:
    setConfigParam(base_dir, 'instanceDescriptionShort',
                   'Just another ActivityPub server')

if args.domain:
    domain = args.domain
    setConfigParam(base_dir, 'domain', domain)

if args.rss:
    session = createSession(None)
    testRSS = getRSS(base_dir, domain, session, args.rss,
                     False, False, 1000, 1000, 1000, 1000, debug)
    pprint(testRSS)
    sys.exit()

if args.onion:
    if not args.onion.endswith('.onion'):
        print(args.onion + ' does not look like an onion domain')
        sys.exit()
    if '://' in args.onion:
        args.onion = args.onion.split('://')[1]
    onionDomain = args.onion
    setConfigParam(base_dir, 'onion', onionDomain)

i2pDomain = None
if args.i2pDomain:
    if not args.i2pDomain.endswith('.i2p'):
        print(args.i2pDomain + ' does not look like an i2p domain')
        sys.exit()
    if '://' in args.i2pDomain:
        args.onion = args.onion.split('://')[1]
    i2pDomain = args.i2pDomain
    setConfigParam(base_dir, 'i2pDomain', i2pDomain)

if not args.language:
    languageCode = getConfigParam(base_dir, 'language')
    if languageCode:
        args.language = languageCode
    else:
        args.language = 'en'

# maximum number of new registrations
if not args.maxRegistrations:
    maxRegistrations = getConfigParam(base_dir, 'maxRegistrations')
    if not maxRegistrations:
        maxRegistrations = 10
        setConfigParam(base_dir, 'maxRegistrations', str(maxRegistrations))
    else:
        maxRegistrations = int(maxRegistrations)
else:
    maxRegistrations = args.maxRegistrations
    setConfigParam(base_dir, 'maxRegistrations', str(maxRegistrations))

# if this is the initial run then allow new registrations
if not getConfigParam(base_dir, 'registration'):
    if args.registration.lower() == 'open':
        setConfigParam(base_dir, 'registration', 'open')
        setConfigParam(base_dir, 'maxRegistrations', str(maxRegistrations))
        setConfigParam(base_dir, 'registrationsRemaining',
                       str(maxRegistrations))

if args.resetregistrations:
    setConfigParam(base_dir, 'registrationsRemaining', str(maxRegistrations))
    print('Number of new registrations reset to ' + str(maxRegistrations))

# unique ID for the instance
instanceId = getConfigParam(base_dir, 'instanceId')
if not instanceId:
    instanceId = createPassword(32)
    setConfigParam(base_dir, 'instanceId', instanceId)
    print('Instance ID: ' + instanceId)

# get domain name from configuration
configDomain = getConfigParam(base_dir, 'domain')
if configDomain:
    domain = configDomain
else:
    domain = 'localhost'

# get onion domain name from configuration
configOnionDomain = getConfigParam(base_dir, 'onion')
if configOnionDomain:
    onionDomain = configOnionDomain
else:
    onionDomain = None

# get i2p domain name from configuration
configi2pDomain = getConfigParam(base_dir, 'i2pDomain')
if configi2pDomain:
    i2pDomain = configi2pDomain
else:
    i2pDomain = None

# get port number from configuration
configPort = getConfigParam(base_dir, 'port')
if configPort:
    port = configPort
else:
    if domain.endswith('.onion') or \
       domain.endswith('.i2p'):
        port = 80
    else:
        port = 443

configProxyPort = getConfigParam(base_dir, 'proxyPort')
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
        setConfigParam(base_dir, 'federationList', federationList)
else:
    configFederationList = getConfigParam(base_dir, 'federationList')
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
        domain = getConfigParam(base_dir, 'domain')
    signingPrivateKeyPem = None
    if args.secureMode:
        signingPrivateKeyPem = getInstanceActorKey(base_dir, domain)
    manualApproveFollowRequest(session, base_dir,
                               http_prefix,
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
        domain = getConfigParam(base_dir, 'domain')
    signingPrivateKeyPem = None
    if args.secureMode:
        signingPrivateKeyPem = getInstanceActorKey(base_dir, domain)
    manualDenyFollowRequest(session, base_dir,
                            http_prefix,
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

    accountsDir = acctDir(base_dir, args.nickname, domain)
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
        domain = getConfigParam(base_dir, 'domain')
    signingPrivateKeyPem = None
    if args.secureMode:
        signingPrivateKeyPem = getInstanceActorKey(base_dir, domain)
    print('Sending post to ' + args.sendto)

    sendPostViaServer(signingPrivateKeyPem, __version__,
                      base_dir, session, args.nickname, args.password,
                      domain, port,
                      toNickname, toDomain, toPort, ccUrl,
                      http_prefix, sendMessage, followersOnly,
                      args.commentsEnabled, attach, mediaType,
                      attachedImageDescription, city,
                      cachedWebfingers, personCache, isArticle,
                      args.language, args.low_bandwidth,
                      args.content_license_url, args.debug,
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
        domain = getConfigParam(base_dir, 'domain')
    signingPrivateKeyPem = None
    if args.secureMode:
        signingPrivateKeyPem = getInstanceActorKey(base_dir, domain)
    print('Sending announce/repeat of ' + args.announce)

    sendAnnounceViaServer(base_dir, session, args.nickname, args.password,
                          domain, port,
                          http_prefix, args.announce,
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
        domain = getConfigParam(base_dir, 'domain')
    signingPrivateKeyPem = None
    if args.secureMode:
        signingPrivateKeyPem = getInstanceActorKey(base_dir, domain)

    session = createSession(proxyType)
    boxJson = c2sBoxJson(base_dir, session,
                         args.nickname, args.password,
                         domain, port, http_prefix,
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
        domain = getConfigParam(base_dir, 'domain')
    signingPrivateKeyPem = None
    if args.secureMode:
        signingPrivateKeyPem = getInstanceActorKey(base_dir, domain)
    print('Sending shared item: ' + args.itemName)

    sendShareViaServer(base_dir, session,
                       args.nickname, args.password,
                       domain, port,
                       http_prefix,
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
        domain = getConfigParam(base_dir, 'domain')
    signingPrivateKeyPem = None
    if args.secureMode:
        signingPrivateKeyPem = getInstanceActorKey(base_dir, domain)
    print('Sending undo of shared item: ' + args.undoItemName)

    sendUndoShareViaServer(base_dir, session,
                           args.nickname, args.password,
                           domain, port,
                           http_prefix,
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
        domain = getConfigParam(base_dir, 'domain')
    signingPrivateKeyPem = None
    if args.secureMode:
        signingPrivateKeyPem = getInstanceActorKey(base_dir, domain)
    print('Sending wanted item: ' + args.wantedItemName)

    sendWantedViaServer(base_dir, session,
                        args.nickname, args.password,
                        domain, port,
                        http_prefix,
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
        domain = getConfigParam(base_dir, 'domain')
    signingPrivateKeyPem = None
    if args.secureMode:
        signingPrivateKeyPem = getInstanceActorKey(base_dir, domain)
    print('Sending undo of wanted item: ' + args.undoWantedItemName)

    sendUndoWantedViaServer(base_dir, session,
                            args.nickname, args.password,
                            domain, port,
                            http_prefix,
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
        domain = getConfigParam(base_dir, 'domain')
    signingPrivateKeyPem = None
    if args.secureMode:
        signingPrivateKeyPem = getInstanceActorKey(base_dir, domain)
    print('Sending like of ' + args.like)

    sendLikeViaServer(base_dir, session,
                      args.nickname, args.password,
                      domain, port,
                      http_prefix, args.like,
                      cachedWebfingers, personCache,
                      True, __version__, signingPrivateKeyPem)
    for i in range(10):
        # TODO detect send success/fail
        time.sleep(1)
    sys.exit()

if args.react:
    if not args.nickname:
        print('Specify a nickname with the --nickname option')
        sys.exit()
    if not args.emoji:
        print('Specify a reaction emoji with the --emoji option')
        sys.exit()
    if not validEmojiContent(args.emoji):
        print('This is not a valid emoji')
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
        domain = getConfigParam(base_dir, 'domain')
    signingPrivateKeyPem = None
    if args.secureMode:
        signingPrivateKeyPem = getInstanceActorKey(base_dir, domain)
    print('Sending emoji reaction ' + args.emoji + ' to ' + args.react)

    sendReactionViaServer(base_dir, session,
                          args.nickname, args.password,
                          domain, port,
                          http_prefix, args.react, args.emoji,
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
        domain = getConfigParam(base_dir, 'domain')
    signingPrivateKeyPem = None
    if args.secureMode:
        signingPrivateKeyPem = getInstanceActorKey(base_dir, domain)
    print('Sending undo like of ' + args.undolike)

    sendUndoLikeViaServer(base_dir, session,
                          args.nickname, args.password,
                          domain, port,
                          http_prefix, args.undolike,
                          cachedWebfingers, personCache,
                          True, __version__,
                          signingPrivateKeyPem)
    for i in range(10):
        # TODO detect send success/fail
        time.sleep(1)
    sys.exit()

if args.undoreact:
    if not args.nickname:
        print('Specify a nickname with the --nickname option')
        sys.exit()
    if not args.emoji:
        print('Specify a reaction emoji with the --emoji option')
        sys.exit()
    if not validEmojiContent(args.emoji):
        print('This is not a valid emoji')
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
        domain = getConfigParam(base_dir, 'domain')
    signingPrivateKeyPem = None
    if args.secureMode:
        signingPrivateKeyPem = getInstanceActorKey(base_dir, domain)
    print('Sending undo emoji reaction ' + args.emoji + ' to ' + args.react)

    sendUndoReactionViaServer(base_dir, session,
                              args.nickname, args.password,
                              domain, port,
                              http_prefix, args.undoreact, args.emoji,
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
        domain = getConfigParam(base_dir, 'domain')
    signingPrivateKeyPem = None
    if args.secureMode:
        signingPrivateKeyPem = getInstanceActorKey(base_dir, domain)
    print('Sending bookmark of ' + args.bookmark)

    sendBookmarkViaServer(base_dir, session,
                          args.nickname, args.password,
                          domain, port,
                          http_prefix, args.bookmark,
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
        domain = getConfigParam(base_dir, 'domain')
    signingPrivateKeyPem = None
    if args.secureMode:
        signingPrivateKeyPem = getInstanceActorKey(base_dir, domain)
    print('Sending undo bookmark of ' + args.unbookmark)

    sendUndoBookmarkViaServer(base_dir, session,
                              args.nickname, args.password,
                              domain, port,
                              http_prefix, args.unbookmark,
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
        domain = getConfigParam(base_dir, 'domain')
    signingPrivateKeyPem = None
    if args.secureMode:
        signingPrivateKeyPem = getInstanceActorKey(base_dir, domain)
    print('Sending delete request of ' + args.delete)

    sendDeleteViaServer(base_dir, session,
                        args.nickname, args.password,
                        domain, port,
                        http_prefix, args.delete,
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
    followHttpPrefix = http_prefix
    if args.follow.startswith('https'):
        followHttpPrefix = 'https'
    if not domain:
        domain = getConfigParam(base_dir, 'domain')
    signingPrivateKeyPem = None
    if args.secureMode:
        signingPrivateKeyPem = getInstanceActorKey(base_dir, domain)

    sendFollowRequestViaServer(base_dir, session,
                               args.nickname, args.password,
                               domain, port,
                               followNickname, followDomain, followPort,
                               http_prefix,
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
    followHttpPrefix = http_prefix
    if args.follow.startswith('https'):
        followHttpPrefix = 'https'
    if not domain:
        domain = getConfigParam(base_dir, 'domain')
    signingPrivateKeyPem = None
    if args.secureMode:
        signingPrivateKeyPem = getInstanceActorKey(base_dir, domain)

    sendUnfollowRequestViaServer(base_dir, session,
                                 args.nickname, args.password,
                                 domain, port,
                                 followNickname, followDomain, followPort,
                                 http_prefix,
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
    followHttpPrefix = http_prefix
    if not domain:
        domain = getConfigParam(base_dir, 'domain')
    signingPrivateKeyPem = None
    if args.secureMode:
        signingPrivateKeyPem = getInstanceActorKey(base_dir, domain)

    followingJson = \
        getFollowingViaServer(base_dir, session,
                              args.nickname, args.password,
                              domain, port,
                              http_prefix, args.pageNumber,
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
    followHttpPrefix = http_prefix
    if not domain:
        domain = getConfigParam(base_dir, 'domain')
    signingPrivateKeyPem = None
    if args.secureMode:
        signingPrivateKeyPem = getInstanceActorKey(base_dir, domain)

    followersJson = \
        getFollowersViaServer(base_dir, session,
                              args.nickname, args.password,
                              domain, port,
                              http_prefix, args.pageNumber,
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
    followHttpPrefix = http_prefix
    if not domain:
        domain = getConfigParam(base_dir, 'domain')
    signingPrivateKeyPem = None
    if args.secureMode:
        signingPrivateKeyPem = getInstanceActorKey(base_dir, domain)

    followRequestsJson = \
        getFollowRequestsViaServer(base_dir, session,
                                   args.nickname, args.password,
                                   domain, port,
                                   http_prefix, args.pageNumber,
                                   cachedWebfingers, personCache,
                                   debug, __version__, signingPrivateKeyPem)
    if followRequestsJson:
        pprint(followRequestsJson)
    sys.exit()

nickname = 'admin'
if args.domain:
    domain = args.domain
    setConfigParam(base_dir, 'domain', domain)
if args.port:
    port = args.port
    setConfigParam(base_dir, 'port', port)
if args.proxyPort:
    proxyPort = args.proxyPort
    setConfigParam(base_dir, 'proxyPort', proxyPort)
if args.gnunet:
    http_prefix = 'gnunet'
if args.dat or args.hyper:
    http_prefix = 'hyper'
if args.i2p:
    http_prefix = 'http'

if args.migrations:
    cachedWebfingers = {}
    if args.http or domain.endswith('.onion'):
        http_prefix = 'http'
        port = 80
        proxyType = 'tor'
    elif domain.endswith('.i2p'):
        http_prefix = 'http'
        port = 80
        proxyType = 'i2p'
    elif args.gnunet:
        http_prefix = 'gnunet'
        port = 80
        proxyType = 'gnunet'
    else:
        http_prefix = 'https'
        port = 443
    session = createSession(proxyType)
    if not domain:
        domain = getConfigParam(base_dir, 'domain')
    signingPrivateKeyPem = None
    if args.secureMode:
        signingPrivateKeyPem = getInstanceActorKey(base_dir, domain)
    ctr = migrateAccounts(base_dir, session,
                          http_prefix, cachedWebfingers,
                          True, signingPrivateKeyPem)
    if ctr == 0:
        print('No followed accounts have moved')
    else:
        print(str(ctr) + ' followed accounts were migrated')
    sys.exit()

if args.actor:
    if not domain:
        domain = getConfigParam(base_dir, 'domain')
    signingPrivateKeyPem = getInstanceActorKey(base_dir, domain)
    if debug:
        print('base_dir: ' + str(base_dir))
        if signingPrivateKeyPem:
            print('Obtained instance actor signing key')
        else:
            print('Did not obtain instance actor key for ' + domain)
    getActorJson(domain, args.actor, args.http, args.gnunet,
                 debug, False, signingPrivateKeyPem, None)
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
        http_prefix = 'http'
        port = 80
        proxyType = 'tor'
    elif domain.endswith('.i2p'):
        http_prefix = 'http'
        port = 80
        proxyType = 'i2p'
    elif args.gnunet:
        http_prefix = 'gnunet'
        port = 80
        proxyType = 'gnunet'
    else:
        http_prefix = 'https'
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
        signingPrivateKeyPem = getInstanceActorKey(base_dir, domain)
    wfRequest = webfingerHandle(session, handle,
                                http_prefix, cachedWebfingers,
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
        personUrl = getUserUrl(wfRequest, 0, args.debug)
    if nickname == domain:
        personUrl = personUrl.replace('/users/', '/actor/')
        personUrl = personUrl.replace('/accounts/', '/actor/')
        personUrl = personUrl.replace('/channel/', '/actor/')
        personUrl = personUrl.replace('/profile/', '/actor/')
        personUrl = personUrl.replace('/u/', '/actor/')
        personUrl = personUrl.replace('/c/', '/actor/')
    if not personUrl:
        # try single user instance
        personUrl = http_prefix + '://' + domain
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
        signingPrivateKeyPem = getInstanceActorKey(base_dir, domain)
    followersList = \
        downloadFollowCollection(signingPrivateKeyPem,
                                 'followers', session,
                                 http_prefix, personUrl, 1, 3, args.debug)
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
        if not args.domain or not getConfigParam(base_dir, 'domain'):
            print('Use the --domain option to set the domain name')
            sys.exit()

    configuredDomain = getConfigParam(base_dir, 'domain')
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
    accountDir = acctDir(base_dir, nickname, domain)
    if os.path.isdir(accountDir):
        print('Account already exists')
        sys.exit()
    if os.path.isdir(base_dir + '/deactivated/' + nickname + '@' + domain):
        print('Account is deactivated')
        sys.exit()
    if domain.endswith('.onion') or \
       domain.endswith('.i2p'):
        port = 80
        http_prefix = 'http'
    createPerson(base_dir, nickname, domain, port, http_prefix,
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
        if not args.domain or not getConfigParam(base_dir, 'domain'):
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
    accountDir = acctDir(base_dir, nickname, domain)
    if os.path.isdir(accountDir):
        print('Group already exists')
        sys.exit()
    createGroup(base_dir, nickname, domain, port, http_prefix,
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
        if not args.domain or not getConfigParam(base_dir, 'domain'):
            print('Use the --domain option to set the domain name')
            sys.exit()
        if args.domain:
            domain = args.domain
        else:
            domain = getConfigParam(base_dir, 'domain')

    configuredDomain = getConfigParam(base_dir, 'domain')
    if configuredDomain:
        if domain != configuredDomain:
            print('The account domain is expected to be ' + configuredDomain)
            sys.exit()

    if args.deactivate:
        if deactivateAccount(base_dir, nickname, domain):
            print('Account for ' + nickname + '@' + domain +
                  ' was deactivated')
        else:
            print('Account for ' + nickname + '@' + domain + ' was not found')
        sys.exit()
    if removeAccount(base_dir, nickname, domain, port):
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
        if not args.domain or not getConfigParam(base_dir, 'domain'):
            print('Use the --domain option to set the domain name')
            sys.exit()
    if activateAccount(base_dir, nickname, domain):
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
        if not args.domain or not getConfigParam(base_dir, 'domain'):
            print('Use the --domain option to set the domain name')
            sys.exit()
    newPassword = args.changepassword[1]
    if len(newPassword) < 8:
        print('Password should be at least 8 characters')
        sys.exit()
    accountDir = acctDir(base_dir, nickname, domain)
    if not os.path.isdir(accountDir):
        print('Account ' + nickname + '@' + domain + ' not found')
        sys.exit()
    passwordFile = base_dir + '/accounts/passwords'
    if os.path.isfile(passwordFile):
        if nickname + ':' in open(passwordFile).read():
            storeBasicCredentials(base_dir, nickname, newPassword)
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
    archiveMedia(base_dir, args.archive, args.archiveWeeks)
    archivePosts(base_dir, http_prefix, args.archive, {}, args.archiveMaxPosts)
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
    if setProfileImage(base_dir, http_prefix, args.nickname, domain,
                       port, args.avatar, 'avatar', '128x128', city,
                       args.content_license_url):
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
    if setProfileImage(base_dir, http_prefix, args.nickname, domain,
                       port, args.backgroundImage, 'background',
                       '256x256', city, args.content_license_url):
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
        domain = getConfigParam(base_dir, 'domain')
    signingPrivateKeyPem = None
    if args.secureMode:
        signingPrivateKeyPem = getInstanceActorKey(base_dir, domain)
    print('Sending ' + args.skill + ' skill level ' +
          str(args.skillLevelPercent) + ' for ' + nickname)

    sendSkillViaServer(base_dir, session,
                       nickname, args.password,
                       domain, port,
                       http_prefix,
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
        domain = getConfigParam(base_dir, 'domain')
    signingPrivateKeyPem = None
    if args.secureMode:
        signingPrivateKeyPem = getInstanceActorKey(base_dir, domain)
    print('Sending availability status of ' + nickname +
          ' as ' + args.availability)

    sendAvailabilityViaServer(base_dir, session, nickname, args.password,
                              domain, port,
                              http_prefix,
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

    runDesktopClient(base_dir, proxyType, http_prefix,
                     nickname, domain, port, args.password,
                     args.screenreader, args.language,
                     args.notificationSounds,
                     args.notificationType,
                     args.noKeyPress,
                     storeInboxPosts,
                     args.notifyShowNewPosts,
                     args.language,
                     args.debug, args.low_bandwidth)
    sys.exit()

if federationList:
    print('Federating with: ' + str(federationList))
if args.shared_items_federated_domains:
    print('Federating shared items with: ' +
          args.shared_items_federated_domains)

shared_items_federated_domains = []
if args.shared_items_federated_domains:
    fed_domains_str = args.shared_items_federated_domains
    setConfigParam(base_dir, 'shared_items_federated_domains',
                   fed_domains_str)
else:
    fed_domains_str = \
        getConfigParam(base_dir, 'shared_items_federated_domains')
if fed_domains_str:
    fed_domains_list = fed_domains_str.split(',')
    for sharedFederatedDomain in fed_domains_list:
        shared_items_federated_domains.append(sharedFederatedDomain.strip())

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
        blockedActor = http_prefix + '://' + blockedDomain + \
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
        domain = getConfigParam(base_dir, 'domain')
    signingPrivateKeyPem = None
    if args.secureMode:
        signingPrivateKeyPem = getInstanceActorKey(base_dir, domain)
    print('Sending block of ' + args.block)

    sendBlockViaServer(base_dir, session, nickname, args.password,
                       domain, port,
                       http_prefix, args.block,
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
        domain = getConfigParam(base_dir, 'domain')
    signingPrivateKeyPem = None
    if args.secureMode:
        signingPrivateKeyPem = getInstanceActorKey(base_dir, domain)
    print('Sending mute of ' + args.mute)

    sendMuteViaServer(base_dir, session, nickname, args.password,
                      domain, port,
                      http_prefix, args.mute,
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
        domain = getConfigParam(base_dir, 'domain')
    signingPrivateKeyPem = None
    if args.secureMode:
        signingPrivateKeyPem = getInstanceActorKey(base_dir, domain)
    print('Sending undo mute of ' + args.unmute)

    sendUndoMuteViaServer(base_dir, session, nickname, args.password,
                          domain, port,
                          http_prefix, args.unmute,
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
        blockedActor = http_prefix + '://' + blockedDomain + \
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
        domain = getConfigParam(base_dir, 'domain')
    signingPrivateKeyPem = None
    if args.secureMode:
        signingPrivateKeyPem = getInstanceActorKey(base_dir, domain)
    print('Sending undo block of ' + args.unblock)

    sendUndoBlockViaServer(base_dir, session, nickname, args.password,
                           domain, port,
                           http_prefix, args.unblock,
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
    if addFilter(base_dir, args.nickname, domain, args.filterStr):
        print('Filter added to ' + args.nickname + ': ' + args.filterStr)
    sys.exit()

if args.unfilterStr:
    if not args.nickname:
        print('Please specify a nickname')
        sys.exit()
    if removeFilter(base_dir, args.nickname, domain, args.unfilterStr):
        print('Filter removed from ' + args.nickname + ': ' + args.unfilterStr)
    sys.exit()

if args.testdata:
    args.language = 'en'
    city = 'London, England'
    nickname = 'testuser567'
    password = 'boringpassword'
    print('Generating some test data for user: ' + nickname)

    if os.path.isdir(base_dir + '/tags'):
        shutil.rmtree(base_dir + '/tags', ignore_errors=False, onerror=None)
    if os.path.isdir(base_dir + '/accounts'):
        shutil.rmtree(base_dir + '/accounts',
                      ignore_errors=False, onerror=None)
    if os.path.isdir(base_dir + '/keys'):
        shutil.rmtree(base_dir + '/keys', ignore_errors=False, onerror=None)
    if os.path.isdir(base_dir + '/media'):
        shutil.rmtree(base_dir + '/media', ignore_errors=False, onerror=None)
    if os.path.isdir(base_dir + '/sharefiles'):
        shutil.rmtree(base_dir + '/sharefiles',
                      ignore_errors=False, onerror=None)
    if os.path.isdir(base_dir + '/wfendpoints'):
        shutil.rmtree(base_dir + '/wfendpoints',
                      ignore_errors=False, onerror=None)

    setConfigParam(base_dir, 'registrationsRemaining',
                   str(maxRegistrations))

    createPerson(base_dir, 'maxboardroom', domain, port, http_prefix,
                 True, False, password)
    createPerson(base_dir, 'ultrapancake', domain, port, http_prefix,
                 True, False, password)
    createPerson(base_dir, 'drokk', domain, port, http_prefix,
                 True, False, password)
    createPerson(base_dir, 'sausagedog', domain, port, http_prefix,
                 True, False, password)

    createPerson(base_dir, nickname, domain, port, http_prefix,
                 True, False, 'likewhateveryouwantscoob')
    setSkillLevel(base_dir, nickname, domain, 'testing', 60)
    setSkillLevel(base_dir, nickname, domain, 'typing', 50)
    setRole(base_dir, nickname, domain, 'admin')
    setAvailability(base_dir, nickname, domain, 'busy')

    addShare(base_dir,
             http_prefix, nickname, domain, port,
             "spanner",
             "It's a spanner",
             "img/shares1.png",
             1, "tool",
             "mechanical",
             "City", "0", "GBP",
             "2 months",
             debug, city, args.language, {}, 'shares', args.low_bandwidth,
             args.content_license_url)
    addShare(base_dir,
             http_prefix, nickname, domain, port,
             "witch hat",
             "Spooky",
             "img/shares2.png",
             1, "hat",
             "clothing",
             "City", "0", "GBP",
             "3 months",
             debug, city, args.language, {}, 'shares', args.low_bandwidth,
             args.content_license_url)

    deleteAllPosts(base_dir, nickname, domain, 'inbox')
    deleteAllPosts(base_dir, nickname, domain, 'outbox')

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
    low_bandwidth = False

    createPublicPost(base_dir, nickname, domain, port, http_prefix,
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
                     low_bandwidth, args.content_license_url)
    createPublicPost(base_dir, nickname, domain, port, http_prefix,
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
                     low_bandwidth, args.content_license_url)
    createPublicPost(base_dir, nickname, domain, port, http_prefix,
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
                     low_bandwidth, args.content_license_url)
    createPublicPost(base_dir, nickname, domain, port, http_prefix,
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
                     low_bandwidth, args.content_license_url)
    createPublicPost(base_dir, nickname, domain, port, http_prefix,
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
                     low_bandwidth, args.content_license_url)
    createPublicPost(base_dir, nickname, domain, port, http_prefix,
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
                     low_bandwidth, args.content_license_url)
    createPublicPost(base_dir, nickname, domain, port, http_prefix,
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
                     low_bandwidth, args.content_license_url)
    createPublicPost(base_dir, nickname, domain, port, http_prefix,
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
                     low_bandwidth, args.content_license_url)
    domainFull = domain + ':' + str(port)
    clearFollows(base_dir, nickname, domain)
    followPerson(base_dir, nickname, domain, 'maxboardroom', domainFull,
                 federationList, False, False)
    followPerson(base_dir, nickname, domain, 'ultrapancake', domainFull,
                 federationList, False, False)
    followPerson(base_dir, nickname, domain, 'sausagedog', domainFull,
                 federationList, False, False)
    followPerson(base_dir, nickname, domain, 'drokk', domainFull,
                 federationList, False, False)
    followerOfPerson(base_dir, nickname, domain, 'drokk', domainFull,
                     federationList, False, False)
    followerOfPerson(base_dir, nickname, domain, 'maxboardroom', domainFull,
                     federationList, False, False)
    setConfigParam(base_dir, 'admin', nickname)

# set a lower bound to the maximum mentions
# so that it can't be accidentally set to zero and disable replies
if args.maxMentions < 4:
    args.maxMentions = 4

registration = getConfigParam(base_dir, 'registration')
if not registration:
    registration = False

minimumvotes = getConfigParam(base_dir, 'minvotes')
if minimumvotes:
    args.minimumvotes = int(minimumvotes)

content_license_url = ''
if args.content_license_url:
    content_license_url = args.content_license_url
    setConfigParam(base_dir, 'content_license_url', content_license_url)
else:
    content_license_url = getConfigParam(base_dir, 'content_license_url')

votingtime = getConfigParam(base_dir, 'votingtime')
if votingtime:
    args.votingtime = votingtime

# only show the date at the bottom of posts
dateonly = getConfigParam(base_dir, 'dateonly')
if dateonly:
    args.dateonly = dateonly

# set the maximum number of newswire posts per account or rss feed
max_newswire_postsPerSource = \
    getConfigParam(base_dir, 'max_newswire_postsPerSource')
if max_newswire_postsPerSource:
    args.max_newswire_postsPerSource = int(max_newswire_postsPerSource)

# set the maximum number of newswire posts appearing in the right column
max_newswire_posts = \
    getConfigParam(base_dir, 'max_newswire_posts')
if max_newswire_posts:
    args.max_newswire_posts = int(max_newswire_posts)

# set the maximum size of a newswire rss/atom feed in Kilobytes
max_newswire_feed_size_kb = \
    getConfigParam(base_dir, 'max_newswire_feed_size_kb')
if max_newswire_feed_size_kb:
    args.max_newswire_feed_size_kb = int(max_newswire_feed_size_kb)

max_mirrored_articles = \
    getConfigParam(base_dir, 'max_mirrored_articles')
if max_mirrored_articles is not None:
    args.max_mirrored_articles = int(max_mirrored_articles)

max_news_posts = \
    getConfigParam(base_dir, 'max_news_posts')
if max_news_posts is not None:
    args.max_news_posts = int(max_news_posts)

max_followers = \
    getConfigParam(base_dir, 'max_followers')
if max_followers is not None:
    args.max_followers = int(max_followers)

max_feed_item_size_kb = \
    getConfigParam(base_dir, 'max_feed_item_size_kb')
if max_feed_item_size_kb is not None:
    args.max_feed_item_size_kb = int(max_feed_item_size_kb)

dormant_months = \
    getConfigParam(base_dir, 'dormant_months')
if dormant_months is not None:
    args.dormant_months = int(dormant_months)

send_threads_timeout_mins = \
    getConfigParam(base_dir, 'send_threads_timeout_mins')
if send_threads_timeout_mins is not None:
    args.send_threads_timeout_mins = int(send_threads_timeout_mins)

max_like_count = \
    getConfigParam(base_dir, 'max_like_count')
if max_like_count is not None:
    args.max_like_count = int(max_like_count)

show_publish_as_icon = \
    getConfigParam(base_dir, 'show_publish_as_icon')
if show_publish_as_icon is not None:
    args.show_publish_as_icon = bool(show_publish_as_icon)

icons_as_buttons = \
    getConfigParam(base_dir, 'icons_as_buttons')
if icons_as_buttons is not None:
    args.icons_as_buttons = bool(icons_as_buttons)

rss_icon_at_top = \
    getConfigParam(base_dir, 'rss_icon_at_top')
if rss_icon_at_top is not None:
    args.rss_icon_at_top = bool(rss_icon_at_top)

publish_button_at_top = \
    getConfigParam(base_dir, 'publish_button_at_top')
if publish_button_at_top is not None:
    args.publish_button_at_top = bool(publish_button_at_top)

full_width_tl_button_header = \
    getConfigParam(base_dir, 'full_width_tl_button_header')
if full_width_tl_button_header is not None:
    args.full_width_tl_button_header = bool(full_width_tl_button_header)

allow_local_network_access = \
    getConfigParam(base_dir, 'allow_local_network_access')
if allow_local_network_access is not None:
    args.allow_local_network_access = bool(allow_local_network_access)

verify_all_signatures = \
    getConfigParam(base_dir, 'verify_all_signatures')
if verify_all_signatures is not None:
    args.verify_all_signatures = bool(verify_all_signatures)

broch_mode = \
    getConfigParam(base_dir, 'broch_mode')
if broch_mode is not None:
    args.broch_mode = bool(broch_mode)

log_login_failures = \
    getConfigParam(base_dir, 'log_login_failures')
if log_login_failures is not None:
    args.log_login_failures = bool(log_login_failures)

show_node_info_accounts = \
    getConfigParam(base_dir, 'show_node_info_accounts')
if show_node_info_accounts is not None:
    args.show_node_info_accounts = bool(show_node_info_accounts)

show_node_info_version = \
    getConfigParam(base_dir, 'show_node_info_version')
if show_node_info_version is not None:
    args.show_node_info_version = bool(show_node_info_version)

low_bandwidth = \
    getConfigParam(base_dir, 'low_bandwidth')
if low_bandwidth is not None:
    args.low_bandwidth = bool(low_bandwidth)

user_agents_blocked = []
if args.userAgentBlocks:
    user_agents_blockedStr = args.userAgentBlocks
    setConfigParam(base_dir, 'user_agents_blocked', user_agents_blockedStr)
else:
    user_agents_blockedStr = \
        getConfigParam(base_dir, 'user_agents_blocked')
if user_agents_blockedStr:
    agentBlocksList = user_agents_blockedStr.split(',')
    for agentBlockStr in agentBlocksList:
        user_agents_blocked.append(agentBlockStr.strip())

lists_enabled = ''
if args.lists_enabled:
    lists_enabled = args.lists_enabled
    setConfigParam(base_dir, 'lists_enabled', lists_enabled)
else:
    lists_enabled = getConfigParam(base_dir, 'lists_enabled')

city = \
    getConfigParam(base_dir, 'city')
if city is not None:
    args.city = city

YTDomain = getConfigParam(base_dir, 'youtubedomain')
if YTDomain:
    if '://' in YTDomain:
        YTDomain = YTDomain.split('://')[1]
    if '/' in YTDomain:
        YTDomain = YTDomain.split('/')[0]
    if '.' in YTDomain:
        args.yt_replace_domain = YTDomain

twitterDomain = getConfigParam(base_dir, 'twitterdomain')
if twitterDomain:
    if '://' in twitterDomain:
        twitterDomain = twitterDomain.split('://')[1]
    if '/' in twitterDomain:
        twitterDomain = twitterDomain.split('/')[0]
    if '.' in twitterDomain:
        args.twitterReplacementDomain = twitterDomain

if setTheme(base_dir, themeName, domain,
            args.allow_local_network_access, args.language):
    print('Theme set to ' + themeName)

# whether new registrations are open or closed
if args.registration:
    if args.registration.lower() == 'open':
        registration = getConfigParam(base_dir, 'registration')
        if not registration:
            setConfigParam(base_dir, 'registrationsRemaining',
                           str(maxRegistrations))
        else:
            if registration != 'open':
                setConfigParam(base_dir, 'registrationsRemaining',
                               str(maxRegistrations))
        setConfigParam(base_dir, 'registration', 'open')
        print('New registrations open')
    else:
        setConfigParam(base_dir, 'registration', 'closed')
        print('New registrations closed')

defaultCurrency = getConfigParam(base_dir, 'defaultCurrency')
if not defaultCurrency:
    setConfigParam(base_dir, 'defaultCurrency', 'EUR')
if args.defaultCurrency:
    if args.defaultCurrency == args.defaultCurrency.upper():
        setConfigParam(base_dir, 'defaultCurrency', args.defaultCurrency)
        print('Default currency set to ' + args.defaultCurrency)

if __name__ == "__main__":
    runDaemon(content_license_url,
              lists_enabled,
              args.default_reply_interval_hrs,
              args.low_bandwidth, args.max_like_count,
              shared_items_federated_domains,
              user_agents_blocked,
              args.log_login_failures,
              args.city,
              args.show_node_info_accounts,
              args.show_node_info_version,
              args.broch_mode,
              args.verify_all_signatures,
              args.send_threads_timeout_mins,
              args.dormant_months,
              args.max_newswire_posts,
              args.allow_local_network_access,
              args.max_feed_item_size_kb,
              args.publish_button_at_top,
              args.rss_icon_at_top,
              args.icons_as_buttons,
              args.full_width_tl_button_header,
              args.show_publish_as_icon,
              args.max_followers,
              args.max_news_posts,
              args.max_mirrored_articles,
              args.max_newswire_feed_size_kb,
              args.max_newswire_postsPerSource,
              args.dateonly,
              args.votingtime,
              args.positivevoting,
              args.minimumvotes,
              args.newsinstance,
              args.blogsinstance, args.mediainstance,
              args.maxRecentPosts,
              not args.nosharedinbox,
              registration, args.language, __version__,
              instanceId, args.client, base_dir,
              domain, onionDomain, i2pDomain,
              args.yt_replace_domain,
              args.twitterReplacementDomain,
              port, proxyPort, http_prefix,
              federationList, args.maxMentions,
              args.maxEmoji, args.secureMode,
              proxyType, args.maxReplies,
              args.domainMaxPostsPerDay,
              args.accountMaxPostsPerDay,
              args.allowdeletion, debug, False,
              args.instanceOnlySkillsSearch, [],
              not args.noapproval)
