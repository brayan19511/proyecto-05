from dataclasses import dataclass
from enum import StrEnum

from app.core.exceptions import ValidationError


class TableKind(StrEnum):
    TRANSACTIONAL = "transactional"
    MASTER = "master"


class MasterStorageMode(StrEnum):
    LATEST = "latest"
    SNAPSHOT = "snapshot"


@dataclass(frozen=True)
class IcgTableConfig:
    name: str
    kind: TableKind
    sql: str
    master_storage_mode: MasterStorageMode | None = None


ICG_TABLES: dict[str, IcgTableConfig] = {
    "albventacab": IcgTableConfig(
        name="albventacab",
        kind=TableKind.TRANSACTIONAL,
        sql="""
            SELECT *
            FROM albventacab WITH (NOLOCK)
            WHERE fecha >= :business_date
              AND fecha < DATEADD(day, 1, :business_date)
        """,
    ),
    "albventalin": IcgTableConfig(
        name="albventalin",
        kind=TableKind.TRANSACTIONAL,
        sql="""
            SELECT l.*
            FROM albventalin l WITH (NOLOCK)
            INNER JOIN albventacab c WITH (NOLOCK)
              ON c.numserie = l.numserie
             AND c.numalbaran = l.numalbaran
             AND l.UNIDADESTOTAL != 0
            WHERE c.fecha >= :business_date
              AND c.fecha < DATEADD(day, 1, :business_date)
        """,
    ),
    "tesoreria": IcgTableConfig(
        name="tesoreria",
        kind=TableKind.TRANSACTIONAL,
        sql="""
            SELECT t3.*
            FROM tesoreria t3 WITH (NOLOCK)
            INNER JOIN albventacab t1 WITH (NOLOCK)
              ON t1.numserie = t3.serie
             AND t1.numfac = t3.numero
            WHERE t1.fecha >= :business_date
              AND t1.fecha < DATEADD(day, 1, :business_date)
        """,
    ),
    "facturasventa": IcgTableConfig(
        name="facturasventa",
        kind=TableKind.TRANSACTIONAL,
        sql="""
            SELECT *
            FROM FACTURASVENTA WITH (NOLOCK)
            WHERE fecha >= :business_date
              AND fecha < DATEADD(day, 1, :business_date)
        """,
    ),
    "facturasventacamposlibres": IcgTableConfig(
        name="facturasventacamposlibres",
        kind=TableKind.TRANSACTIONAL,
        sql="""
            SELECT t3.*
            FROM FACTURASVENTACAMPOSLIBRES t3 WITH (NOLOCK)
            INNER JOIN albventacab t1 WITH (NOLOCK)
              ON t1.numserie = t3.numserie
             AND t1.numfac = t3.numfactura
            WHERE t1.fecha >= :business_date
              AND t1.fecha < DATEADD(day, 1, :business_date)
        """,
    ),
    "albventacamposlibres": IcgTableConfig(
        name="albventacamposlibres",
        kind=TableKind.TRANSACTIONAL,
        sql="""
            SELECT t3.*
            FROM ALBVENTACAMPOSLIBRES t3 WITH (NOLOCK)
            INNER JOIN albventacab t1 WITH (NOLOCK)
              ON t1.numserie = t3.numserie
             AND t1.numalbaran = t3.numalbaran
            WHERE t1.fecha >= :business_date
              AND t1.fecha < DATEADD(day, 1, :business_date)
        """,
    ),
    "albcompracab": IcgTableConfig(
        name="albcompracab",
        kind=TableKind.TRANSACTIONAL,
        sql="""
            SELECT *
            FROM ALBCOMPRACAB WITH (NOLOCK)
            WHERE fechaalbaran >= :business_date
              AND fechaalbaran < DATEADD(day, 1, :business_date)
        """,
    ),
    "albcompralin": IcgTableConfig(
        name="albcompralin",
        kind=TableKind.TRANSACTIONAL,
        sql="""
            SELECT t2.*
            FROM ALBCOMPRACAB t1 WITH (NOLOCK)
            INNER JOIN ALBCOMPRALIN t2 WITH (NOLOCK)
              ON t2.NUMSERIE = t1.NUMSERIE
             AND t2.NUMALBARAN = t1.NUMALBARAN
             AND t2.N = t1.N
             AND t2.UNIDADESTOTAL != 0
            WHERE t1.fechaalbaran >= :business_date
              AND t1.fechaalbaran < DATEADD(day, 1, :business_date)
        """,
    ),
    "transpasoscab": IcgTableConfig(
        name="transpasoscab",
        kind=TableKind.TRANSACTIONAL,
        sql="""
            SELECT *
            FROM TRASPASOSCAB WITH (NOLOCK)
            WHERE fecha >= :business_date
              AND fecha < DATEADD(day, 1, :business_date)
        """,
    ),
    "moviments": IcgTableConfig(
        name="moviments",
        kind=TableKind.TRANSACTIONAL,
        sql="""
            SELECT T2.*
            FROM TRASPASOSCAB T1 WITH (NOLOCK)
            INNER JOIN MOVIMENTS T2 WITH (NOLOCK)
              ON T2.SERIEDOC = T1.SERIE
             AND T2.NUMDOC = T1.NUMERO
            WHERE T1.fecha >= :business_date
              AND T1.fecha < DATEADD(day, 1, :business_date)
        """,
    ),
    "vista_articulos": IcgTableConfig(
        name="vista_articulos",
        kind=TableKind.MASTER,
        master_storage_mode=MasterStorageMode.LATEST,
        sql="SELECT * FROM VISTA_ARTICULOS",
    ),
    "sbo_articulos_costo": IcgTableConfig(
        name="sbo_articulos_costo",
        kind=TableKind.MASTER,
        master_storage_mode=MasterStorageMode.LATEST,
        sql="SELECT * FROM [BD_INTEGRACION].[sap].[SBO_ARTICULOS_COSTO]",
    ),
    "tiposdoc": IcgTableConfig(
        name="tiposdoc",
        kind=TableKind.MASTER,
        master_storage_mode=MasterStorageMode.LATEST,
        sql="SELECT * FROM tiposdoc",
    ),
    "vendedores": IcgTableConfig(
        name="vendedores",
        kind=TableKind.MASTER,
        master_storage_mode=MasterStorageMode.LATEST,
        sql="SELECT * FROM vendedores",
    ),
    "almacen": IcgTableConfig(
        name="almacen",
        kind=TableKind.MASTER,
        master_storage_mode=MasterStorageMode.LATEST,
        sql="SELECT * FROM almacen",
    ),
    "marcapropia": IcgTableConfig(
        name="marcapropia",
        kind=TableKind.MASTER,
        master_storage_mode=MasterStorageMode.LATEST,
        sql="SELECT * FROM [BD_INTEGRACION].SISTEMAINTEGRADO.MARCAPROPIA",
    ),
    "stockcierreanual": IcgTableConfig(
        name="stockcierreanual",
        kind=TableKind.MASTER,
        master_storage_mode=MasterStorageMode.SNAPSHOT,
        sql="""
            SELECT *
            FROM [BD_INTEGRACION].SISTEMAINTEGRADO.STOCKCIERREANUAL
            WHERE empresa = 1
              AND year(fecha) >= year(getdate()) - 1
        """,
    ),
}


def get_icg_table_config(table_name: str) -> IcgTableConfig:
    normalized = table_name.strip().lower()
    try:
        return ICG_TABLES[normalized]
    except KeyError as exc:
        raise ValidationError(f"Tabla ICG no soportada: {table_name}") from exc
