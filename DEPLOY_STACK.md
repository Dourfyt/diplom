# Деплой полного стека на сервер

## Домены (основной доступ)

| Сервис | URL |
|--------|-----|
| **Лендинг** | https://runcourse.online |
| API платформы | https://api.runcourse.online (Swagger: `/docs`) |
| Модуль планирования (ЭкоПлан) | https://plan.runcourse.online |
| Модуль отчётности (ECO) | https://eco.runcourse.online |

Gateway (nginx, порты **80** и **443**) маршрутизирует по `Host`.  
Лендинг: скачивание **EcoDesk-setup.exe** и **app-release.apk**.

## Обратная совместимость (IP + порты, HTTP)

| Сервис | URL |
|--------|-----|
| API | http://178.57.217.79:8080 |
| Планирование | http://178.57.217.79:5173 |
| ECO | http://178.57.217.79:8001 |

---

## DNS

A-записи на IP сервера `178.57.217.79`:

```
runcourse.online          → 178.57.217.79
www.runcourse.online      → 178.57.217.79
api.runcourse.online      → 178.57.217.79
plan.runcourse.online     → 178.57.217.79
eco.runcourse.online      → 178.57.217.79
```

---

## 1. Подготовка на сервере

```bash
ssh user@178.57.217.79
cd ~/waste-stack   # корень, где лежит docker-compose.stack.yml

cp .env.example .env
# отредактируйте JWT_SECRET, ECO_SECRET_KEY, CERTBOT_EMAIL
```

Убедитесь, что в `landing/downloads/` лежат:
- `EcoDesk-setup.exe`
- `app-release.apk`

---

## 2. Запуск стека

```bash
docker compose -f docker-compose.stack.yml up -d --build
```

По умолчанию gateway работает по **HTTP** (`gateway/nginx.init.conf`).

Проверка:

```bash
curl -s -o /dev/null -w "%{http_code}" http://runcourse.online/
curl -s http://api.runcourse.online/api/health
```

---

## 3. HTTPS — Certbot (Let's Encrypt)

**Требования:** DNS уже указывает на сервер, порт **443** открыт в файрволе.

Один скрипт выпускает сертификат на все домены и включает HTTPS:

```bash
chmod +x gateway/init-ssl.sh gateway/renew-ssl.sh
CERTBOT_EMAIL=ваш@email.ru ./gateway/init-ssl.sh
```

Скрипт:
1. Поднимает gateway на HTTP с webroot для ACME
2. Запускает `certbot certonly` в Docker
3. Переключает `GATEWAY_NGINX_CONF=./gateway/nginx.conf` в `.env`
4. Перезапускает gateway с редиректом HTTP → HTTPS

Проверка после выпуска:

```bash
curl -I https://runcourse.online
curl -I https://plan.runcourse.online
curl -I https://eco.runcourse.online
curl -s https://api.runcourse.online/api/health
```

### Продление сертификата

```bash
./gateway/renew-ssl.sh
```

Cron (раз в сутки, на сервере):

```bash
0 3 * * * cd /home/user/waste-stack && ./gateway/renew-ssl.sh >> /var/log/certbot-renew.log 2>&1
```

### Ручной certbot (если нужно)

```bash
docker compose -f docker-compose.stack.yml --profile tools run --rm certbot certonly \
  --webroot -w /var/www/certbot \
  --email ваш@email.ru --agree-tos --no-eff-email \
  -d runcourse.online -d www.runcourse.online \
  -d api.runcourse.online -d plan.runcourse.online -d eco.runcourse.online
```

---

## 4. Порты и файрвол

Открыть: **80**, **443**, **8080**, **5173**, **8001**.

---

## 5. Учётные записи

| Email | Пароль (по умолчанию) | Роль |
|-------|----------------------|------|
| admin@eco.local | eco2026 | admin |
| ecologist@eco.local | eco2026 | ecologist |
| chief@eco.local | chief123 | chief |
| operator@eco.local | operator123 | operator |

---

## 6. Обновление

```bash
git pull
docker compose -f docker-compose.stack.yml up -d --build
```

Импорт ФККО (если ещё не выполнен):

```bash
docker compose -f docker-compose.stack.yml exec api python -m app.import_fkko
```

После обновления nginx-конфигов:

```bash
docker compose -f docker-compose.stack.yml exec gateway nginx -s reload
```

### 502 Bad Gateway на поддоменах

Частая причина: gateway стартовал **до** planning/eco или nginx закэшировал старый IP контейнера после `up --build`.

```bash
docker compose -f docker-compose.stack.yml ps
docker compose -f docker-compose.stack.yml up -d --build planning eco landing gateway
docker compose -f docker-compose.stack.yml exec gateway nginx -s reload
```

Проверка:

```bash
curl -I -H "Host: plan.runcourse.online" http://127.0.0.1/
curl -I -H "Host: eco.runcourse.online" http://127.0.0.1/
```
