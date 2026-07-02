from types import SimpleNamespace
import unittest

from sqlalchemy.exc import IntegrityError

from app.core.db.integrity import (
    get_constraint_name,
    raise_integrity_error,
)
from app.core.exceptions import ConflictError, ValidationError


def make_integrity_error(constraint_name: str):
    original = Exception("database detail must not be exposed")
    original.diag = SimpleNamespace(constraint_name=constraint_name)
    return IntegrityError("statement", {}, original)


class IntegrityErrorTests(unittest.TestCase):
    def test_extracts_constraint_name(self):
        error = make_integrity_error("provisions_company_id_ticket_code_key")
        self.assertEqual(
            get_constraint_name(error),
            "provisions_company_id_ticket_code_key",
        )

    def test_maps_unique_constraint_to_conflict(self):
        error = make_integrity_error("auth_email_key")
        with self.assertRaisesRegex(ConflictError, "Email ya registrado"):
            raise_integrity_error(
                error,
                conflicts={"auth_email_key": "Email ya registrado"},
            )

    def test_maps_foreign_key_to_validation_error(self):
        error = make_integrity_error("provisions_company_id_fkey")
        with self.assertRaisesRegex(ValidationError, "empresa"):
            raise_integrity_error(
                error,
                invalid_references={
                    "provisions_company_id_fkey": (
                        "La empresa indicada no existe"
                    )
                },
            )

    def test_unknown_constraint_uses_safe_message(self):
        error = make_integrity_error("unknown_constraint")
        with self.assertRaisesRegex(
            ValidationError,
            "No se pudo guardar la informacion",
        ):
            raise_integrity_error(error)


if __name__ == "__main__":
    unittest.main()
