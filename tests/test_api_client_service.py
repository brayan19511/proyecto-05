from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock
from uuid import uuid4

from fastapi import HTTPException

from app.api.security.api_client.api_client_service import ApiClientService
from app.models import ApiClient


class ApiClientServiceTests(unittest.TestCase):
    def setUp(self):
        self.db = MagicMock()
        self.service = ApiClientService(self.db)
        self.service.repository = MagicMock()

    def test_generated_key_is_hashed_and_has_lookup_prefix(self):
        self.service.repository.get_by_prefix.return_value = None

        raw_key, prefix, key_hash = self.service._generate_key()

        self.assertTrue(raw_key.startswith(f"rsk_{prefix}."))
        self.assertNotEqual(raw_key, key_hash)
        self.assertEqual(len(key_hash), 64)

    def test_valid_key_authenticates_without_writing_raw_secret(self):
        raw_key = "rsk_1234567890abcdef.a-very-long-random-secret"
        client = ApiClient(
            id=uuid4(),
            user_id=uuid4(),
            name="Power BI",
            key_prefix="1234567890abcdef",
            key_hash=self.service._hash_key(raw_key),
            scopes=["analytics.read"],
            active=True,
            last_used_at=datetime.now(timezone.utc),
        )
        self.service.repository.get_by_prefix.return_value = client
        self.service.repository.get_user.return_value = SimpleNamespace(
            active=True,
            active_roles=[SimpleNamespace(name="Analista")],
            permissions=[SimpleNamespace(code="analytics.read")],
        )

        result = self.service.authenticate(raw_key, "analytics.read")

        self.assertIs(result, client)
        self.service.repository.save.assert_not_called()
        self.assertNotEqual(client.key_hash, raw_key)

    def test_last_used_write_is_throttled(self):
        client = ApiClient(
            id=uuid4(),
            user_id=uuid4(),
            name="Excel",
            key_prefix="prefix",
            key_hash="hash",
            scopes=["analytics.read"],
            active=True,
            last_used_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )

        self.service._touch_last_used(client)

        self.service.repository.save.assert_called_once_with(client)

    def test_invalid_scope_is_rejected(self):
        with self.assertRaises(HTTPException) as context:
            self.service._validate_scopes(["coolbox.etl.execute"])

        self.assertEqual(context.exception.status_code, 400)


if __name__ == "__main__":
    unittest.main()
