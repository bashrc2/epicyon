# epicyon

<img src="https://code.freedombone.net/bashrc/epicyon/raw/master/img/logo.png?raw=true" width=256/>

Some experiments with ActivityPub in Python.

Based on the specification: https://www.w3.org/TR/activitypub

Also: https://raw.githubusercontent.com/w3c/activitypub/gh-pages/activitypub-tutorial.txt

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
