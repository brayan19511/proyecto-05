# app\api\libro_mayor\repository\libro_mayor_repository.py
from datetime import date
import math

import numpy as np
import pandas as pd

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.finance.libro_mayor_model import (
    LibroMayor,
    ReglasGastos,
)


class LibroMayorRepository:

    BATCH_SIZE = 5000

    def __init__(self, db: Session):
        self.db = db

    # =====================================================
    # REGLAS
    # =====================================================

    def get_reglas_activas(self) -> list[ReglasGastos]:
        """
        Obtiene reglas activas ordenadas por prioridad.
        """
        return (
            self.db.query(ReglasGastos)
            .filter(ReglasGastos.activo.is_(True))
            .order_by(ReglasGastos.prioridad.asc())
            .all()
        )

    # =====================================================
    # CONSULTAS LIBRO MAYOR
    # =====================================================

    def get_by_account_and_date_range(
        self,
        account: str,
        start_date: date,
        end_date: date,
    ):
        """
        Obtiene registros de una cuenta dentro de un rango.
        """

        return (
            self.db.query(LibroMayor)
            .filter(
                LibroMayor.tipo_cuenta == account,
                LibroMayor.fecha_contabilizacion.between(
                    start_date,
                    end_date,
                ),
            )
            .yield_per(self.BATCH_SIZE)
            .all()
        )

    def get_by_tipo_cuenta(
        self,
        tipo_cuenta: str,
    ):
        """
        Obtiene todos los registros de una cuenta.
        Usar únicamente cuando realmente se requiera.
        """

        return (
            self.db.query(LibroMayor)
            .filter(
                LibroMayor.tipo_cuenta == tipo_cuenta
            )
            .yield_per(self.BATCH_SIZE)
            .all()
        )

    def get_by_rule(
        self,
        rule_id: int,
    ):
        """
        Registros clasificados por una regla específica.
        """

        return (
            self.db.query(LibroMayor)
            .filter(
                LibroMayor.id_regla == rule_id
            )
            .yield_per(self.BATCH_SIZE)
            .all()
        )

    def get_libro_mayor_by_account(
        self,
        start_date: date,
        end_date: date,
        account: str,
    ):
        """
        Consulta principal usada por la pantalla.
        """

        return (
            self.db.query(LibroMayor)
            .filter(
                LibroMayor.fecha_contabilizacion.between(
                    start_date,
                    end_date,
                ),
                LibroMayor.tipo_cuenta == account,
            )
            .all()
        )

    def get_last_libro_mayor(
        self,
        account: str,
    ):
        """
        Última sincronización registrada.
        """

        return (
            self.db.query(LibroMayor)
            .filter(
                LibroMayor.tipo_cuenta == account
            )
            .order_by(
                LibroMayor.fecha_actualizacion.desc()
            )
            .first()
        )

    # =====================================================
    # REPROCESAMIENTO
    # =====================================================

    def get_candidates_by_rule(
        self,
        regla: ReglasGastos,
    ):
        """
        Obtiene únicamente los registros que potencialmente
        podrían ser afectados por una regla.
        """

        query = self.db.query(LibroMayor)

        if regla.cuenta:
            query = query.filter(
                LibroMayor.cuenta_asociada == regla.cuenta
            )

        if regla.cuenta_contrapartida:
            query = query.filter(
                LibroMayor.cuenta_contrapartida
                == regla.cuenta_contrapartida
            )

        if regla.centro_costo:
            query = query.filter(
                LibroMayor.centro_costo
                == regla.centro_costo
            )

        if regla.monto_min is not None:
            query = query.filter(
                LibroMayor.cargo_abono_ml >= regla.monto_min
            )

        if regla.monto_max is not None:
            query = query.filter(
                LibroMayor.cargo_abono_ml <= regla.monto_max
            )

        return query.yield_per(self.BATCH_SIZE).all()

    def get_records_by_deleted_rule(
        self,
        rule_id: int,
    ):
        """
        Registros que estaban clasificados con una regla eliminada.
        """

        return (
            self.db.query(LibroMayor)
            .filter(
                LibroMayor.id_regla == rule_id
            )
            .yield_per(self.BATCH_SIZE)
            .all()
        )

    # =====================================================
    # UPSERT
    # =====================================================

    def upsert(
        self,
        df: pd.DataFrame,
    ):

        if df.empty:
            return {"procesados": 0}

        df = df.where(
            pd.notnull(df),
            None,
        )

        df = df.replace(
            {
                np.nan: None,
                "nan": None,
                "NaN": None,
                "NAN": None,
                "None": None,
            }
        )
        registros = df.to_dict(
            orient="records"
        )

        stmt = insert(
            LibroMayor
        ).values(registros)

        update_columns = {
            column.name: getattr(
                stmt.excluded,
                column.name,
            )
            for column in LibroMayor.__table__.columns
            if column.name
            not in (
                "transaccion_id",
                "linea",
                "created_at",
                "created_by",
            )
        }

        stmt = stmt.on_conflict_do_update(
            index_elements=[
                "transaccion_id",
                "linea",
            ],
            set_=update_columns,
        )

        self.db.execute(stmt)
        self.db.commit()

        return {
            "procesados": len(registros)
        }

    # =====================================================
    # ACTUALIZACIÓN MASIVA
    # =====================================================

    def update_classification(
        self,
        df: pd.DataFrame,
    ):

        if df.empty:
            return {
                "procesados": 0
            }

        df = df.where(
            pd.notnull(df),
            None,
        )

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
        ].to_dict(
            orient="records"
        )

        for i in range(
            0,
            len(registros),
            self.BATCH_SIZE,
        ):

            lote = registros[
                i : i + self.BATCH_SIZE
            ]

            self.db.bulk_update_mappings(
                LibroMayor,
                lote,
            )

        self.db.commit()

        return {
            "procesados": len(registros),
            "lotes": math.ceil(
                len(registros)
                / self.BATCH_SIZE
            ),
        }

    # =====================================================
    # DATAFRAME
    # =====================================================

    def to_dataframe(
        self,
        registros,
    ) -> pd.DataFrame:

        if not registros:
            return pd.DataFrame()

        return pd.DataFrame(
            [
                {
                    column.name: getattr(
                        row,
                        column.name,
                    )
                    for column in LibroMayor.__table__.columns
                }
                for row in registros
            ]
        )

    def to_dataframe_date(
        self,
        registros,
    ) -> pd.DataFrame:

        df = self.to_dataframe(
            registros
        )

        if df.empty:
            return df

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

        df["nmes"] = df["mes"].map(
            meses
        )

        return df