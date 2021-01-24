# Epicyon Project Goals

 * A minimal ActivityPub server, comparable to an email MTA
 * "Small Tech" ethos. Not many accounts per instance.
 * Centering people and personal computing, not corporate or organizational accounts abstracting people away
 * AGPLv3+
 * Server-to-server and client-to-server protocols supported
 * Implemented in a common language (Python 3)
 * Keyword filtering.
 * Attention to accessibility and should be usable in lynx with a screen reader
 * Remove metadata from attached images, avatars and backgrounds
 * Support for multiple themes, with ability to create custom themes
 * Being able to build crowdsouced organizations with roles and skills
 * Sharings collection, similar to the gnusocial sharings plugin
 * Quotas for received posts per day, per domain and per account
 * Hellthread detection and removal
 * Instance and account level federation lists
 * Support content warnings, reporting and blocking
 * http signatures and basic auth
 * json-LD signatures on outgoing posts, optional on incoming
 * Compatible with http (onion addresses, i2p), https and hypercore
 * Minimal dependencies.
 * Dependencies are maintained Debian packages
 * Data minimization principle. Configurable post expiry time
 * Likes and repeats only visible to authorized viewers
 * ReplyGuy mitigation - maxmimum replies per post or posts per day
 * Ability to delete or hide specific conversation threads
 * Commandline interface
 * Simple web interface
 * Designed for intermittent connectivity. Assume network disruptions
 * Limited visibility of follows/followers
 * Suitable for single board computers
 * Progressive Web App interface. Doesn't need native apps on mobile
 * Integration with RSS feeds, for reading news or blogs
 * Moderation capabilities for posts, hashtags and blocks

**Features which won't be implemented**

The following are considered antifeatures of other social network systems, since they encourage dysfunctional social interactions.

 * Features designed to scale to large numbers of accounts (say, more than 20 active users)
 * Trending hashtags, or trending anything
 * Ranking, rating or recommending mechanisms for posts or people (other than likes or repeats/boosts)
 * Geolocation features
 * Algorithmic timelines (i.e. non-chronological)
 * Direct payment mechanisms, although integration with other services may be possible
 * Any variety of blockchain
 * Sponsored posts
 * Collaborative editing of posts, although you could do that outside of this system using etherpad, or similar
 * Anonymous posts from random internet users published under a single generic instance account
 * Hierarchies of roles beyond ordinary moderation, such as X requires special agreement from Y before sending a post
