FROM mcr.microsoft.com/playwright@sha256:c091b21d9fae78c76e85cd4356431e9b018402f172a214fc7d7a5e9a7e29d8ac
RUN apt-get update && apt-get install -y --no-install-recommends iptables && rm -rf /var/lib/apt/lists/*
# Supply the verified Claude Code 2.1.263 Linux binary as a build input.
COPY claude /usr/local/bin/claude
RUN chmod 755 /usr/local/bin/claude && claude --version
