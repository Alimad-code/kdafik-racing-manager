# Local: запуск на своей машине

Локальная разработка использует Vite по HTTP, без Nginx и TLS. Из корня
репозитория создайте `.env` из `.env.example` и `deploy/.env.local` из
`deploy/.env.local.example`; в root `.env` оставьте `APP_ENVIRONMENT=local` и
`COMPOSE_PROFILES=${APP_ENVIRONMENT}`. Задайте `POSTGRES_PASSWORD` и обновите
тот же пароль в `DATABASE_URL`.

```powershell
docker compose config --quiet
docker compose up --build -d
docker compose ps
```

Сервисы: локальный PostgreSQL, одноразовый `migrate`, FastAPI и Vite dev-server.
`migrate` выполняет только `alembic upgrade head`: две начальные миграции
`0001_initial_schema` и `0002_initial_data` создают схему, MVP catalog и legal
metadata. После squash используйте чистую локальную БД; не применяйте эти
миграции к существующей базе от прежней цепочки миграций.

Откройте:

- `http://localhost:5173` — приложение и Vite proxy для `/api`/WebSocket;
- `http://localhost:8000/docs` — Swagger UI;
- `http://localhost:8000/api/v1/health` — healthcheck API.

При включённой отправке писем укажите local-only `EMAIL_CODE_SECRET` длиной не
менее 32 символов. Коды подтверждения действуют 15 минут, коды сброса пароля —
10 минут, повторная отправка ограничена 60 секундами. Письма содержат код, а не
ссылку с секретом или кодом в URL.

```powershell
docker compose down
```

Обычная остановка сохраняет Compose-managed volume PostgreSQL. Не используйте
`docker compose down -v`, если хотите сохранить локальные данные.
