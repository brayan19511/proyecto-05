import unittest
from decimal import Decimal
from unittest.mock import Mock

from app.api.finance.payment_provider.pdf_parser import (
    PaymentPdfParser,
    extraer_monto,
    normalizar_texto,
    obtener_valor,
)
from app.api.finance.payment_provider.processor import PaymentProviderProcessor
from app.api.finance.payment_provider.processor import build_pdf_filename


class PaymentProviderParsingTests(unittest.TestCase):
    def test_obtener_valor_ignores_accents_in_label(self):
        contenido = "Fecha de envio 10/07/2026\nEstado Procesado"

        self.assertEqual(obtener_valor(contenido, "Fecha de envio"), "10/07/2026")
        self.assertEqual(obtener_valor(contenido, "Fecha de envío"), "10/07/2026")

    def test_extracts_amount_and_currency(self):
        monto = extraer_monto("S/ 4,372.79")

        self.assertEqual(monto["moneda"], "PEN")
        self.assertEqual(monto["monto"], Decimal("4372.79"))

    def test_builds_suggested_pdf_filename(self):
        self.assertEqual(
            build_pdf_filename("DARYZA S.A.C.", "03/01/2026"),
            "DARYZA_S.A.C_ENERO_03.pdf",
        )

    def test_builds_readable_filename_for_provider_with_spaces(self):
        self.assertEqual(
            build_pdf_filename("ELEONORA PATRICIA BIGATTON DEL CARPIO", "03/01/2026"),
            "ELEONORA_PATRICIA_BIGATTON_DEL_CARPIO_ENERO_03.pdf",
        )

    def test_extracts_transfer_section_when_destination_section_is_missing(self):
        contenido = """
        Datos de la transferencia
        RUC 20378890161
        Beneficiario CORPORACION PERU TONERS S.A.C.
        Monto total S/ 4,324.70
        Referencia F001-1342
        Datos de envio de constancia
        """

        data = PaymentPdfParser()._extract_payment_data(contenido)

        self.assertEqual(data["source_section"], "TRANSFER")
        self.assertEqual(data["titular"], "CORPORACION PERU TONERS S.A.C.")
        self.assertEqual(data["ruc"], "20378890161")
        self.assertEqual(data["moneda"], "PEN")
        self.assertEqual(data["monto_decimal"], Decimal("4324.70"))


class PaymentProviderGroupingTests(unittest.TestCase):
    def test_group_uses_provider_normalized_names_when_available(self):
        provider = Mock(
            id="11111111-1111-1111-1111-111111111111",
            tax_id="20378890161",
            legal_name="Proveedor Formal SAC",
            normalized_names=[normalizar_texto("Proveedor Formal S.A.C.")],
            emails_payments=["pagos@proveedor.pe"],
        )

        result = PaymentProviderProcessor([provider]).group(
            [
                {
                    "archivo": "pago.pdf",
                    "datos_destino": {
                        "titular": "Proveedor Formal S.A.C.",
                        "cuenta": "001",
                        "moneda": "PEN",
                        "monto_decimal": Decimal("100.00"),
                        "monto_texto": "S/ 100.00",
                        "moneda_original": "S/",
                        "tipo": "Cuenta corriente",
                        "referencia": "REF",
                    },
                    "datos_operacion": {
                        "fecha_envio": "10/07/2026",
                        "fecha_proceso": "10/07/2026",
                        "estado": "Procesado",
                    },
                }
            ]
        )

        self.assertEqual(result[0]["provider_id"], provider.id)
        self.assertTrue(result[0]["identificado"])
        self.assertEqual(result[0]["status"], "READY")
        self.assertEqual(result[0]["proveedor"], "Proveedor Formal SAC")
        self.assertEqual(result[0]["emails_payments"], ["pagos@proveedor.pe"])
        self.assertEqual(
            result[0]["pagos"][0]["suggested_filename"],
            "PROVEEDOR_FORMAL_S.A.C_JULIO_10.pdf",
        )
        self.assertEqual(result[0]["pagos"][0]["moneda_simbolo"], "S/")
        self.assertEqual(result[0]["totales"][0]["moneda"], "PEN")
        self.assertEqual(result[0]["totales"][0]["moneda_simbolo"], "S/")

    def test_group_marks_missing_payment_email(self):
        provider = Mock(
            id="11111111-1111-1111-1111-111111111111",
            tax_id="20378890161",
            legal_name="Proveedor Formal SAC",
            normalized_names=[normalizar_texto("Proveedor Formal S.A.C.")],
            emails_payments=[],
        )

        result = PaymentProviderProcessor([provider]).group(
            [
                {
                    "archivo": "pago.pdf",
                    "datos_destino": {
                        "titular": "Proveedor Formal S.A.C.",
                        "cuenta": "001",
                        "moneda": "PEN",
                        "monto_decimal": Decimal("100.00"),
                        "monto_texto": "S/ 100.00",
                        "moneda_original": "S/",
                        "tipo": "Cuenta corriente",
                        "referencia": "REF",
                    },
                    "datos_operacion": {
                        "fecha_envio": "10/07/2026",
                        "fecha_proceso": "10/07/2026",
                        "estado": "Procesado",
                    },
                }
            ]
        )

        self.assertEqual(result[0]["status"], "MISSING_PAYMENT_EMAIL")


if __name__ == "__main__":
    unittest.main()
