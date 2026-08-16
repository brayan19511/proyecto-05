from decimal import Decimal
import re
from typing import Any

from app.api.finance.payment_provider.pdf_parser import (
    clave_comparacion,
    clave_documento,
    normalizar_texto,
)


MONTH_NAMES = {
    1: "ENERO",
    2: "FEBRERO",
    3: "MARZO",
    4: "ABRIL",
    5: "MAYO",
    6: "JUNIO",
    7: "JULIO",
    8: "AGOSTO",
    9: "SETIEMBRE",
    10: "OCTUBRE",
    11: "NOVIEMBRE",
    12: "DICIEMBRE",
}

CURRENCY_SYMBOLS = {
    "PEN": "S/",
    "USD": "US$",
    "EUR": "EUR",
}


class PaymentProviderProcessor:
    """Agrupa pagos extraidos y los relaciona con proveedores conocidos."""

    def __init__(self, providers):
        self.providers = providers

    def group(self, payments: list[dict]) -> list[dict]:
        groups: dict[str, dict] = {}

        for payment in payments:
            destination = payment["datos_destino"]
            operation = payment["datos_operacion"]
            titular = destination["titular"]
            ruc = destination.get("ruc")
            currency = destination["moneda"]
            amount = destination["monto_decimal"]

            # Se identifica primero por documento (RUC/DNI), que es lo mas
            # confiable; si no, por nombre (tolerante a puntuacion).
            provider = self._find_provider(ruc, titular)
            display_name = (
                provider.legal_name if provider else (titular or ruc or "SIN IDENTIFICAR")
            )
            group_key = self._group_key(provider, ruc, titular)

            if group_key not in groups:
                groups[group_key] = {
                    "provider_id": provider.id if provider else None,
                    "provider_tax_id": provider.tax_id if provider else ruc,
                    "proveedor": display_name,
                    "titular_pdf": titular or ruc,
                    "identificado": provider is not None,
                    "emails_payments": provider.emails_payments if provider else [],
                    "cantidad_pagos": 0,
                    "archivos": [],
                    "totales": {},
                    "pagos": [],
                }

            group = groups[group_key]
            group["totales"].setdefault(currency, Decimal("0.00"))
            group["totales"][currency] += amount
            group["cantidad_pagos"] += 1
            group["archivos"].append(payment["archivo"])
            payment_item = self._build_payment_item(payment, operation)
            payment_item["suggested_filename"] = build_pdf_filename(
                titular=titular or display_name,
                fecha=operation["fecha_proceso"] or operation["fecha_envio"],
            )
            group["pagos"].append(payment_item)

        return [self._serialize_group(group) for group in groups.values()]

    def _find_provider(self, ruc: str | None, titular: str | None):
        return self._find_by_taxid(ruc) or self._find_by_name(titular)

    def _find_by_taxid(self, ruc: str | None):
        clave = clave_documento(ruc)
        if not clave:
            return None
        for provider in self.providers:
            if clave_documento(provider.tax_id) == clave:
                return provider
        return None

    def _find_by_name(self, titular: str | None):
        clave = clave_comparacion(titular)
        if not clave:
            return None
        for provider in self.providers:
            for nombre in provider.normalized_names or []:
                if clave_comparacion(nombre) == clave:
                    return provider
        return None

    @staticmethod
    def _group_key(provider, ruc: str | None, titular: str | None) -> str:
        if provider:
            return f"id:{provider.id}"
        if ruc:
            return f"ruc:{clave_documento(ruc)}"
        return f"name:{clave_comparacion(titular)}"

    @staticmethod
    def _build_payment_item(payment: dict, operation: dict) -> dict[str, Any]:
        destination = payment["datos_destino"]
        return {
            "archivo": payment["archivo"],
            "monto_texto": destination["monto_texto"],
            "monto_decimal": destination["monto_decimal"],
            "moneda": destination["moneda"],
            "moneda_simbolo": currency_symbol(destination["moneda"]),
            "moneda_original": destination["moneda_original"],
            "titular": destination["titular"],
            "cuenta": destination["cuenta"],
            "tipo": destination["tipo"],
            "referencia": destination["referencia"],
            "fecha_envio": operation["fecha_envio"],
            "fecha_proceso": operation["fecha_proceso"],
            "estado": operation["estado"],
        }

    @staticmethod
    def _serialize_group(group: dict) -> dict:
        if not group["identificado"]:
            group["status"] = "MISSING_PROVIDER"
        elif not group["emails_payments"]:
            group["status"] = "MISSING_PAYMENT_EMAIL"
        else:
            group["status"] = "READY"

        group["totales"] = [
            {
                "moneda": currency,
                "moneda_simbolo": currency_symbol(currency),
                "total": str(total.quantize(Decimal("0.01"))),
            }
            for currency, total in group["totales"].items()
        ]
        for payment in group["pagos"]:
            payment["monto_decimal"] = str(
                payment["monto_decimal"].quantize(Decimal("0.01"))
            )
        return group


def build_pdf_filename(titular: str | None, fecha: str | None) -> str:
    provider_name = sanitize_filename_part(titular or "PROVEEDOR")
    date_label = build_date_label(fecha)
    return f"{provider_name}_{date_label}.pdf"


def currency_symbol(currency_code: str | None) -> str:
    if not currency_code:
        return ""
    return CURRENCY_SYMBOLS.get(currency_code, currency_code)


def sanitize_filename_part(value: str) -> str:
    normalized = normalizar_texto(value)
    # Mantiene el nombre legible para el usuario y evita caracteres
    # problematicos para Windows/Linux al descargar el ZIP.
    normalized = re.sub(r"[^A-Z0-9.]+", "_", normalized)
    normalized = re.sub(r"_+", "_", normalized)
    normalized = normalized.rstrip("._-")
    return normalized or "PROVEEDOR"


def build_date_label(value: str | None) -> str:
    parsed = parse_pdf_date(value)
    if not parsed:
        return "SIN_FECHA"
    month = MONTH_NAMES[parsed["month"]]
    return f"{month}_{parsed['day']:02d}"


def parse_pdf_date(value: str | None) -> dict[str, int] | None:
    if not value:
        return None
    match = re.search(r"(?P<day>\d{1,2})[/-](?P<month>\d{1,2})[/-](?P<year>\d{2,4})", value)
    if not match:
        return None
    day = int(match.group("day"))
    month = int(match.group("month"))
    if not 1 <= day <= 31 or not 1 <= month <= 12:
        return None
    return {"day": day, "month": month}
