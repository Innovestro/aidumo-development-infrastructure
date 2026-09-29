#!/usr/bin/env bash
# Initialize one disposable, loopback-only database service; preserve existing data.
set -euo pipefail
[[ $(hostname) == aidumo-linux-runner-01 && $(id -un) == aidumo ]]
base=/opt/aidumo-b19/mariadb-11.4.13-linux-systemd-x86_64
sudo -n id b19-mysql >/dev/null 2>&1 || sudo -n useradd --system --home-dir /var/lib/aidumo-b19-mariadb --shell /usr/sbin/nologin b19-mysql
sudo -n install -d -o b19-mysql -g b19-mysql -m 700 /var/lib/aidumo-b19-mariadb
if ! sudo -n test -f /var/lib/aidumo-b19-mariadb/.b19-initialized; then
  if [[ -n $(sudo -n find /var/lib/aidumo-b19-mariadb -mindepth 1 -maxdepth 1 -print -quit) ]]; then
    echo 'Unconfirmed database initialization: inspect and retain existing data before retrying.' >&2
    exit 1
  fi
  sudo -n env LD_LIBRARY_PATH="$base/lib" "$base/scripts/mariadb-install-db" \
    --no-defaults --basedir="$base" --datadir=/var/lib/aidumo-b19-mariadb \
    --user=b19-mysql --auth-root-authentication-method=socket --skip-test-db
  sudo -n touch /var/lib/aidumo-b19-mariadb/.b19-initialized
fi
sudo -n tee /etc/systemd/system/aidumo-b19-mariadb.service >/dev/null <<UNIT
[Unit]
Description=Disposable Aidumo B19 qualification MariaDB
After=network.target
[Service]
User=b19-mysql
Group=b19-mysql
Environment=LD_LIBRARY_PATH=$base/lib
RuntimeDirectory=aidumo-b19-mariadb
RuntimeDirectoryMode=0755
ExecStart=$base/bin/mariadbd --no-defaults --basedir=$base --datadir=/var/lib/aidumo-b19-mariadb --socket=/run/aidumo-b19-mariadb/mysql.sock --pid-file=/run/aidumo-b19-mariadb/mysql.pid --bind-address=127.0.0.1 --skip-name-resolve --port=3306 --character-set-server=utf8mb4 --collation-server=utf8mb4_unicode_ci
TimeoutStopSec=120
[Install]
WantedBy=multi-user.target
UNIT
sudo -n systemctl daemon-reload
sudo -n systemctl enable --now aidumo-b19-mariadb
for attempt in $(seq 1 30); do
  if sudo -n env LD_LIBRARY_PATH="$base/lib" "$base/bin/mariadb" --no-defaults --socket=/run/aidumo-b19-mariadb/mysql.sock -e 'SELECT VERSION()'; then break; fi
  sleep 1
done
# These are public disposable CI fixture credentials, matching Suite's workflow.
# Root remains socket-authenticated locally; TCP root is only loopback.
sudo -n env LD_LIBRARY_PATH="$base/lib" "$base/bin/mariadb" --no-defaults --socket=/run/aidumo-b19-mariadb/mysql.sock <<'SQL'
CREATE DATABASE IF NOT EXISTS aidumo_suite_ci CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'aidumo'@'127.0.0.1' IDENTIFIED BY 'aidumo';
GRANT ALL ON aidumo_suite_ci.* TO 'aidumo'@'127.0.0.1';
CREATE USER IF NOT EXISTS 'root'@'127.0.0.1' IDENTIFIED BY 'root';
GRANT ALL ON *.* TO 'root'@'127.0.0.1' WITH GRANT OPTION;
SQL
