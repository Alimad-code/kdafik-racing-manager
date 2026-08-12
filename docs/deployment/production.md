# Production: публичный запуск

Эта инструкция не является разрешением на публикацию. Production намеренно
fail-closed, пока legal manifest содержит DRAFT-тексты или placeholders. Нельзя
отключать эту проверку; сначала документы должны пройти проверку российского
юриста и получить финальные версии, даты и SHA-256.

Локальный запуск описан в [local.md](local.md).

## Подготовка

На deployment host подготовьте Docker Engine, DNS и доступ к external Managed
PostgreSQL. База должна быть доступна только приложению по защищённому
соединению; localhost и локальная Compose-база для production не подходят.

Создайте root-файл из `.env.example`:

```sh
cp .env.example .env
```

Измените только `APP_ENVIRONMENT`; производную строку
`COMPOSE_PROFILES=${APP_ENVIRONMENT}` оставьте без изменений:

```text
APP_ENVIRONMENT=production
COMPOSE_PROFILES=${APP_ENVIRONMENT}
```

Затем создайте `deploy/.env.production` из `deploy/.env.production.example`.
Заполните public domain, `DATABASE_URL` external PostgreSQL, `AUTH_JWT_SECRET`,
CORS/trusted hosts и SMTP-секреты. Оставьте `ENVIRONMENT=production`,
`DEBUG=false` и `REFRESH_COOKIE_SECURE=true`.

Положите сертификат домена на deployment host:

```text
deploy/tls/production/fullchain.pem
deploy/tls/production/privkey.pem
```

Не коммитьте ключи и не копируйте их в `deploy/tls/local/`.

## Запуск

Из корня репозитория:

```sh
docker compose config --quiet
docker compose up --build -d
docker compose ps
docker compose logs --tail=200 migrate backend web
curl --fail https://<public-domain>/api/v1/health
```

`migrate` должен завершиться с кодом 0 до запуска backend. Если legal validation
не проходит, migrate завершится ошибкой, а backend не стартует.

Для остановки используйте `docker compose down`. Перед обновлением сделайте
backup external PostgreSQL и проверьте env, legal manifest и healthchecks.
