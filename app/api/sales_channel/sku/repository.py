"""Persistence operations shared by all externally managed SKU tables."""

from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Session


class SkuRepository:
    def __init__(
        self,
        db: Session,
        model: type,
        external_id_field: str | None = None,
    ):
        self.db = db
        self.model = model
        self.external_id_field = external_id_field

    def list(self, search: str | None = None, active: bool | None = None):
        query = self.db.query(self.model)

        if search:
            search_value = f"%{search.strip()}%"
            filters = [self.model.sku.like(search_value)]
            if self.external_id_field:
                filters.append(
                    getattr(self.model, self.external_id_field).like(search_value)
                )
            query = query.filter(or_(*filters))

        if active is not None and hasattr(self.model, "is_active"):
            query = query.filter(self.model.is_active == active)

        return query.order_by(self.model.sku).all()

    def get(self, sku: str):
        return (
            self.db.query(self.model)
            .filter(self.model.sku == sku.strip())
            .first()
        )

    def list_skus(self, model: type) -> set[str]:
        return {
            sku
            for (sku,) in self.db.query(model.sku).all()
        }

    def sku_exists(self, model: type, sku: str) -> bool:
        return (
            self.db.query(model.sku)
            .filter(model.sku == sku.strip())
            .first()
            is not None
        )

    def add(self, entity: Any):
        self.db.add(entity)
        return entity

    def delete(self, entity: Any) -> None:
        self.db.delete(entity)

    def commit(self) -> None:
        self.db.commit()

    def rollback(self) -> None:
        self.db.rollback()

    def refresh(self, entity: Any) -> None:
        self.db.refresh(entity)
