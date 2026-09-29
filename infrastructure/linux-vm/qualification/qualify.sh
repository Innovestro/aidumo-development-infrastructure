#!/usr/bin/env bash
# Execute existing Suite commands against the selected revision; no GitHub writes.
set -euo pipefail
[[ $(hostname) == aidumo-linux-runner-01 && $(id -un) == aidumo ]]
export PATH=/opt/aidumo-b19/php/bin:/opt/aidumo-b19/node-v22.23.3-linux-x64/bin:$PATH
suite=${1:?usage: qualify.sh ABSOLUTE_SUITE_DIRECTORY php|frontend|mariadb}
lane=${2:?missing lane}
[[ $suite == /home/aidumo/b19/* ]]
cd "$suite"
[[ $(git rev-parse HEAD) == dcdea09ffd16cb20485d369772aac018451483de ]]
git diff --quiet
case "$lane" in
  php)
    composer validate --strict
    composer check-platform-reqs
    ./vendor/bin/pint --test
    composer analyse
    php artisan test --compact
    ;;
  frontend)
    npm ci
    npm run check
    npm run build
    ;;
  mariadb)
    export DB_CONNECTION=mysql DB_HOST=127.0.0.1 DB_PORT=3306
    export DB_DATABASE=aidumo_suite_ci DB_USERNAME=aidumo DB_PASSWORD=aidumo
    export P649B_MARIADB_ROOT_PASSWORD=root
    groups=$(python3 -c 'import sys,json; sys.path.insert(0,".github/scripts"); from run_mariadb_validation import KNOWN_GROUPS; print(json.dumps(KNOWN_GROUPS))')
    python3 .github/scripts/run_mariadb_validation.py --groups-json "$groups"
    ;;
  *) exit 2 ;;
esac
git diff --exit-code
