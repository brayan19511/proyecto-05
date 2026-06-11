# app\api\libro_mayor\repository\libro_mayor_repository.py
from datetime import date
import math

import numpy as np
import pandas as pd
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.finance.libro_mayor_model import LibroMayor, ReglasGastos


class LibroMayorRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self):
        return self.db.query(LibroMayor).all()

    # CRUD reglas gastos
    def get_reglas_activas(self) -> list[ReglasGastos]:
        """Trae las reglas contables locales ordenadas estrictamente por prioridad."""
        return (
            self.db.query(ReglasGastos)
            .filter(ReglasGastos.activo == True)
            .order_by(ReglasGastos.prioridad.asc())
            .all()
        )

    def get_by_tipo_cuenta(
        self,
        tipo_cuenta: str
    ) -> list[LibroMayor]:

        return (
            self.db.query(LibroMayor)
            .filter(LibroMayor.tipo_cuenta == tipo_cuenta)
            .all()
        )

    def get_by_rule(
        self,
        rule_id: int
    ):

        return (
            self.db.query(LibroMayor)
            .filter(LibroMayor.id_regla == rule_id)
            .all()
        )

    def get_libro_mayor_by_account(self, start_date: date, end_date: date, account: str):
        query = self.db.query(LibroMayor)
        query = query.filter(
            LibroMayor.fecha_contabilizacion.between(start_date, end_date))
        query = query.filter(LibroMayor.tipo_cuenta == account)
        registros = query.all()
        return registros

    def get_last_libro_mayor(self, account: str) -> LibroMayor:
        last_registro = (
            self.db.query(LibroMayor)
            .filter(LibroMayor.tipo_cuenta == account)
            .order_by(LibroMayor.fecha_creacion.desc())
            .first()
        )
        return last_registro

    # guardar ventas bulk
    def upsert(self, df_limpio: pd.DataFrame):
        df_limpio = df_limpio.where(
            pd.notnull(df_limpio),
            None
        )
        df_limpio = df_limpio.replace(
            {
                np.nan: None,
                "nan": None,
                "NaN": None,
                "NAN": None,
                "None": None,
            }
        )
        registros = df_limpio.to_dict(orient="records")

        stmt = insert(LibroMayor).values(registros)

        update_columns = {
            column.name: getattr(stmt.excluded, column.name)
            for column in LibroMayor.__table__.columns
            if column.name
            not in [
                "transaccion_id",
                "linea",
                "created_at",
                "created_by"
            ]
        }

        stmt = stmt.on_conflict_do_update(
            index_elements=["transaccion_id", "linea"], set_=update_columns
        )

        self.db.execute(stmt)
        self.db.commit()

        return {"procesados": len(registros)}

    def get_candidates_by_rule(
        self,
        regla: ReglasGastos
    ) -> list[LibroMayor]:
        query = self.db.query(LibroMayor)

        if regla.cuenta:
            query = query.filter(
                LibroMayor.cuenta_asociada == regla.cuenta
            )

        if regla.centro_costo:
            query = query.filter(
                LibroMayor.centro_costo == regla.centro_costo
            )

        return query.all()

    def update_classification(self, df: pd.DataFrame):

        if df.empty:
            return {"procesados": 0}
        df = df.where(pd.notnull(df), None)

        registros = df[
            [
                "transaccion_id",
                "linea",
                "id_regla",
                "tiene_regla",
                "codigo",
                "subcodigo",
                "nombre_cuenta",
                "updated_by",
            ]
        ].to_dict(orient="records")

        batch_size = 5000

        for i in range(0, len(registros), batch_size):

            lote = registros[i:i + batch_size]

            self.db.bulk_update_mappings(
                LibroMayor,
                lote
            )

        self.db.commit()

        return {
            "procesados": len(registros),
            "lotes": math.ceil(len(registros) / batch_size)
        }

    def to_dataframe(
        self,
        registros: list[LibroMayor]
    ) -> pd.DataFrame:

        if not registros:
            return pd.DataFrame()

        return pd.DataFrame([
            {
                column.name: getattr(row, column.name)
                for column in LibroMayor.__table__.columns
            }
            for row in registros
        ])

    def to_dataframe_date(
        self,
        registros: list[LibroMayor]
    ) -> pd.DataFrame:

        if not registros:
            return pd.DataFrame()

        df = pd.DataFrame([
            {
                column.name: getattr(row, column.name)
                for column in LibroMayor.__table__.columns
            }
            for row in registros
        ])

        if not df.empty:

            df["anio"] = pd.to_datetime(
                df["fecha_contabilizacion"]
            ).dt.year

            df["mes"] = pd.to_datetime(
                df["fecha_contabilizacion"]
            ).dt.month

            meses = {
                1: "Enero",
                2: "Febrero",
                3: "Marzo",
                4: "Abril",
                5: "Mayo",
                6: "Junio",
                7: "Julio",
                8: "Agosto",
                9: "Septiembre",
                10: "Octubre",
                11: "Noviembre",
                12: "Diciembre",
            }

            df["nmes"] = df["mes"].map(meses)

        return df
