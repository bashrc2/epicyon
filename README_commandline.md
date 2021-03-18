# Command-line Admin

This system can be administrated from the command-line.

## Account Management

The first thing you will need to do is to create an account. You can do this with the command:

``` bash
python3 epicyon.py --addaccount nickname@domain --password [yourpassword]
```

You can also leave out the **--password** option and then enter it manually, which has the advantage of passwords not being logged within command history.

To remove an account (be careful!):

``` bash
python3 epicyon.py --rmaccount nickname@domain
```

To change the password for an account:

``` bash
python3 epicyon.py --changepassword nickname@domain newpassword
```

To set an avatar for an account:

``` bash
python3 epicyon.py --nickname [nick] --domain [name] --avatar [image filename]
```

To set the background image for an account:

``` bash
python3 epicyon.py --nickname [nick] --domain [name] --background [image filename]
```

## Groups

Groups are a special type of account which relays any posts sent to it to its members (followers).

To create a group:

``` bash
python3 epicyon.py --addgroup nickname@domain --password [yourpassword]
```

To remove an account (be careful!):

``` bash
python3 epicyon.py --rmgroup nickname@domain
```

Setting avatar or changing background is the same as for any other account on the system. You can also moderate a group, applying filters, blocks or a perimeter, in the same way as for other accounts.

## Defining a perimeter

By default the server will federate with any others, but there may be cases where you want to limit this down to a defined set of servers within an organization.

You can specify the domains which can federate with your server with the *--federate* option.

``` bash
python3 epicyon.py --domain [name] --port 8000 --https --federate domain1.net domain2.org domain3.co.uk
```

## Following other accounts

With your server running you can then follow other accounts with:

``` bash
python3 epicyon.py --nickname [yournick] --domain [name] --follow othernick@domain --password [c2s password]
```

The password is for the client to obtain access to the server.

You may or may not need to use the *--port*, *--https* and *--tor* options, depending upon how your server was set up.

Unfollowing is similar:

``` bash
python3 epicyon.py --nickname [yournick] --domain [name] --unfollow othernick@domain --password [c2s password]
```

## Sending posts

To make a public post:

``` bash
python3 epicyon.py --nickname [yournick] --domain [name] \
                   --sendto public --message "hello" \
                   --warning "This is a content warning" \
                   --password [c2s password]
```

To post to followers only:

``` bash
python3 epicyon.py --nickname [yournick] --domain [name] \
                   --sendto followers --message "hello" \
                   --warning "This is a content warning" \
                   --password [c2s password]
```

To send a post to a particular address (direct message):

``` bash
python3 epicyon.py --nickname [yournick] --domain [name] \
                   --sendto othernick@domain --message "hello" \
                   --warning "This is a content warning" \
                   --password [c2s password]
```

The password is the c2s password for your account.

You can also attach an image. It must be in png, jpg or gif format.

``` bash
python3 epicyon.py --nickname [yournick] --domain [name] \
                   --sendto othernick@domain --message "bees!" \
                   --warning "bee-related content" --attach bees.png \
                   --imagedescription "bees on flowers" \
                   --password [c2s password]
```

## Viewing Public Posts

To view the public posts for a person:

``` bash
python3 epicyon.py --posts nickname@domain
```

If you want to view the raw JSON:

``` bash
python3 epicyon.py --postsraw nickname@domain
```

## Getting the JSON for your timelines

The **--posts** option applies for any ActivityPub compatible fediverse account with visible public posts. You can also use an authenticated version to obtain the paginated JSON for your inbox, outbox, direct messages, etc.

``` bash
python3 epicyon.py --nickname [yournick] --domain [yourdomain] --box [inbox|outbox|dm] --page [number] --password [yourpassword]
```

You could use this to make your own c2s client, or create your own notification system.

## Listing referenced domains

To list the domains referenced in public posts:

``` bash
python3 epicyon.py --postDomains nickname@domain
```

## Plotting federated instances

To plot a set of federated instances, based upon a sample of handles on those instances:

``` bash
python3 epicyon.py --socnet nickname1@domain1,nickname2@domain2,nickname3@domain3
xdot socnet.dot
```

## Delete posts

To delete a post which you wrote you must first know its URL. It is usually something like:

``` text
https://yourDomain/users/yourNickname/statuses/number
```

Once you know that they you can use the command:

``` bash
python3 epicyon.py --nickname [yournick] --domain [name] \
                   --delete [url] --password [c2s password]
```

Deletion of posts in a federated system is not always reliable. Some instances may not implement deletion, and this may be because of the possibility of spurious deletes being sent by an adversary to cause trouble.

