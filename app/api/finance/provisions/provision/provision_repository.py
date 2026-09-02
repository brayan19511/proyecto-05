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
from app.core.scope import UserScope, scope_condition
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
        scope: UserScope | None = None,
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

        # Alcance por empresa/area. None = sin restriccion (admin o *_all);
        # vacio = el usuario no tiene alcance configurado y se ignora, para no
        # romper a quienes todavia no lo tienen asignado.
        area_condition = None
        if scope is not None and not scope.is_empty:
            area_condition = scope_condition(Provision, scope)

        if review_queue or user_id is None:
            # Sin restriccion por autoria (revisor o "ve todo"): queda solo el
            # limite por empresa/area, si corresponde.
            if area_condition is not None:
                query = query.filter(area_condition)

        else:
            # Visibilidad: lo propio, lo compartido explicitamente y, si el
            # usuario tiene alcance por area, todo lo de sus areas.
            visibility = [
                Provision.created_by == user_id,
                ProvisionAccess.user_id == user_id,
            ]

            if area_condition is not None:
                visibility.append(area_condition)

            query = (
                query.outerjoin(
                    ProvisionAccess,
                    ProvisionAccess.provision_id == Provision.id,
                )
                .filter(or_(*visibility))
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

    def get_provision_by_ticket(
        self,
        company_id: int,
        ticket_code: str,
    ):
        return (
            self.db.query(Provision)
            .filter(
                Provision.company_id == company_id,
                Provision.ticket_code == ticket_code,
            )
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

    def get_provision_access(
        self,
        provision_id: UUID,
        user_id: UUID,
    ):
        return (
            self.db.query(ProvisionAccess)
            .filter(
                ProvisionAccess.provision_id == provision_id,
                ProvisionAccess.user_id == user_id,
            )
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
