# Production: публичный запуск

Эта инструкция не является разрешением на публикацию. Production fail-closed,
пока legal manifest содержит DRAFT-тексты или placeholders: сначала нужны
финальные документы, даты, SHA-256 и проверка российского юриста.

Production использует Nginx как HTTPS edge с security headers, privacy logging
и rate limits для регистрации, повторной отправки кода, подтверждения,
восстановления и сброса пароля. Локальная разработка использует только Vite:
см. [local.md](local.md).

Целевая схема для небольшого запуска — один VDS: Nginx, frontend, backend и
PostgreSQL запускаются Docker Compose на одной внутренней сети. PostgreSQL не
открывает порт в интернет. Отдельно необходим приватный Selectel S3-бакет с
ежедневным резервным копированием и проверкой восстановления.

На deployment host подготовьте Docker Engine, DNS и TLS-сертификат. Создайте
root `.env` из `.env.example` с `APP_ENVIRONMENT=production`, затем
`deploy/.env.production` из примера. Заполните `POSTGRES_PASSWORD`, внутренний
`DATABASE_URL` с хостом `db`, `AUTH_JWT_SECRET`, CORS/trusted hosts и уникальный
`EMAIL_CODE_SECRET` длиной не менее 32 символов. Для автоматических писем
используйте Почтовый сервис Selectel: отправитель
`no-reply@kdafik-racing.ru`, `smtp.mail.selcloud.ru`, порт `1127`,
`SMTP_USE_SSL=true` и `SMTP_USE_TLS=false`. Не используйте placeholder из
примера и не коммитьте секреты.

Положите сертификат на deployment host:

```text
deploy/tls/production/fullchain.pem
deploy/tls/production/privkey.pem
```

Запустите из корня репозитория:

```sh
docker compose -f compose.yaml -f compose.production.yaml --profile production config --quiet
docker compose -f compose.yaml -f compose.production.yaml --profile production up --build -d
docker compose ps
docker compose -f compose.yaml -f compose.production.yaml --profile production logs --tail=200 migrate backend web
curl --fail https://<public-domain>/api/v1/health
```

`migrate` должен завершиться с кодом 0 до запуска backend. Он выполняет только
`alembic upgrade head`; `0001_initial_schema` и `0002_initial_data` создают
схему и initial data (MVP catalog и legal metadata). После squash требуется
чистая production DB: не применяйте новую двухмиграционную историю к базе от
предыдущих миграций. Отдельные `seed_legal.py` и `python -m app.seed.mvp`
остаются только администраторскими утилитами, не частью startup.

Подтверждение email и сброс пароля используют одноразовые коды; письма не
содержат ссылок с секретами или кодами в URL. Коды подтверждения действуют 15 минут, сброса — 10 минут;
между отправками действует 60-секундный cooldown.

Для остановки используйте `docker compose down`. Перед обновлением сделайте
проверенный backup PostgreSQL в Selectel S3 и проверьте env, legal manifest и
healthchecks.
