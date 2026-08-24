FROM postgres:16.10-alpine

RUN apk add --no-cache bash rclone

COPY --chown=999:999 --chmod=0555 run-postgres-s3-backup.sh /usr/local/bin/run-postgres-s3-backup

USER 999:999
ENTRYPOINT ["/usr/local/bin/run-postgres-s3-backup"]
