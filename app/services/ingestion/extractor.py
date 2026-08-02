from datetime import date

import polars as pl
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.ingestion.catalog import IcgTableConfig, TableKind


class IcgExtractor:
    def __init__(self, db_icg: Session):
        self.db_icg = db_icg

    def extract(
        self,
        table_config: IcgTableConfig,
        *,
        business_date: date | None = None,
    ) -> pl.DataFrame:
        params = {}
        if table_config.kind == TableKind.TRANSACTIONAL:
            if business_date is None:
                raise ValueError("La fecha de negocio es obligatoria")
            params["business_date"] = business_date.isoformat()

        result = self.db_icg.execute(text(table_config.sql), params)
        rows = result.mappings().all()
        if rows:
            return pl.from_dicts(
                [dict(row) for row in rows],
                infer_schema_length=None,
            )
        return pl.DataFrame(schema={column: pl.Null for column in result.keys()})
