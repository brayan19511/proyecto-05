import unittest
from unittest.mock import patch

from app.api.jobs.constants import JOB_MODULES, JobType
from app.api.observability.constants import COMPONENT_MODULES
from app.api.verify.seed_service import PERMISSIONS, ROLE_PERMISSIONS
from app.core.exceptions import ModuleDisabledError
from app.core.modules import (
    MODULE_CATALOG,
    MODULE_CODES,
    MODULE_EMAIL,
    MODULE_SAP,
    enabled_module_codes,
    get_disabled_reason,
    is_module_enabled,
    require_module,
)


class FakeRow:
    def __init__(self, code, enabled=True, disabled_reason=None):
        self.code = code
        self.enabled = enabled
        self.disabled_reason = disabled_reason


class FakeQuery:
    def __init__(self, rows):
        self._rows = rows

    def filter(self, *_args):
        # El unico filtro que usa el codigo es por code; se resuelve en first().
        return self

    def first(self):
        return self._rows[0] if self._rows else None

    def all(self):
        return self._rows


class FakeSession:
    """Sesion minima: devuelve las filas que se le den, sin tocar la base."""

    def __init__(self, rows=None):
        self.rows = rows or []

    def query(self, _model):
        return FakeQuery(self.rows)


class ModuleSwitchTests(unittest.TestCase):
    def test_module_without_row_is_enabled(self):
        # Un modulo nuevo no debe quedar muerto si falta correr el seed.
        self.assertTrue(is_module_enabled(MODULE_SAP, FakeSession([])))

    def test_row_disabled_turns_module_off(self):
        session = FakeSession([FakeRow(MODULE_SAP, enabled=False)])

        self.assertFalse(is_module_enabled(MODULE_SAP, session))

    def test_disabled_reason_falls_back_to_generic_text(self):
        session = FakeSession([FakeRow(MODULE_SAP, enabled=False)])

        self.assertEqual(
            get_disabled_reason(MODULE_SAP, session),
            "Desactivado por el administrador",
        )

    def test_disabled_reason_uses_operator_text(self):
        session = FakeSession(
            [FakeRow(MODULE_SAP, enabled=False, disabled_reason="Migracion SAP")]
        )

        self.assertEqual(get_disabled_reason(MODULE_SAP, session), "Migracion SAP")

    def test_environment_wins_over_table(self):
        # La fila dice encendido, el .env dice apagado: manda el .env.
        session = FakeSession([FakeRow(MODULE_SAP, enabled=True)])

        with patch("app.core.modules.settings") as settings:
            settings.modules_disabled = frozenset({MODULE_SAP})

            self.assertFalse(is_module_enabled(MODULE_SAP, session))
            self.assertEqual(
                get_disabled_reason(MODULE_SAP, session),
                "Desactivado por configuracion del entorno",
            )

    def test_require_module_raises_with_code_and_reason(self):
        session = FakeSession(
            [FakeRow(MODULE_EMAIL, enabled=False, disabled_reason="Buzon lleno")]
        )

        with self.assertRaises(ModuleDisabledError) as ctx:
            require_module(MODULE_EMAIL, session)

        self.assertEqual(ctx.exception.code, MODULE_EMAIL)
        self.assertEqual(ctx.exception.reason, "Buzon lleno")
        self.assertIn("Envio de correos", str(ctx.exception))

    def test_require_module_passes_when_enabled(self):
        self.assertIsNone(require_module(MODULE_SAP, FakeSession([])))

    def test_enabled_module_codes_respects_environment(self):
        session = FakeSession([])

        with patch("app.core.modules.settings") as settings:
            settings.modules_disabled = frozenset({MODULE_SAP})
            codes = enabled_module_codes(session)

        self.assertNotIn(MODULE_SAP, codes)
        self.assertIn(MODULE_EMAIL, codes)


class ModuleCatalogTests(unittest.TestCase):
    def test_catalog_codes_are_unique(self):
        codes = [item["code"] for item in MODULE_CATALOG]

        self.assertEqual(len(codes), len(set(codes)))

    def test_every_job_type_maps_to_a_real_module(self):
        # Si se agrega un JobType nuevo sin mapearlo, el dispatcher no lo
        # protege: este test obliga a mantener el mapa completo.
        self.assertEqual(set(JOB_MODULES), {item.value for item in JobType})

        for module_code in JOB_MODULES.values():
            self.assertIn(module_code, MODULE_CODES)

    def test_observability_components_map_to_real_modules(self):
        for module_code in COMPONENT_MODULES.values():
            self.assertIn(module_code, MODULE_CODES)


class ModulePermissionSeedTests(unittest.TestCase):
    def test_module_permissions_are_seeded(self):
        codes = {item["code"] for item in PERMISSIONS}

        self.assertIn("master.modules.view", codes)
        self.assertIn("master.modules.edit", codes)

    def test_master_admin_can_switch_modules(self):
        self.assertIn("master.modules.edit", ROLE_PERMISSIONS["Master Admin"])

    def test_master_consulta_can_only_view_modules(self):
        permissions = ROLE_PERMISSIONS["Master Consulta"]

        self.assertIn("master.modules.view", permissions)
        self.assertNotIn("master.modules.edit", permissions)


if __name__ == "__main__":
    unittest.main()
