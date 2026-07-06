"""PostgreSQL smoke test for the jobs model graph and service."""

from uuid import uuid4

from app.api.jobs.constants import JobStatus, JobType
from app.api.jobs.service import JobService
from app.core.db.db_postgres import SessionLocal
from app.models.auth import Auth
from app.models.jobs import Job


def main() -> None:
    user_id = uuid4()
    with SessionLocal() as db:
        user = Auth(
            id=user_id,
            email=f"jobs-smoke-{user_id}@example.com",
            password_hash="not-used",
            active=True,
        )
        db.add(user)
        db.commit()

        try:
            service = JobService(db)
            job = service.create_job(
                job_type=JobType.SAP_DOCUMENT_ACTION.value,
                parameters={
                    "database": "TEST",
                    "entity": "Invoices",
                    "action": "Cancel",
                },
                references=[1, 2, 2, 3],
                user_id=user_id,
                batch_size=2,
                idempotency_key="smoke-test",
            )

            assert job.total_items == 3
            assert job.total_batches == 2
            assert job.creator_email == user.email
            assert sum(len(batch.items) for batch in job.batches) == 3

            cancelled = service.cancel_job(
                job.id,
                user_id=user_id,
                can_cancel_all=False,
            )
            assert cancelled.status == JobStatus.CANCELLED.value
            assert cancelled.cancelled_items == 3
        finally:
            db.query(Job).filter(Job.created_by == user_id).delete()
            db.query(Auth).filter(Auth.id == user_id).delete()
            db.commit()


if __name__ == "__main__":
    main()
