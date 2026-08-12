#!/bin/sh
set -eu

public_host=${PUBLIC_HOST-}

fail() {
    printf '%s\n' "Invalid or missing PUBLIC_HOST; expected a DNS hostname without scheme, port, path, wildcard, or whitespace." >&2
    exit 1
}

[ -n "$public_host" ] || fail
[ "${#public_host}" -le 253 ] || fail

case "$public_host" in
    *[!A-Za-z0-9.-]*|.*|*.|*..*) fail ;;
esac

old_ifs=$IFS
IFS=.
set -- $public_host
IFS=$old_ifs

for label in "$@"; do
    [ -n "$label" ] || fail
    [ "${#label}" -le 63 ] || fail
    case "$label" in
        -*|*-) fail ;;
    esac
done

command -v envsubst >/dev/null 2>&1 || {
    printf '%s\n' "envsubst is required to render the Nginx configuration." >&2
    exit 1
}

envsubst '${PUBLIC_HOST}' \
    < /etc/nginx/kdafik/nginx.production.conf.template \
    > /tmp/nginx.conf

exec nginx -c /tmp/nginx.conf -g 'daemon off;'
