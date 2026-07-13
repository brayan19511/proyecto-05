# app\api\libro_mayor\repository\libro_mayor_repository.py
from calendar import monthrange
from datetime import date
import math
import numpy as np
import pandas as pd

from sqlalchemy import and_, extract, func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.api.finance.libro_mayor.constants import TEXT_SEARCH_COLUMNS
from app.models.finance.libro_mayor_model import (
    LibroMayor,
    ReglasGastos,
)


class LibroMayorRepository:

    BATCH_SIZE = 5000
    EXPORT_COLUMNS = [
        "tiene_regla",
        "id_regla",
        "nombre_cuenta",
        "codigo",
        "subcodigo",
        "fecha_contabilizacion",
        "fecha_documento",
        "numero_documento",
        "transaccion_id",
        "folio",
        "tipo_documento",
        "linea",
        "cuenta_asociada",
        "nombre_cuenta_asociada",
        "proveedor",
        "descripcion",
        "comentario_linea",
        "cuenta_contrapartida",
        "nombre_contrapartida",
        "referencia_1",
        "referencia_2",
        "referencia_3",
        "cargo_abono_ml",
        "cargo_abono_me",
        "centro_costo",
        "centro_area",
        "nombre_area",
    ]

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
            .filter(LibroMayor.tipo_cuenta == tipo_cuenta)
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
            .filter(LibroMayor.id_regla == rule_id)
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

    def get_export_rows_by_account(
        self,
        start_date: date,
        end_date: date,
        account: str,
    ):
        columns = [getattr(LibroMayor, column) for column in self.EXPORT_COLUMNS]

        stmt = (
            select(
                *columns,
                extract("year", LibroMayor.fecha_contabilizacion).label("anio"),
                extract("month", LibroMayor.fecha_contabilizacion).label("mes"),
            )
            .where(
                LibroMayor.fecha_contabilizacion.between(
                    start_date,
                    end_date,
                ),
                LibroMayor.tipo_cuenta == account,
            )
            .order_by(
                LibroMayor.fecha_contabilizacion.asc(),
                LibroMayor.numero_documento.asc(),
            )
        )

        return self.db.execute(stmt).mappings().all()

    def get_last_libro_mayor(
        self,
        account: str,
    ):
        """
        Última sincronización registrada.
        """

        return (
            self.db.query(LibroMayor)
            .filter(LibroMayor.tipo_cuenta == account)
            .order_by(LibroMayor.fecha_actualizacion.desc())
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

        candidate_conditions = []

        if regla.cuenta:
            candidate_conditions.append(
                LibroMayor.cuenta_asociada == regla.cuenta
            )

        if regla.cuenta_contrapartida:
            candidate_conditions.append(
                LibroMayor.cuenta_contrapartida == regla.cuenta_contrapartida
            )

        if regla.centro_costo:
            candidate_conditions.append(
                LibroMayor.centro_costo == regla.centro_costo
            )

        if regla.monto_min is not None:
            candidate_conditions.append(
                LibroMayor.cargo_abono_ml >= regla.monto_min
            )

        if regla.monto_max is not None:
            candidate_conditions.append(
                LibroMayor.cargo_abono_ml <= regla.monto_max
            )

        if regla.filtro_texto and regla.filtro_texto.strip():
            searchable_text = func.concat_ws(
                " ",
                *[
                    getattr(LibroMayor, column)
                    for column in TEXT_SEARCH_COLUMNS
                ],
            )
            candidate_conditions.append(
                func.lower(searchable_text).contains(
                    regla.filtro_texto.strip().casefold(),
                    autoescape=True,
                )
            )

        new_candidates = (
            and_(*candidate_conditions)
            if candidate_conditions
            else True
        )

        query = self.db.query(LibroMayor).filter(
            or_(
                LibroMayor.id_regla == regla.id_regla,
                new_candidates,
            )
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
            .filter(LibroMayor.id_regla == rule_id)
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

        total = len(df)

        for inicio in range(
            0,
            total,
            self.BATCH_SIZE,
        ):

            lote_df = df.iloc[inicio : inicio + self.BATCH_SIZE]

            registros = lote_df.to_dict(orient="records")

            stmt = insert(LibroMayor).values(registros)

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
            "procesados": total,
            "lotes": math.ceil(total / self.BATCH_SIZE),
        }

    # =====================================================
    # ACTUALIZACIÓN MASIVA
    # =====================================================

    def update_classification(
        self,
        df: pd.DataFrame,
    ):

        if df.empty:
            return {"procesados": 0}

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
        ].to_dict(orient="records")

        for i in range(
            0,
            len(registros),
            self.BATCH_SIZE,
        ):

            lote = registros[i : i + self.BATCH_SIZE]

            self.db.bulk_update_mappings(
                LibroMayor,
                lote,
            )

        self.db.commit()

        return {
            "procesados": len(registros),
            "lotes": math.ceil(len(registros) / self.BATCH_SIZE),
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

        df = self.to_dataframe(registros)

        if df.empty:
            return df

        df["anio"] = pd.to_datetime(df["fecha_contabilizacion"]).dt.year

        df["mes"] = pd.to_datetime(df["fecha_contabilizacion"]).dt.month

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

    def to_export_dataframe(
        self,
        registros,
    ) -> pd.DataFrame:

        df = self.to_dataframe_date(registros)

        if df.empty:
            return df

        column_order = [
            "tiene_regla",
            "id_regla",
            "nombre_cuenta",
            "codigo",
            "subcodigo",
            "anio",
            "mes",
            "nmes",
            "fecha_contabilizacion",
            "fecha_documento",
            "numero_documento",
            "transaccion_id",
            "folio",
            "tipo_documento",
            "linea",
            "cuenta_asociada",
            "nombre_cuenta_asociada",
            "proveedor",
            "descripcion",
            "comentario_linea",
            "cuenta_contrapartida",
            "nombre_contrapartida",
            "referencia_1",
            "referencia_2",
            "referencia_3",
            "cargo_abono_ml",
            "cargo_abono_me",
            "centro_costo",
            "centro_area",
            "nombre_area",
        ]

        df = df.reindex(columns=[c for c in column_order if c in df.columns])

        df = df.rename(
            columns={
                "tiene_regla": "Tiene Regla",
                "id_regla": "Id Regla",
                "nombre_cuenta": "Nombre de Cuenta",
                "codigo": "Código",
                "subcodigo": "Subcódigo",
                "anio": "Año",
                "mes": "Mes",
                "nmes": "Mes Nombre",
                "fecha_contabilizacion": "Fecha Contabilizacion",
                "fecha_documento": "Fecha Documento",
                "numero_documento": "Numero documento",
                "transaccion_id": "Transaccion Id",
                "folio": "Folio",
                "tipo_documento": "Tipo Documento",
                "linea": "Linea",
                "cuenta_asociada": "Cuenta Asociada",
                "nombre_cuenta_asociada": "Nombre Cuenta Asociada",
                "proveedor": "Proveedor",
                "descripcion": "Descripcion",
                "comentario_linea": "Comentario Linea",
                "cuenta_contrapartida": "Cuenta Contrapartida",
                "nombre_contrapartida": "Nombre Contrapartida",
                "referencia_1": "Referencia 1",
                "referencia_2": "Referencia 2",
                "referencia_3": "Referencia 3",
                "cargo_abono_ml": "Importe Soles",
                "cargo_abono_me": "Importe Dolares",
                "centro_costo": "Centro Costo",
                "centro_area": "Centro Area",
                "nombre_area": "Nombre Area",
            }
        )

        return df

    def to_export_dataframe_from_rows(
        self,
        rows,
    ) -> pd.DataFrame:
        if not rows:
            return pd.DataFrame()

        df = pd.DataFrame([dict(row) for row in rows])

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

        df["anio"] = df["anio"].astype(int)
        df["mes"] = df["mes"].astype(int)
        df["nmes"] = df["mes"].map(meses)

        column_order = [
            "tiene_regla",
            "id_regla",
            "nombre_cuenta",
            "codigo",
            "subcodigo",
            "anio",
            "mes",
            "nmes",
            "fecha_contabilizacion",
            "fecha_documento",
            "numero_documento",
            "transaccion_id",
            "folio",
            "tipo_documento",
            "linea",
            "cuenta_asociada",
            "nombre_cuenta_asociada",
            "proveedor",
            "descripcion",
            "comentario_linea",
            "cuenta_contrapartida",
            "nombre_contrapartida",
            "referencia_1",
            "referencia_2",
            "referencia_3",
            "cargo_abono_ml",
            "cargo_abono_me",
            "centro_costo",
            "centro_area",
            "nombre_area",
        ]

        df = df.reindex(columns=[c for c in column_order if c in df.columns])

        return df.rename(
            columns={
                "tiene_regla": "Tiene Regla",
                "id_regla": "Id Regla",
                "nombre_cuenta": "Nombre de Cuenta",
                "codigo": "Codigo",
                "subcodigo": "Subcodigo",
                "anio": "Anio",
                "mes": "Mes",
                "nmes": "Mes Nombre",
                "fecha_contabilizacion": "Fecha Contabilizacion",
                "fecha_documento": "Fecha Documento",
                "numero_documento": "Numero documento",
                "transaccion_id": "Transaccion Id",
                "folio": "Folio",
                "tipo_documento": "Tipo Documento",
                "linea": "Linea",
                "cuenta_asociada": "Cuenta Asociada",
                "nombre_cuenta_asociada": "Nombre Cuenta Asociada",
                "proveedor": "Proveedor",
                "descripcion": "Descripcion",
                "comentario_linea": "Comentario Linea",
                "cuenta_contrapartida": "Cuenta Contrapartida",
                "nombre_contrapartida": "Nombre Contrapartida",
                "referencia_1": "Referencia 1",
                "referencia_2": "Referencia 2",
                "referencia_3": "Referencia 3",
                "cargo_abono_ml": "Importe Soles",
                "cargo_abono_me": "Importe Dolares",
                "centro_costo": "Centro Costo",
                "centro_area": "Centro Area",
                "nombre_area": "Nombre Area",
            }
        )

    def export_dataframe_by_account(
        self,
        start_date: date,
        end_date: date,
        account: str,
    ) -> pd.DataFrame:
        rows = self.get_export_rows_by_account(
            start_date=start_date,
            end_date=end_date,
            account=account,
        )

        return self.to_export_dataframe_from_rows(rows)

    # =====================================================
    # DATAFRAME
    # =====================================================
    def get_resumen(
        self,
        start_date,
        end_date,
        account,
    ):

        return (
            self.db.query(
                func.extract(
                    "year",
                    LibroMayor.fecha_contabilizacion,
                ).label("anio"),
                func.extract(
                    "month",
                    LibroMayor.fecha_contabilizacion,
                ).label("mes"),
                LibroMayor.codigo,
                LibroMayor.subcodigo,
                LibroMayor.nombre_cuenta,
                LibroMayor.proveedor,
                func.count().label("cantidad_registros"),
                func.sum(LibroMayor.cargo_abono_ml).label("importe_soles"),
                func.sum(LibroMayor.cargo_abono_me).label("importe_dolares"),
            )
            .filter(
                LibroMayor.tipo_cuenta == account,
                LibroMayor.fecha_contabilizacion.between(
                    start_date,
                    end_date,
                ),
            )
            .group_by(
                func.extract(
                    "year",
                    LibroMayor.fecha_contabilizacion,
                ),
                func.extract(
                    "month",
                    LibroMayor.fecha_contabilizacion,
                ),
                LibroMayor.codigo,
                LibroMayor.subcodigo,
                LibroMayor.nombre_cuenta,
                LibroMayor.proveedor,
            )
            .order_by(
                "anio",
                "mes",
                LibroMayor.codigo,
            )
            .all()
        )

    def get_resumen_detalle(
        self,
        start_date,
        end_date,
        account,
        codigo: str | None = None,
        subcodigo: str | None = None,
        proveedor: str | None = None,
        anio: int | None = None,
        mes: int | None = None,
    ):

        if anio and mes:
            month_start = date(anio, mes, 1)
            month_end = date(anio, mes, monthrange(anio, mes)[1])
            start_date = max(start_date, month_start)
            end_date = min(end_date, month_end)

        query = self.db.query(LibroMayor).filter(
            LibroMayor.tipo_cuenta == account,
            LibroMayor.fecha_contabilizacion.between(
                start_date,
                end_date,
            ),
        )

        if codigo:
            query = query.filter(LibroMayor.codigo == codigo)

        if subcodigo:
            query = query.filter(LibroMayor.subcodigo == subcodigo)

        if proveedor:
            query = query.filter(LibroMayor.proveedor == proveedor)
            
        if anio and not mes:
            query = query.filter(
                extract(
                    "year",
                    LibroMayor.fecha_contabilizacion
                ) == anio
            )

        if mes and not anio:
            query = query.filter(
                extract(
                    "month",
                    LibroMayor.fecha_contabilizacion
                ) == mes
            )

        return query.order_by(
            LibroMayor.fecha_contabilizacion.asc(),
            LibroMayor.numero_documento.asc(),
        ).all()
