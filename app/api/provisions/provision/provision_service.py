# provision_service.py

from uuid import UUID

from sqlalchemy.orm import Session

from app.api.provisions.provision.provision_repository import ProvisionRepository
from app.api.provisions.provision.provision_schema import (
    ProvisionCreateRequest,
)

from app.models.finance.provision_model import (
    Provision,
    ProvisionDocument,
    ProvisionStatusHistory,
)

from app.models.master.master_model import Attachment




class ProvisionService:

    def __init__(self, db: Session):

        self.db = db
        self.repository = ProvisionRepository(db)

    # =====================================================
    # CREATE PROVISION
    # =====================================================

    def create_provision(
        self,
        request: ProvisionCreateRequest,
        user_id: int,
    ):

        try:

            # =============================================
            # CREATE PROVISION
            # =============================================

            provision = Provision(
                ticket_code=request.ticket_code,
                description=request.description,
                concept_id=request.concept_id,
                status_id=request.status_id,
                area_id=request.area_id,
                currency_id=request.currency_id,
                company_id=request.company_id,
                amount=request.amount,
                provision_date=request.provision_date,
                observations=request.observations,
                created_by=user_id,
            )

            self.repository.create_provision(provision)

            # =============================================
            # CREATE DOCUMENTS
            # =============================================

            documents_to_create = []

            attachments_to_create = []

            for item in request.documents:

                document = ProvisionDocument(
                    provision_id=provision.id,
                    document_type=item.document_type,
                    document_number=item.document_number,
                    supplier_tax_id=item.supplier_tax_id,
                    supplier_name=item.supplier_name,
                    amount=item.amount,
                    currency_id=item.currency_id,
                    created_by=user_id,
                )

                documents_to_create.append(document)

            self.repository.create_provision_documents(
                documents_to_create
            )

            # =============================================
            # CREATE ATTACHMENTS
            # =============================================

            for index, item in enumerate(request.documents):

                document = documents_to_create[index]

                for attachment_item in item.attachments:

                    attachment = Attachment(
                        entity_type="provision_document",
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

                    attachments_to_create.append(attachment)

            if attachments_to_create:

                self.repository.create_attachments(
                    attachments_to_create
                )

            # =============================================
            # CREATE STATUS HISTORY
            # =============================================

            history = ProvisionStatusHistory(
                provision_id=provision.id,
                status_id=request.status_id,
                changed_by_user_id=user_id,
                comments="Creación inicial",
            )

            self.repository.create_status_history(history)

            # =============================================
            # COMMIT
            # =============================================

            self.repository.commit()

            return provision

        except Exception as e:

            self.repository.rollback()
            raise e

    # =====================================================
    # GET PROVISION
    # =====================================================

    def get_provision(
        self,
        provision_id: UUID
    ):

        provision = self.repository.get_provision(
            provision_id
        )

        if not provision:
            raise Exception("Provision no encontrada")

        return provision

    # =====================================================
    # GET PROVISIONS
    # =====================================================

    def get_provisions(
        self,
        search: str | None = None,
        status_id: int | None = None,
        area_id: int | None = None,
        company_id: int | None = None,
    ):

        return self.repository.get_provisions(
            search=search,
            status_id=status_id,
            area_id=area_id,
            company_id=company_id,
        )

    # =====================================================
    # DELETE PROVISION (SOFT DELETE)
    # =====================================================

    def delete_provision(
        self,
        provision_id: UUID
    ):

        try:

            provision = self.repository.get_provision(
                provision_id
            )

            if not provision:
                raise Exception(
                    "Provision no encontrada"
                )

            provision.active = False

            self.repository.update_provision(
                provision
            )

            self.repository.commit()

            return True

        except Exception as e:

            self.repository.rollback()
            raise e