# provision_repository.py

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.finance.provision_model import (
    Provision,
    ProvisionDocument,
    ProvisionStatus,
    ProvisionStatusHistory,
)

from app.models.master.master_model import Attachment


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
        area_id: int | None = None,
        company_id: int | None = None,
    ):

        query = self.db.query(Provision)

        if search:
            query = query.filter(
                Provision.ticket_code.contains(search)
            )

        if status_id is not None:
            query = query.filter(
                Provision.status_id == status_id
            )

        if area_id is not None:
            query = query.filter(
                Provision.area_id == area_id
            )

        if company_id is not None:
            query = query.filter(
                Provision.company_id == company_id
            )

        return query.all()

    def get_provision(
        self,
        provision_id: UUID
    ):

        return (
            self.db.query(Provision)
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

    def get_provision_document(
        self,
        document_id: UUID
    ):

        return (
            self.db.query(ProvisionDocument)
            .filter(ProvisionDocument.id == document_id)
            .first()
        )

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