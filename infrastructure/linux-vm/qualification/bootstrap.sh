#!/usr/bin/env bash
# Run as aidumo on the dedicated #19 guest. No host operations.
set -euo pipefail
[[ $(hostname) == aidumo-linux-runner-01 && $(id -un) == aidumo ]]
[[ $(sudo -n /usr/bin/id -u) == 0 ]]
sudo -n /usr/sbin/visudo -c
start=$SECONDS
sudo -n apt-get update -qq
sudo -n apt-get install -y --no-install-recommends build-essential pkg-config \
  libxml2-dev libsqlite3-dev libssl-dev libcurl4-openssl-dev libonig-dev \
  libzip-dev libsodium-dev libreadline-dev unzip libaio1t64 \
  libncurses6 python3-venv
mkdir -p "$HOME/b19/downloads"
cd "$HOME/b19/downloads"
curl -fL https://nodejs.org/dist/v22.23.3/node-v22.23.3-linux-x64.tar.xz -o node.tar.xz
printf '%s  node.tar.xz\n' df450af89261115ef9f9e3830c3eeb2cc9213b63c720b1af623cb5dcbe2e02de | sha256sum -c -
sudo -n mkdir -p /opt/aidumo-b19
sudo -n tar -xf node.tar.xz -C /opt/aidumo-b19
curl -fL https://www.php.net/distributions/php-8.3.35.tar.xz -o php.tar.xz
printf '%s  php.tar.xz\n' ff4630fbbbd94359134b7d3c223db59329905bdc4f5a9ef93d257b48e358619a | sha256sum -c -
tar -xf php.tar.xz
cd php-8.3.35
./configure --prefix=/opt/aidumo-b19/php --with-config-file-path=/opt/aidumo-b19/php/etc \
  --disable-cgi --disable-phpdbg --without-pear --enable-mbstring --enable-bcmath \
  --enable-pcntl --with-pdo-mysql=mysqlnd --with-mysqli=mysqlnd --with-openssl \
  --with-curl --with-zip --with-sodium --with-zlib --with-readline
make -j4
sudo -n make install
sudo -n mkdir -p /opt/aidumo-b19/php/etc
printf 'memory_limit=512M\ndate.timezone=UTC\n' | sudo -n tee /opt/aidumo-b19/php/etc/php.ini >/dev/null
cd "$HOME/b19/downloads"
curl -fL https://getcomposer.org/download/2.10.3/composer.phar -o composer
printf '%s  composer\n' 7a2d379d5b8ffdaa028580ef26494c36d2feef4b178d3dd1473a4dbc5e17c8d6 | sha256sum -c -
sudo -n install -m 755 composer /opt/aidumo-b19/php/bin/composer
curl -fL https://archive.mariadb.org/mariadb-11.4.13/bintar-linux-systemd-x86_64/mariadb-11.4.13-linux-systemd-x86_64.tar.gz -o mariadb.tar.gz
printf '%s  mariadb.tar.gz\n' 3cebf63914df3154b7cb6d548337eb2be42c773aeb641110446b72e2746cfed7 | sha256sum -c -
sudo -n tar -xf mariadb.tar.gz -C /opt/aidumo-b19
# The upstream binary uses the pre-t64 SONAME; Ubuntu supplies ABI-compatible libaio.
sudo -n ln -sfn /usr/lib/x86_64-linux-gnu/libaio.so.1t64 /opt/aidumo-b19/mariadb-11.4.13-linux-systemd-x86_64/lib/libaio.so.1
printf 'BOOTSTRAP_SECONDS=%s\n' "$((SECONDS-start))"
