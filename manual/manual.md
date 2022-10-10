# Contents
# Introduction
*The fediverse* is a set of federated servers, typically using a communication protocol called [ActivityPub](https://www.w3.org/TR/activitypub) which was devised by the [social working group](https://www.w3.org/wiki/Socialwg) within the World Wide Web Consortium (W3C). At present it is mostly used for [microblogging](https://en.wikipedia.org/wiki/Microblogging), although ActivityPub is sufficiently general that it can also be used for a variety of other purposes.

The word *fediverse* (federated universe) appears to have originated around 2012 as the first [identi.ca](https://en.wikipedia.org/wiki/Identi.ca) website was ending and the [pump.io](https://en.wikipedia.org/wiki/Pump.io) project was beginning. The ActivityPub protocol was initially called *ActivityPump*, due to the influence which pump.io had upon its creation. Fediverse servers are typically referred to as "instances".

Servers such as [Mastodon](https://github.com/mastodon/mastodon) are well known, but these are aimed at large scale deployments on powerful hardware running within data centers, making use of content distribution networks (CDN) and due to their large number of dependencies requiring someone with a high level of systems administration skill to maintain. Epicyon is designed for the opposite situation where it is only intended to have a single user or a small number of users (less than ten) running from your home location or on a modest VPS and where maintenance is extremely trivial such that it's possible to keep an instance running for long durations with minimal intervention.

Epicyon is part of the "small web" category of internet software, in that it is intended to scale via federation rather than to scale vertically via resource intensive and expensive hardware. Think many small communicating nodes rather than a small number of large servers. Also, in spite of the prevailing great obsession with scale, not everything needs to. You can federate with a small number of servers for a particular purpose - such as running a club or hackspace - and that's ok.

It is hardly possible to visit many sites on the web without your browser loading and running a large amount of javascript. Epicyon takes a minimalist approach where its web interface only uses HTML and CSS. You can disable javascript, or use a browser which doesn't have javascript capability, and the user experience is unchanged. Lack of javascript also rules out a large area of potential attack surface.

Epicyon also includes some lightweight organizing features, such as calendar, events and sharing economy features.

# Installation
## Prerequisites
You will need python version 3.7 or later.

On a Debian based system:

``` bash
sudo apt install -y tor python3-socks imagemagick python3-setuptools python3-cryptography python3-dateutil python3-idna python3-requests python3-flake8 python3-django-timezone-field python3-pyqrcode python3-png python3-bandit libimage-exiftool-perl certbot nginx wget
```
## Source code
The following instructions install Epicyon to the **/opt** directory. It's not essential that it be installed there, and it could be in any other preferred directory.

Clone the repo, or if you downloaded the tarball then extract it into the **/opt** directory.

```bash
cd /opt
git clone https://gitlab.com/bashrc2/epicyon
```
## Set permissions
Create a user for the server to run as:

```bash
sudo su
adduser --system --home=/opt/epicyon --group epicyon
chown -R epicyon:epicyon /opt/epicyon
```
## News mirrors
Link the news mirrors.

```bash
mkdir /var/www/YOUR_DOMAIN
mkdir -p /opt/epicyon/accounts/newsmirror
ln -s /opt/epicyon/accounts/newsmirror /var/www/YOUR_DOMAIN/newsmirror
```
## Create daemon
```bash
nano /etc/systemd/system/epicyon.service
```

Paste the following:

```bash
[Unit]
Description=epicyon
After=syslog.target
After=network.target

[Service]
Type=simple
User=epicyon
Group=epicyon
WorkingDirectory=/opt/epicyon
ExecStart=/usr/bin/python3 /opt/epicyon/epicyon.py --port 443 --proxy 7156 --domain YOUR_DOMAIN --registration open --debug --log_login_failures
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

Activate the daemon:

```bash
systemctl enable epicyon
systemctl start epicyon
```
## Web server setup
Create a web server configuration.

```bash
nano /etc/nginx/sites-available/YOUR_DOMAIN
```

And paste the following:

```nginx
server {
  listen 80;
  listen [::]:80;
  server_name YOUR_DOMAIN;
  access_log /dev/null;
  error_log /dev/null;
  client_max_body_size 31m;
  client_body_buffer_size 128k;
  
  limit_conn conn_limit_per_ip 10;
  limit_req zone=req_limit_per_ip burst=10 nodelay;
  
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
  gzip_types text/plain text/css text/vcard text/vcard+xml application/json application/ld+json application/javascript text/xml application/xml application/rdf+xml application/xml+rss text/javascript;
  
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

Enable the site:

```bash
ln -s /etc/nginx/sites-available/YOUR_DOMAIN /etc/nginx/sites-enabled/
```

## On your internet router
Forward port 443 from your internet router to your server. If you have dynamic DNS make sure its configured.

## Obtain a TLS certificate
```bash
systemctl stop nginx
certbot certonly -n --server https://acme-v02.api.letsencrypt.org/directory --standalone -d YOUR_DOMAIN --renew-by-default --agree-tos --email YOUR_EMAIL
systemctl start nginx
```

## Restart the web server
```bash
systemctl restart nginx
```

If you need to use [fail2ban](https://www.fail2ban.org) then failed login attempts can be found in **accounts/loginfailures.log**.

If you are using the [Caddy web server](https://caddyserver.com) then see [caddy.example.conf](https://code.libreserver.org/bashrc/epicyon/raw/main/caddy.example.conf).

Now you can navigate to your domain and register an account. The first account becomes the administrator.

## Installing on Onion or i2p domains
If you don't have access to the clearnet, or prefer not to use it, then it's possible to run an Epicyon instance easily from your laptop. There are scripts within the *deploy* directory which can be used to install an instance on a Debian or Arch/Parabola operating system. With some modification of package names they could be also used with other distros.

Please be aware that such installations will not federate with ordinary fediverse instances on the clearnet, unless those instances have been specially modified to do so. But onion instances will federate with other onion instances and i2p instances with other i2p instances.
# Upgrading
Unlike some other instance types, Epicyon is really easy to upgrade. It only requires a git pull to obtain the changes from the upstream repo, then set permissions and restart the daemon.

```bash
cd /opt/epicyon
git pull
chown -R epicyon:epicyon *
systemctl restart epicyon
```
# Registering accounts
# Following
# Creating posts
## Post scopes
## Attachments
## Events
## Maps
# The Timeline
# Side columns
# Account Profiles
## Basic details
## Roles
# Calendar
# Moderation
## Instance level moderation
## Moderator screen
## Account level moderation
# Themes
## Standard themes
## Theme customization
# Sharing economy
## Item ontology
## Federated shares
# Search
## Searching your posts
## Searching hashtags
## Searching shared items
# Building web communities
