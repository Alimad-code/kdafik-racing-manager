#!/usr/bin/env bash
set -euo pipefail

require_value() {
    local name="$1"
    if [[ -z "${!name:-}" ]]; then
        echo "Required backup setting $name is not set." >&2
        exit 2
    fi
}

for name in \
    POSTGRES_PASSWORD \
    S3_BUCKET \
    S3_REGION \
    S3_ENDPOINT \
    S3_ACCESS_KEY_ID \
    S3_SECRET_ACCESS_KEY; do
    require_value "$name"
done

export PGPASSWORD="$POSTGRES_PASSWORD"
export RCLONE_CONFIG_SELECTEL_TYPE=s3
export RCLONE_CONFIG_SELECTEL_PROVIDER=Selectel
export RCLONE_CONFIG_SELECTEL_ENV_AUTH=false
export RCLONE_CONFIG_SELECTEL_ACCESS_KEY_ID="$S3_ACCESS_KEY_ID"
export RCLONE_CONFIG_SELECTEL_SECRET_ACCESS_KEY="$S3_SECRET_ACCESS_KEY"
export RCLONE_CONFIG_SELECTEL_REGION="$S3_REGION"
export RCLONE_CONFIG_SELECTEL_ENDPOINT="$S3_ENDPOINT"
export RCLONE_CONFIG_SELECTEL_FORCE_PATH_STYLE=false
export RCLONE_CONFIG_SELECTEL_NO_CHECK_BUCKET=true
export RCLONE_CONFIG_SELECTEL_NO_HEAD=true

timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
object_name="postgres/kdafik-racing-manager-${timestamp}.dump"
temporary_file="$(mktemp /tmp/kdafik-racing-manager-postgres-XXXXXXXX)"
trap 'rm -f "$temporary_file"' EXIT

echo "Creating PostgreSQL backup ${object_name}."
pg_dump \
    --host=db \
    --port=5432 \
    --username=kdafik \
    --dbname=kdafik_racing_manager \
    --format=custom \
    --no-owner \
    --no-privileges \
    --file="$temporary_file"

echo "Uploading encrypted-in-transit backup to the private S3 bucket."
rclone rcat \
    "selectel:${S3_BUCKET}/${object_name}" \
    --s3-no-check-bucket \
    --s3-no-head < "$temporary_file"

echo "Verifying that the uploaded dump can be read back."
rclone cat "selectel:${S3_BUCKET}/${object_name}" | pg_restore --list >/dev/null

echo "Backup completed: ${object_name}"
