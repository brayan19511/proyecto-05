from datetime import datetime
import unittest
from unittest.mock import Mock

from sqlalchemy.dialects import mssql
from app.api.sales_channel.peya.promotion_service import PromoSkuService
from app.api.sales_channel.peya.schemas import PromoSkuCreateRequest
from app.api.sales_channel.sku.repository import SkuRepository
from app.api.sales_channel.sku.schemas import (
    ActiveSkuSnapshotRequest,
    BulkSkuSyncRequest,
    SkuCreateRequest,
    SkuUpdateRequest,
)
from app.api.sales_channel.sku.service import (
    ManagedSkuService,
    SkuModelConfig,
)
from app.core.exceptions import ConflictError, NotFoundError
from app.models.external.ofisis.ecomm import RappiSku


class FakeSku:
    def __init__(self, sku, id_channel=None, is_active=None):
        self.sku = sku
        self.id_channel = id_channel
        self.is_active = is_active
        self.created_at = datetime(2026, 1, 1)
        self.updated_at = datetime(2026, 1, 1)


class FakePromoSku:
    def __init__(self, sku):
        self.sku = sku


def make_managed_service():
    config = SkuModelConfig(
        model=FakeSku,
        external_id_field="id_channel",
        updated_at_field="updated_at",
        channel_name="Canal",
    )
    service = ManagedSkuService(Mock(), config)
    service.repository = Mock()
    return service


def make_sku_matched_external_id_service():
    config = SkuModelConfig(
        model=FakeSku,
        external_id_field="id_channel",
        updated_at_field="updated_at",
        channel_name="Canal",
        external_id_matches_sku=True,
    )
    service = ManagedSkuService(Mock(), config)
    service.repository = Mock()
    return service


class ManagedSkuServiceTests(unittest.TestCase):
    def test_create_sets_active_and_external_id(self):
        service = make_managed_service()
        service.repository.get.return_value = None

        result = service.create(
            SkuCreateRequest(sku=" SKU-1 ", external_id=" EXT-1 "),
        )

        entity = service.repository.add.call_args.args[0]
        self.assertEqual(entity.sku, "SKU-1")
        self.assertEqual(entity.id_channel, "EXT-1")
        self.assertTrue(entity.is_active)
        self.assertEqual(result["external_id"], "EXT-1")

    def test_create_rejects_duplicate_sku(self):
        service = make_managed_service()
        service.repository.get.return_value = FakeSku("SKU-1")

        with self.assertRaises(ConflictError):
            service.create(SkuCreateRequest(sku="SKU-1"))

    def test_create_can_force_external_id_to_match_sku(self):
        service = make_sku_matched_external_id_service()
        service.repository.get.return_value = None

        result = service.create(SkuCreateRequest(sku="SKU-1"))

        entity = service.repository.add.call_args.args[0]
        self.assertEqual(entity.id_channel, "SKU-1")
        self.assertEqual(result["external_id"], "SKU-1")

    def test_create_rejects_external_id_different_from_sku_when_forced(self):
        service = make_sku_matched_external_id_service()
        service.repository.get.return_value = None

        with self.assertRaises(ConflictError):
            service.create(
                SkuCreateRequest(sku="SKU-1", external_id="OTHER"),
            )

    def test_deactivate_does_not_delete(self):
        service = make_managed_service()
        entity = FakeSku("SKU-1", is_active=True)
        service.repository.get.return_value = entity

        result = service.set_active("SKU-1", False)

        self.assertFalse(entity.is_active)
        self.assertFalse(result["is_active"])
        service.repository.delete.assert_not_called()

    def test_update_changes_external_id(self):
        service = make_managed_service()
        entity = FakeSku("SKU-1", id_channel="OLD", is_active=True)
        service.repository.get.return_value = entity

        result = service.update(
            "SKU-1",
            SkuUpdateRequest(external_id="NEW"),
        )

        self.assertEqual(entity.id_channel, "NEW")
        self.assertEqual(result["external_id"], "NEW")

    def test_get_missing_sku_raises_not_found(self):
        service = make_managed_service()
        service.repository.get.return_value = None

        with self.assertRaises(NotFoundError):
            service.get("UNKNOWN")

    def test_bulk_sync_updates_rows_and_deactivates_missing(self):
        service = make_managed_service()
        sku_1 = FakeSku("SKU-1", is_active=False)
        sku_2 = FakeSku("SKU-2", is_active=True)
        service.repository.list.return_value = [sku_1, sku_2]

        result = service.bulk_sync(
            BulkSkuSyncRequest(
                items=[{"sku": "SKU-1", "on/off": "on"}],
                deactivate_missing=True,
            )
        )

        self.assertTrue(sku_1.is_active)
        self.assertFalse(sku_2.is_active)
        self.assertEqual(result["activated"], 1)
        self.assertEqual(result["deactivated"], 1)
        service.repository.commit.assert_called_once()

    def test_bulk_sync_reports_missing_when_creation_is_disabled(self):
        service = make_managed_service()
        service.repository.list.return_value = []

        result = service.bulk_sync(
            BulkSkuSyncRequest(
                items=[{"sku": "NEW", "active": True}],
                create_missing=False,
            )
        )

        self.assertEqual(result["missing"], ["NEW"])
        service.repository.add.assert_not_called()

    def test_bulk_sync_backfills_external_id_when_it_must_match_sku(self):
        service = make_sku_matched_external_id_service()
        sku_1 = FakeSku("SKU-1", id_channel=None, is_active=True)
        service.repository.list.return_value = [sku_1]

        service.bulk_sync(
            BulkSkuSyncRequest(
                items=[{"sku": "SKU-1", "active": True}],
            )
        )

        self.assertEqual(sku_1.id_channel, "SKU-1")

    def test_peya_list_marks_promotional_skus(self):
        config = SkuModelConfig(
            model=FakeSku,
            external_id_field="id_channel",
            updated_at_field="updated_at",
            channel_name="Peya",
            promotion_model=FakePromoSku,
        )
        service = ManagedSkuService(Mock(), config)
        service.repository = Mock()
        service.repository.list.return_value = [
            FakeSku("PROMO-1", is_active=True),
            FakeSku("REGULAR-1", is_active=True),
        ]
        service.repository.list_skus.return_value = {"PROMO-1"}

        result = service.list()

        self.assertTrue(result[0]["has_promotion"])
        self.assertFalse(result[1]["has_promotion"])

    def test_active_snapshot_activates_list_and_deactivates_rest(self):
        service = make_managed_service()
        sku_1 = FakeSku("SKU-1", is_active=False)
        sku_2 = FakeSku("SKU-2", is_active=True)
        service.repository.list.return_value = [sku_1, sku_2]

        result = service.apply_active_snapshot(
            ActiveSkuSnapshotRequest(
                skus=["SKU-1", "SKU-NEW"],
                create_missing=True,
            )
        )

        created = service.repository.add.call_args.args[0]
        self.assertTrue(sku_1.is_active)
        self.assertFalse(sku_2.is_active)
        self.assertEqual(created.sku, "SKU-NEW")
        self.assertTrue(created.is_active)
        self.assertEqual(result["created"], 1)
        self.assertEqual(result["activated"], 1)
        self.assertEqual(result["deactivated"], 1)

    def test_active_snapshot_rejects_duplicate_skus(self):
        with self.assertRaises(ValueError):
            ActiveSkuSnapshotRequest(skus=["SKU-1", " sku-1 "])

    def test_bulk_preview_rolls_back_instead_of_committing(self):
        service = make_managed_service()
        service.repository.list.return_value = [
            FakeSku("SKU-1", is_active=False)
        ]

        service.bulk_sync(
            BulkSkuSyncRequest(
                items=[{"sku": "SKU-1", "active": True}],
            ),
            dry_run=True,
        )

        service.repository.rollback.assert_called_once()
        service.repository.commit.assert_not_called()


