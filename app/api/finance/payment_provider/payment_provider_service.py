from typing import Any
from decimal import Decimal
from uuid import UUID
from uuid import uuid4
from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi import UploadFile
from sqlalchemy.exc import IntegrityError

from app.api.jobs.constants import JobType
from app.api.jobs.service import JobService
from app.api.master.master_repository import MasterRepository
from app.api.finance.payment_provider.payment_provider_repository import (
    PaymentProviderRepository,
)
from app.api.finance.payment_provider.payment_provider_schema import (
    PaymentProviderCreateRequest,
    PaymentProviderUpdateRequest,
)
from app.api.finance.payment_provider.pdf_parser import PaymentPdfParser
from app.api.finance.payment_provider.pdf_parser import normalizar_texto
from app.api.finance.payment_provider.processor import PaymentProviderProcessor
from app.core.db.integrity import raise_integrity_error
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.core.config import settings
from app.workers.dispatcher import dispatch_job
from app.models.finance.payment_provider_model import PaymentProvider
from app.services.email import EmailAttachment, EmailService
from app.services.email.email_service import parse_email_list


class PaymentProviderService:
    def __init__(self, db):
        self.db = db
        self.repository = PaymentProviderRepository(db)
        self.master_repository = MasterRepository(db)
        self.pdf_parser = PaymentPdfParser()
        self.email_service = EmailService()

    def list_providers(self, search: str | None = None, active: bool | None = None):
        return self.repository.list_providers(search=search, active=active)

    def get_provider(self, provider_id: UUID):
        provider = self.repository.get_provider(provider_id)
        if not provider:
            raise NotFoundError("Proveedor no encontrado")
        return provider

    def create_provider(
        self,
        request: PaymentProviderCreateRequest,
        current_user_id,
    ):
        data = request.model_dump()
        data["tax_id"] = data["tax_id"].strip()
        data["normalized_names"] = self._build_normalized_names(
            data["legal_name"],
            data["commercial_names"],
        )
        if self.repository.get_provider_by_tax_id(data["tax_id"]):
            raise ConflictError("Ya existe un proveedor con este RUC/RUT")

        provider = PaymentProvider(**data, created_by=current_user_id)
        self.repository.add(provider)
        self._commit_provider()
        return self.get_provider(provider.id)

    def update_provider(
        self,
        provider_id: UUID,
        request: PaymentProviderUpdateRequest,
        current_user_id,
    ):
        provider = self.get_provider(provider_id)
        data = request.model_dump(exclude_unset=True)
        if "tax_id" in data and data["tax_id"] is not None:
            data["tax_id"] = data["tax_id"].strip()
            existing = self.repository.get_provider_by_tax_id(data["tax_id"])
            if existing and existing.id != provider_id:
                raise ConflictError("Ya existe un proveedor con este RUC/RUT")

        for key, value in data.items():
            setattr(provider, key, value)
        if "legal_name" in data or "commercial_names" in data:
            provider.normalized_names = self._build_normalized_names(
                provider.legal_name,
                provider.commercial_names,
            )
        provider.updated_by = current_user_id
        self._commit_provider()
        return self.get_provider(provider.id)

    def delete_provider(self, provider_id: UUID, current_user_id):
        provider = self.get_provider(provider_id)
        provider.active = False
        provider.updated_by = current_user_id
        self.repository.commit()
        return True

    def process_files(self, files: list[UploadFile]) -> dict[str, Any]:
        return self.preview_files(files)

    def preview_files(self, files: list[UploadFile]) -> dict[str, Any]:
        processed = []
        errors = []

        for file in files:
            result = self.pdf_parser.parse(file)
            if result["procesado"]:
                processed.append(result)
            else:
                errors.append(result)

        providers = self.repository.list_active_providers()
        grouped = PaymentProviderProcessor(providers).group(processed)
        missing_provider_count = sum(
            1 for item in grouped if item["status"] == "MISSING_PROVIDER"
        )
        missing_email_count = sum(
            1 for item in grouped if item["status"] == "MISSING_PAYMENT_EMAIL"
        )
        return {
            "ready_to_send": (
                not errors and not missing_provider_count and not missing_email_count
            ),
            "total_archivos": len(files),
            "total_procesados": len(processed),
            "total_errores": len(errors),
            "total_proveedores": len(grouped),
            "missing_provider_count": missing_provider_count,
            "missing_email_count": missing_email_count,
            "proveedores": grouped,
            "errores": errors,
        }

    def build_renamed_zip(self, files: list[UploadFile]) -> tuple[str, bytes]:
        preview = self.preview_files(files)
        filename_by_original = {
            payment["archivo"]: payment["suggested_filename"]
            for provider in preview["proveedores"]
            for payment in provider["pagos"]
        }
        zip_buffer = BytesIO()
        used_names: set[str] = set()

        with ZipFile(zip_buffer, mode="w", compression=ZIP_DEFLATED) as zip_file:
            for file in files:
                suggested_name = filename_by_original.get(file.filename)
                if not suggested_name:
                    continue
                arcname = self._deduplicate_filename(suggested_name, used_names)
                used_names.add(arcname)
                file.file.seek(0)
                zip_file.writestr(arcname, file.file.read())
                file.file.seek(0)

        return "constancias_renombradas.zip", zip_buffer.getvalue()

    def send_payment_emails(
        self,
        files: list[UploadFile],
        *,
        mailing_parameter_id: int | None = None,
        mailing_parameter_name: str | None = None,
    ) -> dict[str, Any]:
        """Envia un correo por proveedor usando la misma lectura del preview.

        El frontend debe llamar primero a /payments/preview para corregir
        proveedores o correos faltantes. Este metodo vuelve a validar antes de
        enviar para evitar correos incompletos.
        """
        mailing_parameter = self._get_mailing_parameter(
            mailing_parameter_id,
            mailing_parameter_name,
        )
        preview = self.preview_files(files)
        if not preview["ready_to_send"]:
            raise ValidationError(
                "Hay archivos con error, proveedores sin identificar o correos faltantes"
            )

        file_content_by_name = self._read_uploaded_files(files)
        sent = []
        errors = []

        for provider_group in preview["proveedores"]:
            try:
                attachments = self._build_provider_attachments(
                    provider_group,
                    file_content_by_name,
                )
                message = self.email_service.build_from_template(
                    mailing_parameter,
                    parameters=self._build_mail_parameters(provider_group),
                    subject=f"Constancias de pago - {provider_group['titular_pdf']} || RASHPERU",
                    to=provider_group["emails_payments"] + parse_email_list(mailing_parameter.to),
                    bcc=parse_email_list(mailing_parameter.bcc),
                    cc=parse_email_list(mailing_parameter.cc),
                    attachments=attachments,
                )
                self.email_service.send(message)
                sent.append(
                    {
                        "provider_id": provider_group["provider_id"],
                        "proveedor": provider_group["proveedor"],
                        "to": message.to,
                        "attachments": [item.filename for item in attachments],
                    }
                )
            except Exception as exc:
                errors.append(
                    {
                        "provider_id": provider_group["provider_id"],
                        "proveedor": provider_group["proveedor"],
                        "error": str(exc),
                    }
                )

        return {
            "sent_count": len(sent),
            "error_count": len(errors),
            "sent": sent,
            "errors": errors,
        }

    def enqueue_payment_emails(
        self,
        files: list[UploadFile],
        *,
        current_user_id: UUID,
        mailing_parameter_id: int | None = None,
        mailing_parameter_name: str | None = None,
        idempotency_key: str | None = None,
        batch_size: int = 10,
    ):
        mailing_parameter = self._get_mailing_parameter(
            mailing_parameter_id,
            mailing_parameter_name,
        )
        preview = self.preview_files(files)
        if not preview["ready_to_send"]:
            raise ValidationError(
                "Hay archivos con error, proveedores sin identificar o correos faltantes"
            )

        staging_id = str(uuid4())
        file_path_by_name = self._save_uploaded_files(files, staging_id)
        payloads = {}
        references = []

        for provider_group in preview["proveedores"]:
            reference = self._build_email_job_reference(provider_group)
            if reference in payloads:
                reference = self._deduplicate_reference(reference, payloads)
            references.append(reference)
            payloads[reference] = self._make_json_safe(
                self._build_email_job_payload(
                    provider_group,
                    mailing_parameter,
                    file_path_by_name,
                )
            )

        return JobService(self.db, dispatcher=dispatch_job).create_job(
            job_type=JobType.PAYMENT_PROVIDER_EMAIL.value,
            parameters={
                "staging_id": staging_id,
                "mailing_parameter_id": mailing_parameter.id,
                "mailing_parameter_name": mailing_parameter.name,
            },
            references=references,
            user_id=current_user_id,
            batch_size=batch_size,
            idempotency_key=idempotency_key,
            item_payloads=payloads,
        )

    def _get_mailing_parameter(
        self,
        parameter_id: int | None,
        parameter_name: str | None,
    ):
        if parameter_id:
            parameter = self.master_repository.get_mailing_parameter_by_id(
                parameter_id
            )
        elif parameter_name:
            parameter = self.master_repository.get_mailing_parameter_by_name(
                parameter_name
            )
        else:
            parameter = self.master_repository.get_mailing_parameter_by_name(
                "send_provider"
            )

        if not parameter or not parameter.active:
            raise NotFoundError("Parametro de correo no encontrado o inactivo")
        return parameter

    @staticmethod
    def _read_uploaded_files(files: list[UploadFile]) -> dict[str, bytes]:
        content_by_name = {}
        for file in files:
            file.file.seek(0)
            content_by_name[file.filename] = file.file.read()
            file.file.seek(0)
        return content_by_name

    def _build_provider_attachments(
        self,
        provider_group: dict[str, Any],
        file_content_by_name: dict[str, bytes],
    ) -> list[EmailAttachment]:
        attachments = []
        used_names: set[str] = set()
        for payment in provider_group["pagos"]:
            content = file_content_by_name.get(payment["archivo"])
            if not content:
                continue
            filename = self._deduplicate_filename(
                payment["suggested_filename"],
                used_names,
            )
            used_names.add(filename)
            attachments.append(
                EmailAttachment(
                    filename=filename,
                    content=content,
                    content_type="application/pdf",
                )
            )
        return attachments

    def _build_email_job_payload(
        self,
        provider_group: dict[str, Any],
        mailing_parameter,
        file_path_by_name: dict[str, str],
    ) -> dict[str, Any]:
        return {
            "provider_id": (
                str(provider_group["provider_id"])
                if provider_group["provider_id"]
                else None
            ),
            "provider": provider_group["proveedor"],
            "to": provider_group["emails_payments"]
            + parse_email_list(mailing_parameter.to),
            "cc": parse_email_list(mailing_parameter.cc),
            "bcc": parse_email_list(mailing_parameter.bcc),
            "subject": f"Constancias de pago - {provider_group['titular_pdf']} || RASHPERU",
            "parameters": self._build_mail_parameters(provider_group),
            "mailing_parameter": self._serialize_mailing_parameter(mailing_parameter),
            "attachments": self._build_email_job_attachments(
                provider_group,
                file_path_by_name,
            ),
        }

    def _build_email_job_attachments(
        self,
        provider_group: dict[str, Any],
        file_path_by_name: dict[str, str],
    ) -> list[dict[str, str]]:
        attachments = []
        used_names: set[str] = set()
        for payment in provider_group["pagos"]:
            file_path = file_path_by_name.get(payment["archivo"])
            if not file_path:
                continue
            filename = self._deduplicate_filename(
                payment["suggested_filename"],
                used_names,
            )
            used_names.add(filename)
            attachments.append(
                {
                    "file_path": file_path,
                    "filename": filename,
                    "content_type": "application/pdf",
                }
            )
        return attachments

    @staticmethod
    def _serialize_mailing_parameter(mailing_parameter) -> dict[str, Any]:
        return {
            "name": mailing_parameter.name,
            "template": mailing_parameter.template,
            "template_html": mailing_parameter.template_html,
            "template_text": mailing_parameter.template_text,
            "mp_from": mailing_parameter.mp_from,
            "to": mailing_parameter.to,
            "subject": mailing_parameter.subject,
            "cc": mailing_parameter.cc,
            "bcc": mailing_parameter.bcc,
        }

    @staticmethod
    def _save_uploaded_files(
        files: list[UploadFile],
        staging_id: str,
    ) -> dict[str, str]:
        target_dir = Path(settings.PAYMENT_PROVIDER_STORAGE_DIR) / staging_id
        target_dir.mkdir(parents=True, exist_ok=True)
        path_by_name = {}
        for file in files:
            file.file.seek(0)
            extension = Path(file.filename or "document.pdf").suffix or ".pdf"
            safe_name = f"{uuid4()}{extension.lower()}"
            target_path = target_dir / safe_name
            target_path.write_bytes(file.file.read())
            path_by_name[file.filename] = str(target_path)
            file.file.seek(0)
        return path_by_name

    @staticmethod
    def _build_email_job_reference(provider_group: dict[str, Any]) -> str:
        provider_name = (
            provider_group.get("proveedor")
            or provider_group.get("titular_pdf")
            or "Proveedor sin nombre"
        )
        return f"Enviar correo - {provider_name}"[:120]

    @staticmethod
    def _deduplicate_reference(reference: str, payloads: dict) -> str:
        max_base_length = 116
        base = reference[:max_base_length]
        counter = 2
        while True:
            candidate = f"{base} #{counter}"
            if candidate not in payloads:
                return candidate
            counter += 1

    @classmethod
    def _make_json_safe(cls, value):
        if isinstance(value, UUID):
            return str(value)
        if isinstance(value, Decimal):
            return str(value)
        if isinstance(value, dict):
            return {key: cls._make_json_safe(item) for key, item in value.items()}
        if isinstance(value, list):
            return [cls._make_json_safe(item) for item in value]
        return value

    @staticmethod
    def _build_mail_parameters(provider_group: dict[str, Any]) -> dict[str, Any]:
        return {
            "provider_id": (
                str(provider_group["provider_id"])
                if provider_group["provider_id"]
                else None
            ),
            "provider_tax_id": provider_group["provider_tax_id"],
            "proveedor": provider_group["proveedor"],
            "titular_pdf": provider_group["titular_pdf"],
            "cantidad_pagos": provider_group["cantidad_pagos"],
            "totales": provider_group["totales"],
            "pagos": provider_group["pagos"],
        }

    @staticmethod
    def _deduplicate_filename(filename: str, used_names: set[str]) -> str:
        if filename not in used_names:
            return filename
        stem, extension = filename.rsplit(".", 1)
        counter = 2
        while True:
            candidate = f"{stem}_{counter}.{extension}"
            if candidate not in used_names:
                return candidate
            counter += 1

    @staticmethod
    def _build_normalized_names(
        legal_name: str,
        commercial_names: list[str],
    ) -> list[str]:
        names = [legal_name, *commercial_names]
        return list(dict.fromkeys(normalizar_texto(name) for name in names if name))

    def _commit_provider(self):
        try:
            self.repository.commit()
        except IntegrityError as exc:
            self.repository.rollback()
            raise_integrity_error(
                exc,
                conflicts={
                    "uq_payment_provider_tax_id": (
                        "Ya existe un proveedor con este RUC/RUT"
                    ),
                },
            )
