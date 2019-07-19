# Object Capabilities Prototype

This is one proposed way that OCAP could work.

## TL;DR

 * Works from person to person, not instance to instance. Actor-oriented capabilities.
 * Produces negligible additional network traffic, although see the proviso for shared inbox
 * Doesn't require any additional encryption to be performed
 * Works in the same way between people on different instances or the same instance
 * People can alter what their followers can do on an individual basis
 * Leverages the existing follow request mechanism

## Workflow

Default capabilities are initially set up when a follow request is made. The Accept activity sent back from a follow request can be received by any instance. A capabilities accept activity is attached to the follow accept.

``` text
                            Alice
                              |
                              V
                        Follow Request
                              |
                              V
                             Bob
                              |
                              V
               Create/store default Capabilities
                          for Alice
                              |
                              V
              Follow Accept + default Capabilities
                              |
                              V
                            Alice
                              |
                              V
                   Store Granted Capabilities
```

The default capabilities could be *any preferred policy* of the instance. They could be no capabilities at all, read only or full access to everything.

Example Follow request from **Alice** to **Bob**:

``` json
{'actor': 'http://alicedomain.net/users/alice',
 'cc': ['https://www.w3.org/ns/activitystreams#Public'],
 'id': 'http://alicedomain.net/users/alice/statuses/1562507338839876',
 'object': 'http://bobdomain.net/users/bob',
 'published': '2019-07-07T13:48:58Z',
 'to': ['http://bobdomain.net/users/bob'],
 'type': 'Follow'}
 ```

Follow Accept from **Bob** to **Alice** with attached capabilities.

``` json
{'actor': 'http://bobdomain.net/users/bob',
 'capabilities': {'actor': 'http://bobdomain.net/users/bob',
                  'capability': ['inbox:write', 'objects:read'],
                  'id': 'http://bobdomain.net/caps/alice@alicedomain.net#rOYtHApyr4ZWDUgEE1KqjhTe0kI3T2wJ',
                  'scope': 'http://alicedomain.net/users/alice',
                  'type': 'Capability'},
 'cc': [],
 'object': {'actor': 'http://alicedomain.net/users/alice',
            'cc': ['https://www.w3.org/ns/activitystreams#Public'],
            'id': 'http://alicedomain.net/users/alice/statuses/1562507338839876',
            'object': 'http://bobdomain.net/users/bob',
            'published': '2019-07-07T13:48:58Z',
            'to': ['http://bobdomain.net/users/bob'],
            'type': 'Follow'},
 'to': ['http://alicedomain.net/users/alice'],
 'type': 'Accept'}
```

When posts are subsequently sent from the following instance (server-to-server) they should have the corresponding capability id string attached within the Create wrapper. To handle the *shared inbox* scenario this should be a list rather than a single string. In the above example that would be *['http://bobdomain.net/caps/alice@alicedomain.net#rOYtHApyr4ZWDUgEE1KqjhTe0kI3T2wJ']*. It should contain a random token which is hard to guess by brute force methods.

NOTE: the token should be random and not a hash of anything. Making it a hash would give an adversary a much better chance of calculating it.

``` text
                            Alice
                              |
                              V
                          Send Post
	     Attach id from Stored Capabilities
	              granted by Bob
                              |
                              V
                             Bob
                              |
                              V
                    http signature check
                              |
                              V
                 Check Capability id matches
                     stored capabilities
                              |
                              V
	       Match stored capability scope
	       against actor on received post
                              |
                              V
                Check that stored capability
		 contains inbox:write, etc
                              |
                              V
                      Any other checks
                              |
                              V
                    Accept incoming post		   
```

Subsequently **Bob** could change the stored capabilities for **Alice** in their database, giving the new object a different id. This could be sent back to **Alice** as an **Update** activity with attached capability.

Bob can send this to Alice, altering *capability* to now include *inbox:noreply*. Notice that the random token at the end of the *id* has changed, so that Alice can't continue to use the old capabilities.

