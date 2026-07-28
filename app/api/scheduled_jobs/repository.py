from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.jobs import ScheduledJob


class ScheduledJobRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, scheduled_job_id: UUID) -> ScheduledJob | None:
        return (
            self.db.query(ScheduledJob)
            .filter(ScheduledJob.id == scheduled_job_id)
            .first()
        )

    def get_by_name(self, name: str) -> ScheduledJob | None:
        return self.db.query(ScheduledJob).filter(ScheduledJob.name == name).first()

    def list_jobs(
        self,
        *,
        enabled: bool | None,
        limit: int,
        offset: int,
    ) -> tuple[list[ScheduledJob], int]:
        query = self.db.query(ScheduledJob)
        if enabled is not None:
            query = query.filter(ScheduledJob.enabled == enabled)
        total = query.count()
        items = (
            query.order_by(ScheduledJob.next_run_at, ScheduledJob.name)
            .offset(offset)
            .limit(limit)
            .all()
        )
        return items, total

    def list_due_jobs(self, *, now: datetime, limit: int) -> list[ScheduledJob]:
        return (
            self.db.query(ScheduledJob)
            .filter(
                ScheduledJob.enabled.is_(True),
                ScheduledJob.next_run_at <= now,
            )
            .order_by(ScheduledJob.next_run_at, ScheduledJob.id)
            .with_for_update(skip_locked=True)
            .limit(limit)
            .all()
        )