By default federated deletions are not permitted because of the potential for misuse. If you wish to enable it then set the option **--allowdeletion**.

Another complication of federated deletion is that the followers collection may change between the time when a post was created and the time it was deleted, leaving some stranded copies.

## Announcements/repeats/boosts

To announce or repeat a post you will first need to know it's URL. It is usually something like:

``` text
https://domain/users/name/statuses/number
```

Once you know that they you can use the command:

``` bash
python3 epicyon.py --nickname [yournick] --domain [name] \
                   --repeat [url] --password [c2s password]
```

## Like posts

To like a post you will first need to know it's URL. It is usually something like:

``` text
https://domain/users/name/statuses/number
```

Once you know that they you can use the command:

``` bash
python3 epicyon.py --nickname [yournick] --domain [name] \
                   --like [url] --password [c2s password]
```

To subsequently undo the like:

``` bash
python3 epicyon.py --nickname [yournick] --domain [name] \
                   --undolike [url] --password [c2s password]
```

## Archiving posts

You can archive old posts with:

``` bash
python3 epicyon.py --archive [directory]
```

Which will move old posts to the given directory. You can also specify the number of weeks after which images will be archived, and the maximum number of posts within in/outboxes.

``` bash
python3 epicyon.py --archive [directory] --archiveweeks 4 --maxposts 256
```

If you want old posts to be deleted for data minimization purposes then the archive location can be set to */dev/null*.

``` bash
python3 epicyon.py --archive /dev/null --archiveweeks 4 --maxposts 256
```

## Blocking and unblocking

Whether you are using the **--federate** option to define a set of allowed instances or not, you may want to block particular accounts even inside of the perimeter. To block an account:

``` bash
python3 epicyon.py --nickname yournick --domain yourdomain --block somenick@somedomain --password [c2s password]
```

This blocks at the earliest possible stage of receiving messages, such that nothing from the specified account will be written to your inbox.

Or to unblock:

``` bash
python3 epicyon.py --nickname yournick --domain yourdomain --unblock somenick@somedomain --password [c2s password]
```

## Filtering on words or phrases

Blocking based upon the content of a message containing certain words or phrases is relatively crude and not always effective, but can help to reduce unwanted communications.

To add a word or phrase to be filtered out:

``` bash
python3 epicyon.py --nickname yournick --domain yourdomain --filter "this is a filtered phrase"
```

It can also be removed with:

``` bash
python3 epicyon.py --nickname yournick --domain yourdomain --unfilter "this is a filtered phrase"
```

Like blocking, filters are per account and so different accounts on a server can have differing filter policies.

You can also combine words or phrases with "+", such that they can be present in different parts of the message:

``` bash
python3 epicyon.py --nickname yournick --domain yourdomain --filter "blockedword+some other phrase"
```

## Applying quotas

A common adversarial situation is that a hostile server tries to flood your shared inbox with posts in order to try to overload your system. To mitigate this it's possible to add quotas for the maximum number of received messages per domain per day and per account per day.

If you're running the server it would look like this:

``` bash
python3 epicyon.py --domainmax 1000 --accountmax 200
```

With these settings you're going to be receiving no more than 200 messages for any given account within a day.

## Delegated roles

Within an organization you may want to define different roles and for some projects to be delegated. By default the first account added to the system will be the admin, and be assigned *moderator* and *delegator* roles under a project called *instance*. The admin can then delegate a person to other projects with:

``` bash
python3 epicyon.py --nickname [admin nickname] --domain [mydomain] \
                   --delegate [person nickname] \
                   --project [project name] --role [title] \
                   --password [c2s password]
```

The other person could also be made a delegator, but they will only be able to delegate further within projects which they're assigned to. By design, this creates a restricted organizational hierarchy. For example:

``` bash
python3 epicyon.py --nickname [admin nickname] --domain [mydomain] \
                   --delegate [person nickname] \
                   --project [project name] --role delegator \
                   --password [c2s password]
```

A delegated role can also be removed.

``` bash
python3 epicyon.py --nickname [admin nickname] --domain [mydomain] \
                   --undelegate [person nickname] \
                   --project [project name] \
                   --password [c2s password]
```

This extends the ActivityPub client-to-server protocol to include activities called *Delegate* and *Role*. The JSON looks like:

``` json
{ 'type': 'Delegate',
  'actor': https://somedomain/users/admin,
  'object': {
      'type': 'Role',
      'actor': https://'+somedomain+'/users/'+other,
      'object': 'otherproject;otherrole',
      'to': [],
      'cc': []
  },
  'to': [],
  'cc': []}
```

