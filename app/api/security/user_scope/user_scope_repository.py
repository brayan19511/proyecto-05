# app/api/security/user_scope/user_scope_repository.py

from uuid import UUID

from sqlalchemy.orm import Session, joinedload

from app.models.auth.security_model import UserAreaAccess


class UserScopeRepository:

    def __init__(self, db: Session):
        self.db = db

    def _base_query(self):
        return self.db.query(UserAreaAccess).options(
            joinedload(UserAreaAccess.company),
            joinedload(UserAreaAccess.area),
        )

    def get_accesses(
        self,
        user_id: UUID | None = None,
        company_id: int | None = None,
        area_id: int | None = None,
        active: bool | None = True,
    ):
        query = self._base_query()

        if user_id is not None:
            query = query.filter(UserAreaAccess.user_id == user_id)

        if company_id is not None:
            query = query.filter(UserAreaAccess.company_id == company_id)

        if area_id is not None:
            query = query.filter(UserAreaAccess.area_id == area_id)

        if active is not None:
            query = query.filter(UserAreaAccess.active.is_(active))

        return query.order_by(
            UserAreaAccess.company_id,
            UserAreaAccess.area_id,
        ).all()

    def get_access_by_id(self, access_id: int):
        return (
            self._base_query()
            .filter(UserAreaAccess.id == access_id)
            .first()
        )

    def get_access(
        self,
        user_id: UUID,
        company_id: int,
        area_id: int | None,
    ):
        """Busca la fila exacta, activa o no (para poder reactivarla)."""
        query = self.db.query(UserAreaAccess).filter(
            UserAreaAccess.user_id == user_id,
            UserAreaAccess.company_id == company_id,
        )

        if area_id is None:
            query = query.filter(UserAreaAccess.area_id.is_(None))
        else:
            query = query.filter(UserAreaAccess.area_id == area_id)

        return query.first()

    def create_access(self, access: UserAreaAccess) -> UserAreaAccess:
        self.db.add(access)
        return access

    def commit(self):
        self.db.commit()

    def rollback(self):
        self.db.rollback()
