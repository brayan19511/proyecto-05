# app\api\libro_mayor\repository\libro_mayor_repository.py
from datetime import date
import math

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
