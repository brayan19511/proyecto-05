from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.sales_channel.sku.repository import SkuRepository
from app.api.sales_channel.sku.schemas import (
    ActiveSkuSnapshotRequest,
    BulkSkuSyncRequest,
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
    external_id_matches_sku: bool = False


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
            **{
                self.config.external_id_field: self._resolve_external_id(
                    request.sku,
                    request.external_id,
                )
            },
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
                self._resolve_external_id(entity.sku, data["external_id"]),
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

    def bulk_sync(
        self,
        request: BulkSkuSyncRequest,
        *,
        dry_run: bool = False,
    ) -> dict:
        existing_entities = self.repository.list()
        existing_by_sku = {
            entity.sku.casefold(): entity
            for entity in existing_entities
        }
        received_skus = {item.sku.casefold() for item in request.items}
        # Ademas de los contadores, guardamos QUE SKUs cae en cada accion para
        # que el preview muestre el detalle (no solo el total).
        result = {
            "received": len(request.items),
            "created": 0,
            "activated": 0,
            "deactivated": 0,
            "unchanged": 0,
            "missing": [],
            "created_skus": [],
            "activated_skus": [],
            "deactivated_skus": [],
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
                    **{
                        self.config.external_id_field: (
                            self._resolve_external_id(item.sku, None)
                        )
                    },
                )
                self.repository.add(entity)
                existing_by_sku[item.sku.casefold()] = entity
                result["created"] += 1
                result["created_skus"].append(item.sku)
                continue

            self._sync_external_id(entity)
            current_active = bool(entity.is_active)
            if current_active == item.active:
                result["unchanged"] += 1
                continue

            entity.is_active = item.active
            self._touch(entity)
            if item.active:
                result["activated"] += 1
                result["activated_skus"].append(entity.sku)
            else:
                result["deactivated"] += 1
                result["deactivated_skus"].append(entity.sku)

        if request.deactivate_missing:
            for normalized_sku, entity in existing_by_sku.items():
                if normalized_sku in received_skus or not bool(entity.is_active):
                    continue
                entity.is_active = False
                self._touch(entity)
                result["deactivated"] += 1
                result["deactivated_skus"].append(entity.sku)

        try:
            if dry_run:
                self.repository.rollback()
            else:
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
        *,
        dry_run: bool = False,
    ) -> dict:
        return self.bulk_sync(
            BulkSkuSyncRequest(
                items=[
                    {"sku": sku, "active": True}
                    for sku in request.skus
                ],
                create_missing=request.create_missing,
                deactivate_missing=True,
            ),
            dry_run=dry_run,
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

    def _resolve_external_id(
        self,
        sku: str,
        requested_external_id: str | None,
    ) -> str | None:
        if not self.config.external_id_matches_sku:
            return requested_external_id

        normalized_sku = sku.strip()
        if (
            requested_external_id is not None
            and requested_external_id != normalized_sku
        ):
            raise ConflictError(
                f"En {self.config.channel_name}, el identificador externo "
                "debe ser igual al SKU"
            )
        return normalized_sku

    def _sync_external_id(self, entity) -> None:
        if not self.config.external_id_matches_sku:
            return

        current_external_id = getattr(entity, self.config.external_id_field)
        expected_external_id = self._resolve_external_id(entity.sku, None)
        if current_external_id != expected_external_id:
            setattr(
                entity,
                self.config.external_id_field,
                expected_external_id,
            )
            self._touch(entity)

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
