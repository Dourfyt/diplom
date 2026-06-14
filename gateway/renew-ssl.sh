#!/usr/bin/env bash
# Продление сертификата Let's Encrypt + reload nginx.
# Cron: 0 3 * * * cd /path/to/waste-stack && ./gateway/renew-ssl.sh >> /var/log/certbot-renew.log 2>&1

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

docker compose -f docker-compose.stack.yml run --rm certbot renew --quiet
docker compose -f docker-compose.stack.yml exec gateway nginx -s reload

echo "$(date -Iseconds) certbot renew OK"
