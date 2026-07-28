import unittest
from unittest.mock import Mock

from app.api.finance.payment_provider.constants import (
    DEFAULT_PAYMENT_PROVIDER_MAILING_PARAMETER,
)
from app.api.finance.payment_provider.payment_provider_service import (
    PaymentProviderService,
)


class PaymentProviderServiceMailingTests(unittest.TestCase):
    def test_default_mailing_parameter_uses_summary_seed_name(self):
        service = PaymentProviderService.__new__(PaymentProviderService)
        service.master_repository = Mock()
        parameter = Mock(active=True)
        service.master_repository.get_mailing_parameter_by_name.return_value = parameter

        self.assertIs(service._get_mailing_parameter(None, None), parameter)
        service.master_repository.get_mailing_parameter_by_name.assert_called_once_with(
            DEFAULT_PAYMENT_PROVIDER_MAILING_PARAMETER
        )

    def test_subject_override_is_optional(self):
        self.assertIsNone(PaymentProviderService._build_email_subject(None))
        self.assertIsNone(PaymentProviderService._build_email_subject("  "))
        self.assertEqual(
            PaymentProviderService._build_email_subject(" Pago {{ proveedor }} "),
            "Pago {{ proveedor }}",
        )


if __name__ == "__main__":
    unittest.main()
