"""Constantes propias del flujo de pagos a proveedores."""

# Parametro sembrado por defecto para enviar constancias de pago.
DEFAULT_PAYMENT_PROVIDER_MAILING_PARAMETER = "payment_provider_summary"

# entity_type con el que se guardan las constancias enviadas en
# storage.attachments. El entity_id es el id del JobItem, o sea el correo
# concreto que se envio: desde ahi se sabe destinatario, fecha y proveedor.
PAYMENT_PROVIDER_EMAIL_ENTITY_TYPE = "payment_provider_email"
