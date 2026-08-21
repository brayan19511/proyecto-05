import unittest

from app.api.sales_channel.imports.service import (
    MAX_DESCRIPTION_LOOKUP,
    SkuExcelImportService,
)


class FakeLookup:
    """Simula la busqueda en ICG: devuelve {sku_normalizado: descripcion}."""

    def __init__(self, mapping: dict[str, str]):
        self.mapping = mapping
        self.received: list[str] | None = None

    def descripciones_por_sku(self, skus: list[str]) -> dict[str, str]:
        self.received = skus
        return self.mapping


class BuildDescriptionsTests(unittest.TestCase):
    def test_without_lookup_returns_empty(self):
        descriptions, truncated = SkuExcelImportService._build_descriptions(
            {"created_skus": ["A"]},
            None,
        )
        self.assertEqual(descriptions, {})
        self.assertFalse(truncated)

    def test_maps_by_original_sku_and_dedupes(self):
        result = {
            "created_skus": ["abc", "xyz"],
            "deactivated_skus": ["abc"],  # duplicado: no se repite
            "missing": ["nomatch"],
        }
        lookup = FakeLookup({"ABC": "Teclado", "XYZ": "Mouse"})
        descriptions, truncated = SkuExcelImportService._build_descriptions(
            result,
            lookup,
        )
        self.assertEqual(descriptions, {"abc": "Teclado", "xyz": "Mouse"})
        self.assertFalse(truncated)
        # "nomatch" sin descripcion no aparece; "abc" se consulta una sola vez.
        self.assertEqual(lookup.received.count("abc"), 1)

    def test_truncates_when_over_limit(self):
        shown = [f"SKU{i}" for i in range(MAX_DESCRIPTION_LOOKUP + 5)]
        lookup = FakeLookup({})
        _, truncated = SkuExcelImportService._build_descriptions(
            {"created_skus": shown},
            lookup,
        )
        self.assertTrue(truncated)
        self.assertEqual(len(lookup.received), MAX_DESCRIPTION_LOOKUP)


if __name__ == "__main__":
    unittest.main()
