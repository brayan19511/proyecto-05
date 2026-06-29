from dataclasses import dataclass

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.sales_channel.sku_repository import SkuRepository
from app.api.sales_channel.sku_schema import (
    ActiveSkuSnapshotRequest,
    BulkSkuSyncRequest,
    PromoSkuCreateRequest,
    SkuCreateRequest,
    SkuUpdateRequest,
)
from app.core.exceptions import ConflictError, NotFoundError


@dataclass(frozen=True)
class SkuModelConfig:
    model: type
    external_id_field: str
    updated_at_field: str
    channel_name: str
    promotion_model: type | None = None


class ManagedSkuService:
    def __init__(self, db: Session, config: SkuModelConfig):
        self.config = config
        self.repository = SkuRepository(
            db,
            config.model,
            config.external_id_field,
        )

    def list(self, search: str | None = None, active: bool | None = None):
        promotion_skus = self._get_promotion_skus()
        return [
            self._serialize(entity, promotion_skus)
            for entity in self.repository.list(search, active)
        ]

    def get(self, sku: str):
        return self._serialize_one(self._get_or_raise(sku))

    def create(self, request: SkuCreateRequest):
        if self.repository.get(request.sku):
            raise ConflictError(
                f"El SKU {request.sku} ya existe en {self.config.channel_name}"
            )

        entity = self.config.model(
            sku=request.sku,
            is_active=True,
            **{self.config.external_id_field: request.external_id},
        )
        self.repository.add(entity)
        self._commit(entity)
        return self._serialize_one(entity)

    def update(self, sku: str, request: SkuUpdateRequest):
        entity = self._get_or_raise(sku)
        data = request.model_dump(exclude_unset=True)
        if "external_id" in data:
            setattr(
                entity,
                self.config.external_id_field,
                data["external_id"],
            )
        self._touch(entity)
        self._commit(entity)
        return self._serialize_one(entity)

    def set_active(self, sku: str, active: bool):
        entity = self._get_or_raise(sku)
        entity.is_active = active
        self._touch(entity)
        self._commit(entity)
        return self._serialize_one(entity)

    def bulk_sync(self, request: BulkSkuSyncRequest) -> dict:
        existing_entities = self.repository.list()
        existing_by_sku = {
            entity.sku.casefold(): entity
            for entity in existing_entities
        }
        received_skus = {item.sku.casefold() for item in request.items}
        result = {
            "received": len(request.items),
            "created": 0,
            "activated": 0,
            "deactivated": 0,
            "unchanged": 0,
            "missing": [],
        }

        for item in request.items:
            entity = existing_by_sku.get(item.sku.casefold())
            if entity is None:
                if not request.create_missing:
                    result["missing"].append(item.sku)
                    continue
                entity = self.config.model(
                    sku=item.sku,
                    is_active=item.active,
                    **{self.config.external_id_field: None},
                )
                self.repository.add(entity)
                existing_by_sku[item.sku.casefold()] = entity
                result["created"] += 1
                continue

            current_active = bool(entity.is_active)
            if current_active == item.active:
                result["unchanged"] += 1
                continue

            entity.is_active = item.active
            self._touch(entity)
            if item.active:
                result["activated"] += 1
            else:
                result["deactivated"] += 1

        if request.deactivate_missing:
            for normalized_sku, entity in existing_by_sku.items():
                if normalized_sku in received_skus or not bool(entity.is_active):
                    continue
                entity.is_active = False
                self._touch(entity)
                result["deactivated"] += 1

        try:
            self.repository.commit()
        except IntegrityError as exc:
            self.repository.rollback()
            raise ConflictError(
                f"No se pudo sincronizar la lista de {self.config.channel_name}"
            ) from exc

        return result

    def apply_active_snapshot(
        self,
        request: ActiveSkuSnapshotRequest,
    ) -> dict:
        return self.bulk_sync(
            BulkSkuSyncRequest(
                items=[
                    {"sku": sku, "active": True}
                    for sku in request.skus
                ],
                create_missing=request.create_missing,
                deactivate_missing=True,
            )
        )

    def _get_or_raise(self, sku: str):
        entity = self.repository.get(sku)
        if not entity:
            raise NotFoundError(
                f"El SKU {sku} no existe en {self.config.channel_name}"
            )
        return entity

    def _touch(self, entity) -> None:
        setattr(entity, self.config.updated_at_field, func.getdate())

    def _commit(self, entity) -> None:
        try:
            self.repository.commit()
            self.repository.refresh(entity)
        except IntegrityError as exc:
            self.repository.rollback()
            raise ConflictError(
                f"No se pudo guardar el SKU en {self.config.channel_name}"
            ) from exc

    def _get_promotion_skus(self) -> set[str] | None:
        if self.config.promotion_model is None:
            return None
        return {
            sku.casefold()
            for sku in self.repository.list_skus(self.config.promotion_model)
        }

    def _serialize(
        self,
        entity,
        promotion_skus: set[str] | None = None,
    ) -> dict:
        result = {
            "sku": entity.sku,
            "external_id": getattr(entity, self.config.external_id_field),
            "is_active": bool(entity.is_active),
            "created_at": entity.created_at,
            "updated_at": getattr(entity, self.config.updated_at_field),
        }
        if promotion_skus is not None:
            result["has_promotion"] = entity.sku.casefold() in promotion_skus
        return result

    def _serialize_one(self, entity) -> dict:
        if self.config.promotion_model is None:
            return self._serialize(entity)

        has_promotion = self.repository.sku_exists(
            self.config.promotion_model,
            entity.sku,
        )
        promotion_skus = {entity.sku.casefold()} if has_promotion else set()
        return self._serialize(entity, promotion_skus)


class PromoSkuService:
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

    def _get_or_raise(self, sku: str):
        entity = self.repository.get(sku)
        if not entity:
            raise NotFoundError(
                f"El SKU promocional {sku} no existe en Peya"
            )
        return entity
