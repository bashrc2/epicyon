<blockquote><b>Epicyon</b>, meaning <i>"more than a dog"</i>. Largest of the <i>Borophaginae</i> which lived in North America 20-5 million years ago.<blockquote>

Epicyon is a modern [ActivityPub](https://www.w3.org/TR/activitypub) compliant server implementing both S2S and C2S protocols and sutable for installation on single board computers. It includes features such as moderation tools, post expiry, content warnings, image descriptions and perimeter defense against adversaries.

[Project Goals](README_goals.md) - [Commandline interface](README_commandline.md) - [Customizations](README_customizations.md) - [Object Capabilities](ocaps.md) - [Code of Conduct](code-of-conduct.md)

Includes emojis designed by [OpenMoji](https://openmoji.org) – the open-source emoji and icon project. License: [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0)

<img src="https://code.freedombone.net/bashrc/epicyon/raw/master/img/screenshots.jpg?raw=true" width=50%/>

## Package Dependencies

On Arch/Parabola:

``` bash
sudo pacman -S tor python-pip python-pysocks python-pycryptodome \
               python-beautifulsoup4 imagemagick python-pillow \
	       python-numpy python-dateutil certbot
sudo pip install commentjson
```

Or on Debian:

``` bash
sudo apt-get -y install tor python3-pip python3-socks imagemagick \
                python3-numpy python3-setuptools python3-crypto \
		python3-dateutil python3-pil.imagetk certbot
sudo pip3 install commentjson beautifulsoup4 pycryptodome
```

## Installation

In the most common case you'll be using systemd to set up a daemon to run the server.

Add a dedicated user so that we don't have to run as root.

``` bash
adduser --system --home=/etc/epicyon --group epicyon
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
WorkingDirectory=/etc/epicyon
ExecStart=/usr/bin/python3 /etc/epicyon/epicyon.py --port 443 --proxy 7156 --domain YOUR_DOMAIN --registration open --debug
Environment=USER=epicyon
Restart=always
StandardError=syslog

[Install]
WantedBy=multi-user.target
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

You'll also need to set up a web server configuration. For Nginx edit */etc/nginx/sites-available/YOUR_DOMAIN* as follows:

``` nginx
server {
    listen 80;
    listen [::]:80;
    server_name YOUR_DOMAIN;
    root /var/www/YOUR_DOMAIN/htdocs;
    access_log /dev/null;
    error_log /dev/null;
    client_max_body_size 20m;
    client_body_buffer_size 128k;

    limit_conn conn_limit_per_ip 10;
    limit_req zone=req_limit_per_ip burst=10 nodelay;

    index index.html;
    rewrite ^ https://$server_name$request_uri? permanent;
}

server {
    listen 443 ssl;
    server_name YOUR_DOMAIN;

    ssl_stapling off;
    ssl_stapling_verify off;
    ssl on;
    ssl_certificate /etc/letsencrypt/live/YOUR_DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/YOUR_DOMAIN/privkey.pem;
    #ssl_dhparam /etc/ssl/certs/YOUR_DOMAIN.dhparam;

    ssl_session_cache  builtin:1000  shared:SSL:10m;
    ssl_session_timeout 60m;
    ssl_prefer_server_ciphers on;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-AES128-SHA256:ECDHE-RSA-AES128-SHA256:ECDHE-ECDSA-AES128-SHA:ECDHE-RSA-AES256-SHA384:ECDHE-RSA-AES128-SHA:ECDHE-ECDSA-AES256-SHA384:ECDHE-ECDSA-AES256-SHA:ECDHE-RSA-AES256-SHA:DHE-RSA-AES128-SHA256:DHE-RSA-AES128-SHA:DHE-RSA-AES256-SHA256:DHE-RSA-AES256-SHA:ECDHE-ECDSA-DES-CBC3-SHA:ECDHE-RSA-DES-CBC3-SHA:EDH-RSA-DES-CBC3-SHA:AES128-GCM-SHA256:AES256-GCM-SHA384:AES128-SHA256:AES256-SHA256:AES128-SHA:AES256-SHA:DES-CBC3-SHA:!DSS';
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header X-Download-Options noopen;
    add_header X-Permitted-Cross-Domain-Policies none;

    add_header X-Robots-Tag "noindex, nofollow, nosnippet, noarchive";
    add_header Strict-Transport-Security max-age=15768000;

    access_log /dev/null;
    error_log /dev/null;

    root /var/www/YOUR_DOMAIN/htdocs;
    index index.html;
 
    location / {
        proxy_http_version 1.1;
        client_max_body_size 11M;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
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
    }
}
```

Changing your domain name as appropriate. Active the configuration with:

``` bash
ln -s /etc/nginx/sites-available/YOUR_DOMAIN /etc/nginx/sites-enabled/
```

Generate a LetsEncrypt certificate.

``` bash
certbot certonly -n --server https://acme-v01.api.letsencrypt.org/directory --standalone -d YOUR_DOMAIN --renew-by-default --agree-tos --email YOUR_EMAIL
```

And restart the web server:

``` bash
systemctl restart nginx
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

