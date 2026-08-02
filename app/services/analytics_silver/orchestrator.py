from datetime import date, timedelta
from uuid import UUID

from sqlalchemy.orm import Session

from app.api.jobs.constants import JobType
from app.api.jobs.service import JobService


class AnalyticsSilverJobService:
    def __init__(self, db: Session):
        self.db = db

    def enqueue_icg_sales_build(
        self,
        *,
        start_date: date,
        end_date: date,
        user_id: UUID,
        batch_size: int = 1,
        idempotency_key: str | None = None,
        scheduled_job_id: UUID | None = None,
        trigger_source: str = "API",
    ):
        payloads = self._build_daily_payloads(
            dataset_group="sales",
            start_date=start_date,
            end_date=end_date,
        )

        from app.workers.dispatcher import dispatch_job

        return JobService(self.db, dispatcher=dispatch_job).create_job(
            job_type=JobType.ANALYTICS_SILVER_BUILD.value,
            parameters={
                "source": "icg",
                "dataset_group": "sales",
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
            references=list(payloads),
            user_id=user_id,
            batch_size=batch_size,
            idempotency_key=idempotency_key,
            scheduled_job_id=scheduled_job_id,
            trigger_source=trigger_source,
            item_payloads=payloads,
        )

    @staticmethod
    def _build_daily_payloads(
        *,
        dataset_group: str,
        start_date: date,
        end_date: date,
    ) -> dict[str, dict]:
        if end_date < start_date:
            raise ValueError("end_date no puede ser menor que start_date")

        payloads = {}
        current = start_date
        while current <= end_date:
            reference = f"silver:icg:{dataset_group}:{current.isoformat()}"
            payloads[reference] = {
                "source": "icg",
                "dataset_group": dataset_group,
                "business_date": current.isoformat(),
            }
            current += timedelta(days=1)
        return payloads
