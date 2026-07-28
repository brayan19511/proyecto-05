import unittest
from unittest.mock import Mock
from uuid import uuid4

from pydantic import ValidationError as PydanticValidationError

from app.api.jobs.constants import (
    JOBS_CANCEL_ALL_PERMISSION,
    JOBS_RETRY_PERMISSION,
    JOBS_VIEW_ALL_PERMISSION,
    JobBatchStatus,
    JobItemStatus,
    JobStatus,
    JobTriggerSource,
    JobType,
    SCHEDULED_JOBS_EDIT_PERMISSION,
    SCHEDULED_JOBS_RUN_PERMISSION,
    SCHEDULED_JOBS_VIEW_PERMISSION,
)
from app.api.jobs.service import JobService, chunked
from app.api.sap.sap_schema import SapServiceDocumentos
from app.api.sap.service.sap_job_service import safe_sap_error
from app.api.verify.seed_service import ROLE_PERMISSIONS
from app.core.middleware import sanitize_payload
from app.core.secret_cipher import (
    decrypt_job_secrets,
    encrypt_job_secrets,
)
from app.models.jobs import Job, JobBatch, JobItem
from app.workers.celery_app import celery_app
from app.workers.dispatcher import resolve_job_queue


class JobServiceTests(unittest.TestCase):
    def test_chunks_job_items_and_deduplicates_references(self):
        db = Mock()
        dispatcher = Mock()
        service = JobService(db, dispatcher=dispatcher)
        service.repository = Mock()
        service.repository.get_by_idempotency_key.return_value = None

        created = {}

        def remember_job(job_id, **kwargs):
            return created["job"]

        service.get_job = Mock(side_effect=remember_job)
        db.add.side_effect = lambda job: created.update(job=job)

        result = service.create_job(
            job_type=JobType.SAP_DOCUMENT_ACTION.value,
            parameters={
                "database": "COMPANY",
                "entity": "Invoices",
                "action": "Cancel",
            },
            references=[1, 2, 2, 3, 4, 5],
            user_id=uuid4(),
            batch_size=2,
            idempotency_key="request-1",
        )

        self.assertEqual(result.total_items, 5)
        self.assertEqual(result.total_batches, 3)
        self.assertEqual(result.trigger_source, JobTriggerSource.API.value)
        self.assertEqual(
            [
                item.reference
                for batch in result.batches
                for item in batch.items
            ],
            ["1", "2", "3", "4", "5"],
        )
        dispatcher.assert_called_once_with(result.id)
        db.commit.assert_called_once()

    def test_retry_job_marks_child_as_retry_source(self):
        user_id = uuid4()
        parent = Job(
            id=uuid4(),
            job_type=JobType.SAP_DOCUMENT_ACTION.value,
            status=JobStatus.FAILED.value,
            parameters={"operation": "cancel"},
            encrypted_secrets="encrypted",
            scheduled_job_id=uuid4(),
            created_by=user_id,
        )
        service = JobService(Mock())
        service.get_job = Mock(return_value=parent)
        service.repository = Mock()
        service.repository.get_dispatchable_batches.return_value = []
        service.repository.get_failed_references.return_value = ["doc-1"]
        service.repository.get_failed_item_payloads.return_value = {}
        service.create_job = Mock(return_value="retry-job")

        result = service.retry_job(
            parent.id,
            user_id=user_id,
            can_retry_all=True,
            batch_size=1,
        )

        self.assertEqual(result, "retry-job")
        self.assertEqual(
            service.create_job.call_args.kwargs["trigger_source"],
            JobTriggerSource.RETRY.value,
        )

    def test_existing_idempotency_key_returns_same_job(self):
        db = Mock()
        dispatcher = Mock()
        service = JobService(db, dispatcher=dispatcher)
        existing = Job(
            id=uuid4(),
            job_type=JobType.SAP_DOCUMENT_ACTION.value,
            status=JobStatus.QUEUED.value,
            parameters={},
            total_items=1,
            created_by=uuid4(),
        )
        service.repository = Mock()
        service.repository.get_by_idempotency_key.return_value = existing
        service.get_job = Mock(return_value=existing)

        result = service.create_job(
            job_type=existing.job_type,
            parameters={},
            references=[1],
            user_id=existing.created_by,
            batch_size=100,
            idempotency_key="same-request",
        )

        self.assertIs(result, existing)
        dispatcher.assert_not_called()
        db.add.assert_not_called()

    def test_cancel_marks_only_non_running_batches_immediately(self):
        user_id = uuid4()
        pending_batch = JobBatch(
            sequence=1,
            status=JobBatchStatus.QUEUED.value,
            total_items=1,
            celery_task_id="pending-task",
            items=[
                JobItem(
                    job_id=uuid4(),
                    reference="1",
                    status=JobItemStatus.PENDING.value,
                )
            ],
        )
        running_batch = JobBatch(
            sequence=2,
            status=JobBatchStatus.RUNNING.value,
            total_items=1,
            celery_task_id="running-task",
            items=[
                JobItem(
                    job_id=uuid4(),
                    reference="2",
                    status=JobItemStatus.RUNNING.value,
                )
            ],
        )
        job = Job(
            id=uuid4(),
            job_type=JobType.SAP_DOCUMENT_ACTION.value,
            status=JobStatus.RUNNING.value,
            parameters={},
            total_items=2,
            total_batches=2,
            created_by=user_id,
            batches=[pending_batch, running_batch],
        )

        service = JobService(Mock())
        service.get_job = Mock(return_value=job)
        service.refresh_progress = Mock()
        service._revoke_tasks = Mock()

        result = service.cancel_job(
            job.id,
            user_id=user_id,
            can_cancel_all=False,
        )

        self.assertEqual(result.status, JobStatus.CANCEL_REQUESTED.value)
        self.assertEqual(
            pending_batch.status,
            JobBatchStatus.CANCELLED.value,
        )
        self.assertEqual(
            pending_batch.items[0].status,
            JobItemStatus.CANCELLED.value,
        )
        self.assertEqual(running_batch.status, JobBatchStatus.RUNNING.value)
        service._revoke_tasks.assert_called_once_with(
            ["pending-task", "running-task"]
        )

    def test_chunked_keeps_memory_bounded_units(self):
        self.assertEqual(
            list(chunked(["1", "2", "3", "4", "5"], 2)),
            [["1", "2"], ["3", "4"], ["5"]],
        )

    def test_retry_preserves_failed_item_payloads(self):
        user_id = uuid4()
        job = Job(
            id=uuid4(),
            job_type=JobType.LEDGER_SYNC_DELTA.value,
            status=JobStatus.FAILED.value,
            parameters={"operation": "sync_delta"},
            total_items=1,
            created_by=user_id,
        )
        service = JobService(Mock())
        service.get_job = Mock(return_value=job)
        service.repository = Mock()
        service.repository.get_dispatchable_batches.return_value = []
        service.repository.get_failed_references.return_value = [
            "sync_delta:95:2026-07-25"
        ]
        service.repository.get_failed_item_payloads.return_value = {
            "sync_delta:95:2026-07-25": {
                "operation": "sync_delta",
                "account": "95",
            }
        }
        service.create_job = Mock(return_value="retry-job")

        result = service.retry_job(
            job.id,
            user_id=user_id,
            can_retry_all=False,
            batch_size=1,
        )

        self.assertEqual(result, "retry-job")
        self.assertEqual(
            service.create_job.call_args.kwargs["item_payloads"],
            {
                "sync_delta:95:2026-07-25": {
                    "operation": "sync_delta",
                    "account": "95",
                }
            },
        )


