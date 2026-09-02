"""Tests del alcance empresa/area de un usuario (app/core/scope.py)."""

import unittest
from types import SimpleNamespace
from uuid import uuid4

from app.core.exceptions import ForbiddenError
from app.core.scope import (
    UserScope,
    assert_in_scope,
    get_user_scope,
    scope_condition,
)
from app.models.finance.provision_model import Provision


def make_user(*role_names, user_id=None):
    """Usuario minimo con los roles activos indicados."""
    return SimpleNamespace(
        id=user_id or uuid4(),
        user_roles_links=[
            SimpleNamespace(active=True, role=SimpleNamespace(name=name))
            for name in role_names
        ],
        permissions=[],
    )


class FakeQuery:
    """Query de SQLAlchemy simulada: solo devuelve las filas configuradas."""

    def __init__(self, rows):
        self._rows = rows

    def filter(self, *args, **kwargs):
        return self

    def all(self):
        return self._rows


class FakeSession:
    def __init__(self, rows):
        self._rows = rows

    def query(self, *args, **kwargs):
        return FakeQuery(self._rows)


class UserScopeTests(unittest.TestCase):
    def test_scope_vacio(self):
        scope = UserScope()

        self.assertTrue(scope.is_empty)
        self.assertFalse(scope.allows(1, 1))

    def test_scope_sin_restriccion_permite_todo(self):
        scope = UserScope(unrestricted=True)

        self.assertFalse(scope.is_empty)
        self.assertTrue(scope.allows(99, 99))
        self.assertTrue(scope.allows(None, None))

    def test_empresa_completa_cubre_cualquier_area(self):
        scope = UserScope(companies=frozenset({1}))

        self.assertTrue(scope.allows(1, 7))
        self.assertTrue(scope.allows(1, None))
        self.assertFalse(scope.allows(2, 7))

    def test_par_empresa_area_es_exacto(self):
        scope = UserScope(pairs=frozenset({(1, 5)}))

        self.assertTrue(scope.allows(1, 5))
        self.assertFalse(scope.allows(1, 6))
        self.assertFalse(scope.allows(2, 5))
        # Sin area concreta no alcanza para un permiso por area.
        self.assertFalse(scope.allows(1, None))

    def test_area_ids_y_company_ids(self):
        scope = UserScope(
            companies=frozenset({1}),
            pairs=frozenset({(2, 5), (2, 6), (3, 7)}),
        )

        self.assertEqual(scope.company_ids, {1, 2, 3})
        self.assertEqual(scope.area_ids(), {5, 6, 7})
        self.assertEqual(scope.area_ids(company_id=2), {5, 6})


class GetUserScopeTests(unittest.TestCase):
    def test_admin_queda_sin_restriccion(self):
        scope = get_user_scope(FakeSession([]), make_user("Admin"))

        self.assertTrue(scope.unrestricted)

    def test_permiso_ver_todo_queda_sin_restriccion(self):
        user = make_user("Gastos Admin")
        user.permissions = [SimpleNamespace(id=1, code="provisions.view_all")]

        scope = get_user_scope(FakeSession([]), user, "provisions.view_all")

        self.assertTrue(scope.unrestricted)

    def test_agrupa_empresas_completas_y_pares(self):
        rows = [(1, None), (2, 5), (2, 6)]

        scope = get_user_scope(FakeSession(rows), make_user("Gastos Operador"))

        self.assertFalse(scope.unrestricted)
        self.assertEqual(scope.companies, frozenset({1}))
        self.assertEqual(scope.pairs, frozenset({(2, 5), (2, 6)}))

    def test_empresa_completa_absorbe_sus_pares(self):
        # Si ya tiene toda la empresa 1, el par (1, 5) es redundante.
        rows = [(1, None), (1, 5)]

        scope = get_user_scope(FakeSession(rows), make_user("Gastos Operador"))

        self.assertEqual(scope.companies, frozenset({1}))
        self.assertEqual(scope.pairs, frozenset())
        self.assertTrue(scope.allows(1, 5))

    def test_sin_accesos_queda_vacio(self):
        scope = get_user_scope(FakeSession([]), make_user("Gastos Operador"))

        self.assertTrue(scope.is_empty)


class ScopeConditionTests(unittest.TestCase):
    def compile_condition(self, scope):
        condition = scope_condition(Provision, scope)

        if condition is None:
            return None

        return str(condition.compile(compile_kwargs={"literal_binds": True}))

    def test_sin_restriccion_no_filtra(self):
        self.assertIsNone(self.compile_condition(UserScope(unrestricted=True)))

    def test_scope_vacio_es_condicion_falsa(self):
        self.assertEqual(self.compile_condition(UserScope()), "false")

    def test_empresa_completa(self):
        sql = self.compile_condition(UserScope(companies=frozenset({1, 2})))

        self.assertIn("company_id IN (1, 2)", sql)

    def test_pares_empresa_area(self):
        sql = self.compile_condition(UserScope(pairs=frozenset({(1, 5)})))

        self.assertIn("company_id = 1", sql)
        self.assertIn("area_id = 5", sql)

    def test_combina_empresas_y_pares_con_or(self):
        sql = self.compile_condition(
            UserScope(companies=frozenset({1}), pairs=frozenset({(2, 5)}))
        )

        self.assertIn(" OR ", sql)


class AssertInScopeTests(unittest.TestCase):
    def test_scope_vacio_no_bloquea(self):
        # Compatibilidad: quien todavia no tiene alcance asignado sigue igual.
        assert_in_scope(UserScope(), 1, 1)

    def test_sin_restriccion_no_bloquea(self):
        assert_in_scope(UserScope(unrestricted=True), 99, 99)

    def test_dentro_del_alcance_no_bloquea(self):
        assert_in_scope(UserScope(pairs=frozenset({(1, 5)})), 1, 5)

    def test_fuera_del_alcance_lanza_403(self):
        scope = UserScope(pairs=frozenset({(1, 5)}))

        with self.assertRaises(ForbiddenError):
            assert_in_scope(scope, 1, 6)


if __name__ == "__main__":
    unittest.main()
