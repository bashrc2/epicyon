<img src="https://code.freedombone.net/bashrc/epicyon/raw/master/img/logo.png?raw=true" width=256/>

A minimal ActivityPub server.

Based on the specification: https://www.w3.org/TR/activitypub

Also: https://raw.githubusercontent.com/w3c/activitypub/gh-pages/activitypub-tutorial.txt

Goals
=====

 * A minimal ActivityPub server, comparable to an email MTA.
 * Server-to-server and client-to-server protocols supported.
 * Opt-in federation. Federate with a well-defined list of instances.
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
