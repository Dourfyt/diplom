# Деплой полного стека на сервер

## Домены (основной доступ)

| Сервис | URL |
|--------|-----|
| **Лендинг** | http://runcourse.online |
| API платформы | http://api.runcourse.online (Swagger: `/docs`) |
| Модуль планирования (ЭкоПлан) | http://plan.runcourse.online |
| Модуль отчётности (ECO) | http://eco.runcourse.online |

Gateway (nginx, порт **80**) маршрутизирует по `Host`.  
Лендинг: скачивание **EcoDesk-setup.exe** и **app-release.apk**.

## Обратная совместимость (IP + порты)

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

HTTPS (Let's Encrypt) — опционально через certbot на хосте или отдельный reverse-proxy.

---

## 1. Подготовка на сервере

```bash
ssh user@178.57.217.79
cd ~/waste-stack   # корень, где лежит docker-compose.stack.yml
```

Убедитесь, что в `landing/downloads/` лежат:
- `EcoDesk-setup.exe`
- `app-release.apk`

---

## 2. Запуск

```bash
export JWT_SECRET='ваш-секретный-ключ-jwt'
export ECO_SECRET_KEY='ваш-django-secret'

docker compose -f docker-compose.stack.yml up -d --build
```

Проверка:

```bash
curl -s http://localhost/api/health          # через gateway → landing (если default)
curl -s http://localhost:8080/api/health
curl -s -o /dev/null -w "%{http_code}" http://localhost:5173/
curl -s -o /dev/null -w "%{http_code}" http://localhost:8001/
curl -s -o /dev/null -w "%{http_code}" http://localhost/   # лендинг
```

После настройки DNS:

```bash
curl -s http://api.runcourse.online/api/health
curl -s -o /dev/null -w "%{http_code}" http://plan.runcourse.online/
curl -s -o /dev/null -w "%{http_code}" http://eco.runcourse.online/
```

---

## 3. Порты и файрвол

Открыть: **80** (gateway + лендинг), **8080**, **5173**, **8001**.

---

## 4. Учётные записи

| Email | Пароль (по умолчанию) | Роль |
|-------|----------------------|------|
| admin@eco.local | eco2026 | admin |
| ecologist@eco.local | eco2026 | ecologist |
| chief@eco.local | chief123 | chief |
| operator@eco.local | operator123 | operator |

---

## 5. Обновление

```bash
git pull
docker compose -f docker-compose.stack.yml up -d --build
```

Импорт ФККО (если ещё не выполнен):

```bash
docker compose -f docker-compose.stack.yml exec api python -m app.import_fkko
```
