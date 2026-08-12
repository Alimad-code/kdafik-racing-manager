from enum import StrEnum
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field


class ErrorCode(StrEnum):
    EMAIL_ALREADY_REGISTERED = "EMAIL_ALREADY_REGISTERED"
    DISPLAY_NAME_ALREADY_REGISTERED = "DISPLAY_NAME_ALREADY_REGISTERED"
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    EMAIL_NOT_VERIFIED = "EMAIL_NOT_VERIFIED"
    EMAIL_DELIVERY_UNAVAILABLE = "EMAIL_DELIVERY_UNAVAILABLE"
    INVALID_EMAIL_ACTION_TOKEN = "INVALID_EMAIL_ACTION_TOKEN"
    EMAIL_ACTION_COOLDOWN = "EMAIL_ACTION_COOLDOWN"
    LEGAL_DOCUMENTS_UNAVAILABLE = "LEGAL_DOCUMENTS_UNAVAILABLE"
    INVALID_LEGAL_ACCEPTANCE = "INVALID_LEGAL_ACCEPTANCE"
    UNAUTHORIZED = "UNAUTHORIZED"
    INVALID_TOKEN = "INVALID_TOKEN"
    INSUFFICIENT_FUNDS = "INSUFFICIENT_FUNDS"
    INVALID_ROSTER = "INVALID_ROSTER"
    DUPLICATE_DRIVER = "DUPLICATE_DRIVER"
    STAGE_LOCKED = "STAGE_LOCKED"
    SESSION_ALREADY_COMPLETED = "SESSION_ALREADY_COMPLETED"
    PREVIOUS_SESSION_NOT_COMPLETED = "PREVIOUS_SESSION_NOT_COMPLETED"
    SEASON_ALREADY_FINISHED = "SEASON_ALREADY_FINISHED"
    SEASON_NOT_IN_PROGRESS = "SEASON_NOT_IN_PROGRESS"
    ENTITY_NOT_FOUND = "ENTITY_NOT_FOUND"
    FORBIDDEN = "FORBIDDEN"
    INVALID_STATE_TRANSITION = "INVALID_STATE_TRANSITION"
    LIVE_RACE_NOT_FINISHED = "LIVE_RACE_NOT_FINISHED"
    VALIDATION_ERROR = "VALIDATION_ERROR"


class ErrorResponse(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class DomainError(Exception):
    def __init__(
        self,
        code: ErrorCode | str,
        message: str,
        *,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


async def domain_error_handler(_request: Request, exc: DomainError) -> JSONResponse:
    error = ErrorResponse(code=str(exc.code), message=exc.message, details=exc.details)
    return JSONResponse(
        status_code=exc.status_code,
        content=error.model_dump(mode="json"),
        headers={"Content-Type": "application/json; charset=utf-8"},
    )


async def validation_error_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    error = ErrorResponse(
        code=ErrorCode.VALIDATION_ERROR,
        message="Request validation failed.",
        details={"errors": jsonable_encoder(exc.errors())},
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content=error.model_dump(mode="json"),
        headers={"Content-Type": "application/json; charset=utf-8"},
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainError, domain_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
