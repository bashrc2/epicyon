<blockquote><b>Epicyon</b>, meaning <i>"more than a dog"</i>. Largest of the <i>Borophaginae</i> which lived in North America 20-5 million years ago.</blockquote>

<img src="https://libreserver.org/epicyon/img/screenshot_rc3.jpg" width="80%"/>

<img src="https://libreserver.org/epicyon/img/mobile.jpg" width="30%"/>

Epicyon is a [fediverse](https://en.wikipedia.org/wiki/Fediverse) server suitable for self-hosting a small number of accounts on low power systems.

Key features:

 * Open standards: HTML, CSS, ActivityPub, RSS, CalDAV.
 * Supports common web browsers and [shell browsers](https://lynx.invisible-island.net).
 * Will not drain your mobile or laptop battery.
 * Customisable themes. It doesn't have to look bland.
 * Emoji reactions.
 * Geospatial hashtags.
 * Does not require much RAM, either on server or client.
 * Suitable for installation on single board computers.
 * No timeline algorithms.
 * No javascript.
 * No database. Data stored as ordinary files.
 * No fashionable web frameworks. *"Boring by design"*.
 * No blockchain garbage.
 * Written in Python, with few dependencies.
 * AGPL license, which big tech hates.

Epicyon is for people who are tired of *big anything* and just want to DIY their online social experience without much fuss or expense. Think *water cooler discussions* rather than *shouting into the void*, in which you're mainly just reading and responding to the posts of people that you're following.

[Project Goals](README_goals.md) - [Commandline interface](README_commandline.md) - [Customizations](README_customizations.md) - [Software Architecture](README_architecture.md) - [Code of Conduct](code-of-conduct.md) - [Principles of Unity](principlesofunity.md) - [C2S Desktop Client](README_desktop_client.md) - [Coding Style](README_coding_style.md)

Matrix room: **#epicyon:matrix.libreserver.org**

Includes emojis designed by [OpenMoji](https://openmoji.org) – the open-source emoji and icon project. License: [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0). Blob Cat Emoji and Meowmoji were made by Nitro Blob Hub, licensed under [Apache 2.0](https://www.apache.org/licenses/LICENSE-2.0). [Digital Pets emoji](https://opengameart.org/content/16x16-emotes-for-rpgs-and-digital-pets) were made by Tomcat94 and licensed under CC0.

<img src="https://libreserver.org/epicyon/img/screenshot_light.jpg" width="80%"/>

<img src="https://libreserver.org/epicyon/img/screenshot_login.jpg" width="80%"/>

## Package Dependencies

You will need python version 3.7 or later.

On Arch/Parabola:

``` bash
sudo pacman -S tor python-pip python-pysocks python-cryptography \
               imagemagick python-requests \
               perl-image-exiftool python-dateutil \
               certbot flake8 bandit
sudo pip3 install pyqrcode pypng
```

Or on Debian:

``` bash
sudo apt install -y \
    tor python3-socks imagemagick \
    python3-setuptools \
    python3-cryptography \
    python3-dateutil \
    python3-idna python3-requests \
    python3-django-timezone-field \
    libimage-exiftool-perl python3-flake8 \
    python3-pyqrcode python3-png python3-bandit \
    certbot nginx wget
```

## Installation

In the most common case you'll be using systemd to set up a daemon to run the server.

The following instructions install Epicyon to the **/opt** directory. It's not essential that it be installed there, and it could be in any other preferred directory.

Clone the repo, or if you downloaded the tarball then extract it into the **/opt** directory.

``` bash
cd /opt
git clone https://gitlab.com/bashrc2/epicyon
```

Add a dedicated user so that we don't have to run as root.

``` bash
adduser --system --home=/opt/epicyon --group epicyon
```

Link news mirrors:

``` bash
mkdir /var/www/YOUR_DOMAIN
mkdir -p /opt/epicyon/accounts/newsmirror
ln -s /opt/epicyon/accounts/newsmirror /var/www/YOUR_DOMAIN/newsmirror
```

Edit */etc/systemd/system/epicyon.service* and add the following:

``` systemd
[Unit]
Description=epicyon
After=syslog.target
After=network.target

[Service]
Type=simple
User=epicyon
Group=epicyon
WorkingDirectory=/opt/epicyon
ExecStart=/usr/bin/python3 /opt/epicyon/epicyon.py --port 443 --proxy 7156 --domain YOUR_DOMAIN --registration open --logLoginFailures
Environment=USER=epicyon
Environment=PYTHONUNBUFFERED=true
Restart=always
StandardError=syslog
CPUQuota=80%
ProtectHome=true
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true
ProtectKernelLogs=true
ProtectHostname=true
ProtectClock=true
ProtectProc=invisible
ProcSubset=pid
PrivateTmp=true
PrivateUsers=true
PrivateDevices=true
PrivateIPC=true
MemoryDenyWriteExecute=true
NoNewPrivileges=true
LockPersonality=true
RestrictRealtime=true
RestrictSUIDSGID=true
RestrictNamespaces=true
SystemCallArchitectures=native

[Install]
WantedBy=multi-user.target
```

Here the server was installed to */opt/epicyon*, but you can change that to wherever you installed it.

Then run the daemon:

``` bash
systemctl enable epicyon
chown -R epicyon:epicyon /opt/epicyon
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

You'll also need to set up a web server configuration. For Nginx edit */etc/nginx/sites-available/YOUR_DOMAIN* as follows:

``` nginx
server {
    listen 80;
    listen [::]:80;
    server_name YOUR_DOMAIN;
    access_log /dev/null;
    error_log /dev/null;
    client_max_body_size 31m;
    client_body_buffer_size 128k;

    index index.html;
    rewrite ^ https://$server_name$request_uri? permanent;
}

server {
    listen 443 ssl;
    server_name YOUR_DOMAIN;

    gzip on;
    gzip_disable "msie6";
    gzip_vary on;
    gzip_proxied any;
    gzip_min_length 1024;
    gzip_comp_level 6;
    gzip_buffers 16 8k;
    gzip_http_version 1.1;
    gzip_types text/plain text/css application/json application/ld+json application/javascript text/xml application/xml application/rdf+xml application/xml+rss text/javascript;

    ssl_stapling off;
    ssl_stapling_verify off;
    ssl on;
    ssl_certificate /etc/letsencrypt/live/YOUR_DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/YOUR_DOMAIN/privkey.pem;
    #ssl_dhparam /etc/ssl/certs/YOUR_DOMAIN.dhparam;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!MEDIUM:!LOW:!aNULL:!NULL:!SHA;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_tickets off;

    add_header Content-Security-Policy "default-src https:; script-src https: 'unsafe-inline'; style-src https: 'unsafe-inline'";
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header X-Download-Options noopen;
    add_header X-Permitted-Cross-Domain-Policies none;
	add_header Strict-Transport-Security "max-age=15768000; includeSubDomains; preload" always;

    access_log /dev/null;
    error_log /dev/null;

    index index.html;

    location /newsmirror {
        root /var/www/YOUR_DOMAIN;
        try_files $uri =404;
    }

    keepalive_timeout 70;
    sendfile on;

    location / {
        proxy_http_version 1.1;
        client_max_body_size 31M;
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forward-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forward-Proto http;
        proxy_set_header X-Nginx-Proxy true;
        proxy_temp_file_write_size 64k;
        proxy_connect_timeout 10080s;
        proxy_send_timeout 10080;
        proxy_read_timeout 10080;
        proxy_buffer_size 64k;
        proxy_buffers 16 32k;
        proxy_busy_buffers_size 64k;
        proxy_redirect off;
        proxy_request_buffering off;
        proxy_buffering off;
        proxy_pass http://localhost:7156;
        tcp_nodelay on;
    }
}
```

Changing your domain name as appropriate. Activate the configuration with:

``` bash
ln -s /etc/nginx/sites-available/YOUR_DOMAIN /etc/nginx/sites-enabled/
```

Generate a LetsEncrypt certificate.

``` bash
certbot certonly -n --server https://acme-v02.api.letsencrypt.org/directory --standalone -d YOUR_DOMAIN --renew-by-default --agree-tos --email YOUR_EMAIL
```

And restart the web server:

``` bash
systemctl restart nginx
```

If you need to use **fail2ban** then failed login attempts can be found in *accounts/loginfailures.log*.

If you are using the [Caddy web server](https://caddyserver.com) then see *caddy.example.conf*

## Running Static Analysis

Static analysis can be run with:

``` bash
./static_analysis
```

## Running a security audit

To run a security audit:

``` bash
./security_audit
```

Note that not all of the issues identified will necessarily be relevant to this project. Consider its output as a list of things which potentially can be investigated but usually will turn out not to be relevant.


## Installing on Onion or i2p domains

If you don't have access to the clearnet, or prefer not to use it, then it's possible to run an Epicyon instance easily from your laptop. There are scripts within the ```deploy``` directory which can be used to install an instance on a Debian or Arch/Parabola operating system. With some modification of package names they could be also used with other distros.

Please be aware that such installations will not federate with ordinary fediverse instances on the clearnet, unless those instances have been specially modified to do so. But onion instances will federate with other onion instances and i2p instances with other i2p instances.


## Custom Fonts

If you want to use a particular font then copy it into the *fonts* directory, rename it as *custom.ttf/woff/woff2/otf* and then restart the Epicyon daemon.

``` bash
systemctl restart epicyon
```

## Custom Favicon

If you want to use your own favicon then copy your `favicon.ico` file to the base directory where you installed Epicyon.


## Changing Themes

When changing themes you may need to ensure that your nginx cache is cleared (/var/www/cache/*) and that your local browser cache is cleared for the site (Shift + Reload). Otherwise images and icons from the previous theme may remain.


## Adding Themes

If you want to add a new theme then first add the name of your theme to the translations files.

Within the `theme` directory create a directory with the name of your theme and add icons and banners. As a quick way to begin you could copy the contents of `theme/default`, then edit the graphics. Keep the size of images as small as possible to avoid creating a laggy user interface.

On a running instance you can experiment with colors or fonts by editing `epicyon.css` and then reloading the web page. Once you are happy with the results then you can update the changed variable values within your `theme/yourtheme/theme.json` file.

Epicyon normally uses one set of CSS files whose variables are then altered per theme. If you want to use entirely bespoke CSS then copy `epicyon-*.css` into your theme directory and edit it to your requirements. This will be used rather than the default CSS files. Be warned that if you're maintaining the CSS files yourself then you may need to keep up with whatever changes are happening upstream, otherwise your user interface will break.


## Running Unit Tests

To run the unit tests:

``` bash
python3 epicyon.py --tests
```

To run the network tests. These simulate instances exchanging messages.

``` bash
python3 epicyon.py --testsnetwork
```

## Software Bill of Materials

To update the software bill of materials:

``` bash
sudo pip3 install scanoss
make clean
make sbom
```
