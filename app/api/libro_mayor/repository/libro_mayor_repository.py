# app\api\libro_mayor\repository\libro_mayor_repository.py
from datetime import date

import pandas as pd
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.finance.libro_mayor_model import LibroMayor, ReglasGastos


class LibroMayorRepository:
    def __init__(self, db: Session):
        self.db = db

    # CRUD reglas gastos
    def get_reglas_activas(self) -> list[ReglasGastos]:
        """Trae las reglas contables locales ordenadas estrictamente por prioridad."""
        return (
            self.db.query(ReglasGastos)
            .filter(ReglasGastos.activo == True)
            .order_by(ReglasGastos.prioridad.asc())
            .all()
        )
    def get_libro_mayor_by_account(self, start_date: date, end_date: date, account: str):
        query=self.db.query(LibroMayor)
        query = query.filter(LibroMayor.fecha_contabilizacion.between(start_date, end_date))
        query=query.filter(LibroMayor.tipo_cuenta==account)
        registros = query.all()
        return registros
            
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
