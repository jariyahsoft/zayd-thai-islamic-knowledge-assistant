FROM debian:bookworm-slim

RUN apt-get update \
    && apt-get install --yes --no-install-recommends awscli ca-certificates gnupg postgresql-client \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10002 zaydbackup

WORKDIR /opt/zayd
COPY --chmod=0555 infra/backup/backup.sh /usr/local/bin/zayd-backup
COPY docs/governance ./docs/governance
COPY docs/05_data ./docs/05_data
COPY docs/06_islamic_governance ./docs/06_islamic_governance
RUN mkdir -p /var/backups/zayd && chown zaydbackup:zaydbackup /var/backups/zayd

USER zaydbackup
ENTRYPOINT ["/usr/local/bin/zayd-backup"]
