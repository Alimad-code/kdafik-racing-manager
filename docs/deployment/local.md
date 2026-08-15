# Local: запуск на своей машине

## Разработка через Vite

Для разработки весь стек запускается одной командой Docker Compose. Фронтенд
работает как Vite dev-server по HTTP на фиксированном адресе
`http://localhost:5173`; исходный код смонтирован в контейнер, поэтому изменения
подхватываются без пересборки. Backend публикуется только на loopback-интерфейсе,
поэтому API и Swagger доступны с этой же машины:

```powershell
docker compose up --build -d
```

Откройте:

- `http://localhost:5173` — приложение;
- `http://localhost:8000/docs` — Swagger UI FastAPI;
- `http://localhost:8000/api/v1/health` — проверка API.

В контейнере Vite проксирует `/api` и WebSocket-запросы на `backend:8000`,
поэтому во фронтенде не требуется указывать URL backend. Для запуска Vite вне
Docker сохранён `npm run dev`: он использует `127.0.0.1:8000`. HTTP допустим
только для локального окружения: `REFRESH_COOKIE_SECURE=false` задан
исключительно в `deploy/.env.local`.

## HTTPS-режим в Docker

Локальный пользовательский режим использует production-сборки, PostgreSQL и HTTPS
на `https://kdafik.localhost`. Это не dev-server.

Все команды выполняйте из корня репозитория после запуска Docker Desktop.

## Подготовка

Создайте root-файл, который выбирает окружение и Compose-профиль:

```powershell
Copy-Item .env.example .env
```

В `.env` изменяйте только `APP_ENVIRONMENT`; производную строку
`COMPOSE_PROFILES=${APP_ENVIRONMENT}` оставьте без изменений:

```text
APP_ENVIRONMENT=local
COMPOSE_PROFILES=${APP_ENVIRONMENT}
```

Затем создайте настройки сервисов:

```powershell
Copy-Item deploy\.env.local.example deploy\.env.local
notepad deploy\.env.local
```

Задайте `POSTGRES_PASSWORD` и случайный `AUTH_JWT_SECRET` длиной не менее 32
символов. Обновите тот же пароль в `DATABASE_URL`. Для этого режима должны
остаться `ENVIRONMENT=local`, `DEBUG=false`, `REFRESH_COOKIE_SECURE=true` и
`EMAIL_ENABLED=false`.

Подготовьте локальный TLS:

```powershell
.\deploy\scripts\new-local-tls.ps1
```

Скрипт создаёт `deploy/tls/local/fullchain.pem` и `privkey.pem`. Браузерное
предупреждение о self-signed сертификате ожидаемо; доверяйте ему только для
`kdafik.localhost`.

## Запуск и проверка

```powershell
docker compose config --quiet
docker compose -f compose.yaml -f compose.production.yaml --profile production up --build -d
docker compose ps
docker compose -f compose.yaml -f compose.production.yaml --profile production logs -f migrate backend web
```

Compose запускает `db`, одноразовый `migrate`, `backend` и `web`. `migrate`
применяет миграции и начальные данные, после успеха имеет статус `Exited (0)` и
не потребляет память, пока не будет запущен снова. Откройте
`https://kdafik.localhost` и при необходимости проверьте:

```powershell
curl.exe -k https://kdafik.localhost/api/v1/health
```

## Остановка

```powershell
docker compose down
```

Обычная остановка сохраняет Compose-managed named volume PostgreSQL
`kdafik-racing-manager_local_postgres_data` и сезоны. Не используйте
`docker compose down -v`, если хотите сохранить сезоны: эта команда удаляет
volume вместе с локальными данными.
