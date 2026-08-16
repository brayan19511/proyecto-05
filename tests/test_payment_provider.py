import unittest
from decimal import Decimal
from unittest.mock import Mock, patch

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

    def test_extracts_bbva_consulta_operaciones_by_document(self):
        contenido = """
        RASH PERU S.R.L. 2026/08/14 16:53:02
        Consulta de Operaciones
        Su operacion ha sido realizada
        Numero de Operacion 000963753
        Tipo de Operacion TRANSF INTERBANCARIA POR HORARIO
        Importe Cargado 27,417.72 SOLES
        Cuenta / Tarjeta / Servicio Beneficiario 00320000300450459138
        Doc. Identidad R - 20609307235
        Fecha / Hora 2026-08-14 16:31:03
        Referencia TRANSF.INTERBANCARIA.CCE 007246861
        """

        parser = PaymentPdfParser()
        operation = parser._extract_operation_data(contenido)
        data = parser._extract_payment_data(contenido)

        self.assertEqual(operation["numero_operacion"], "000963753")
        self.assertEqual(operation["fecha_proceso"], "14/08/2026")
        self.assertEqual(data["source_section"], "CONSULTA_OPERACIONES")
        self.assertIsNone(data["titular"])
        self.assertEqual(data["ruc"], "20609307235")
        self.assertEqual(data["cuenta"], "00320000300450459138")
        self.assertEqual(data["moneda"], "PEN")
        self.assertEqual(data["monto_decimal"], Decimal("27417.72"))

    def test_extracts_bbva_consulta_operaciones_account_and_name(self):
        contenido = """
        Consulta de Operaciones
        Su operacion ha sido realizada
        Numero de Operacion 000055189
        Tipo de Operacion TRANSF A CTAS DE TERCEROS
        Importe Cargado 26,664.61 DOLARES
        Cuenta / Tarjeta / Servicio Beneficiario 00110716810100023566 BUSINESS IT PERU SAC
        Fecha / Hora 2026-08-14 16:31:03
        Referencia SERVICIO F002-9681 F002-9966
        """

        data = PaymentPdfParser()._extract_payment_data(contenido)

        self.assertEqual(data["source_section"], "CONSULTA_OPERACIONES")
        self.assertEqual(data["titular"], "BUSINESS IT PERU SAC")
        self.assertEqual(data["cuenta"], "00110716810100023566")
        self.assertIsNone(data["ruc"])
        self.assertEqual(data["moneda"], "USD")
        self.assertEqual(data["monto_decimal"], Decimal("26664.61"))

    def test_extracts_service_payment_section_when_provider_is_company(self):
        contenido = """
        Datos de la operación
        Tipo de operacion Pago de servicios
        Estado Procesada
        Número de operación 100105
        Fecha de proceso 11/02/2025 - 03:59 p. m.
        Datos del pago
        Empresa proveedora SAT - LIMA
        Servicio a pagar IMPUESTO VEHICULAR
        Titular del servicio 23******BA*** AL****
        Código de servicio 0203381289v25
        Monto a pagar S/ 2,898.04
        Datos de la cuenta de cargo
        Titular RASH PERU S.R.L.
        """

        data = PaymentPdfParser()._extract_payment_data(contenido)

        self.assertEqual(data["source_section"], "SERVICE_PAYMENT")
        self.assertEqual(data["titular"], "SAT - LIMA")
        self.assertEqual(data["tipo"], "IMPUESTO VEHICULAR")
        self.assertEqual(data["cuenta"], "0203381289v25")
        self.assertEqual(data["referencia"], "0203381289v25")
        self.assertEqual(data["moneda"], "PEN")
        self.assertEqual(data["monto_decimal"], Decimal("2898.04"))

    def test_extracts_service_payment_section_from_column_ocr(self):
        contenido = """
        Datos del pago

        Empresa proveedora
        Servico a pagar
        Titular del servicio
        Código de servicio
        Monto a pagar

        31578282
        YESSICA EDIMAR GARCIA ROSALES
        11/02/2025 - 12:44 p. m.
        HECTOR MARCELO BAZAN ALVAREZ
        MIGUEL MONGILARDI FUCHS
        YESSICA EDIMAR GARCIA ROSALES
        11/02/2025 - 03:59 p. m.
        SAT - LIMA
        IMPUESTO VEHICULAR
        YE olaaa = Y - Velada Apu
        0203381289v25
        S/ 2,898.04

        Datos de la cuenta de cargo
        """

        data = PaymentPdfParser()._extract_payment_data(contenido)

        self.assertEqual(data["source_section"], "SERVICE_PAYMENT")
        self.assertEqual(data["titular"], "SAT - LIMA")
        self.assertEqual(data["tipo"], "IMPUESTO VEHICULAR")
        self.assertEqual(data["cuenta"], "0203381289v25")
        self.assertEqual(data["moneda"], "PEN")
        self.assertEqual(data["monto_decimal"], Decimal("2898.04"))

    def test_extracts_operation_data_from_column_ocr(self):
        contenido = """
        Datos de la operación

        Tipo de operacion
        Estado
        Número de operación
        Fecha de proceso

        Pago de servicios
        e Procesada
        100105
        11/02/2025 - 03:59 p. m.

        Datos de procesos de la operación
        """

        data = PaymentPdfParser()._extract_operation_data(contenido)

        self.assertEqual(data["tipo_operacion"], "Pago de servicios")
        self.assertEqual(data["estado"], "Procesada")
        self.assertEqual(data["numero_operacion"], "100105")
        self.assertEqual(data["fecha_proceso"], "11/02/2025 - 03:59 p. m.")

    def test_pdf_text_extraction_skips_ocr_when_pdf_has_text(self):
        parser = PaymentPdfParser()
        file = Mock()
        contenido = "texto extraido correctamente " * 5

        with patch.object(
            parser,
            "_extract_pdf_text_with_pdfplumber",
            return_value=contenido,
        ), patch.object(parser, "_extract_pdf_text_with_ocr") as ocr:
            self.assertEqual(parser._extract_pdf_text(file), contenido)

        ocr.assert_not_called()

    def test_pdf_text_extraction_uses_ocr_when_pdf_has_no_text(self):
        parser = PaymentPdfParser()
        file = Mock()
        contenido_ocr = "texto extraido por ocr en espanol " * 5

        with patch.object(
            parser,
            "_extract_pdf_text_with_pdfplumber",
            return_value="",
        ), patch.object(
            parser,
            "_extract_pdf_text_with_ocr",
            return_value=contenido_ocr,
        ):
            self.assertEqual(parser._extract_pdf_text(file), contenido_ocr)


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

    def test_group_matches_provider_names_ignoring_punctuation(self):
        provider = Mock(
            id="22222222-2222-2222-2222-222222222222",
            tax_id="PE0000000313",
            legal_name="METEC ELECTRONICS CO. LIMITED",
            normalized_names=[normalizar_texto("METEC ELECTRONICS CO. LIMITED")],
            emails_payments=["pagos@proveedor.pe"],
        )

        result = PaymentProviderProcessor([provider]).group(
            [
                {
                    "archivo": "pago.pdf",
                    "datos_destino": {
                        "titular": "METEC ELECTRONICS CO., LIMITED",
                        "cuenta": "60134 4 09732",
                        "moneda": "USD",
                        "monto_decimal": Decimal("18110.78"),
                        "monto_texto": "$ 18,110.78",
                        "moneda_original": "$",
                        "tipo": "Transferencia exterior",
                        "referencia": "METEC",
                        "ruc": None,
                    },
                    "datos_operacion": {
                        "fecha_envio": "12/08/2026",
                        "fecha_proceso": "12/08/2026",
                        "estado": "Procesada",
                    },
                }
            ]
        )

        self.assertEqual(result[0]["provider_id"], provider.id)
        self.assertTrue(result[0]["identificado"])
        self.assertEqual(result[0]["status"], "READY")


if __name__ == "__main__":
    unittest.main()
