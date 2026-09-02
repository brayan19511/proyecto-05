"""Tests del enmascarado de la auditoria (app/core/middleware.py).

Solo se enmascaran credenciales; el resto del detalle se guarda tal cual.
"""

import unittest

from app.core.config import normalize_key, split_config_list, settings
from app.core.middleware import (
    REDACTED,
    FILE_CONTENT_PLACEHOLDER,
    sanitize_headers,
    sanitize_payload,
    sanitize_query_params,
    should_redact_response_body,
)


class FakeQueryParams:
    """Imita starlette.QueryParams: soporta llaves repetidas."""

    def __init__(self, items):
        self._items = items

    def multi_items(self):
        return list(self._items)


class NormalizeKeyTests(unittest.TestCase):
    def test_quita_tildes_y_baja_a_minuscula(self):
        self.assertEqual(normalize_key("Contraseña"), "contrasena")
        self.assertEqual(normalize_key("  PASSWORD  "), "password")

    def test_split_config_list_limpia_espacios_y_vacios(self):
        self.assertEqual(
            split_config_list("password, Contraseña ,, token"),
            ["password", "contrasena", "token"],
        )


class SensitivePayloadTests(unittest.TestCase):
    def test_enmascara_credenciales(self):
        payload = {
            "password": "secreto123",
            "current_password": "viejo",
            "new_password": "nuevo",
            "access_token": "eyJhbG",
            "api_key": "ak_live_1",
        }

        result = sanitize_payload(payload)

        for key in payload:
            self.assertEqual(result[key], REDACTED, key)

    def test_enmascara_contrasena_con_tilde(self):
        result = sanitize_payload({"contraseña": "secreto"})

        self.assertEqual(result["contraseña"], REDACTED)

    def test_coincide_por_substring_sin_configurar_cada_variante(self):
        result = sanitize_payload(
            {"passwordConfirm": "x", "usuario_password_hash": "y"}
        )

        self.assertEqual(result["passwordConfirm"], REDACTED)
        self.assertEqual(result["usuario_password_hash"], REDACTED)

    def test_no_toca_datos_de_negocio(self):
        # Estos campos se enmascaraban antes y ahora deben verse completos.
        payload = {
            "document_number": "12345678",
            "document_numbers": ["1", "2"],
            "documentos": [{"ticket_code": "T-1"}],
            "references": ["REF-1"],
            "email": "jperez@rashperu.com",
            "supplier_tax_id": "20512345678",
            "amount": 1500.5,
            "company_id": 1,
            "area_id": 3,
        }

        self.assertEqual(sanitize_payload(payload), payload)

    def test_recorre_estructuras_anidadas(self):
        payload = {
            "usuarios": [
                {"email": "a@rashperu.com", "password": "x"},
                {"email": "b@rashperu.com", "password": "y"},
            ],
            "config": {"nested": {"secret": "s", "timeout": 30}},
        }

        result = sanitize_payload(payload)

        self.assertEqual(result["usuarios"][0]["email"], "a@rashperu.com")
        self.assertEqual(result["usuarios"][0]["password"], REDACTED)
        self.assertEqual(result["config"]["nested"]["secret"], REDACTED)
        self.assertEqual(result["config"]["nested"]["timeout"], 30)

    def test_omite_adjuntos_base64_por_tamano(self):
        result = sanitize_payload({"file_base64": "JVBERi0xLj...", "name": "a.pdf"})

        self.assertEqual(result["file_base64"], FILE_CONTENT_PLACEHOLDER)
        self.assertEqual(result["name"], "a.pdf")

    def test_valores_no_dict_pasan_sin_cambios(self):
        self.assertEqual(sanitize_payload("texto"), "texto")
        self.assertEqual(sanitize_payload(None), None)
        self.assertEqual(sanitize_payload([1, 2, 3]), [1, 2, 3])


class SensitiveHeaderTests(unittest.TestCase):
    def test_enmascara_cabeceras_de_credenciales(self):
        result = sanitize_headers(
            {
                "Authorization": "Bearer eyJhbG",
                "Cookie": "session=abc",
                "X-API-Key": "ak_1",
                "User-Agent": "Mozilla/5.0",
                "Content-Type": "application/json",
            }
        )

        self.assertEqual(result["Authorization"], REDACTED)
        self.assertEqual(result["Cookie"], REDACTED)
        self.assertEqual(result["X-API-Key"], REDACTED)
        self.assertEqual(result["User-Agent"], "Mozilla/5.0")
        self.assertEqual(result["Content-Type"], "application/json")


class SensitiveQueryTests(unittest.TestCase):
    def test_no_enmascara_filtros_de_negocio(self):
        params = FakeQueryParams(
            [
                ("document_number", "12345678"),
                ("company_id", "1"),
                ("search", "T-1"),
            ]
        )

        result = sanitize_query_params(params)

        self.assertEqual(result["document_number"], "12345678")
        self.assertEqual(result["company_id"], "1")
        self.assertEqual(result["search"], "T-1")

    def test_enmascara_credenciales_en_query(self):
        result = sanitize_query_params(FakeQueryParams([("token", "eyJhbG")]))

        self.assertEqual(result["token"], REDACTED)

    def test_conserva_llaves_repetidas(self):
        params = FakeQueryParams(
            [("area_id", "3"), ("area_id", "7"), ("area_id", "9")]
        )

        result = sanitize_query_params(params)

        self.assertEqual(result["area_id"], ["3", "7", "9"])


class ResponseBodyPathTests(unittest.TestCase):
    def test_por_defecto_no_se_omite_ninguna_ruta(self):
        self.assertEqual(settings.audit_redact_response_paths, ())
        self.assertFalse(should_redact_response_body("/api/sap/documents"))
        self.assertFalse(should_redact_response_body("/api/jobs"))
        self.assertFalse(should_redact_response_body("/api/attendance/marks"))

    def test_respeta_los_prefijos_configurados(self):
        original = settings.AUDIT_REDACT_RESPONSE_PATHS
        try:
            settings.AUDIT_REDACT_RESPONSE_PATHS = "/api/sap,/api/jobs"

            self.assertTrue(should_redact_response_body("/api/sap/documents"))
            self.assertTrue(should_redact_response_body("/api/jobs"))
            self.assertFalse(should_redact_response_body("/api/master/area"))
        finally:
            settings.AUDIT_REDACT_RESPONSE_PATHS = original


class ConfigurableWordListTests(unittest.TestCase):
    def test_se_pueden_agregar_palabras_sin_tocar_codigo(self):
        original = settings.AUDIT_SENSITIVE_KEYS
        try:
            settings.AUDIT_SENSITIVE_KEYS = original + ",clave"

            result = sanitize_payload({"clave_sunat": "x", "amount": 10})

            self.assertEqual(result["clave_sunat"], REDACTED)
            self.assertEqual(result["amount"], 10)
        finally:
            settings.AUDIT_SENSITIVE_KEYS = original

        # Al volver al valor original deja de enmascararse.
        self.assertEqual(
            sanitize_payload({"clave_sunat": "x"}),
            {"clave_sunat": "x"},
        )


if __name__ == "__main__":
    unittest.main()
