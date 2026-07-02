from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.sales_channel.peya.schemas import PromoSkuCreateRequest
from app.api.sales_channel.sku.repository import SkuRepository
from app.core.exceptions import ConflictError, NotFoundError


class PromoSkuService:
    """Manage Peya promotion membership, represented by presence in a table."""

    def __init__(self, db: Session, model: type, parent_model: type):
        self.model = model
        self.parent_model = parent_model
        self.repository = SkuRepository(db, model)

    def list(self, search: str | None = None):
        return self.repository.list(search)

    def get(self, sku: str):
        return self._get_or_raise(sku)

    def create(self, request: PromoSkuCreateRequest):
        if not self.repository.sku_exists(self.parent_model, request.sku):
            raise NotFoundError(
                f"El SKU {request.sku} no existe en el catalogo Peya"
            )

        if self.repository.get(request.sku):
            raise ConflictError(
                f"El SKU promocional {request.sku} ya existe en Peya"
            )

        entity = self.repository.add(self.model(sku=request.sku))
        try:
            self.repository.commit()
            self.repository.refresh(entity)
        except IntegrityError as exc:
            self.repository.rollback()
            raise ConflictError(
                f"No se pudo guardar el SKU promocional {request.sku}"
            ) from exc
        return entity

    def delete(self, sku: str) -> None:
        entity = self._get_or_raise(sku)
        self.repository.delete(entity)
        try:
            self.repository.commit()
        except IntegrityError as exc:
            self.repository.rollback()
            raise ConflictError(
                f"No se pudo eliminar el SKU promocional {sku}"
            ) from exc

    def sync_snapshot(
        self,
        skus: list[str],
        *,
        dry_run: bool = False,
    ) -> dict:
        existing = self.repository.list()
        existing_by_sku = {
            entity.sku.casefold(): entity
            for entity in existing
        }
        parent_skus = {
            sku.casefold()
            for sku in self.repository.list_skus(self.parent_model)
        }
        requested = {sku.casefold(): sku for sku in skus}
        missing = [
            sku
            for normalized, sku in requested.items()
            if normalized not in parent_skus
        ]
        additions = [
            sku
            for normalized, sku in requested.items()
            if normalized not in existing_by_sku
            and normalized in parent_skus
        ]
        removals = [
            entity
            for normalized, entity in existing_by_sku.items()
            if normalized not in requested
        ]
        result = {
            "received": len(skus),
            "promotions_added": len(additions),
            "promotions_removed": len(removals),
            "unchanged": len(skus) - len(additions) - len(missing),
            "missing": missing,
        }

        # Unknown parent SKU blocks the whole snapshot to prevent partial data.
        if missing or dry_run:
            self.repository.rollback()
            return result

        for sku in additions:
            self.repository.add(self.model(sku=sku))
        for entity in removals:
            self.repository.delete(entity)

        try:
            self.repository.commit()
        except IntegrityError as exc:
            self.repository.rollback()
            raise ConflictError(
                "No se pudo sincronizar el snapshot de promociones Peya"
            ) from exc
        return result

    def _get_or_raise(self, sku: str):
        entity = self.repository.get(sku)
        if not entity:
            raise NotFoundError(
                f"El SKU promocional {sku} no existe en Peya"
            )
        return entity
