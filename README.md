<img src="https://code.freedombone.net/bashrc/epicyon/raw/master/img/logo.png?raw=true" width=256/>

A minimal ActivityPub server.

Based on the specification: https://www.w3.org/TR/activitypub

Also: https://raw.githubusercontent.com/w3c/activitypub/gh-pages/activitypub-tutorial.txt

https://blog.dereferenced.org/what-is-ocap-and-why-should-i-care

https://alexcastano.com/what-is-activity-pub

This project is currently *pre alpha* and not recommended for any real world uses.

## Goals

 * A minimal ActivityPub server, comparable to an email MTA.
 * AGPLv3+
 * Server-to-server and client-to-server protocols supported.
 * Implemented in a common language (Python 3)
 * Keyword filtering.
 * Being able to define roles and skills, similar to the Pursuance project.
 * Sharings collection, similar to the gnusocial sharings plugin
 * Resistant to flooding, hellthreads, etc.
 * Support content warnings, reporting and blocking.
 * http signatures and basic auth.
 * Compatible with http (onion addresses), https and dat.
 * Minimal dependencies.
 * Capabilities based security
 * Data minimization principle. Configurable post expiry time.
 * Commandline interface. If there's a GUI it should be a separate project.
 * Designed for intermittent connectivity. Assume network disruptions.
 * Suitable for single board computers.

## Object capabilities workflow

This is one proposed way that OCAP could work.

 * Works from person to person, not instance to instance.
 * Produces negligible additional network traffic
 * Works in the same way between people on different instances or the same instance
 * People can alter what their followers can do on an individual basis
 * Leverages the existing follow request mechanism

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
                  'id': 'http://bobdomain.net/caps/rOYtHApyr4ZWDUgEE1KqjhTe0kI3T2wJ',
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

When posts are subsequently sent from the following instance (server-to-server) they should have the corresponding capability id string attached within the Create wrapper. In the above example that would be **http://bobdomain.net/caps/rOYtHApyr4ZWDUgEE1KqjhTe0kI3T2wJ**. It should contain a random string which is hard to guess by brute force methods.

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
                 Check Capability id matches
                     stored capabilities
                              |
                              V
               http signature and other checks
                              |
                              V
               Accept or reject incoming post		   
```

Subsequently **Bob** could change the stored capabilities for **Alice** in their database, giving the new object a different id. This could be sent back to **Alice**, perhaps as another **follow Accept** activity with attached capabilities. This could then change the way in which **Alice** can interact with **Bob**, for example by adding or removing the ability to like or reply to posts.

Object capabilities can be strictly enforced by adding the **--ocap** option when running the daemon. The only activities which it is not enforced upon are **Follow** and **Accept**. Anyone can create a follow request or accept updated capabilities.

## Object capabilities adversaries

If **Eve** subsequently learns what the capabilities id is for **Alice** by somehow intercepting the traffic (eg. suppose she works for *Eveflare*) then she can't gain the capabilities of Alice due to the *scope* parameter against which the actors of incoming posts are checked.

**Eve** could create a post pretending to be from Alice's domain, but the http signature check would fail due to her not having Alice's keys.

The only scenarios in which Eve might triumph would be if she could also do DNS highjacking and:

 * Bob isn't storing Alice's public key and looks it up repeatedly
 * Alice and Bob's instances are foolishly configured to perform *blind key rotation* such that her being in the middle is indistinguishable from expected key changes

Even if Eve has an account on Alice's instance this won't help her very much unless she can get write access to the database.

## Install

``` bash
sudo pacman -S tor python-pip python-pysocks python-pycryptodome python-beautifulsoup4
sudo pip install commentjson
```

## Running Tests

To run the unit tests:

``` bash
python3 epicyon.py --tests
```

To run the network tests. These simulate instances exchanging messages.

``` bash
python3 epicyon.py --testsnetwork
```

## Viewing Public Posts

To view the public posts for a person:

``` bash
python3 epicyon.py --posts nickname@domain
```

If you want to view the raw json:

``` bash
python3 epicyon.py --postsraw nickname@domain
```

## Account Management

To add a new account:

``` bash
python3 epicyon.py --addaccount nickname@domain --password [yourpassword]
```

To remove an account (be careful!):

``` bash
python3 epicyon.py --rmaccount nickname@domain
```

To change the password for an account:

``` bash
python3 epicyon.py --changepassword nickname@domain newpassword
```

## Running the Server

To run with defaults:

``` bash
python3 epicyon.py
```

In a browser of choice (but not Tor browser) you can then navigate to:

``` text
http://localhost:8085/users/admin
```

If it's working then you should see the json actor for the default admin account.

For a more realistic installation you can run on a defined domain and port:

``` bash
python3 epicyon.py --domain [name] --port 8000 --https
```

You will need to proxy port 8000 through your web server and set up CA certificates as needed.

By default data will be stored in the directory in which you run the server, but you can also specify a directory:

``` bash
python3 epicyon.py --domain [name] --port 8000 --https --path [data directory]
```

By default the server will federate with any others. You can limit this to a well-defined list with the *--federate* option.

``` bash
python3 epicyon.py --domain [name] --port 8000 --https --federate domain1.net domain2.org domain3.co.uk
```
