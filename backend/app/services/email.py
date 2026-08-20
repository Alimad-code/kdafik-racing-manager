from __future__ import annotations

import smtplib
import ssl
from email.message import EmailMessage
from html import escape
from typing import Protocol

from app.core.config import YANDEX_SMTP_SENDER, Settings

SMTP_TIMEOUT_SECONDS = 10


class EmailDeliveryError(Exception):
    """Raised without including recipient or message content in application errors."""


class EmailSender(Protocol):
    def send_verification(self, recipient: str, code: str) -> None: ...

    def send_password_reset(self, recipient: str, code: str) -> None: ...

    def send_password_changed(self, recipient: str) -> None: ...


class SmtpEmailSender:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def send_verification(self, recipient: str, code: str) -> None:
        self._send(
            recipient,
            "Подтверждение email — Kdafik Racing Manager",
            self._verification_text(recipient, code),
            self._verification_html(recipient, code),
        )

    def send_password_reset(self, recipient: str, code: str) -> None:
        self._send(
            recipient,
            "Восстановление пароля — Kdafik Racing Manager",
            """Здравствуйте!

Мы получили запрос на восстановление пароля для вашего аккаунта Kdafik Racing Manager.
Введите код в форме восстановления в течение 10 минут:

{code}

Повторно запросить код можно не раньше чем через 60 секунд.
Если вы не запрашивали восстановление пароля, просто проигнорируйте это письмо.""",
            (
                "<p>Здравствуйте!</p>"
                "<p>Мы получили запрос на восстановление пароля для вашего аккаунта "
                "Kdafik Racing Manager.</p>"
                "<p>Введите код в форме восстановления в течение 10 минут:</p>"
                '<p style="font-size:32px;font-weight:bold;letter-spacing:8px">{code}</p>'
                "<p>Повторно запросить код можно не раньше чем через 60 секунд.</p>"
                "<p>Если вы не запрашивали восстановление пароля, просто проигнорируйте "
                "это письмо.</p>"
            ),
            code,
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
    def _verification_text(recipient: str, code: str) -> str:
        return f"""Здравствуйте!

Вы указали адрес {recipient} при регистрации в Kdafik Racing Manager.
Введите код в форме подтверждения в течение 15 минут:

{code}

Повторно запросить код можно не раньше чем через 60 секунд.
Если вы не регистрировались, просто проигнорируйте это письмо."""

    @staticmethod
    def _verification_html(recipient: str, code: str) -> str:
        safe_recipient = escape(recipient)
        return (
            f"<p>Здравствуйте!</p><p>Вы указали адрес {safe_recipient} при регистрации в "
            "Kdafik Racing Manager.</p><p>Введите код в форме подтверждения в течение 15 минут:</p>"
            f'<p style="font-size:32px;font-weight:bold;letter-spacing:8px">{escape(code)}</p>'
            "<p>Повторно запросить код можно не раньше чем через 60 секунд.</p>"
            "<p>Если вы не регистрировались, просто проигнорируйте это письмо.</p>"
        )

    def _send(
        self,
        recipient: str,
        subject: str,
        text_template: str,
        html_template: str,
        code: str | None = None,
    ) -> None:
        message = EmailMessage()
        message["From"] = YANDEX_SMTP_SENDER
        message["To"] = recipient
        message["Subject"] = subject
        message.set_content(text_template.format(code=code or ""))
        message.add_alternative(html_template.format(code=escape(code or "")), subtype="html")
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
