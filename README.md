<img src="https://code.freedombone.net/bashrc/epicyon/raw/master/img/logo.png?raw=true" width=256/>

A minimal ActivityPub server.

Based on the specification: https://www.w3.org/TR/activitypub

Also: https://raw.githubusercontent.com/w3c/activitypub/gh-pages/activitypub-tutorial.txt

This project is currently *pre alpha* and not recommended for any real world uses.

## Goals

 * A minimal ActivityPub server, comparable to an email MTA.
 * AGPLv3+
 * Server-to-server and client-to-server protocols supported.
 * Implemented in a common language (Python 3)
 * Opt-in federation. Federate with a well-defined list of instances.
 * Keyword filtering.
 * Resistant to flooding, hellthreads, etc.
 * Support content warnings, reporting and blocking.
 * http signatures and basic auth.
 * Compatible with http (onion addresses), https and dat.
 * Minimal dependencies.
 * Data minimization principle. Configurable post expiry time.
 * Commandline interface. If there's a GUI it should be a separate project.
 * Designed for intermittent connectivity. Assume network disruptions.
 * Suitable for single board computers.

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