Projects and roles are only scoped within a single instance. There presently are not enough security mechanisms to support multi-instance distributed organizations.

## Assigning skills

To help create organizations you can assign some skills to your account. Note that you can only assign skills to yourself and not to other people. The command is:

``` bash
python3 epicyon.py --nickname [nick] --domain [mydomain] \
                   --skill [tag] --level [0-100] \
                   --password [c2s password]
```

The level value is a percentage which indicates how proficient you are with that skill.

This extends the ActivityPub client-to-server protocol to include an activity called *Skill*. The JSON looks like:

``` json
{ 'type': 'Skill',
  'actor': https://somedomain/users/somenickname,
  'object': gardening;80,
  'to': [],
  'cc': []}
```

## Setting availability status

For the purpose of things like knowing current task status or task completion a status value can be set.

``` bash
python3 epicyon.py --nickname [nick] --domain [mydomain] \
                   --availability [status] \
                   --password [c2s password]
```

The status value can be any string, and can become part of organization building by combining it with roles and skills.

This extends the ActivityPub client-to-server protocol to include an activity called *Availability*. "Status" was avoided because of the possibility of confusion with other things. The JSON looks like:

``` json
{ 'type': 'Availability',
  'actor': https://somedomain/users/somenickname,
  'object': ready,
  'to': [],
  'cc': []}
```

## Shares

This system includes a feature for bartering or gifting (i.e. common resource pooling or exchange without money), based upon the earlier Sharings plugin made by the Las Indias group which existed within GNU Social. It's intended to operate at the municipal level, sharing physical objects with people in your local vicinity. For example, sharing gardening tools on a street or a 3D printer between maker-spaces.

To share an item.

``` bash
python3 epicyon.py --itemName "spanner" --nickname [yournick] --domain [yourdomain] --summary "It's a spanner" --itemType "tool" --itemCategory "mechanical" --location [yourCity] --duration "2 months" --itemImage spanner.png --password [c2s password]
```

For the duration of the share you can use hours, days, weeks, months, or years.

To remove a shared item:

``` bash
python3 epicyon.py --undoItemName "spanner" --nickname [yournick] --domain [yourdomain] --password [c2s password]
```

## Desktop client

You can install the desktop client with:

``` bash
./install-desktop-client
```

and run it with:

``` bash
~/epicyon-client
```

To run it with text-to-speech via espeak:

``` bash
~/epicyon-client-tts
```

Or if you have picospeaker installed:

``` bash
~/epicyon-client-pico
```

The desktop client has a few commands, which may be more convenient than the web interface for some purposes:

``` bash
quit                         Exit from the desktop client
mute                         Turn off the screen reader
speak                        Turn on the screen reader
sounds on                    Turn on notification sounds
sounds off                   Turn off notification sounds
rp                           Repeat the last post
like                         Like the last post
unlike                       Unlike the last post
reply                        Reply to the last post
post                         Create a new post
post to [handle]             Create a new direct message
announce/boost               Boost the last post
follow [handle]              Make a follow request
unfollow [handle]            Stop following the give handle
show dm|sent|inbox|replies   Show a timeline
next                         Next page in the timeline
prev                         Previous page in the timeline
read [post number]           Read a post from a timeline
open [post number]           Open web links within a timeline post
```

If you have a GPG key configured on your local system and are sending a direct message to someone who has a PGP key (the exported key, not just the key ID) set as a tag on their profile then it will try to encrypt the message automatically. So under some conditions end-to-end encryption is possible, such that the instance server only sees ciphertext. Conversely, for arriving direct messages if they are PGP encrypted then the desktop client will try to obtain the relevant public key and decrypt.

## Speaking your inbox

It is possible to use text-to-speech to read your inbox as posts arrive. This can be useful if you are not looking at a screen but want to stay ambiently informed of what's happening.

On Debian based systems you will need to have the **python3-espeak** package installed.

``` bash
python3 epicyon.py --notifyShowNewPosts --screenreader espeak --desktop yournickname@yourdomain
```

Or a quicker version, if you have installed the desktop client as described above.

``` bash
~/epicyon-client-stream
```

Or if you have [picospeaker](https://gitlab.com/ky1e/picospeaker) installed:

``` bash
python3 epicyon.py --notifyShowNewPosts --screenreader picospeaker --desktop yournickname@yourdomain
```

You can also use the **--password** option to provide the password. This will then stay running and incoming posts will be announced as they arrive.
