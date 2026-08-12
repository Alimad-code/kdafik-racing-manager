import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const repositoryRoot = dirname(dirname(fileURLToPath(import.meta.url)));
const read = (relativePath) => readFileSync(join(repositoryRoot, relativePath), "utf8");
const nginx = read("nginx.production.conf.template");
const dockerfile = read("Dockerfile.production");
const entrypoint = read("docker-entrypoint.production.sh");
const dockerignore = read(".dockerignore");

function requireCondition(condition, description) {
  if (!condition) throw new Error(`Production edge verification failed: ${description}`);
}

function exactLocation(path) {
  const marker = `location = ${path} {`;
  const start = nginx.indexOf(marker);
  requireCondition(start >= 0, `missing exact location ${path}`);
  const end = nginx.indexOf("\n        }", start);
  requireCondition(end >= 0, `unterminated exact location ${path}`);
  return nginx.slice(start, end);
}

const protectedRoutes = new Map([
  ["/api/v1/auth/login", "auth_login_per_source"],
  ["/api/v1/auth/register", "auth_register_per_source"],
  ["/api/v1/auth/registration/resend", "auth_email_delivery_per_source"],
  ["/api/v1/auth/registration/confirm", "auth_token_action_per_source"],
  ["/api/v1/auth/email/resend-verification", "auth_email_delivery_per_source"],
  ["/api/v1/auth/password/forgot", "auth_email_delivery_per_source"],
  ["/api/v1/auth/email/verify", "auth_token_action_per_source"],
  ["/api/v1/auth/password/reset", "auth_token_action_per_source"],
  ["/api/v1/ws/ticket", "ws_ticket_per_source"]
]);

requireCondition(
  (nginx.match(/limit_req_zone \$binary_remote_addr/g) ?? []).length === 5,
  "expected five volatile source rate-limit zones"
);
requireCondition(
  nginx.includes("limit_conn_zone $binary_remote_addr zone=ws_live_per_source:10m;"),
  "missing volatile WebSocket connection-limit zone"
);
for (const [path, zone] of protectedRoutes) {
  const location = exactLocation(path);
  requireCondition(location.includes(`limit_req zone=${zone} `), `${path} lacks ${zone}`);
  requireCondition(
    location.includes("include /etc/nginx/includes/backend-proxy.conf;"),
    `${path} lacks the common private proxy include`
  );
}

requireCondition(nginx.includes("location /api/ {"), "missing fallback /api/ location");
requireCondition(nginx.includes("limit_req_status 429;"), "rate limits do not return 429");
requireCondition(nginx.includes("limit_conn_status 429;"), "connection limits do not return 429");
requireCondition(nginx.includes("location @rate_limited {"), "missing safe 429 response location");
requireCondition(nginx.includes("default_type application/json;"), "429 response is not JSON");
requireCondition(
  nginx.includes('add_header Retry-After "60" always;'),
  "429 response lacks Retry-After"
);
requireCondition(
  nginx.includes('add_header Cache-Control "no-store" always;'),
  "429 response may be cached"
);
requireCondition(
  nginx.includes('return 429 \'{"code":"RATE_LIMITED"'),
  "429 response lacks safe error code"
);
requireCondition(
  nginx.includes("access_log /dev/stdout privacy;"),
  "access log is not the privacy format"
);

const privacyLog = nginx.match(/log_format privacy '([^']+)'/);
requireCondition(privacyLog?.[1].includes("$uri"), "privacy log omits URI");
requireCondition(!privacyLog?.[1].includes("$request_uri"), "privacy log includes query strings");
requireCondition(!nginx.includes("X-Real-IP"), "client IP is forwarded to the backend");
requireCondition(!nginx.includes("X-Forwarded-For"), "client IP is forwarded to the backend");
requireCondition(
  dockerfile.includes(
    "COPY nginx/includes/backend-proxy.conf /etc/nginx/includes/backend-proxy.conf"
  ),
  "Dockerfile does not copy proxy include"
);

