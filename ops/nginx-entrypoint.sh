#!/bin/sh
set -eu
: "${API_TOKEN:?Set API_TOKEN}"
case "$API_TOKEN" in *[!A-Za-z0-9_-]*|'') echo 'Invalid API_TOKEN character' >&2; exit 1 ;; esac
# Keep the original config read-only. Only materialize generated configs into /tmp.
awk '{gsub(/\$API_TOKEN/, ENVIRON["API_TOKEN"]); print}' /etc/nginx/conf.d/default.conf.template > /tmp/default.conf
cat > /tmp/nginx.conf <<'EOF'
pid /tmp/nginx.pid;
worker_processes 1;
events { worker_connections 512; }
http {
  include /etc/nginx/mime.types;
  default_type application/octet-stream;
  access_log off;
  error_log /dev/stderr warn;
  sendfile on;
  client_body_temp_path /tmp/nginx_body;
  proxy_temp_path /tmp/nginx_proxy;
  include /tmp/default.conf;
}
EOF
exec nginx -c /tmp/nginx.conf -g 'daemon off;'
