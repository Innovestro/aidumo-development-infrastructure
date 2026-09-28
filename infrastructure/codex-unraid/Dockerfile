# linux/amd64: the Unraid pilot, not a multi-platform support promise.
FROM node:22.23.2-bookworm-slim@sha256:43aeff40f4afc22e83f7589a2f37e111cff5ca84529571f1c8415bcc5fcc21b2
ARG CODEX_VERSION=0.157.1
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl git openssh-client python3 util-linux \
    && rm -rf /var/lib/apt/lists/* \
    && curl -fsSL https://github.com/cli/cli/releases/download/v2.101.0/gh_2.101.0_linux_amd64.tar.gz -o /tmp/gh.tar.gz \
    && echo '9bca2d1c16825f109907a23307628a2f0698fbf99662b73a5cf0b020293072b8  /tmp/gh.tar.gz' | sha256sum -c - \
    && tar -xzf /tmp/gh.tar.gz -C /tmp \
    && install -m 755 /tmp/gh_2.101.0_linux_amd64/bin/gh /usr/local/bin/gh \
    && rm -rf /tmp/gh.tar.gz /tmp/gh_2.101.0_linux_amd64 \
    && npm install --global @openai/codex@${CODEX_VERSION} \
    && npm cache clean --force
ENV HOME=/home/node CODEX_HOME=/codex GH_CONFIG_DIR=/tmp/gh \
    GIT_SSH_COMMAND="ssh -F /etc/codex-ssh.conf" \
    GH_PROMPT_DISABLED=1 GIT_TERMINAL_PROMPT=0
COPY config.toml /opt/codex/config.toml
COPY ssh.conf /etc/codex-ssh.conf
COPY known_hosts /etc/codex-known-hosts
COPY runtime.py /usr/local/bin/runtime
RUN chmod 755 /usr/local/bin/runtime
USER 1000:1000
WORKDIR /workspace
ENTRYPOINT ["runtime"]
CMD ["idle"]
