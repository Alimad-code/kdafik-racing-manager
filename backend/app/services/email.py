from __future__ import annotations

import smtplib
import ssl
from email.message import EmailMessage
from html import escape
from typing import Protocol
from urllib.parse import quote

from app.core.config import YANDEX_SMTP_SENDER, Settings

SMTP_TIMEOUT_SECONDS = 10


class EmailDeliveryError(Exception):
    """Raised without including recipient or message content in application errors."""


class EmailSender(Protocol):
    def send_verification(self, recipient: str, token: str) -> None: ...

    def send_password_reset(self, recipient: str, token: str) -> None: ...

    def send_password_changed(self, recipient: str) -> None: ...


class SmtpEmailSender:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def send_verification(self, recipient: str, token: str) -> None:
        self._send(
            recipient,
            "Подтверждение email — Kdafik Racing Manager",
            self._verification_text(recipient),
            self._verification_html(recipient),
            "/verify-email?token=",
            token,
        )

    def send_password_reset(self, recipient: str, token: str) -> None:
        self._send(
            recipient,
            "Восстановление пароля — Kdafik Racing Manager",
            """Здравствуйте!

Мы получили запрос на восстановление пароля для вашего аккаунта Kdafik Racing Manager.
Перейдите по ссылке в течение 30 минут:
{url}

Если вы не запрашивали восстановление пароля, просто проигнорируйте это письмо.""",
            (
                "<p>Здравствуйте!</p>"
                "<p>Мы получили запрос на восстановление пароля для вашего аккаунта "
                "Kdafik Racing Manager.</p>"
                "<p>Перейдите по ссылке в течение 30 минут:</p>"
                '<p><a href="{url}">Восстановить пароль</a></p>'
                "<p>Если вы не запрашивали восстановление пароля, просто проигнорируйте "
                "это письмо.</p>"
            ),
            "/reset-password?token=",
            token,
        )

    def send_password_changed(self, recipient: str) -> None:
        self._send(
            recipient,
            "Пароль изменён — Kdafik Racing Manager",
            """Здравствуйте!

Пароль для аккаунта Kdafik Racing Manager был изменён.

Если это сделали не вы, восстановите пароль через форму входа.""",
            (
                "<p>Здравствуйте!</p><p>Пароль для аккаунта Kdafik Racing Manager был "
                "изменён.</p><p>Если это сделали не вы, восстановите пароль через форму "
                "входа.</p>"
            ),
        )

    @staticmethod
    def _verification_text(recipient: str) -> str:
        return f"""Здравствуйте!

Вы указали адрес {recipient} при регистрации в Kdafik Racing Manager.
Подтвердите его в течение 24 часов:
{{url}}

Повторно запросить письмо можно не раньше чем через 5 минут.
Если вы не регистрировались, просто проигнорируйте это письмо."""

    @staticmethod
    def _verification_html(recipient: str) -> str:
        safe_recipient = escape(recipient)
        return (
            f"<p>Здравствуйте!</p><p>Вы указали адрес {safe_recipient} при регистрации в "
            "Kdafik Racing Manager.</p><p>Подтвердите его в течение 24 часов:</p>"
            '<p><a href="{url}">Подтвердить email</a></p>'
            "<p>Повторно запросить письмо можно не раньше чем через 5 минут.</p>"
            "<p>Если вы не регистрировались, просто проигнорируйте это письмо.</p>"
        )

    def _send(
        self,
        recipient: str,
        subject: str,
        text_template: str,
        html_template: str,
        path: str | None = None,
        token: str | None = None,
    ) -> None:
        url = None
        if path is not None and token is not None:
            encoded_token = quote(token, safe="")
            url = f"{self._settings.frontend_public_base_url.rstrip('/')}{path}{encoded_token}"
        message = EmailMessage()
        message["From"] = YANDEX_SMTP_SENDER
        message["To"] = recipient
        message["Subject"] = subject
        message.set_content(text_template.format(url=url or ""))
        message.add_alternative(
            html_template.format(url=escape(url or "", quote=True)), subtype="html"
        )
        try:
            with smtplib.SMTP(
                self._settings.smtp_host, self._settings.smtp_port, timeout=SMTP_TIMEOUT_SECONDS
            ) as smtp:
                smtp.starttls(context=ssl.create_default_context())
                smtp.login(
                    self._settings.smtp_username,
                    self._settings.smtp_password.get_secret_value(),
                )
                smtp.send_message(message)
        except (OSError, smtplib.SMTPException) as exc:
            raise EmailDeliveryError("Email delivery is unavailable.") from exc
