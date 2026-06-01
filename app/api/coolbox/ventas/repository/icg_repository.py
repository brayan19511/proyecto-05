# app/api/coolbox/ventas/ventas_repository.py
from sqlalchemy import text


class IcgRepository:
    def __init__(self, db):
        self.db = db

    def get_productos(self):
        sql = text(
            """SELECT 
                T1.CODARTICULO, T1.REFPROVEEDOR, T1.DESCRIPCION , T1.DESCRIPADIC,
                T6.DESCRIPCION AS MARCA, 
                T5.CO_RUBR, 
                T2.DESCRIPCION AS RUBRO, 
                T5.CO_FAMI, T3.DESCRIPCION AS FAMILIA, 
                T5.CO_SFAM, T4.DESCRIPCION AS SUBFAMILIA, 
                T5.CODIGOSAP, T5.ESTADOSARTICULOS, T5.TI_ITEM, T5.ORIGEN,T1.DESCATALOGADO
                FROM     ARTICULOS AS T1 
                INNER JOIN SECCIONES AS T2 
                    ON T1.DPTO = T2.NUMDPTO AND T1.SECCION = T2.NUMSECCION 
                LEFT OUTER JOIN FAMILIAS AS T3
                    ON T1.DPTO = T3.NUMDPTO AND T1.SECCION = T3.NUMSECCION AND T1.FAMILIA = T3.NUMFAMILIA 
                LEFT OUTER JOIN SUBFAMILIAS AS T4 
                    ON T1.DPTO = T4.NUMDPTO AND T1.SECCION = T4.NUMSECCION AND T1.FAMILIA = T4.NUMFAMILIA AND T1.SUBFAMILIA = T4.NUMSUBFAMILIA 
                LEFT OUTER JOIN ARTICULOSCAMPOSLIBRES AS T5 
                    ON T1.CODARTICULO = T5.CODARTICULO 
                LEFT OUTER JOIN MARCA AS T6 
                    ON T1.MARCA = T6.CODMARCA
                WHERE  (T1.CODARTICULO NOT IN (32869))"""
        )
        result = self.db.execute(sql)
        return result.mappings().all()

    def get_ventas(self, fecha):
        sql = text("""
                SELECT 
                    t1.FECHACREACION, t1.FECHA, t1.CODVENDEDOR, t1.CODCLIENTE, t1.NUMSERIE, t1.NUMALBARAN, t1.TIPODOC, t1.NUMFAC,
                    t2.CODALMACEN, t2.CODARTICULO, t2.UNIDADESTOTAL, t2.PRECIO, t2.DTO, t2.TOTAL, t2.IVA,
                    t2.ABONODE_NUMSERIE, t2.ABONODE_NUMALBARAN,
                    t3.TIPOFACT, t3.CANAL_VENTA, t3.NRO_PEDIDO,
                    t4.PEDIDOVTEX,
                    t5.CODFORMAPAGO
                FROM albventacab t1
                INNER JOIN albventalin t2 ON t1.NUMSERIE = t2.NUMSERIE AND t1.NUMALBARAN = t2.NUMALBARAN
                INNER JOIN FACTURASVENTACAMPOSLIBRES T3 ON T1.NUMSERIE = T3.NUMSERIE AND T1.NUMFAC = T3.NUMFACTURA
                LEFT JOIN ALBVENTACAMPOSLIBRES T4 WITH(NOLOCK) ON T4.NUMSERIE = T1.NUMSERIE AND T4.NUMALBARAN = T1.NUMALBARAN  
                LEFT JOIN TESORERIA T5 ON T5.SERIE = T1.NUMSERIE AND T5.NUMERO = T1.NUMFAC AND T5.CODFORMAPAGO = 15  
                WHERE CAST(t1.FECHA AS DATE) = :fecha
                AND t2.UNIDADESTOTAL <> 0
                AND t2.CODALMACEN NOT IN ('P01')
                AND t1.tipodoc IN (5,13,37,38)
            """)
        result = self.db.execute(
            sql,
            {"fecha": fecha},
        )

        return result.mappings().all()

    def obtener_totales_control_fuente(self, fecha):
        sql = text("""
            SELECT 
                COUNT(*) as total_filas,
                SUM(t2.TOTAL) as suma_total
            FROM albventacab t1
            INNER JOIN albventalin t2 ON t1.NUMSERIE = t2.NUMSERIE AND t1.NUMALBARAN = t2.NUMALBARAN
            WHERE CAST(t1.FECHA AS DATE) = :fecha
            AND t2.UNIDADESTOTAL <> 0
            AND t2.CODALMACEN NOT IN ('P01')
            AND t1.tipodoc IN (5,13,37,38)
        """)
        return self.db.execute(sql, {"fecha": fecha}).mappings().one()
