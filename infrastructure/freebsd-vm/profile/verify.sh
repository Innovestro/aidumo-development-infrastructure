#!/bin/sh
# Bounded functional probes; run as guest root after profile installation.
set -eu
PATH=/sbin:/bin:/usr/sbin:/usr/bin:/usr/local/sbin:/usr/local/bin
export PATH
[ "$(id -u)" = 0 ]
[ "$(hostname)" = aidumo-freebsd-hostpoint-01 ]
php -l /usr/local/www/aidumo-b6/public/index.php
php-fpm -t
httpd -t
service php_fpm status
service apache24 status
service mysql-server status
su -m b6web -c '/usr/local/bin/php /usr/local/etc/aidumo-b6/fixture.php'
su -m b6web -c '/usr/local/bin/composer --version'
work=$(mktemp -d /tmp/b6-verify.XXXXXXXX)
trap 'rm -rf "$work"' EXIT HUP INT TERM
cert=/usr/local/etc/aidumo-b6/tls/cert.pem
for scheme in http https; do
  case "$scheme" in http) port=18080 ;; https) port=18443 ;; esac
  curl --fail --silent --show-error --cacert "$cert" -H 'Proxy: should-be-removed' \
    -D "$work/headers" "$scheme://localhost:$port/rewritten" > "$work/body"
  grep -iq '^X-Content-Type-Options: nosniff' "$work/headers"
  if grep -iq '^X-Powered-By:' "$work/headers"; then exit 1; fi
  php -r '$j=json_decode(file_get_contents($argv[1]),true,512,JSON_THROW_ON_ERROR); if (!str_starts_with($j["php"],"8.3.") || $j["sapi"]!=="fpm-fcgi" || $j["missing"]!==[] || $j["uri"]!=="/rewritten" || $j["db_user"]!=="b6web@localhost" || $j["db_marker"]!=="b6-persistent-v1" || !$j["private_writable"] || $j["public_writable"] || $j["http_proxy"]!==null || ($argv[2]==="https" && $j["https"]!=="on")) exit(1); echo json_encode($j,JSON_PRETTY_PRINT),"\n";' "$work/body" "$scheme"
  printf '%s_FPM_REWRITE_HEADERS_DB=PASS\n' "$scheme"
done
for path in /.htaccess /.env /fixture.php /private/persistence /missing; do
  code=$(curl --silent --show-error -o "$work/body" -w '%{http_code}' "http://127.0.0.1:18080$path")
  case "$path:$code" in /.htaccess:403|/.env:403|/fixture.php:404|/private/persistence:404|/missing:404) ;; *) echo "unexpected $path $code"; exit 1 ;; esac
  printf 'PUBLIC_BOUNDARY %s %s PASS\n' "$path" "$code"
done
# An untrusted self-signed certificate must fail rather than use a TLS bypass.
if curl --silent --show-error https://localhost:18443/rewritten > "$work/untrusted" 2> "$work/tls-error"; then
  echo 'unexpected default certificate trust'; exit 1
else
  code=$?
  [ "$code" = 60 ]
fi
printf 'UNTRUSTED_CERT_REJECTED=PASS\n'
httpd -M > "$work/modules"
grep -q proxy_fcgi_module "$work/modules"
grep -q mpm_event_module "$work/modules"
if grep -q php_module "$work/modules"; then exit 1; fi
sockstat -46l
printf 'PROFILE_VERIFICATION=PASS\n'
