from dataclasses import dataclass, field
from email.message import EmailMessage as MimeEmailMessage
from functools import lru_cache
from email.utils import formataddr, parseaddr
from html import escape
import mimetypes
from pathlib import Path
import smtplib
from string import Formatter
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import ValidationError
from app.core.modules import MODULE_EMAIL, require_module


@dataclass
class EmailAttachment:
    filename: str
    content: bytes
    content_type: str = "application/octet-stream"


@dataclass
class EmailMessage:
    to: list[str]
    subject: str
    body: str
    is_html: bool = False
    from_header: str | None = None
    cc: list[str] = field(default_factory=list)
    bcc: list[str] = field(default_factory=list)
    reply_to: str | None = None
    attachments: list[EmailAttachment] = field(default_factory=list)


def parse_email_list(value: str | list[str] | None) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        candidates = value
    else:
        candidates = value.split(",")
    return [email.strip() for email in candidates if email and email.strip()]


class EmailService:
    """Servicio SMTP reutilizable para cualquier flujo del sistema."""

    def __init__(self):
        template_dir = Path(settings.EMAIL_TEMPLATE_DIR)
        self.template_env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(["html", "xml"]),
        )

    def build_from_template(
        self,
        template,
        *,
        parameters: dict[str, Any] | None = None,
        to: str | list[str] | None = None,
        cc: str | list[str] | None = None,
        bcc: str | list[str] | None = None,
        subject: str | None = None,
        body_override: str | None = None,
        attachments: list[EmailAttachment] | None = None,
    ) -> EmailMessage:
        values = parameters or {}
        body, is_html = self._render_body(template, values, body_override)
        subject_template = subject or _get_attr(template, "subject")
        return EmailMessage(
            to=parse_email_list(to)
            or parse_email_list(_get_attr(template, "to", "mail_to")),
            cc=parse_email_list(cc) or parse_email_list(_get_attr(template, "cc")),
            bcc=parse_email_list(bcc) or parse_email_list(_get_attr(template, "bcc")),
            subject=render_template(subject_template, values) or "Notificacion",
            body=body,
            is_html=is_html,
            from_header=_get_attr(template, "mp_from", "mail_from"),
            reply_to=None,
            attachments=attachments or [],
        )

    def send(self, message: EmailMessage, db: Session | None = None) -> None:
        # Ultima reja del modulo de correo: todo envio del sistema pasa por
        # aqui, asi que un flujo nuevo no se puede escapar del interruptor por
        # olvidar el guard en su router. Quien ya tiene sesion la pasa en db
        # para no abrir una conexion extra por correo.
        require_module(MODULE_EMAIL, db)
        self._validate_settings()
        recipients = [*message.to, *message.cc, *message.bcc]
        if not recipients:
            raise ValidationError("Debe indicar al menos un destinatario")

        mime_message = self._build_message(message)
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=30) as smtp:
            if settings.SMTP_USE_TLS:
                smtp.starttls()
            if settings.SMTP_USER:
                smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD or "")
            smtp.send_message(mime_message, to_addrs=recipients)

    def _build_message(self, message: EmailMessage) -> MimeEmailMessage:
        mime_message = MimeEmailMessage()
        mime_message["From"] = self._resolve_from_header(message.from_header)
        mime_message["To"] = ", ".join(message.to)
        if message.cc:
            mime_message["Cc"] = ", ".join(message.cc)
        if message.reply_to:
            mime_message["Reply-To"] = message.reply_to
        mime_message["Subject"] = message.subject
        if message.is_html:
            # Los clientes antiguos tendran un texto minimo y los modernos veran el HTML.
            mime_message.set_content("Este correo contiene contenido HTML.")
            mime_message.add_alternative(message.body, subtype="html")
        else:
            mime_message.set_content(message.body)

        for attachment in message.attachments:
            content_type = attachment.content_type
            if not content_type or content_type == "application/octet-stream":
                content_type = (
                    mimetypes.guess_type(attachment.filename)[0]
                    or "application/octet-stream"
                )
            maintype, subtype = content_type.split("/", 1)
            mime_message.add_attachment(
                attachment.content,
                maintype=maintype,
                subtype=subtype,
                filename=attachment.filename,
            )
        return mime_message

    @staticmethod
    def _validate_settings() -> None:
        missing = []
        if not settings.SMTP_HOST:
            missing.append("SMTP_HOST")
        if not (settings.SMTP_FROM_EMAIL or settings.SMTP_USER):
            missing.append("SMTP_FROM_EMAIL o SMTP_USER")
        if missing:
            raise ValidationError(
                "Falta configurar SMTP para enviar correos: "
                + ", ".join(missing)
            )

    def _render_body(
        self,
        template,
        parameters: dict[str, Any],
        body_override: str | None = None,
    ) -> tuple[str, bool]:
        if body_override and body_override.strip():
            # El mensaje personalizado viene del usuario. Lo renderizamos con
            # variables permitidas y lo escapamos para tratarlo como texto seguro.
            return render_user_message(body_override, parameters), True

        html_value = _get_attr(template, "template_html")
        text_value = _get_attr(template, "template_text")
        template_value = _get_attr(template, "template")

        if html_value:
            return render_jinja_template(html_value, parameters, autoescape=True), True
        if text_value:
            return render_jinja_template(text_value, parameters), False
        if not template_value:
            return "", False

        # Si la plantilla termina en .html se interpreta como archivo dentro
        # de EMAIL_TEMPLATE_DIR; si no, se renderiza como texto/HTML en linea.
        if template_value.endswith(".html"):
            try:
                template = self.template_env.get_template(template_value)
            except Exception as exc:
                raise ValidationError(
                    f"No se encontro la plantilla de correo: {template_value}"
                ) from exc
            return template.render(**parameters), True

        body = render_template(template_value, parameters)
        return body, _looks_like_html(body)

    @staticmethod
    def _resolve_from_header(from_header: str | None) -> str:
        if from_header:
            name, email = parseaddr(from_header)
            if email:
                return formataddr((name, email))

        from_email = settings.SMTP_FROM_EMAIL or settings.SMTP_USER
        return formataddr((settings.SMTP_FROM_NAME, from_email))


def render_template(template: str | None, parameters: dict[str, Any]) -> str:
    if not template:
        return ""
    rendered = render_jinja_template(template, parameters)
    if rendered != template:
        return rendered
    safe_parameters = SafeTemplateParameters(parameters)
    return Formatter().vformat(template, (), safe_parameters)


class SafeTemplateParameters(dict):
    def __missing__(self, key):
        return ""


def _looks_like_html(value: str) -> bool:
    return "<html" in value.lower() or "<body" in value.lower() or "</" in value


@lru_cache(maxsize=2)
def _string_template_env(autoescape: bool) -> Environment:
    # Reutiliza una unica instancia de Environment por modo (HTML vs texto).
    return Environment(autoescape=autoescape)


def render_jinja_template(
    template: str,
    parameters: dict[str, Any],
    *,
    autoescape: bool = False,
) -> str:
    # autoescape=True escapa los VALORES interpolados (no el HTML propio de la
    # plantilla). Para HTML intencional en un parametro usar el filtro |safe.
    return _string_template_env(autoescape).from_string(template).render(**parameters)


def render_user_message(template: str, parameters: dict[str, Any]) -> str:
    rendered = render_template(template, parameters)
    safe_lines = [escape(line) for line in rendered.splitlines()]
    return "<br>".join(safe_lines)


def _get_attr(source, *names: str):
    for name in names:
        value = getattr(source, name, None)
        if value is not None:
            return value
    return None
