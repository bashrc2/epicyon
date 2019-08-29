<img src="https://code.freedombone.net/bashrc/epicyon/raw/master/img/logo.png?raw=true" width=256/>

A minimal ActivityPub server.

[Commandline interface](README_commandline.md).

[W3C Specification](https://www.w3.org/TR/activitypub)

Includes emojis designed by [OpenMoji](https://openmoji.org) – the open-source emoji and icon project. License: [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0)

[Project Goals](README_goals.md)

[Customizations](README_customizations.md)

## Install

On Arch/Parabola:

``` bash
sudo pacman -S tor python-pip python-pysocks python-pycryptodome python-beautifulsoup4 imagemagick python-pillow python-numpy python-dateutil
sudo pip install commentjson
```

Or on Debian:

``` bash
sudo apt-get -y install tor python3-pip python3-socks imagemagick python3-numpy python3-setuptools python3-crypto python3-dateutil python3-pil.imagetk
sudo pip3 install commentjson beautifulsoup4 pycryptodome
```

## Running Unit Tests

To run the unit tests:

``` bash
python3 epicyon.py --tests
```

To run the network tests. These simulate instances exchanging messages.

``` bash
python3 epicyon.py --testsnetwork
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


## Culling follower numbers

In this system the number of followers which an account has will only be visible to the account holder. Other viewers will see a made up number. Which accounts are followed or followed by a person will also only have limited visibility.

The intention is to prevent the construction of detailed social graphs by adversaries, and to frustrate attempts to build celebrity status based on number of followers, which on sites like Twitter creates a dubious economy of fake accounts and the trading thereof.

If you are the account holder though you will be able to see exactly who you're following or being followed by.


## Object Capabilities Security

A description of the proposed object capabilities model [is here](ocaps.md).

