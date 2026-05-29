# API для WPF-клиента (waste-complex-platform)

**Базовый URL:** `http://178.57.217.79:8080/api/v1`  
**OpenAPI:** `http://178.57.217.79:8080/openapi.json`  
**Health:** `GET /api/v1/core/health` (без токена)

## Тестовые учётные записи

| Роль | Email | Пароль |
|------|-------|--------|
| operator | operator@eco.local | operator123 |
| chief | chief@eco.local | chief123 |
| ecologist | ecologist@eco.local | ecologist123 |
| admin | admin@eco.local | admin123 или eco2026 (зависит от seed на сервере) |

## Статусы партий

| status | Смысл |
|--------|--------|
| `accepted` | Зарегистрирована, ожидает классификации экологом |
| `classified` | Классифицирована экологом |
| `rejected` | Отклонена экологом |
| `processing` | В переработке (после операций/плана) |
| `done` | Завершена |

## Примеры curl

```bash
BASE=http://178.57.217.79:8080/api/v1

# Вход (в ответе role, full_name)
TOKEN=$(curl -s -X POST "$BASE/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"operator@eco.local","password":"operator123"}' | jq -r .access_token)

# Health
curl -s "$BASE/core/health"

# Дашборд (chief/ecologist/admin)
curl -s -H "Authorization: Bearer $TOKEN" "$BASE/reporting/dashboard"

# Загрузка документа партии (operator)
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  -F "file=@act.pdf" -F "document_type=confirming" \
  "$BASE/accounting/batches/1/documents"

# Сохранение отчёта на сервере (chief/ecologist/admin)
curl -s -X POST -H "Authorization: Bearer $(curl -s -X POST $BASE/auth/login -H 'Content-Type: application/json' -d '{"email":"chief@eco.local","password":"chief123"}' | jq -r .access_token)" \
  -F "file=@report.xlsx" -F "report_type=batches_excel" -F "title=Реестр партий" \
  "$BASE/reporting/reports"
```

## RBAC (кратко)

- **operator:** POST batches, documents upload, GET batches/balance/docs, departments, health
- **chief:** operations, dashboard, reports, summary
- **ecologist:** classify, reject, reports, dashboard
- **admin:** read + delete documents/reports, audit-logs; без register/classify/operations

При нарушении прав: `403` с `{"detail":"Недостаточно прав"}`.

## Публичная регистрация

`POST /api/v1/auth/register` открыт, если в окружении API:

```bash
ALLOW_PUBLIC_REGISTRATION=true
# или
PUBLIC_REGISTER_ENABLED=true
```

По умолчанию в коде: **включено** (`true`). Чтобы снова закрыть после первого пользователя — `ALLOW_PUBLIC_REGISTRATION=false` и перезапуск контейнера `api`.

Если таблица `users` пуста после обновления:

```bash
docker compose exec api python -m app.seed
```

## Деплой обновления

На сервере в каталоге `waste-complex-platform`:

```bash
docker compose up -d --build
docker compose exec api python -m app.seed
```

Файлы хранятся в volume `api_storage` (`/app/storage` в контейнере).
