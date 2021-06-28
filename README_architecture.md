# Epicyon Software Architecture

## High level architecture

The main modules are *epicyon.py* and *daemon.py*. *epicyon.py* is the commandline interface and *daemon.py* is the http server.

![commandline and core modules](https://gitlab.com/bashrc2/epicyon/-/raw/main/architecture/epicyon_groups_Commandline-Interface_Core.png)

The daemon runs the inbox queue in a separate thread (see *inbox.py*) and the inbox que processes incoming ActivityPub posts one at a time in a strictly serial fashion. Doing it this way means minimum potential for any parallelism/locking issues. It also means that the inbox queue is not highly scalable, but that's ok for a system which is only intended to have a few users per instance.

All ActivityPub posts are stored as text files, and there is no database as such other than the filesystem itself. Think of it as being like an email server. Each post is a json file stored in *accounts/nick@domain/inbox* or *accounts/nick@domain/outbox*. To avoid parsing problems slashes are replaced by hashes within the ActivityPub post filename. The filename for each post is the same as its ActivityPub id.

![timeline and core modules](https://gitlab.com/bashrc2/epicyon/-/raw/main/architecture/epicyon_groups_Timeline_Core.png)

## Themes security

It is possible to include arbitrary CSS within a custom theme. To avoid security problems the CSS is sanitized before being used. Scripts or import references to other CSS files are not permitted.

The way that the theming system was designed is in order to avoid problems similar to Wordpress, in which an adversary will create an attactive looking theme which contains an expolit. The discovery of exploits then leads to a centralizing dynamic where there is a single "official" themes website or app store. With Epicyon, *themes should always be safe to use no matter where they were downloaded from*.



