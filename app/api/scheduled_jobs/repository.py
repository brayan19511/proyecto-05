from datetime import datetime

from app.core.db.base_repository import BaseRepository
from app.models.jobs import ScheduledJob


class ScheduledJobRepository(BaseRepository[ScheduledJob]):
    model = ScheduledJob

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
        query = query.order_by(ScheduledJob.next_run_at, ScheduledJob.name)
        return self.paginate(query, limit=limit, offset=offset)

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
