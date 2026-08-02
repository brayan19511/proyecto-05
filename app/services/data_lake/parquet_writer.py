from dataclasses import dataclass
from pathlib import Path
import shutil
from uuid import uuid4

import polars as pl


@dataclass(frozen=True)
class DataLakeWriteResult:
    output_path: str
    rows_count: int


class ParquetDataLakeWriter:
    def write_partition(
        self,
        frame: pl.DataFrame,
        partition_dir: Path,
        *,
        replace: bool = True,
    ) -> DataLakeWriteResult:
        partition_dir = partition_dir.resolve()
        temp_dir = partition_dir.with_name(f".{partition_dir.name}.{uuid4().hex}.tmp")
        temp_dir.mkdir(parents=True, exist_ok=False)
        temp_file = temp_dir / "data.parquet"
        frame.write_parquet(temp_file)

        if replace and partition_dir.exists():
            shutil.rmtree(partition_dir)
        partition_dir.parent.mkdir(parents=True, exist_ok=True)
        temp_dir.replace(partition_dir)

        return DataLakeWriteResult(
            output_path=str(partition_dir / "data.parquet"),
            rows_count=frame.height,
        )
