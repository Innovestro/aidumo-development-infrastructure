#!/bin/bash
set -euo pipefail
# Run on the Docker host. Never mount this script's checkout or Docker socket.
base=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
root=${B1_ROOT:-/mnt/user/appdata/aidumo-codex}
name=${B1_CONTAINER:-aidumo-codex}
image=${B1_IMAGE:-aidumo-codex:0.157.1}
case ${1:-help} in
  build)
    docker build --platform linux/amd64 -t "$image" "$base"
    ;;
  create)
    for part in workspace codex state secrets; do
      test -d "$root/$part" || { echo "Missing $root/$part; follow README setup." >&2; exit 1; }
    done
    test -s "$root/secrets/git_key"
    test -s "$root/secrets/git_key_suite"
    test -s "$root/secrets/gh_token"
    test -s "$root/secrets/linux_vm_key"
    test -s "$root/secrets/linux_vm_known_hosts"
    test -s "$root/secrets/freebsd_vm_key"
    test -s "$root/secrets/freebsd_vm_known_hosts"
    docker run --pull never -d --name "$name" --hostname aidumo-codex --init \
      --restart unless-stopped --platform linux/amd64 --user 1000:1000 \
      --cpus 2 --memory 4g --memory-swap 4g --pids-limit 256 \
      --read-only --cap-drop ALL --security-opt no-new-privileges:true \
      --tmpfs /tmp:rw,nosuid,nodev,size=256m,mode=1777 \
      --tmpfs /home/node:rw,nosuid,nodev,size=16m,uid=1000,gid=1000,mode=700 \
      --log-driver json-file --log-opt max-size=1m --log-opt max-file=2 \
      --mount "type=bind,src=$root/workspace,dst=/workspace" \
      --mount "type=bind,src=$root/codex,dst=/codex" \
      --mount "type=bind,src=$root/state,dst=/state" \
      --mount "type=bind,src=$root/secrets/git_key,dst=/run/secrets/git_key,readonly" \
      --mount "type=bind,src=$root/secrets/git_key_suite,dst=/run/secrets/git_key_suite,readonly" \
      --mount "type=bind,src=$root/secrets/gh_token,dst=/run/secrets/gh_token,readonly" \
      --mount "type=bind,src=$root/secrets/linux_vm_key,dst=/run/secrets/linux_vm_key,readonly" \
      --mount "type=bind,src=$root/secrets/linux_vm_known_hosts,dst=/run/secrets/linux_vm_known_hosts,readonly" \
      --mount "type=bind,src=$root/secrets/freebsd_vm_key,dst=/run/secrets/freebsd_vm_key,readonly" \
      --mount "type=bind,src=$root/secrets/freebsd_vm_known_hosts,dst=/run/secrets/freebsd_vm_known_hosts,readonly" \
      "$image"
    ;;
  start) docker start "$name" ;;
  login) docker exec -it "$name" codex login --device-auth ;;
  login-api) docker exec -i "$name" codex login --with-api-key ;;
  auth-status) docker exec "$name" codex login status ;;
  shell) docker exec -it "$name" bash ;;
  run|resume)
    test "$#" -eq 2 || { echo 'Supply a prompt file (no secrets).' >&2; exit 1; }
    test "$(wc -c < "$2")" -le 65536
    # Each submission has its own input; runtime admits at most one, without a queue.
    prompt=$(docker exec "$name" mktemp /tmp/b1-task.XXXXXX)
    docker exec -i "$name" sh -c 'cat > "$1"' sh "$prompt" < "$2"
    docker exec -d "$name" runtime "$1" "$prompt"
    echo 'Detached invocation submitted; inspect logs/exit-code for actual result.'
    ;;
  undrain) docker exec "$name" rm -f /state/drain ;;
  drain)
    docker exec "$name" touch /state/drain
    docker exec "$name" flock -w 60 /state/executor.lock true
    ;;
  stop|restart)
    "$0" drain  # Timeout leaves the running container drained; no forced kill.
    docker "$1" "$name"
    ;;
  logs)
    docker logs --tail 10 "$name"
    docker exec "$name" sh -c 'test ! -f /state/runtime.jsonl || tail -40 /state/runtime.jsonl'
    ;;
  measure)
    docker stats --no-stream --format '{{.Name}} CPU={{.CPUPerc}} RAM={{.MemUsage}} PIDs={{.PIDs}} NET={{.NetIO}} BLOCK={{.BlockIO}}' "$name"
    docker exec "$name" du -s -B1 /workspace /codex /state
    docker image inspect "$(docker inspect "$name" --format '{{.Image}}')" --format 'Image={{.Id}} bytes={{.Size}}'
    ;;
  *) echo 'Usage: unraid.sh build|create|start|login|login-api|auth-status|shell|run FILE|resume FILE|undrain|drain|stop|restart|logs|measure' ;;
esac
