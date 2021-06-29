# Epicyon Software Architecture

## Design Constraints

### Open Standards Compliance

Follow the standards for HTML, CSS and ActivityPub. Especially with ActivityPub there is always some room for interpretation, so if in doubt about a protocol implementation detail then do whatever Mastodon does to maintain maximum compatibility.

### Multi-User

It is assumed that an instance may have multiple users, although the maximum number of users is not expected to be very high. This system is for a "family and friends" or small club type of scenario.

Although it can be single user, this is not strictly a single user system.

### Opinionated

The design of this system is opinionated, and to a large extent informed by years of past experience in the fediverse. There is no claim to neutrality of any sort. Automatic removal of hellthreads and other common griefing tactics is an example of this.

### Resisting Centralization

Centralization is characterized by the typical fixation upon "scale" within the software industry. In general, methods have been preferred which do not vertically scale. This includes the decision not to use a database, and the way that the inbox is processed. Lack of scalability also simplifies the design.

Being hostile towards the common notion of scaling means that this system will be of no interest to "big tech" and can't easily be used within extractive economic models without needing a substantial rewrite.

This system should however be able to scale rhizomatically with the deployment of many small instances federated together.

### No Javascript

This is so that the system can be accessed and used normally with javascript in the web browser turned off. If you want to have good security then this is useful, since lack of javascript greatly reduces the attack surface and constrains adversaries to a limited number of vectors.

### Block Crawlers

Ordinarily web crawlers would not be a problem, but in the context of a social network even having crawlers index public posts can create ethical dilemmas in some circumstances. News instances may allow crawlers, but other types of instances should block them.

### No Local or Federated Timelines

The local and federated timelines of other ActivityPub servers don't add much value (especially the federated one), and tend to pollute the default timeline with irrelevant posts from people that you don't follow.

Especially on a small instance with a few users, the local timeline would not be significantly useful.

### Notification handling is out of scope

There are no notifications in the conventional sense. That is, there is no streaming API or linkage to browser notifications. Instead when significant events occur these create text files which can then be detected by other systems via polling.

See *scripts/epicyon-notifications* for an example of a script which could be run in a cron job to then send notifications via XMPP or Matrix.

### Limited Linked Data Support

Where Json linked data signatures are supported there should not be arbitrary schema lookups via the web. Instead, recognized contexts should be added to *context.py*. This is in order to follow the principle of *no processing without full recognition*, in which the recognition step is not endlessly extendable by untrusted parties.


## High Level Architecture

The main modules are *epicyon.py* and *daemon.py*. *epicyon.py* is the commandline interface and *daemon.py* is the http server.

![commandline and core modules](https://gitlab.com/bashrc2/epicyon/-/raw/main/architecture/epicyon_groups_Commandline-Interface_Core.png)

The daemon runs the inbox queue in a separate thread (see *inbox.py*) and the inbox queue processes incoming ActivityPub posts one at a time in a strictly serial fashion. Doing it this way means minimum potential for any parallelism/locking issues. It also means that the inbox queue is not highly scalable, but that's ok for a system which is only intended to have a few users per instance.

All ActivityPub posts are stored as text files, and there is no database as such other than the filesystem itself. Think of it as being like an email server. Each post is a json file stored in *accounts/nick@domain/inbox* or *accounts/nick@domain/outbox*. To avoid parsing problems slashes are replaced by hashes within the ActivityPub post filename. The filename for each post is the same as its ActivityPub id.

![timeline and core modules](https://gitlab.com/bashrc2/epicyon/-/raw/main/architecture/epicyon_groups_Timeline_Core.png)


## Security

### Themes

It is possible to include arbitrary CSS within a custom theme. To avoid security problems the CSS is sanitized before being used. Scripts or import references to other CSS files are not permitted.

The way that the theming system was designed is in order to avoid problems similar to Wordpress, in which an adversary will create an attactive looking theme which contains an expolit. The discovery of exploits then leads to a centralizing dynamic where there is a single "official" themes website or app store. With Epicyon, *themes should always be safe to use no matter where they were downloaded from*. There should be nothing *Turing complete* within a theme.

### C2S

This currently uses basic auth, which is simple to implement. Oauth2 is conventional, but seems overly complex and the user interface for it within other comparable apps is clunky.

## Accessibility

Trying to keep up with web accessibility standards. There should be configurable keyboard shortcuts for all of the main navigation actions. High contrast themes should be available. The desktop client should support text-to-speech. There should be the ability to run in a shell browser such as Lynx, without any significant loss of functionality.

Avoid adding any features which would be hard to make accessible.

