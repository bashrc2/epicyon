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

## Running the Server

In the most common case you'll be using systemd to set up a daemon to run the server.

Add a dedicated user so that we don't have to run as root.

``` bash
adduser --system --home=/etc/epicyon --group epicyon
```

Edit */etc/systemd/system/epicyon.service* and add the following:

``` bash
[Unit]
Description=epicyon
After=syslog.target
After=network.target
Documentation=$EPICYON_REPO";

[Service]
Type=simple
User=epicyon
Group=epicyon
WorkingDirectory=/etc/epicyon
ExecStart=/usr/bin/python3 /etc/epicyon/epicyon.py --port 443 --proxy 7156 --domain YOUR_DOMAIN --registration open --debug";
Environment=USER=epicyon
Restart=always
StandardError=syslog

[Install]
WantedBy=multi-user.target }
```

Here the server was installed to */etc/epicyon*, but you can change that to wherever you installed it.

Then run the daemon:

``` bash
systemctl enable epicyon
chown -R epicyon:epicyon /etc/epicyon
systemctl start epicyon
```

Check the status of the daemon with:

``` bash
systemctl status epicyon
```

If it's not running then you can also look at the log:

``` bash
journalctl -u epicyon
```

You'll also need to set up a web server configuration. An Nginx example is as follows:

``` bash
```

## Object Capabilities Security

A description of the proposed object capabilities model [is here](ocaps.md).

## Running Unit Tests

To run the unit tests:

``` bash
python3 epicyon.py --tests
```

To run the network tests. These simulate instances exchanging messages.

``` bash
python3 epicyon.py --testsnetwork
```

