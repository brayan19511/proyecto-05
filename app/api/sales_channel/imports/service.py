"""Orchestrate XLSX parsing and domain synchronization for SKU imports."""

from fastapi import UploadFile

from app.api.sales_channel.imports.excel_reader import parse_sku_workbook
from app.api.sales_channel.imports.schemas import (
    SkuImportMode,
    SkuImportResponse,
)
from app.api.sales_channel.peya.promotion_service import PromoSkuService
from app.api.sales_channel.sku.schemas import (
    ActiveSkuSnapshotRequest,
    BulkSkuSyncRequest,
)
from app.api.sales_channel.sku.service import ManagedSkuService
from app.core.exceptions import ValidationError


class SkuExcelImportService:
    def preview_managed(
        self,
        upload: UploadFile,
        mode: SkuImportMode,
        create_missing: bool,
        service: ManagedSkuService,
    ) -> SkuImportResponse:
        return self._process_managed(
            upload,
            mode,
            create_missing,
            service,
            dry_run=True,
        )

    def import_managed(
        self,
        upload: UploadFile,
        mode: SkuImportMode,
        create_missing: bool,
        service: ManagedSkuService,
        expected_sha256: str | None = None,
    ) -> SkuImportResponse:
        return self._process_managed(
            upload,
            mode,
            create_missing,
            service,
            dry_run=False,
            expected_sha256=expected_sha256,
        )

    def _process_managed(
        self,
        upload: UploadFile,
        mode: SkuImportMode,
        create_missing: bool,
        service: ManagedSkuService,
        *,
        dry_run: bool,
        expected_sha256: str | None = None,
    ) -> SkuImportResponse:
        if mode == SkuImportMode.PROMOTION_SNAPSHOT:
            raise ValidationError(
                "promotion_snapshot solo se admite en promo-skus"
            )

        parsed = parse_sku_workbook(upload, mode)
        if expected_sha256 and parsed.sha256 != expected_sha256.casefold():
            return self._response(
                parsed,
                mode,
                preview=dry_run,
                errors=[
                    {
                        "message": (
                            "El archivo no coincide con el SHA-256 "
                            "confirmado en preview"
                        )
                    }
                ],
            )
        if parsed.errors:
            return self._response(
                parsed,
                mode,
                preview=dry_run,
                errors=parsed.errors,
            )

        if mode == SkuImportMode.ACTIVE_SNAPSHOT:
            result = service.apply_active_snapshot(
                ActiveSkuSnapshotRequest(
                    skus=[row["sku"] for row in parsed.rows],
                    create_missing=create_missing,
                ),
                dry_run=dry_run,
            )
        else:
            result = service.bulk_sync(
                BulkSkuSyncRequest(
                    items=parsed.rows,
                    create_missing=create_missing,
                    deactivate_missing=False,
                ),
                dry_run=dry_run,
            )

        return self._response(
            parsed,
            mode,
            preview=dry_run,
            result=result,
        )

    def preview_promotions(
        self,
        upload: UploadFile,
        service: PromoSkuService,
    ) -> SkuImportResponse:
        return self._process_promotions(upload, service, dry_run=True)

    def import_promotions(
        self,
        upload: UploadFile,
        service: PromoSkuService,
        expected_sha256: str | None = None,
    ) -> SkuImportResponse:
        return self._process_promotions(
            upload,
            service,
            dry_run=False,
            expected_sha256=expected_sha256,
        )

    def _process_promotions(
        self,
        upload: UploadFile,
        service: PromoSkuService,
        *,
        dry_run: bool,
        expected_sha256: str | None = None,
    ) -> SkuImportResponse:
        mode = SkuImportMode.PROMOTION_SNAPSHOT
        parsed = parse_sku_workbook(upload, mode)
        if expected_sha256 and parsed.sha256 != expected_sha256.casefold():
            return self._response(
                parsed,
                mode,
                preview=dry_run,
                errors=[
                    {
                        "message": (
                            "El archivo no coincide con el SHA-256 "
                            "confirmado en preview"
                        )
                    }
                ],
            )
        if parsed.errors:
            return self._response(
                parsed,
                mode,
                preview=dry_run,
                errors=parsed.errors,
            )

        result = service.sync_snapshot(
            [row["sku"] for row in parsed.rows],
            dry_run=dry_run,
        )
        missing_errors = [
            {
                "field": "sku",
                "message": f"El SKU {sku} no existe en el catalogo Peya",
            }
            for sku in result["missing"]
        ]
        return self._response(
            parsed,
            mode,
            preview=dry_run,
            result=result,
            errors=missing_errors,
        )

    @staticmethod
    def _response(
        parsed,
        mode: SkuImportMode,
        *,
        preview: bool,
        result: dict | None = None,
        errors: list | None = None,
    ) -> SkuImportResponse:
        result = result or {}
        errors = errors or []
        can_apply = not errors
        return SkuImportResponse(
            filename=parsed.filename,
            sha256=parsed.sha256,
            mode=mode,
            preview=preview,
            can_apply=can_apply,
            applied=not preview and can_apply,
            received=parsed.received,
            valid=len(parsed.rows),
            created=result.get("created", 0),
            activated=result.get("activated", 0),
            deactivated=result.get("deactivated", 0),
            unchanged=result.get("unchanged", 0),
            promotions_added=result.get("promotions_added", 0),
            promotions_removed=result.get("promotions_removed", 0),
            missing=result.get("missing", []),
            created_skus=result.get("created_skus", []),
            activated_skus=result.get("activated_skus", []),
            deactivated_skus=result.get("deactivated_skus", []),
            errors=errors,
        )
