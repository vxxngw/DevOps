FROM jenkins/inbound-agent:3391.va_37fa_a_305d6d-5-jdk21 AS java
FROM docker:29.9.3-cli AS docker
FROM node:24.22.1-trixie-slim AS node
FROM ghcr.io/gitleaks/gitleaks:v8.30.1 AS gitleaks
FROM aquasec/trivy:0.76.2 AS trivy
FROM python:3.12.16-slim-trixie@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b AS infra-tools
COPY infra/versions.json /tmp/versions.json
COPY ci/install-agent-tools.py /tmp/install.py
RUN python /tmp/install.py

FROM python:3.12.16-slim-trixie@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b
RUN apt-get update && apt-get install -y --no-install-recommends git curl openssh-client libstdc++6 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 1000 jenkins && useradd --uid 1000 --gid 1000 --create-home jenkins \
    && mkdir -p /home/jenkins/agent /home/jenkins/.cache \
    && chown -R 1000:1000 /home/jenkins
COPY --from=java /opt/java/openjdk/ /opt/java/openjdk/
COPY --from=java /usr/share/jenkins/agent.jar /usr/share/jenkins/agent.jar
COPY --from=java /usr/local/bin/jenkins-agent /usr/local/bin/jenkins-agent
COPY --from=docker /usr/local/bin/docker /usr/local/bin/docker
COPY --from=docker /usr/local/libexec/docker/cli-plugins/ /usr/local/libexec/docker/cli-plugins/
COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/lib/node_modules/ /usr/local/lib/node_modules/
COPY --from=gitleaks /usr/bin/gitleaks /usr/local/bin/gitleaks
COPY --from=trivy /usr/local/bin/trivy /usr/local/bin/trivy
COPY --from=infra-tools /out/ /usr/local/bin/
RUN ln -s ../lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
    && ln -s ../lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx
ENV JAVA_HOME=/opt/java/openjdk AGENT_WORKDIR=/home/jenkins/agent
ENV PATH="/opt/java/openjdk/bin:${PATH}"
WORKDIR /home/jenkins/agent
USER 1000:1000
HEALTHCHECK --interval=15s --timeout=3s --start-period=45s --retries=10 CMD python3 -c "from pathlib import Path; import sys; sys.exit(not any(p.read_bytes().split(b'\0')[0].endswith(b'/java') for p in Path('/proc').glob('[0-9]*/cmdline') if p.is_file()))"
ENTRYPOINT ["/usr/local/bin/jenkins-agent"]
