
from datetime import datetime

from pydantic import BaseModel


class ProvisionCreate(BaseModel):
    description: str | None = None
    company_id: int
    concept_id: int
    area_id: int
    currency_id: int
    amount: float
    provision_date: datetime
    observations: str | None = None
