from datetime import date

from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session


class AttendanceRepository:
    """Execute read-only attendance queries against the CIC schema."""

    def __init__(self, db: Session):
        self.db = db

    def get_marks(
        self,
        document_numbers: list[int],
        date_from: date | None,
        date_to: date | None,
        limit: int,
        offset: int,
    ) -> tuple[list[dict], int]:
        filters = ["IN_NUMERO_DOCUMENTO IN :document_numbers"]
        parameters = {
            "document_numbers": document_numbers,
            "date_from": date_from,
            "date_to": date_to,
            "limit": limit,
            "offset": offset,
        }
        if date_from is not None:
            filters.append("DT_FECHA_MARCA >= :date_from")
        if date_to is not None:
            filters.append(
                "DT_FECHA_MARCA < DATEADD(day, 1, CAST(:date_to AS date))"
            )

        # Filter before ROW_NUMBER so entry/exit pairing is calculated only
        # within the requested attendance period.
        where_clause = " AND ".join(filters)
        count_query = text(
            f"""
            SELECT COUNT(*)
            FROM rash.FASI_TA_MARCA_TXT_COOLBOX
            WHERE {where_clause}
            """
        ).bindparams(bindparam("document_numbers", expanding=True))
        total = int(self.db.execute(count_query, parameters).scalar_one())

        query = text(
            f"""
            WITH ordered_marks AS (
                SELECT
                    IN_SECUENCIA_CARGA,
                    IN_NUMERO_DOCUMENTO,
                    DT_FECHA_MARCA,
                    CAST(DT_FECHA_MARCA AS date) AS MARK_DATE,
                    ROW_NUMBER() OVER (
                        PARTITION BY
                            IN_NUMERO_DOCUMENTO,
                            CAST(DT_FECHA_MARCA AS date)
                        ORDER BY
                            DT_FECHA_MARCA,
                            IN_SECUENCIA_CARGA
                    ) AS ROW_NUMBER
                FROM rash.FASI_TA_MARCA_TXT_COOLBOX
                WHERE {where_clause}
            )
            SELECT
                IN_SECUENCIA_CARGA AS sequence_id,
                IN_NUMERO_DOCUMENTO AS document_number,
                DT_FECHA_MARCA AS marked_at,
                MARK_DATE AS mark_date,
                ROW_NUMBER AS row_number,
                CASE
                    WHEN ROW_NUMBER % 2 = 1 THEN 'INGRESO'
                    ELSE 'SALIDA'
                END AS mark_type
            FROM ordered_marks
            ORDER BY marked_at DESC, sequence_id DESC
            OFFSET :offset ROWS FETCH NEXT :limit ROWS ONLY
            """
        ).bindparams(bindparam("document_numbers", expanding=True))

        rows = self.db.execute(query, parameters).mappings().all()
        return [dict(row) for row in rows], total
