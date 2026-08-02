from dataclasses import dataclass
from datetime import date
from pathlib import Path

from app.core.config import settings


@dataclass(frozen=True)
class DataLakePathBuilder:
    root: Path

    @classmethod
    def from_settings(cls) -> "DataLakePathBuilder":
        return cls(Path(settings.DATA_LAKE_ROOT))

    def transactional_partition(
        self,
        *,
        source: str,
        table_name: str,
        business_date: date,
    ) -> Path:
        return (
            self.root
            / "bronze"
            / source
            / "transaccional"
            / table_name
            / f"year={business_date:%Y}"
            / f"month={business_date:%m}"
            / f"day={business_date:%d}"
        )

    def master_latest(self, *, source: str, table_name: str) -> Path:
        return self.root / "bronze" / source / "maestros" / table_name / "latest"

    def master_snapshot(
        self,
        *,
        source: str,
        table_name: str,
        snapshot_date: date,
    ) -> Path:
        return (
            self.root
            / "bronze"
            / source
            / "maestros"
            / table_name
            / f"snapshot_date={snapshot_date:%Y-%m-%d}"
        )

    def silver_partition(
        self,
        *,
        source: str,
        dataset_name: str,
        business_date: date,
    ) -> Path:
        return (
            self.root
            / "silver"
            / source
            / dataset_name
            / f"year={business_date:%Y}"
            / f"month={business_date:%m}"
            / f"day={business_date:%d}"
        )
