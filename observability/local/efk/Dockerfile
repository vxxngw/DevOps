# Local EFK collector: same filters/labels as observability/efk/fluent.conf,
# but reads Docker json-file logs instead of Kubernetes CRI logs and writes to
# a plain-HTTP single-node Elasticsearch. The k8s config remains authoritative.
#
# Docker Desktop bind-mounts /var/lib/docker/containers as root-only, so the
# collector runs as root here (it only reads log files and writes its own
# buffer directory). The k8s deployment keeps its non-root securityContext.
FROM fluent/fluentd:v1.17-1

USER root
RUN apk add --no-cache --virtual .build-deps build-base ruby-dev \
 && gem install --no-document \
      fluent-plugin-elasticsearch:5.4.3 \
      fluent-plugin-prometheus:2.2.1 \
 && apk del .build-deps \
 && mkdir -p /buffers && chmod 777 /buffers

COPY fluent.local.conf /fluentd/etc/fluent.local.conf
ENV FLUENTD_CONF=fluent.local.conf
EXPOSE 24231
# The base image sets USER fluent; the local collector must stay root to read
# the Docker log directory, so the last instruction re-asserts it.
USER root
