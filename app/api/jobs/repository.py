from uuid import UUID

from sqlalchemy.orm import Session, selectinload

from app.models.jobs import Job, JobBatch, JobItem


class JobRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, job_id: UUID, *, with_batches: bool = False) -> Job | None:
        query = self.db.query(Job)
        if with_batches:
            query = query.options(selectinload(Job.batches))
        return query.filter(Job.id == job_id).first()

    def get_by_idempotency_key(
        self,
        *,
        user_id: UUID,
        job_type: str,
        idempotency_key: str,
    ) -> Job | None:
        return (
            self.db.query(Job)
            .filter(
                Job.created_by == user_id,
                Job.job_type == job_type,
                Job.idempotency_key == idempotency_key,
            )
            .first()
        )

    def list_jobs(
        self,
        *,
        user_id: UUID | None,
        job_type: str | None,
        status: str | None,
        scheduled_job_id: UUID | None,
        limit: int,
        offset: int,
    ) -> tuple[list[Job], int]:
        query = self.db.query(Job)
        if user_id is not None:
            query = query.filter(Job.created_by == user_id)
        if job_type is not None:
            query = query.filter(Job.job_type == job_type)
        if status is not None:
            query = query.filter(Job.status == status)
        if scheduled_job_id is not None:
            query = query.filter(Job.scheduled_job_id == scheduled_job_id)

        total = query.count()
        items = (
            query.order_by(Job.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return items, total

    def list_items(
        self,
        *,
        job_id: UUID,
        status: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[JobItem], int]:
        query = self.db.query(JobItem).filter(JobItem.job_id == job_id)
        if status is not None:
            query = query.filter(JobItem.status == status)

        total = query.count()
        items = (
            query.order_by(JobItem.created_at, JobItem.id)
            .offset(offset)
            .limit(limit)
            .all()
        )
        return items, total

    def get_failed_references(self, job_id: UUID) -> list[str]:
        return [
            reference
            for (reference,) in (
                self.db.query(JobItem.reference)
                .filter(
                    JobItem.job_id == job_id,
                    JobItem.status == "FAILED",
                )
                .order_by(JobItem.created_at)
                .all()
            )
        ]

    def get_failed_item_payloads(self, job_id: UUID) -> dict[str, dict | list | str]:
        rows = (
            self.db.query(JobItem.reference, JobItem.result_data)
            .filter(
                JobItem.job_id == job_id,
                JobItem.status == "FAILED",
                JobItem.result_data.isnot(None),
            )
            .order_by(JobItem.created_at)
            .all()
        )
        return {reference: payload for reference, payload in rows}

    def get_dispatchable_batches(self, job_id: UUID) -> list[JobBatch]:
        return (
            self.db.query(JobBatch)
            .filter(
                JobBatch.job_id == job_id,
                JobBatch.status.in_(["PENDING", "RETRYING"]),
            )
            .order_by(JobBatch.sequence)
            .all()
        )
