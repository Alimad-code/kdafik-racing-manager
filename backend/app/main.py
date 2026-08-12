from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.api.v1.router import api_router
from app.core.config import ALLOWED_CORS_HEADERS, ALLOWED_CORS_METHODS, get_settings
from app.core.errors import ErrorResponse, register_exception_handlers


class ApiSecurityHeadersMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        async def send_with_security_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = message.setdefault("headers", [])
                headers.extend(
                    [
                        (b"x-content-type-options", b"nosniff"),
                        (b"x-frame-options", b"DENY"),
                        (b"referrer-policy", b"no-referrer"),
                    ]
                )
                if scope["path"].startswith("/api/"):
                    headers.append((b"cache-control", b"no-store"))
            await send(message)

        await self.app(scope, receive, send_with_security_headers)


def create_app() -> FastAPI:
    settings = get_settings()
    documentation_url = "/docs" if settings.environment != "production" else None
    openapi_url = "/openapi.json" if settings.environment != "production" else None

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        docs_url=documentation_url,
        redoc_url="/redoc" if documentation_url else None,
        openapi_url=openapi_url,
        responses={422: {"model": ErrorResponse}},
    )

    app.add_middleware(ApiSecurityHeadersMiddleware)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=ALLOWED_CORS_METHODS,
        allow_headers=ALLOWED_CORS_HEADERS,
    )

    register_exception_handlers(app)
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    return app


app = create_app()
