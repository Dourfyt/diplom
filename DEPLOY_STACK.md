# Деплой полного стека на сервер

Три модуля на одном хосте (`178.57.217.79`):

| Сервис | Порт | URL |
|--------|------|-----|
| API платформы (учёт, планирование, отчётность) | **8080** | http://178.57.217.79:8080 |
| Модуль планирования (React) | **5173** | http://178.57.217.79:5173 |
| Модуль отчётности eco (Django) | **8001** | http://178.57.217.79:8001 |

Общая БД PostgreSQL — только у API. Eco хранит локально SQLite (сессии Django).

---

## 1. Подготовка на сервере

```bash
# Установить Docker и Docker Compose v2, если ещё нет
ssh user@178.57.217.79

# Скопировать папку проекта (с хоста разработки):
# scp -r "Новая папка" user@178.57.217.79:~/waste-stack
cd ~/waste-stack   # корень, где лежит docker-compose.stack.yml
```

---

## 2. Запуск

```bash
export JWT_SECRET='ваш-секретный-ключ-jwt'
export ECO_SECRET_KEY='ваш-django-secret'

docker compose -f docker-compose.stack.yml up -d --build
```

Проверка:

```bash
curl -s http://localhost:8080/api/health
curl -s -o /dev/null -w "%{http_code}" http://localhost:5173/
curl -s -o /dev/null -w "%{http_code}" http://localhost:8001/
```

---

## 3. Если API уже работает на сервере

Если `waste-complex-platform` уже запущен отдельно на `:8080`:

**Вариант A** — остановить старый compose и поднять полный стек (рекомендуется):

```bash
cd waste-complex-platform && docker compose down
cd .. && docker compose -f docker-compose.stack.yml up -d --build
```

**Вариант B** — поднять только фронты, API не трогать:

```bash
docker compose -f docker-compose.stack.yml up -d --build planning eco
```

Убедитесь, что контейнер `api` из stack в той же сети доступен как `api:8000`, либо в `eco` задайте `API_BASE_URL=http://178.57.217.79:8080` (если API снаружи docker-сети).

---

## 4. Учётные записи

После первого запуска API (seed) и `eco` (`setup_roles`):

| Email | Пароль (по умолчанию) | Роль |
|-------|----------------------|------|
| admin@eco.local | eco2026 | admin |
| ecologist@eco.local | eco2026 | ecologist |
| manager@eco.local | eco2026 | chief (руководитель) |
| operator@eco.local | operator123 | operator (только API seed) |

Пароль демо в eco: переменная `ECO_DEMO_PASSWORD` (по умолчанию `eco2026`).

---

## 5. Порты и файрвол

Открыть на сервере: `8080`, `5173`, `8001`.

---

## 6. Обновление

```bash
git pull   # или scp новых файлов
docker compose -f docker-compose.stack.yml up -d --build
```
