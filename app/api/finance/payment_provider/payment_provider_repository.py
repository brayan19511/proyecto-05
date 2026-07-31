from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.finance.payment_provider_model import PaymentProvider


class PaymentProviderRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_providers(self, search: str | None = None, active: bool | None = None):
        query = self.db.query(PaymentProvider)
        if active is not None:
            query = query.filter(PaymentProvider.active == active)
        if search:
            pattern = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    PaymentProvider.tax_id.ilike(pattern),
                    PaymentProvider.legal_name.ilike(pattern),
                )
            )
        return query.order_by(PaymentProvider.legal_name).all()

    def get_provider(self, provider_id):
        return self.db.get(PaymentProvider, provider_id)

    def get_provider_by_tax_id(self, tax_id: str):
        return (
            self.db.query(PaymentProvider)
            .filter(PaymentProvider.tax_id == tax_id)
            .first()
        )

    def list_active_providers(self):
        return (
            self.db.query(PaymentProvider)
            .filter(PaymentProvider.active.is_(True))
            .order_by(PaymentProvider.legal_name)
            .all()
        )

    def add(self, entity):
        self.db.add(entity)
        return entity

    def commit(self):
        self.db.commit()

    def rollback(self):
        self.db.rollback()
