import unittest
from unittest.mock import Mock, patch

from app.services.email import (
    EmailMessage,
    EmailService,
    parse_email_list,
    render_template,
)
from app.services.email.email_service import render_user_message


class EmailServiceTests(unittest.TestCase):
    def test_parse_email_list_accepts_comma_separated_text(self):
        self.assertEqual(
            parse_email_list("uno@empresa.com, dos@empresa.com "),
            ["uno@empresa.com", "dos@empresa.com"],
        )

    def test_render_template_uses_parameters_and_ignores_missing_values(self):
        self.assertEqual(
            render_template("Hola {proveedor}, total {total} {moneda}", {
                "proveedor": "Daryza",
                "total": "100.00",
            }),
            "Hola Daryza, total 100.00 ",
        )

    def test_render_template_accepts_jinja_syntax(self):
        self.assertEqual(
            render_template("Hola {{ proveedor }}", {"proveedor": "Daryza"}),
            "Hola Daryza",
        )

    def test_build_from_template_allows_nullable_fields(self):
        template = Mock(
            to=None,
            cc=None,
            bcc="bcovenas@rashperu.com",
            subject=None,
            template=None,
            template_html=None,
            template_text=None,
            mp_from=None,
            mail_to=None,
            mail_from=None,
        )

        message = EmailService().build_from_template(
            template,
            to=["pagos@proveedor.pe"],
            parameters={"proveedor": "Daryza"},
        )

        self.assertEqual(message.to, ["pagos@proveedor.pe"])
        self.assertEqual(message.bcc, ["bcovenas@rashperu.com"])
        self.assertEqual(message.subject, "Notificacion")
        self.assertEqual(message.body, "")

    def test_build_from_template_uses_mail_from_and_html_file(self):
        template = Mock(
            to=None,
            cc=None,
            bcc=None,
            subject="Pago {{ proveedor }}",
            template="payment_provider_summary.html",
            template_html=None,
            template_text=None,
            mp_from="Coolbox <no-reply@coolbox.com.pe>",
            mail_to=None,
            mail_from=None,
        )

        message = EmailService().build_from_template(
            template,
            to=["pagos@proveedor.pe"],
            parameters={
                "proveedor": "Daryza",
                "cantidad_pagos": 1,
                "totales": [{"moneda": "PEN", "total": "100.00"}],
                "pagos": [],
            },
        )

        self.assertTrue(message.is_html)
        self.assertEqual(message.from_header, "Coolbox <no-reply@coolbox.com.pe>")
        self.assertIn("Adjunto detalle de pago", message.body)
        self.assertEqual(message.subject, "Pago Daryza")

    def test_build_from_template_accepts_inline_html(self):
        template = Mock(
            to=None,
            cc=None,
            bcc=None,
            subject="Pago",
            template=None,
            template_html="<strong>{{ proveedor }}</strong>",
            template_text=None,
            mp_from=None,
            mail_to=None,
            mail_from=None,
        )

        message = EmailService().build_from_template(
            template,
            to=["pagos@proveedor.pe"],
            parameters={"proveedor": "Daryza"},
        )

        self.assertTrue(message.is_html)
        self.assertEqual(message.body, "<strong>Daryza</strong>")

    def test_build_from_template_allows_subject_override_with_parameters(self):
        template = Mock(
            to=None,
            cc=None,
            bcc=None,
            subject="Subject desde BD {{ proveedor }}",
            template=None,
            template_html=None,
            template_text=None,
            mp_from=None,
            mail_to=None,
            mail_from=None,
        )

        message = EmailService().build_from_template(
            template,
            to=["pagos@proveedor.pe"],
            subject="Constancias de pago - {{ proveedor }}",
            parameters={"proveedor": "Daryza"},
        )

        self.assertEqual(message.subject, "Constancias de pago - Daryza")

    def test_build_from_template_allows_user_message_override(self):
        template = Mock(
            to=None,
            cc=None,
            bcc=None,
            subject="Pago",
            template="Este cuerpo no debe usarse",
            template_html=None,
            template_text=None,
            mp_from=None,
            mail_to=None,
            mail_from=None,
        )

        message = EmailService().build_from_template(
            template,
            to=["pagos@proveedor.pe"],
            body_override="Buenas tardes\nEnvio constancia de {{ proveedor }}",
            parameters={"proveedor": "Daryza"},
        )

        self.assertTrue(message.is_html)
        self.assertEqual(
            message.body,
            "Buenas tardes<br>Envio constancia de Daryza",
        )

    def test_render_user_message_escapes_html(self):
        self.assertEqual(
            render_user_message("Hola <script>{{ proveedor }}</script>", {
                "proveedor": "Daryza",
            }),
            "Hola &lt;script&gt;Daryza&lt;/script&gt;",
        )

    @patch("app.services.email.email_service.settings")
    @patch("app.services.email.email_service.smtplib.SMTP")
    @patch("app.services.email.email_service.require_module")
    def test_send_uses_tls_and_login_when_configured(
        self,
        require_module,
        smtp_class,
        settings,
    ):
        settings.SMTP_HOST = "smtp.office365.com"
        settings.SMTP_PORT = 587
        settings.SMTP_USE_TLS = True
        settings.SMTP_USER = "notificaciones@empresa.com"
        settings.SMTP_PASSWORD = "secret"
        settings.SMTP_FROM_EMAIL = "notificaciones@empresa.com"
        settings.SMTP_FROM_NAME = "Rash Peru"
        settings.EMAIL_TEMPLATE_DIR = "app/templates/emails"

        smtp = Mock()
        smtp_class.return_value.__enter__.return_value = smtp

        EmailService().send(
            EmailMessage(
                to=["destino@empresa.com"],
                subject="Prueba",
                body="Contenido",
            )
        )

        smtp_class.assert_called_once_with("smtp.office365.com", 587, timeout=30)
        smtp.starttls.assert_called_once()
        smtp.login.assert_called_once_with("notificaciones@empresa.com", "secret")
        smtp.send_message.assert_called_once()


if __name__ == "__main__":
    unittest.main()
