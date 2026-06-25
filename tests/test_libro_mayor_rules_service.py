from types import SimpleNamespace
import unittest

import pandas as pd

from app.api.libro_mayor.service.libro_mayor_rules_service import (
    LibroMayorRulesService,
)


def make_rule(**overrides):
    values = {
        "id_regla": 1,
        "cuenta": None,
        "cuenta_contrapartida": None,
        "centro_costo": None,
        "filtro_texto": None,
        "texto_excluido": None,
        "monto_min": None,
        "monto_max": None,
        "codigo": "GASTO",
        "subcodigo": "OTROS",
        "nombre_cuenta": "Gastos",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def make_dataframe(**overrides):
    values = {
        "transaccion_id": [1],
        "linea": [1],
        "cuenta_asociada": ["9510"],
        "cuenta_contrapartida": [None],
        "centro_costo": [None],
        "cargo_abono_ml": [100],
        "descripcion": [None],
        "referencia_1": [None],
        "referencia_2": [None],
        "referencia_3": [None],
    }
    values.update(overrides)
    return pd.DataFrame(values)


class LibroMayorRulesServiceTests(unittest.TestCase):
    def setUp(self):
        self.service = LibroMayorRulesService()

    def test_matches_text_in_each_supported_column(self):
        for column in (
            "descripcion",
            "referencia_1",
            "referencia_2",
            "referencia_3",
        ):
            with self.subTest(column=column):
                df = make_dataframe(**{column: ["Servicio CLOUD mensual"]})
                result = self.service.aplicar(
                    df,
                    [make_rule(filtro_texto="cloud")],
                )
                self.assertEqual(result.loc[0, "id_regla"], 1)

    def test_text_match_is_literal_and_case_insensitive(self):
        df = make_dataframe(referencia_1=["AJUSTE 100% [TI]"])
        result = self.service.aplicar(
            df,
            [make_rule(filtro_texto="100% [ti]")],
        )
        self.assertEqual(result.loc[0, "id_regla"], 1)

    def test_excluded_text_applies_to_all_supported_columns(self):
        df = make_dataframe(
            descripcion=["Servicio cloud"],
            referencia_3=["ANULADO"],
        )
        result = self.service.aplicar(
            df,
            [
                make_rule(
                    filtro_texto="cloud",
                    texto_excluido="anulado",
                )
            ],
        )
        self.assertTrue(pd.isna(result.loc[0, "id_regla"]))

    def test_missing_reference_columns_do_not_fail(self):
        df = make_dataframe()[
            [
                "transaccion_id",
                "linea",
                "cuenta_asociada",
                "cuenta_contrapartida",
                "centro_costo",
                "cargo_abono_ml",
                "descripcion",
            ]
        ]
        df.loc[0, "descripcion"] = "Licencia"
        result = self.service.aplicar(
            df,
            [make_rule(filtro_texto="licencia")],
        )
        self.assertEqual(result.loc[0, "id_regla"], 1)

    def test_first_rule_keeps_priority(self):
        df = make_dataframe(descripcion=["Servicio cloud"])
        result = self.service.aplicar(
            df,
            [
                make_rule(id_regla=10, filtro_texto="cloud", codigo="PRIMERO"),
                make_rule(id_regla=20, filtro_texto="cloud", codigo="SEGUNDO"),
            ],
        )
        self.assertEqual(result.loc[0, "id_regla"], 10)
        self.assertEqual(result.loc[0, "codigo"], "PRIMERO")


if __name__ == "__main__":
    unittest.main()
