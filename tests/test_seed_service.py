from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from app.api.verify.seed_service import SeedService
from app.models import UserRole


class SeedServiceTests(unittest.TestCase):
    def test_run_seed_commits_once(self):
        db = MagicMock()
        service = SeedService(db)
        service._reconcile = MagicMock(return_value={"message": "ok"})

        result = service.run_seed()

        db.commit.assert_called_once_with()
        db.rollback.assert_not_called()
        self.assertEqual(result["status"], "success")

    def test_run_seed_rolls_back_on_failure(self):
        db = MagicMock()
        service = SeedService(db)
        service._reconcile = MagicMock(side_effect=ValueError("invalid"))

        with self.assertRaises(ValueError):
            service.run_seed()

        db.rollback.assert_called_once_with()
        db.commit.assert_not_called()

    def test_existing_role_permission_is_a_noop(self):
        db = MagicMock()
        db.scalar.return_value = object()
        service = SeedService(db)

        service._ensure_role_permission(
            SimpleNamespace(id=1),
            SimpleNamespace(id=2),
            {"relations_created": 0},
        )

        db.add.assert_not_called()

    def test_existing_admin_without_role_gets_relation(self):
        db = MagicMock()
        admin = SimpleNamespace(id="user-id", active=True)
        db.scalar.side_effect = [admin, None]
        counters = {
            "created": 0,
            "updated": 0,
            "existing": 0,
            "relations_created": 0,
        }
        service = SeedService(db)

        with (
            patch(
                "app.api.verify.seed_service.settings.SEED_ADMIN_EMAIL",
                "admin@example.com",
            ),
            patch(
                "app.api.verify.seed_service.settings.SEED_ADMIN_PASSWORD",
                None,
            ),
        ):
            result = service._ensure_admin(
                SimpleNamespace(id=10),
                counters,
            )

        relation = db.add.call_args.args[0]
        self.assertIsInstance(relation, UserRole)
        self.assertEqual(result["status"], "existing")
        self.assertEqual(counters["relations_created"], 1)


if __name__ == "__main__":
    unittest.main()