requireCondition(
  (nginx.match(/server_name \$\{PUBLIC_HOST\};/g) ?? []).length === 2,
  "canonical host is not used by exactly the HTTP and HTTPS application servers"
);
requireCondition(
  nginx.includes("listen 8080 default_server;"),
  "missing default HTTP host rejection server"
);
requireCondition(
  nginx.includes("listen 8443 ssl default_server;") && nginx.includes("ssl_reject_handshake on;"),
  "missing default TLS SNI rejection server"
);
requireCondition(!nginx.includes("https://$host"), "HTTP redirect reflects the request Host");
requireCondition(
  nginx.includes("return 308 https://${PUBLIC_HOST}$request_uri;"),
  "canonical HTTP redirect is missing"
);
requireCondition(
  (nginx.match(/\$request_uri/g) ?? []).length === 1,
  "$request_uri must appear only in the fixed-host redirect"
);
requireCondition(
  (nginx.match(/return 444;/g) ?? []).length >= 2,
  "unknown HTTP Host or HTTPS Host is not rejected"
);

const internalHealth = exactLocation("/internal-health");
requireCondition(internalHealth.includes("access_log off;"), "internal health is logged");
requireCondition(
  internalHealth.includes("if ($remote_addr != 127.0.0.1)") &&
    internalHealth.includes("return 444;"),
  "internal health is not rejected outside loopback"
);
requireCondition(internalHealth.includes("return 204;"), "internal health does not return 204");

requireCondition(
  entrypoint.includes("public_host=${PUBLIC_HOST-}") &&
    entrypoint.includes('[ -n "$public_host" ] || fail'),
  "entrypoint does not require PUBLIC_HOST"
);
requireCondition(
  entrypoint.includes("*[!A-Za-z0-9.-]*|.*|*.|*..*) fail"),
  "entrypoint lacks strict DNS-character/shape validation"
);
requireCondition(
  entrypoint.includes('[ "${#public_host}" -le 253 ]') &&
    entrypoint.includes('[ "${#label}" -le 63 ]') &&
    entrypoint.includes("-*|*-) fail"),
  "entrypoint lacks DNS label length or hyphen-boundary validation"
);
requireCondition(!/\beval\b/.test(entrypoint), "entrypoint uses eval");
requireCondition(!/\bsed\b/.test(entrypoint), "entrypoint uses sed for host substitution");
requireCondition(
  entrypoint.includes("envsubst '${PUBLIC_HOST}'") &&
    entrypoint.includes("> /tmp/nginx.conf"),
  "entrypoint does not restrict runtime templating to PUBLIC_HOST"
);
requireCondition(
  entrypoint.includes("exec nginx -c /tmp/nginx.conf -g 'daemon off;'"),
  "entrypoint does not execute the rendered configuration"
);
requireCondition(
  dockerfile.includes(
    "COPY nginx.production.conf.template /etc/nginx/kdafik/nginx.production.conf.template"
  ),
  "Dockerfile does not copy the Nginx template"
);
requireCondition(
  dockerfile.includes(
    "COPY --chmod=0555 docker-entrypoint.production.sh /usr/local/bin/kdafik-edge-entrypoint"
  ),
  "Dockerfile does not install a non-writable executable entrypoint"
);
requireCondition(
  dockerfile.includes('CMD ["/usr/local/bin/kdafik-edge-entrypoint"]'),
  "Dockerfile does not start through the validating entrypoint"
);
requireCondition(
  dockerignore.includes("!nginx.production.conf.template") &&
    dockerignore.includes("!docker-entrypoint.production.sh"),
  "Docker build context may exclude the template or entrypoint"
);

const wsRaceLocation = "location ~ ^/api/v1/ws/seasons/[^/]+/stages/[^/]+/race$ {";
const wsRaceStart = nginx.indexOf(wsRaceLocation);
requireCondition(wsRaceStart >= 0, "missing dynamic live-race WebSocket location");
const wsRaceEnd = nginx.indexOf("\n        }", wsRaceStart);
requireCondition(wsRaceEnd >= 0, "unterminated live-race WebSocket location");
const wsRaceBlock = nginx.slice(wsRaceStart, wsRaceEnd);
requireCondition(
  wsRaceBlock.includes("limit_conn ws_live_per_source 10;"),
  "live-race WebSocket location lacks per-source connection cap of 10"
);
requireCondition(
  wsRaceBlock.includes("include /etc/nginx/includes/backend-proxy.conf;"),
  "live-race WebSocket location lacks the common private proxy include"
);
requireCondition(
  nginx.indexOf("location = /api/v1/ws/ticket {") < wsRaceStart,
  "exact WebSocket ticket route must precede live-race routing"
);
