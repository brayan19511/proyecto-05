# provision_service.py
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.finance.provisions.constants import (
    APPROVED_STATUS,
    BASE_CURRENCY_CODE,
    CANCELLED_STATUS,
    PENDING_DETAIL_STATUS,
    READY_FOR_REVIEW_STATUS,
    REJECTED_FINAL_STATUS,
    REJECTED_FOR_EDIT_STATUS,
)
from app.api.finance.provisions.provision.provision_repository import ProvisionRepository
from app.api.finance.provisions.provision.provision_schema import (
    ProvisionAccessRequest,
    ProvisionActionRequest,
    ProvisionCreateRequest,
    ProvisionDocumentRequest,
    ProvisionDocumentUpdateRequest,
    ProvisionUpdateRequest,
)
from app.models.finance.provision_model import (
    Provision,
    ProvisionAccess,
    ProvisionDocument,
    ProvisionStatusHistory,
)
from app.api.storage.constants import (
    PROVISION_DOCUMENT_ENTITY_TYPE,
    PROVISION_ENTITY_TYPE,
)
from app.core.db.integrity import raise_integrity_error
from app.core.exceptions import ConflictError
from app.models.storage import Attachment


MONEY_QUANTIZER = Decimal("0.01")


class ProvisionService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = ProvisionRepository(db)

    # =====================================================
    # PROVISION STATUS
    # =====================================================
    def get_provision_statuses(
        self,
        search: str | None = None,
    ):
        return self.repository.get_provision_statuses(search=search)

    def _get_status_or_500(self, code: str):
        status_record = self.repository.get_provision_status_by_code(code)

        if not status_record:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Estado de provision no configurado: {code}",
            )

        return status_record

    # =====================================================
    # CREATE / UPDATE
    # =====================================================
    def create_provision(
        self,
        request: ProvisionCreateRequest,
        user_id: UUID,
    ):
        ticket_code = request.ticket_code.strip()
        access_user_ids = [item.user_id for item in request.access]
        if len(access_user_ids) != len(set(access_user_ids)):
            raise ConflictError(
                "No se puede repetir el mismo usuario en los accesos"
            )

        if self.repository.get_provision_by_ticket(
            request.company_id,
            ticket_code,
        ):
            raise ConflictError(
                "Ya existe una provision con este codigo para la empresa"
            )

        try:
            initial_status = self._get_status_or_500(PENDING_DETAIL_STATUS)

            provision = Provision(
                ticket_code=ticket_code,
                description=request.description,
                supplier_tax_id=request.supplier_tax_id,
                supplier_name=request.supplier_name,
                concept_id=request.concept_id,
                status_id=initial_status.id,
                area_id=request.area_id,
                currency_id=request.currency_id,
                company_id=request.company_id,
                amount=request.amount,
                provision_date=request.provision_date,
                observations=request.observations,
                created_by=user_id,
            )

            self.repository.create_provision(provision)

            documents = self._build_documents(
                provision_id=provision.id,
                document_requests=request.documents,
                user_id=user_id,
            )

            self.repository.create_provision_documents(documents)
            self._create_document_attachments(request.documents, documents, user_id)
            self._create_access_grants(provision.id, request.access, user_id)

            self._add_history(
                provision=provision,
                status_id=initial_status.id,
                user_id=user_id,
                comments="Creacion inicial",
            )

            self.repository.commit()

            return provision

        except HTTPException:
            self.repository.rollback()
            raise
        except IntegrityError as exc:
            self.repository.rollback()
            raise_integrity_error(
                exc,
                conflicts={
                    "provisions_company_id_ticket_code_key": (
                        "Ya existe una provision con este codigo para la empresa"
                    ),
                    "uq_provision_access_user": (
                        "Uno de los usuarios ya tiene acceso a la provision"
                    ),
                },
                invalid_references={
                    "provisions_company_id_fkey": "La empresa indicada no existe",
                    "provisions_concept_id_fkey": "El concepto indicado no existe",
                    "provisions_area_id_fkey": "El area indicada no existe",
                    "provisions_currency_id_fkey": "La moneda indicada no existe",
                    "provision_access_user_id_fkey": (
                        "Uno de los usuarios de acceso no existe"
                    ),
                    "provision_documents_currency_id_fkey": (
                        "La moneda de uno de los documentos no existe"
                    ),
                },
                default_message="No se pudo crear la provision",
            )
        except Exception as exc:
            self.repository.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No se pudo crear la provision",
            ) from exc

    def update_provision(
        self,
        provision_id: UUID,
        request: ProvisionUpdateRequest,
        user_id: UUID,
        can_edit_all: bool = False,
    ):
        provision = self._get_or_404(provision_id)
        self._ensure_can_edit_access(provision, user_id, can_edit_all)

        if not self._can_edit(provision):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La provision no se puede editar en su estado actual",
            )

        for field, value in request.model_dump(exclude_unset=True).items():
            setattr(provision, field, value)

        provision.updated_by = user_id
        try:
            self.repository.update_provision(provision)
            self.repository.commit()
        except IntegrityError as exc:
            self.repository.rollback()
            raise_integrity_error(
                exc,
                invalid_references={
                    "provisions_concept_id_fkey": "El concepto indicado no existe",
                    "provisions_area_id_fkey": "El area indicada no existe",
                    "provisions_currency_id_fkey": "La moneda indicada no existe",
                },
                default_message="No se pudo actualizar la provision",
            )

        return provision

    def add_document(
        self,
        provision_id: UUID,
        request: ProvisionDocumentRequest,
        user_id: UUID,
        can_edit_all: bool = False,
    ):
        provision = self._get_or_404(provision_id)
        self._ensure_can_edit_access(provision, user_id, can_edit_all)

        if not self._can_edit(provision):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se pueden agregar documentos en el estado actual",
            )

        document = self._build_document(provision.id, request, user_id)
        try:
            self.repository.create_provision_documents([document])
            self._create_document_attachments([request], [document], user_id)
            self.repository.commit()
        except IntegrityError as exc:
            self.repository.rollback()
            raise_integrity_error(
                exc,
                invalid_references={
                    "provision_documents_currency_id_fkey": (
                        "La moneda indicada no existe"
                    )
                },
                default_message="No se pudo agregar el documento",
            )

        return self._document_response(document)

    def update_document(
        self,
        document_id: UUID,
        request: ProvisionDocumentUpdateRequest,
        user_id: UUID,
        can_edit_all: bool = False,
    ):
        document = self._get_document_or_404(document_id)
        provision = document.provision

        self._ensure_can_edit_access(provision, user_id, can_edit_all)

        if not self._can_edit(provision):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se puede editar el documento en el estado actual",
            )

        for field, value in request.model_dump(exclude_unset=True).items():
            setattr(document, field, value)

        document.updated_by = user_id
        try:
            self.repository.update_provision_document(document)
            self.repository.commit()
        except IntegrityError as exc:
            self.repository.rollback()
            raise_integrity_error(
                exc,
                invalid_references={
                    "provision_documents_currency_id_fkey": (
                        "La moneda indicada no existe"
                    )
                },
                default_message="No se pudo actualizar el documento",
            )

        return self._document_response(document)

    def delete_document(
        self,
        document_id: UUID,
        user_id: UUID,
        can_edit_all: bool = False,
    ):
        document = self._get_document_or_404(document_id)
        provision = document.provision

        self._ensure_can_edit_access(provision, user_id, can_edit_all)

        if not self._can_edit(provision):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se puede eliminar el documento en el estado actual",
            )

        self.repository.delete_provision_document(document)
        self.repository.commit()

        return True

    def grant_access(
        self,
        provision_id: UUID,
        request: ProvisionAccessRequest,
        user_id: UUID,
        can_edit_all: bool = False,
    ):
        provision = self._get_or_404(provision_id)
        self._ensure_can_edit_access(provision, user_id, can_edit_all)

        existing_access = self.repository.get_provision_access(
            provision.id,
            request.user_id,
        )
        if existing_access:
            existing_access.access_type = request.access_type
            existing_access.active = True
            existing_access.updated_by = user_id
            self.repository.commit()
            return existing_access

        access = ProvisionAccess(
            provision_id=provision.id,
            user_id=request.user_id,
            access_type=request.access_type,
            active=True,
            created_by=user_id,
        )

        try:
            self.repository.create_provision_access([access])
            self.repository.commit()
        except IntegrityError as exc:
            self.repository.rollback()
            raise_integrity_error(
                exc,
                conflicts={
                    "uq_provision_access_user": (
                        "El usuario ya tiene acceso a la provision"
                    )
                },
                invalid_references={
                    "provision_access_user_id_fkey": "El usuario indicado no existe"
                },
                default_message="No se pudo registrar el acceso",
            )

        return access

    # =====================================================
    # QUERIES
    # =====================================================
    def get_document(
        self,
        document_id: UUID,
        user_id: UUID,
        can_view_all: bool = False,
    ):
        document = self._get_document_or_404(document_id)
        provision = document.provision

        if not can_view_all and not self._can_view(provision, user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes acceso a este documento",
            )

        return self._document_response(document)

    def get_provision(
        self,
        provision_id: UUID,
        user_id: UUID | None = None,
        can_view_all: bool = False,
    ):
        provision = self._get_or_404(provision_id)

        if not can_view_all and not self._can_view(provision, user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes acceso a esta provision",
            )

        return self.to_detail_response(provision)

    def get_provisions(
        self,
        search: str | None = None,
        status_id: int | None = None,
        area_id: int | None = None,
        company_id: int | None = None,
        user_id: UUID | None = None,
    ):
        provisions = self.repository.get_provisions(
            search=search,
            status_id=status_id,
            area_id=area_id,
            company_id=company_id,
            user_id=user_id,
        )

        return [self.to_summary_response(provision) for provision in provisions]

    def get_review_queue(
        self,
        area_id: int | None = None,
        company_id: int | None = None,
    ):
        provisions = self.repository.get_provisions(
            status_codes=[READY_FOR_REVIEW_STATUS],
            area_id=area_id,
            company_id=company_id,
            review_queue=True,
        )

        return [self.to_summary_response(provision) for provision in provisions]

    # =====================================================
    # STATE TRANSITIONS
    # =====================================================
    def submit_for_review(
        self,
        provision_id: UUID,
        request: ProvisionActionRequest,
        user_id: UUID,
        can_edit_all: bool = False,
    ):
        provision = self._get_or_404(provision_id)
        self._ensure_can_edit_access(provision, user_id, can_edit_all)

        if not provision.documents:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Agrega al menos un documento antes de enviar a revision",
            )

        return self._transition(
            provision=provision,
            status_code=READY_FOR_REVIEW_STATUS,
            user_id=user_id,
            comments=request.comments or "Provision lista para revision",
            submitted=True,
        )

    def approve(
        self,
        provision_id: UUID,
        request: ProvisionActionRequest,
        user_id: UUID,
    ):
        return self._transition_review(
            provision_id=provision_id,
            status_code=APPROVED_STATUS,
            user_id=user_id,
            comments=request.comments or "Provision aprobada",
            close=True,
        )

    def reject_for_edit(
        self,
        provision_id: UUID,
        request: ProvisionActionRequest,
        user_id: UUID,
    ):
        return self._transition_review(
            provision_id=provision_id,
            status_code=REJECTED_FOR_EDIT_STATUS,
            user_id=user_id,
            comments=request.comments or "Provision observada para correccion",
        )

    def reject_final(
        self,
        provision_id: UUID,
        request: ProvisionActionRequest,
        user_id: UUID,
    ):
        return self._transition_review(
            provision_id=provision_id,
            status_code=REJECTED_FINAL_STATUS,
            user_id=user_id,
            comments=request.comments or "Provision rechazada definitivamente",
            close=True,
        )

    def cancel(
        self,
        provision_id: UUID,
        request: ProvisionActionRequest,
        user_id: UUID,
        can_edit_all: bool = False,
    ):
        provision = self._get_or_404(provision_id)
        self._ensure_can_edit_access(provision, user_id, can_edit_all)

        return self._transition(
            provision=provision,
            status_code=CANCELLED_STATUS,
            user_id=user_id,
            comments=request.comments or "Provision cancelada",
            close=True,
        )

    # =====================================================
    # DELETE PROVISION (SOFT DELETE)
    # =====================================================
    def delete_provision(
        self,
        provision_id: UUID,
    ):
        try:
            provision = self._get_or_404(provision_id)
            provision.active = False
            self.repository.update_provision(provision)
            self.repository.commit()

            return True

        except Exception as e:
            self.repository.rollback()
            raise e

    # =====================================================
    # HELPERS
    # =====================================================
    def _get_or_404(self, provision_id: UUID) -> Provision:
        provision = self.repository.get_provision(provision_id)

        if not provision:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Provision no encontrada",
            )

        return provision

    def _get_document_or_404(self, document_id: UUID) -> ProvisionDocument:
        document = self.repository.get_provision_document(document_id)

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Documento de provision no encontrado",
            )

        return document

    def _can_edit(self, provision: Provision) -> bool:
        return provision.status.code in {
            PENDING_DETAIL_STATUS,
            REJECTED_FOR_EDIT_STATUS,
        }

    def _can_view(
        self,
        provision: Provision,
        user_id: UUID | None,
    ) -> bool:
        if user_id is None:
            return False

        if provision.created_by == user_id:
            return True

        return any(
            access.active and access.user_id == user_id
            for access in provision.access_grants
        )

    def _can_edit_access(
        self,
        provision: Provision,
        user_id: UUID | None,
    ) -> bool:
        if user_id is None:
            return False

        if provision.created_by == user_id:
            return True

        return any(
            access.active
            and access.user_id == user_id
            and access.access_type in {"editor", "reviewer", "approver"}
            for access in provision.access_grants
        )

    def _ensure_can_edit_access(
        self,
        provision: Provision,
        user_id: UUID,
        can_edit_all: bool,
    ):
        if can_edit_all:
            return

        if self._can_edit_access(provision, user_id):
            return

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para editar esta provision",
        )

    def ensure_entity_access(
        self,
        entity_type: str,
        entity_id: UUID,
        user_id: UUID,
        *,
        write: bool = False,
        can_view_all: bool = False,
        can_edit_all: bool = False,
    ) -> None:
        if entity_type == PROVISION_ENTITY_TYPE:
            provision = self._get_or_404(entity_id)
        elif entity_type == PROVISION_DOCUMENT_ENTITY_TYPE:
            provision = self._get_document_or_404(entity_id).provision
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tipo de entidad no soportado para archivos",
            )

        if write:
            self._ensure_can_edit_access(provision, user_id, can_edit_all)
            if not self._can_edit(provision):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "No se pueden modificar archivos "
                        "en el estado actual de la provision"
                    ),
                )
            return

        if not can_view_all and not self._can_view(provision, user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos para ver esta provision",
            )

    def _build_documents(
        self,
        provision_id: UUID,
        document_requests: list[ProvisionDocumentRequest],
        user_id: UUID,
    ):
        return [
            self._build_document(provision_id, document_request, user_id)
            for document_request in document_requests
        ]

    def _build_document(
        self,
        provision_id: UUID,
        request: ProvisionDocumentRequest,
        user_id: UUID,
    ):
        return ProvisionDocument(
            provision_id=provision_id,
            document_type=request.document_type,
            document_number=request.document_number,
            document_date=request.document_date,
            description=request.description,
            supplier_tax_id=request.supplier_tax_id,
            supplier_name=request.supplier_name,
            amount=request.amount,
            currency_id=request.currency_id,
            created_by=user_id,
        )

    def _create_document_attachments(
        self,
        document_requests: list[ProvisionDocumentRequest],
        documents: list[ProvisionDocument],
        user_id: UUID,
    ):
        attachments = []

        for index, item in enumerate(document_requests):
            document = documents[index]

            for attachment_item in item.attachments:
                attachments.append(
                    Attachment(
                        entity_type=PROVISION_DOCUMENT_ENTITY_TYPE,
                        entity_id=document.id,
                        file_name=attachment_item.file_name,
                        file_extension=attachment_item.file_extension,
                        mime_type=attachment_item.mime_type,
                        storage_type=attachment_item.storage_type,
                        file_size=attachment_item.file_size,
                        file_path=attachment_item.file_path,
                        file_base64=attachment_item.file_base64,
                        created_by=user_id,
                    )
                )

        if attachments:
            self.repository.create_attachments(attachments)

    def _create_access_grants(
        self,
        provision_id: UUID,
        access_requests: list[ProvisionAccessRequest],
        user_id: UUID,
    ):
        access_items = [
            ProvisionAccess(
                provision_id=provision_id,
                user_id=item.user_id,
                access_type=item.access_type,
                active=True,
                created_by=user_id,
            )
            for item in access_requests
        ]

        if access_items:
            self.repository.create_provision_access(access_items)

    def _add_history(
        self,
        provision: Provision,
        status_id: int,
        user_id: UUID,
        comments: str | None,
    ):
        self.repository.create_status_history(
            ProvisionStatusHistory(
                provision_id=provision.id,
                status_id=status_id,
                changed_by_user_id=user_id,
                comments=comments,
            )
        )

    def _transition_review(
        self,
        provision_id: UUID,
        status_code: str,
        user_id: UUID,
        comments: str | None,
        close: bool = False,
    ):
        provision = self._get_or_404(provision_id)

        if provision.status.code != READY_FOR_REVIEW_STATUS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Solo se pueden revisar provisiones listas para revision",
            )

        return self._transition(
            provision=provision,
            status_code=status_code,
            user_id=user_id,
            comments=comments,
            reviewed=True,
            close=close,
        )

    def _transition(
        self,
        provision: Provision,
        status_code: str,
        user_id: UUID,
        comments: str | None = None,
        submitted: bool = False,
        reviewed: bool = False,
        close: bool = False,
    ):
        target_status = self._get_status_or_500(status_code)
        now = datetime.utcnow()

        provision.status_id = target_status.id
        provision.updated_by = user_id

        if submitted:
            provision.submitted_at = now

        if reviewed:
            provision.reviewed_by_user_id = user_id
            provision.reviewed_at = now

        if close:
            provision.closed_at = now

        self.repository.update_provision(provision)
        self._add_history(provision, target_status.id, user_id, comments)
        self.repository.commit()

        return self.to_detail_response(provision)

    def _actual_amount(self, provision: Provision) -> Decimal:
        actual_base = self._actual_amount_base(provision)
        provision_rate = self._exchange_rate_to_base(provision.currency)

        return self._money(actual_base / provision_rate)

    def _expected_amount_base(self, provision: Provision) -> Decimal:
        return self._money(
            (provision.amount or Decimal("0"))
            * self._exchange_rate_to_base(provision.currency)
        )

    def _actual_amount_base(self, provision: Provision) -> Decimal:
        return self._money(
            sum(
                (
                    (document.amount or Decimal("0"))
                    * self._exchange_rate_to_base(document.currency)
                    for document in provision.documents
                ),
                Decimal("0"),
            )
        )

    def _document_amount_base(self, document: ProvisionDocument) -> Decimal:
        return self._money(
            (document.amount or Decimal("0"))
            * self._exchange_rate_to_base(document.currency)
        )

    def _exchange_rate_to_base(self, currency) -> Decimal:
        if not currency or currency.exchange_rate_to_base is None:
            return Decimal("1")

        rate = Decimal(str(currency.exchange_rate_to_base))
        if rate <= 0:
            return Decimal("1")

        return rate

    def _money(self, value: Decimal) -> Decimal:
        return Decimal(value).quantize(MONEY_QUANTIZER, rounding=ROUND_HALF_UP)

    def _document_response(self, document: ProvisionDocument) -> dict:
        return {
            "id": document.id,
            "document_type": document.document_type,
            "document_number": document.document_number,
            "document_date": document.document_date,
            "description": document.description,
            "supplier_tax_id": document.supplier_tax_id,
            "supplier_name": document.supplier_name,
            "amount": document.amount,
            "currency_id": document.currency_id,
            "exchange_rate_to_base": self._exchange_rate_to_base(document.currency),
            "amount_base": self._document_amount_base(document),
        }

    def _variance_status(
        self,
        expected_amount: Decimal,
        actual_amount: Decimal,
    ) -> str:
        if actual_amount > expected_amount:
            return "EXCEDENTE"

        if actual_amount < expected_amount:
            return "INFERIOR"

        return "EXACTO"

    def to_summary_response(self, provision: Provision) -> dict:
        expected_amount = self._money(provision.amount or Decimal("0"))
        actual_amount = self._actual_amount(provision)
        variance_amount = actual_amount - expected_amount
        expected_amount_base = self._expected_amount_base(provision)
        actual_amount_base = self._actual_amount_base(provision)
        variance_amount_base = actual_amount_base - expected_amount_base

        return {
            "id": provision.id,
            "ticket_code": provision.ticket_code,
            "description": provision.description,
            "supplier_tax_id": provision.supplier_tax_id,
            "supplier_name": provision.supplier_name,
            "status_id": provision.status_id,
            "concept_id": provision.concept_id,
            "area_id": provision.area_id,
            "currency_id": provision.currency_id,
            "currency_code": provision.currency.code if provision.currency else None,
            "base_currency_code": BASE_CURRENCY_CODE,
            "company_id": provision.company_id,
            "expected_amount": expected_amount,
            "actual_amount": actual_amount,
            "variance_amount": self._money(variance_amount),
            "expected_amount_base": expected_amount_base,
            "actual_amount_base": actual_amount_base,
            "variance_amount_base": self._money(variance_amount_base),
            "variance_status": self._variance_status(
                expected_amount_base,
                actual_amount_base,
            ),
            "provision_date": provision.provision_date,
            "observations": provision.observations,
            "submitted_at": provision.submitted_at,
            "reviewed_at": provision.reviewed_at,
            "closed_at": provision.closed_at,
        }

    def to_detail_response(self, provision: Provision) -> dict:
        data = self.to_summary_response(provision)
        data["documents"] = [
            self._document_response(document)
            for document in provision.documents
        ]
        data["access"] = [
            access for access in provision.access_grants if access.active
        ]

        return data