class SapJobContractTests(unittest.TestCase):
    def test_request_accepts_user_credentials(self):
        request = SapServiceDocumentos(
            user="sap-user",
            password="secret",
            database="COMPANY",
            entidad="Invoices",
            action="Cancel",
            documentos=[1],
        )

        self.assertEqual(request.user, "sap-user")
        self.assertEqual(request.password.get_secret_value(), "secret")

    def test_request_rejects_unsafe_resource_names(self):
        with self.assertRaises(PydanticValidationError):
            SapServiceDocumentos(
                user="sap-user",
                password="secret",
                database="COMPANY",
                entidad="../Login",
                action="Cancel",
                documentos=[1],
            )

    def test_request_rejects_non_positive_documents(self):
        with self.assertRaises(PydanticValidationError):
            SapServiceDocumentos(
                user="sap-user",
                password="secret",
                database="COMPANY",
                entidad="Invoices",
                action="Cancel",
                documentos=[0, -1],
            )

    def test_worker_routes_sap_jobs_to_heavy_queue(self):
        route = celery_app.conf.task_routes["jobs.sap.process_batch"]
        self.assertEqual(route["queue"], "heavy")
        self.assertTrue(celery_app.conf.task_ignore_result)
        self.assertEqual(celery_app.conf.worker_prefetch_multiplier, 1)

    def test_celery_direct_ledger_route_defaults_to_heavy_queue(self):
        route = celery_app.conf.task_routes["jobs.ledger.process_batch"]
        self.assertEqual(route["queue"], "heavy")
        self.assertEqual(celery_app.conf.task_default_queue, "light")

    def test_dispatcher_routes_small_ledger_job_to_light_queue(self):
        job = Mock(
            job_type=JobType.LEDGER_SYNC_DELTA.value,
            total_items=1,
        )

        self.assertEqual(resolve_job_queue(job), "light")

    def test_dispatcher_routes_large_ledger_job_to_heavy_queue(self):
        job = Mock(
            job_type=JobType.LEDGER_SYNC_DELTA.value,
            total_items=2,
        )

        self.assertEqual(resolve_job_queue(job), "heavy")

    def test_dispatcher_keeps_email_jobs_isolated(self):
        job = Mock(
            job_type=JobType.PAYMENT_PROVIDER_EMAIL.value,
            total_items=1,
        )

        self.assertEqual(resolve_job_queue(job), "email")

    def test_safe_error_has_bounded_size(self):
        self.assertEqual(len(safe_sap_error("x" * 3000)), 2000)

    def test_sap_documents_are_redacted_from_audit_body(self):
        sanitized = sanitize_payload(
            {
                "database": "COMPANY",
                "documentos": [1001, 1002],
            }
        )
        self.assertEqual(sanitized["documentos"], "[REDACTED]")

    def test_credentials_are_encrypted_and_authenticated(self):
        encrypted = encrypt_job_secrets(
            {"user": "sap-user", "password": "secret"}
        )

        self.assertNotIn("sap-user", encrypted)
        self.assertNotIn("secret", encrypted)
        self.assertEqual(
            decrypt_job_secrets(encrypted),
            {"user": "sap-user", "password": "secret"},
        )


class JobModelAndSeedTests(unittest.TestCase):
    def test_only_user_visible_job_has_audit_mixin_fields(self):
        self.assertIn("created_by", Job.__table__.columns)
        self.assertNotIn("created_by", JobBatch.__table__.columns)
        self.assertNotIn("created_by", JobItem.__table__.columns)

    def test_admin_sap_can_operate_all_jobs(self):
        permissions = ROLE_PERMISSIONS["Admin SAP"]
        self.assertIn(JOBS_VIEW_ALL_PERMISSION, permissions)
        self.assertIn(JOBS_CANCEL_ALL_PERMISSION, permissions)
        self.assertIn(JOBS_RETRY_PERMISSION, permissions)
        self.assertIn(SCHEDULED_JOBS_VIEW_PERMISSION, permissions)
        self.assertIn(SCHEDULED_JOBS_EDIT_PERMISSION, permissions)
        self.assertIn(SCHEDULED_JOBS_RUN_PERMISSION, permissions)


if __name__ == "__main__":
    unittest.main()
