# app/api/coolbox/ventas/ventas_repository.py
from sqlalchemy import text

class VentasRepository:
    def __init__(self, db):
        self.db = db

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