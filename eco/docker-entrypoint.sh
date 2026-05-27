#!/bin/sh
set -e

mkdir -p "$(dirname "${SQLITE_PATH:-/app/db.sqlite3}")"

python manage.py migrate --noinput
python manage.py collectstatic --noinput
python manage.py setup_roles --password "${ECO_DEMO_PASSWORD:-eco2026}" || true

exec gunicorn config.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers 2 \
  --timeout 120
