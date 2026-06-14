#!/usr/bin/env bash
# Выпуск Let's Encrypt сертификата для runcourse.online и поддоменов.
# Запуск из корня репозитория (где docker-compose.stack.yml):
#   CERTBOT_EMAIL=you@mail.ru ./gateway/init-ssl.sh

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

EMAIL="${CERTBOT_EMAIL:-}"
if [[ -z "$EMAIL" ]]; then
  echo "Укажите email: CERTBOT_EMAIL=you@mail.ru ./gateway/init-ssl.sh"
  exit 1
fi

ENV_FILE="$ROOT/.env"
if [[ ! -f "$ENV_FILE" ]]; then
  cp .env.example "$ENV_FILE" 2>/dev/null || touch "$ENV_FILE"
fi

if ! grep -q '^GATEWAY_NGINX_CONF=' "$ENV_FILE" 2>/dev/null; then
  echo 'GATEWAY_NGINX_CONF=./gateway/nginx.init.conf' >> "$ENV_FILE"
fi

echo "==> Gateway на HTTP (nginx.init.conf)..."
export GATEWAY_NGINX_CONF=./gateway/nginx.init.conf
docker compose -f docker-compose.stack.yml up -d gateway landing api planning eco

echo "==> Certbot: выпуск сертификата..."
docker compose -f docker-compose.stack.yml run --rm certbot certonly \
  --webroot \
  --webroot-path=/var/www/certbot \
  --email "$EMAIL" \
  --agree-tos \
  --no-eff-email \
  -d runcourse.online \
  -d www.runcourse.online \
  -d api.runcourse.online \
  -d plan.runcourse.online \
  -d eco.runcourse.online

echo "==> Переключение на HTTPS-конфиг..."
if grep -q '^GATEWAY_NGINX_CONF=' "$ENV_FILE"; then
  sed -i.bak 's|^GATEWAY_NGINX_CONF=.*|GATEWAY_NGINX_CONF=./gateway/nginx.conf|' "$ENV_FILE"
else
  echo 'GATEWAY_NGINX_CONF=./gateway/nginx.conf' >> "$ENV_FILE"
fi

export GATEWAY_NGINX_CONF=./gateway/nginx.conf
docker compose -f docker-compose.stack.yml up -d --force-recreate gateway
docker compose -f docker-compose.stack.yml up -d --build planning eco landing

echo ""
echo "Готово. Проверка:"
echo "  curl -I https://runcourse.online"
echo "  curl -I https://plan.runcourse.online"
echo "  curl -I https://eco.runcourse.online"
echo "  curl -I https://api.runcourse.online/api/health"
echo ""
echo "Продление (cron раз в сутки): ./gateway/renew-ssl.sh"
