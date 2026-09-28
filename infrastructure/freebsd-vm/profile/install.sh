#!/bin/sh
set -eu
PATH=/sbin:/bin:/usr/sbin:/usr/bin:/usr/local/sbin:/usr/local/bin
export PATH
[ "$(id -u)" = 0 ]
[ "$(freebsd-version -u)" = 15.1-RELEASE ]
[ "$(hostname)" = aidumo-freebsd-hostpoint-01 ]
[ ! -e /usr/local/etc/aidumo-b6 ]
[ ! -e /root/b6-before-profile ]
for tool in php php-fpm httpd mariadb openssl curl; do command -v "$tool" >/dev/null; done
php -r 'exit(PHP_MAJOR_VERSION === 8 && PHP_MINOR_VERSION === 3 ? 0 : 1);'
if pw usershow b6web >/dev/null 2>&1; then
  echo "STOP: existing b6web account; inspect state" >&2
  exit 1
fi
[ ! -e /var/db/mysql/mysql ]
[ ! -e /var/db/aidumo-b6 ]
[ ! -e /usr/local/www/aidumo-b6 ]
[ ! -e /usr/local/etc/mysql/conf.d/z-b6.cnf ]
install -d -m 700 /root/b6-before-profile
cp -p /usr/local/etc/apache24/httpd.conf /root/b6-before-profile/httpd.conf
cp -p /usr/local/etc/php-fpm.conf /root/b6-before-profile/php-fpm.conf
cp -p /etc/rc.conf /root/b6-before-profile/rc.conf
pw useradd b6web -d /var/db/aidumo-b6 -s /usr/sbin/nologin -c 'B6 local PHP fixture'
install -d -o root -g wheel -m 755 /var/db/aidumo-b6 /usr/local/www/aidumo-b6 /usr/local/www/aidumo-b6/public /usr/local/etc/aidumo-b6
install -d -o b6web -g b6web -m 700 /var/db/aidumo-b6/private
install -d -o root -g wheel -m 700 /usr/local/etc/aidumo-b6/tls
src=$(CDPATH= cd "$(dirname "$0")" && pwd)
install -m 644 "$src/httpd.conf" /usr/local/etc/apache24/httpd.conf
install -m 644 "$src/php-fpm.conf" /usr/local/etc/php-fpm.conf
install -m 644 "$src/mariadb.cnf" /usr/local/etc/mysql/conf.d/z-b6.cnf
install -m 644 "$src/public/index.php" /usr/local/www/aidumo-b6/public/index.php
install -m 644 "$src/public/.htaccess" /usr/local/www/aidumo-b6/public/.htaccess
install -m 644 "$src/fixture.php" /usr/local/etc/aidumo-b6/fixture.php
openssl req -x509 -newkey rsa:2048 -noenc -days 30 -subj /CN=localhost -addext 'subjectAltName=DNS:localhost,IP:127.0.0.1' -addext 'basicConstraints=critical,CA:FALSE' -addext 'extendedKeyUsage=serverAuth' -keyout /usr/local/etc/aidumo-b6/tls/key.pem -out /usr/local/etc/aidumo-b6/tls/cert.pem 2>/dev/null
chmod 600 /usr/local/etc/aidumo-b6/tls/key.pem
chmod 644 /usr/local/etc/aidumo-b6/tls/cert.pem
php -l /usr/local/etc/aidumo-b6/fixture.php
php -l /usr/local/www/aidumo-b6/public/index.php
php-fpm -t
httpd -t
sysrc php_fpm_enable=YES php_fpm_umask=0077 apache24_enable=YES mysql_enable=YES
service mysql-server start
service php_fpm start
service apache24 start
mariadb -u root <<'SQL'
DROP USER IF EXISTS ''@'localhost', ''@'aidumo-freebsd-hostpoint-01';
DROP DATABASE IF EXISTS test;
CREATE USER 'b6web'@'localhost' IDENTIFIED VIA unix_socket;
GRANT ALL PRIVILEGES ON b6_fixture.* TO 'b6web'@'localhost';
CREATE DATABASE b6_persistence;
CREATE TABLE b6_persistence.marker (id INT PRIMARY KEY, value VARCHAR(32));
INSERT INTO b6_persistence.marker VALUES (1, 'b6-persistent-v1');
GRANT SELECT ON b6_persistence.* TO 'b6web'@'localhost';
SQL
su -m b6web -c '/usr/local/bin/php /usr/local/etc/aidumo-b6/fixture.php --initialize-marker'
curl --fail --silent --show-error http://127.0.0.1:18080/rewritten
curl --fail --silent --show-error --cacert /usr/local/etc/aidumo-b6/tls/cert.pem https://localhost:18443/rewritten