class PromoSkuServiceTests(unittest.TestCase):
    def test_delete_physically_removes_promo_sku(self):
        service = PromoSkuService(Mock(), FakePromoSku, FakeSku)
        service.repository = Mock()
        entity = FakePromoSku("PROMO-1")
        service.repository.get.return_value = entity

        service.delete("PROMO-1")

        service.repository.delete.assert_called_once_with(entity)
        service.repository.commit.assert_called_once()

    def test_create_rejects_duplicate_promo_sku(self):
        service = PromoSkuService(Mock(), FakePromoSku, FakeSku)
        service.repository = Mock()
        service.repository.sku_exists.return_value = True
        service.repository.get.return_value = FakePromoSku("PROMO-1")

        with self.assertRaises(ConflictError):
            service.create(PromoSkuCreateRequest(sku="PROMO-1"))

    def test_create_rejects_orphan_promotion(self):
        service = PromoSkuService(Mock(), FakePromoSku, FakeSku)
        service.repository = Mock()
        service.repository.sku_exists.return_value = False

        with self.assertRaises(NotFoundError):
            service.create(PromoSkuCreateRequest(sku="UNKNOWN"))

    def test_promotion_snapshot_adds_and_removes_atomically(self):
        service = PromoSkuService(Mock(), FakePromoSku, FakeSku)
        service.repository = Mock()
        existing = FakePromoSku("OLD")
        service.repository.list.return_value = [existing]
        service.repository.list_skus.return_value = {"OLD", "NEW"}

        result = service.sync_snapshot(["NEW"])

        created = service.repository.add.call_args.args[0]
        self.assertEqual(created.sku, "NEW")
        service.repository.delete.assert_called_once_with(existing)
        service.repository.commit.assert_called_once()
        self.assertEqual(result["promotions_added"], 1)
        self.assertEqual(result["promotions_removed"], 1)

    def test_promotion_snapshot_does_not_write_with_unknown_sku(self):
        service = PromoSkuService(Mock(), FakePromoSku, FakeSku)
        service.repository = Mock()
        service.repository.list.return_value = []
        service.repository.list_skus.return_value = {"KNOWN"}

        result = service.sync_snapshot(["UNKNOWN"])

        self.assertEqual(result["missing"], ["UNKNOWN"])
        service.repository.add.assert_not_called()
        service.repository.delete.assert_not_called()
        service.repository.commit.assert_not_called()


class SkuRepositorySqlTests(unittest.TestCase):
    def test_active_filter_uses_sql_server_boolean_comparison(self):
        db = Mock()
        query = db.query.return_value
        query.filter.return_value = query
        query.order_by.return_value = query
        query.all.return_value = []

        repository = SkuRepository(db, RappiSku, "id_rappi")
        repository.list(active=True)

        criterion = query.filter.call_args.args[0]
        sql = str(
            criterion.compile(
                dialect=mssql.dialect(),
                compile_kwargs={"literal_binds": True},
            )
        )

        self.assertEqual("rappi_sku.is_active = 1", sql)


if __name__ == "__main__":
    unittest.main()
