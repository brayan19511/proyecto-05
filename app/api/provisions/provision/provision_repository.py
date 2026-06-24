# provision_repository.py

from uuid import UUID

from sqlalchemy.orm import Session, selectinload
from sqlalchemy import or_

from app.models.finance.provision_model import (
    Provision,
    ProvisionAccess,
    ProvisionDocument,
    ProvisionStatus,
    ProvisionStatusHistory,
)

from app.api.storage.constants import PROVISION_DOCUMENT_ENTITY_TYPE
from app.models.storage import Attachment


class ProvisionRepository:

    def __init__(self, db: Session):
        self.db = db

    # =====================================================
    # PROVISION STATUS
    # =====================================================

    def get_provision_statuses(
        self,
        search: str | None = None
    ):

        query = self.db.query(ProvisionStatus)

        if search:
            query = query.filter(
                ProvisionStatus.name.contains(search)
            )

        return query.all()

    def get_provision_status(
        self,
        status_id: int
    ):

        return (
            self.db.query(ProvisionStatus)
            .filter(ProvisionStatus.id == status_id)
            .first()
        )

    def get_provision_status_by_code(
        self,
        code: str,
    ):

        return (
            self.db.query(ProvisionStatus)
            .filter(ProvisionStatus.code == code)
            .first()
        )

    def create_provision_status(
        self,
        provision_status: ProvisionStatus
    ):

        self.db.add(provision_status)
        self.db.flush()

        return provision_status

    def update_provision_status(
        self,
        existing_status: ProvisionStatus
    ):

        self.db.flush()
        return existing_status

    # =====================================================
    # PROVISION
    # =====================================================

    def get_provisions(
        self,
        search: str | None = None,
        status_id: int | None = None,
        status_codes: list[str] | None = None,
        area_id: int | None = None,
        company_id: int | None = None,
        user_id=None,
        review_queue: bool = False,
    ):

        query = self.db.query(Provision).options(
            selectinload(Provision.currency),
            selectinload(Provision.documents).selectinload(ProvisionDocument.currency),
        )

        if search:
            query = query.filter(
                Provision.ticket_code.contains(search)
            )

        if status_id is not None:
            query = query.filter(
                Provision.status_id == status_id
            )

        if status_codes:
            query = (
                query.join(ProvisionStatus)
                .filter(ProvisionStatus.code.in_(status_codes))
            )

        if area_id is not None:
            query = query.filter(
                Provision.area_id == area_id
            )

        if company_id is not None:
            query = query.filter(
                Provision.company_id == company_id
            )

        if user_id is not None and not review_queue:
            query = (
                query.outerjoin(
                    ProvisionAccess,
                    ProvisionAccess.provision_id == Provision.id,
                )
                .filter(
                    or_(
                        Provision.created_by == user_id,
                        ProvisionAccess.user_id == user_id,
                    )
                )
                .distinct()
            )

        return query.all()

    def get_provision(
        self,
        provision_id: UUID
    ):

        return (
            self.db.query(Provision)
            .options(
                selectinload(Provision.currency),
                selectinload(Provision.documents).selectinload(
                    ProvisionDocument.currency,
                ),
                selectinload(Provision.access_grants),
            )
            .filter(Provision.id == provision_id)
            .first()
        )

    def create_provision(
        self,
        provision: Provision
    ):

        self.db.add(provision)
        self.db.flush()

        return provision

    def update_provision(
        self,
        provision: Provision
    ):

        self.db.flush()
        return provision

    # =====================================================
    # PROVISION DOCUMENT
    # =====================================================

    def create_provision_documents(
        self,
        documents: list[ProvisionDocument]
    ):

        self.db.add_all(documents)
        self.db.flush()

        return documents

    def get_provision_document(
        self,
        document_id: UUID
    ):

        return (
            self.db.query(ProvisionDocument)
            .options(
                selectinload(ProvisionDocument.currency),
                selectinload(ProvisionDocument.provision).selectinload(
                    Provision.currency,
                ),
            )
            .filter(ProvisionDocument.id == document_id)
            .first()
        )

    def update_provision_document(
        self,
        document: ProvisionDocument,
    ):

        self.db.flush()
        return document

    def delete_provision_document(
        self,
        document: ProvisionDocument,
    ):

        (
            self.db.query(Attachment)
            .filter(
                Attachment.entity_type == PROVISION_DOCUMENT_ENTITY_TYPE,
                Attachment.entity_id == document.id,
            )
            .delete(synchronize_session=False)
        )
        self.db.delete(document)
        self.db.flush()

    def create_provision_access(
        self,
        access_items: list[ProvisionAccess],
    ):

        self.db.add_all(access_items)
        self.db.flush()

        return access_items

    # =====================================================
    # ATTACHMENTS
    # =====================================================

    def create_attachments(
        self,
        attachments: list[Attachment]
    ):

        self.db.add_all(attachments)
        self.db.flush()

    # =====================================================
    # STATUS HISTORY
    # =====================================================

    def create_status_history(
        self,
        history: ProvisionStatusHistory
    ):

        self.db.add(history)
        self.db.flush()

    # =====================================================
    # TRANSACTION
    # =====================================================

    def commit(self):
        self.db.commit()

    def rollback(self):
        self.db.rollback()
