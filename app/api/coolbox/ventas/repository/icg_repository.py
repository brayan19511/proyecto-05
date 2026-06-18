# app/api/coolbox/ventas/repository/icg_repository.py

from datetime import date, timedelta
from sqlalchemy import text


class IcgRepository:
    def __init__(self, db_icg=None, db_cic=None):
        self.db_icg = db_icg
        self.db_cic = db_cic

    def get_productos(self):
        sql = text("""
            SELECT 
                T1.CODARTICULO,
                T1.REFPROVEEDOR,
                T1.DESCRIPCION,
                T1.DESCRIPADIC,
                T6.DESCRIPCION AS MARCA,
                T5.CO_RUBR,
                T2.DESCRIPCION AS RUBRO,
                T5.CO_FAMI,
                T3.DESCRIPCION AS FAMILIA,
                T5.CO_SFAM,
                T4.DESCRIPCION AS SUBFAMILIA,
                T5.CODIGOSAP,
                T5.ESTADOSARTICULOS,
                T5.TI_ITEM,
                T5.ORIGEN,
                T1.DESCATALOGADO
            FROM ARTICULOS AS T1
            INNER JOIN SECCIONES AS T2
                ON T1.DPTO = T2.NUMDPTO
                AND T1.SECCION = T2.NUMSECCION
            LEFT JOIN FAMILIAS AS T3
                ON T1.DPTO = T3.NUMDPTO
                AND T1.SECCION = T3.NUMSECCION
                AND T1.FAMILIA = T3.NUMFAMILIA
            LEFT JOIN SUBFAMILIAS AS T4
                ON T1.DPTO = T4.NUMDPTO
                AND T1.SECCION = T4.NUMSECCION
                AND T1.FAMILIA = T4.NUMFAMILIA
                AND T1.SUBFAMILIA = T4.NUMSUBFAMILIA
            LEFT JOIN ARTICULOSCAMPOSLIBRES AS T5
                ON T1.CODARTICULO = T5.CODARTICULO
            LEFT JOIN MARCA AS T6
                ON T1.MARCA = T6.CODMARCA
        """)

        return self.db_icg.execute(sql).mappings().all()

    def get_ventas(self, fecha: date):
        fecha_fin = fecha + timedelta(days=1)

        sql = text("""
            SELECT 
                t1.FECHACREACION,
                t1.FECHA,
                t1.CODVENDEDOR,
                t1.CODCLIENTE,
                t1.NUMSERIE,
                t1.NUMALBARAN,
                t1.TIPODOC,
                t1.NUMFAC,
                t2.CODALMACEN,
                t2.CODARTICULO,
                t2.UNIDADESTOTAL,
                t2.PRECIO,
                t2.DTO,
                t2.TOTAL,
                t2.IVA,
                t2.ABONODE_NUMSERIE,
                t2.ABONODE_NUMALBARAN,
                t3.TIPOFACT,
                t3.CANAL_VENTA,
                t3.NRO_PEDIDO,
                t4.PEDIDOVTEX,
                t5.CODFORMAPAGO
            FROM albventacab t1
            INNER JOIN albventalin t2
                ON t1.NUMSERIE = t2.NUMSERIE
                AND t1.NUMALBARAN = t2.NUMALBARAN
            INNER JOIN FACTURASVENTACAMPOSLIBRES t3
                ON t1.NUMSERIE = t3.NUMSERIE
                AND t1.NUMFAC = t3.NUMFACTURA
            LEFT JOIN ALBVENTACAMPOSLIBRES t4 WITH(NOLOCK)
                ON t4.NUMSERIE = t1.NUMSERIE
                AND t4.NUMALBARAN = t1.NUMALBARAN
            LEFT JOIN TESORERIA t5
                ON t5.SERIE = t1.NUMSERIE
                AND t5.NUMERO = t1.NUMFAC
                AND t5.CODFORMAPAGO = 15
            WHERE t1.FECHA >= :fecha_inicio
            AND t1.FECHA < :fecha_fin
            AND t2.UNIDADESTOTAL <> 0
            AND t2.CODALMACEN NOT IN ('P01')
            AND t1.TIPODOC IN (5, 13, 37, 38)
        """)

        return (
            self.db_icg.execute(
                sql,
                {
                    "fecha_inicio": fecha,
                    "fecha_fin": fecha_fin,
                },
            )
            .mappings()
            .all()
        )

    def get_tiendas(self):
        sql = text("""
            SELECT DISTINCT
                T4.ALMA_STR_CODIGO,
                T4.ALMA_STR_DESCRIPCION,
                T4.ALMA_STR_CATEGORIA,
                T4.ALMA_STR_REGION,
                T6.TIE_STR_FORMATO,
                T4.ALMA_DEC_LATITUD,
                T4.ALMA_DEC_LONGITUD,
                T4.ALMA_DEC_METRAJE,
                T4.ALMA_STR_UBIGEO,
                T5.DEPARTAMENTO,
                T5.PROVINCIA,
                T5.DISTRITO
            FROM CIC.DBCOOLBOX.RASH.ALMACEN T4
            LEFT JOIN CIC.DBCOOLBOX.RASH.UBIGEO T5
                ON T4.ALMA_STR_UBIGEO = T5.ZipCodeStart
            LEFT JOIN BD_INTEGRACION.sistemaIntegrado.tienda T6
                ON T6.TIE_STR_CODIGO COLLATE Modern_Spanish_CI_AS = T4.ALMA_STR_CODIGO
        """)

        return self.db_icg.execute(sql).mappings().all()

    def obtener_totales_control_fuente(self, fecha: date):
        fecha_fin = fecha + timedelta(days=1)

        sql = text("""
            SELECT 
                COUNT(*) AS total_filas,
                COALESCE(SUM(t2.TOTAL), 0) AS suma_total,
                COALESCE(SUM(t2.UNIDADESTOTAL), 0) AS suma_cantidad
            FROM albventacab t1
            INNER JOIN albventalin t2
                ON t1.NUMSERIE = t2.NUMSERIE
                AND t1.NUMALBARAN = t2.NUMALBARAN
            WHERE t1.FECHA >= :fecha_inicio
            AND t1.FECHA < :fecha_fin
            AND t2.UNIDADESTOTAL <> 0
            AND t2.CODALMACEN NOT IN ('P01')
            AND t1.TIPODOC IN (5, 13, 37, 38)
        """)

        return (
            self.db_icg.execute(
                sql,
                {
                    "fecha_inicio": fecha,
                    "fecha_fin": fecha_fin,
                },
            )
            .mappings()
            .one()
        )
