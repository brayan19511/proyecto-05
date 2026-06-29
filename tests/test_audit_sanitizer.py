import unittest

from app.core.audit_sanitizer import sanitize_headers, sanitize_payload


class AuditSanitizerTests(unittest.TestCase):
    def test_sensitive_values_are_redacted_recursively(self):
        payload = {
            "email": "admin@example.com",
            "password": "secret",
            "nested": {"access_token": "jwt"},
            "api_key": "rsk_secret",
        }

        result = sanitize_payload(payload)

        self.assertEqual(result["email"], "admin@example.com")
        self.assertEqual(result["password"], "[REDACTED]")
        self.assertEqual(result["nested"]["access_token"], "[REDACTED]")
        self.assertEqual(result["api_key"], "[REDACTED]")

    def test_headers_use_allowlist(self):
        result = sanitize_headers(
            {
                "authorization": "Bearer secret",
                "content-type": "application/json",
                "user-agent": "test-client",
            }
        )

        self.assertNotIn("authorization", result)
        self.assertEqual(result["content-type"], "application/json")


if __name__ == "__main__":
    unittest.main()