``` json
{'actor': 'http://bobdomain.net/users/bob',
 'cc': [],
 'object': {'actor': 'http://bobdomain.net/users/bob',
            'capability': ['inbox:write', 'objects:read', 'inbox:noreply'],
            'id': 'http://bobdomain.net/caps/alice@alicedomain.net#53nwZhHipNFCNwrJ2sgE8GPx13SnV23X',
            'scope': 'http://alicedomain.net/users/alice',
            'type': 'Capability'},
 'to': ['http://alicedomain.net/users/alice'],
 'type': 'Update'}
```

Alice then receives this and updates her capabilities granted by Bob to:

``` json
{'actor': 'http://bobdomain.net/users/bob',
 'capability': ['inbox:write', 'objects:read', 'inbox:noreply'],
 'id': 'http://bobdomain.net/caps/alice@alicedomain.net#53nwZhHipNFCNwrJ2sgE8GPx13SnV23X',
 'scope': 'http://alicedomain.net/users/alice',
 'type': 'Capability'}
```

If she sets her system to somehow ignore the update then if capabilities are strictly enforced she will no longer be able to send messages to Bob's inbox.

Object capabilities can be strictly enforced by adding the **--ocap** option when running the server. The only activities which it is not enforced upon are **Follow** and **Accept**. Anyone can create a follow request or accept updated capabilities.

## Object capabilities in the shared inbox scenario

Shared inboxes are obviously essential for any kind of scalability, otherwise there would be vast amounts of duplicated messages being dumped onto the intertubes like a big truck.

With the shared inbox instead of sending from Alice to 500 of her fans on a different instance - repeatedly sending the same message to individual inboxes - a single message is sent to its shared inbox (which has its own special account called 'inbox') and it then decides how to distribute that. If a list of capability ids is attached to the message which gets sent to the shared inbox then the receiving server can use that.

When a post arrives in the shared inbox it is checked to see that at least one follower exists for it. If there are only a small number of followers then it is treated like a direct message and copied separately to individual account inboxes after capabilities checks. For larger numbers of followers the capabilities checks are done at the time when the inbox is fetched. This avoids a lot of duplicated storage of posts.

A potential down side is that for popular accounts with many followers the number of capabilities ids (one for each follower on the receiving server) on a post sent to the shared inbox could be large. However, in terms of bandwidth it may still not be very significant compared to heavyweight websites containing a lot of javascript.

## Some capabilities

*inbox:write* - follower can post anything to your inbox

*inbox:noreply* - follower can't reply to your posts

*inbox:nolike* - follower can't like your posts

*inbox:nopics* - follower can't post image links

*inbox:noannounce* - follower can't send repeats (announce activities) to your inbox

*inbox:cw* - follower can't post to your inbox unless they include a content warning

## Object capabilities adversaries

If **Eve** subsequently learns what the capabilities id is for **Alice** by somehow intercepting the traffic (eg. suppose she works for *Eveflare*) then she can't gain the capabilities of Alice due to the *scope* parameter against which the actors of incoming posts are checked.

**Eve** could create a post pretending to be from Alice's domain, but the http signature check would fail due to her not having Alice's keys.

The only scenarios in which Eve might triumph would be if she could also do DNS highjacking and:

 * Bob isn't storing Alice's public key and looks it up repeatedly
 * Alice and Bob's instances are foolishly configured to perform *blind key rotation* such that her being in the middle is indistinguishable from expected key changes

Even if Eve has an account on Alice's instance this won't help her very much unless she can get write access to the database.

Another scenario is that you grant capabilities to an account on a hostile instance. The hostile instance then shares the resulting token with all other accounts on it. Potentially those other accounts might be able to gain capabilities which they havn't been granted *but only if they also have identical signing keys*. Checking for public key duplication on the instance granting capabilities could mitigate this. At the point at which a capabilities request is made are there any other known accounts with the same public key? Since actors are public it would also be possible to automatically scan for the existence of instances with duplicated signing keys.
