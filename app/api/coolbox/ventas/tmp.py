  # sql = text("""select  
        #             T1.FECHACREACION,
        #             T1.CODVENDEDOR,
        #             T1.CODCLIENTE,
        #             T1.NUMSERIE + '-' + RIGHT('0000000000' + CAST(T1.NUMALBARAN AS VARCHAR(10)), 10) AS DOCUMENTO,  
        #             T2.CODALMACEN,
        #             T2.CODARTICULO,
        #             SUM(T2.UNIDADESTOTAL) AS UNIDADESTOTAL,
        #             T2.PRECIO,
        #             T2.DTO,
        #             SUM(T2.TOTAL) AS TOTAL,
        #             T2.IVA,
        #             T3.TIPOFACT,
        #             CASE WHEN T3.CANAL_VENTA IN('CLICK & COLLECT','C&C')  THEN 'C&C'
        #                 WHEN T3.CANAL_VENTA IN('360','VENTA 360')        THEN '360'  
        #                 WHEN T3.CANAL_VENTA IN('E-COMMERCE','ECOMMERCE') THEN 'E-COMMERCE'  
        #                 WHEN T5.CODFORMAPAGO = '15'                      THEN 'RAPPI'
        #                 WHEN T3.CANAL_VENTA   = 'PYA'                    THEN 'PYA'
        #                 WHEN T1.TIPODOC IN (17,18) AND LEN(ISNULL(T3.NRO_PEDIDO,T4.PEDIDOVTEX)) > 0 AND ISNULL(T3.NRO_PEDIDO,T4.PEDIDOVTEX) COLLATE MODERN_SPANISH_CI_AS  = T2.ABONODE_NUMSERIE + '-' + RIGHT('0000000000' + CAST(T2.ABONODE_NUMALBARAN AS VARCHAR(10)), 10) THEN '360'  
        #                 WHEN T1.TIPODOC IN (17,18) AND LEN(ISNULL(T3.NRO_PEDIDO,T4.PEDIDOVTEX)) > 0 AND ISNULL(T3.NRO_PEDIDO,T4.PEDIDOVTEX) COLLATE MODERN_SPANISH_CI_AS != T2.ABONODE_NUMSERIE + '-' + RIGHT('0000000000' + CAST(T2.ABONODE_NUMALBARAN AS VARCHAR(10)), 10) THEN 'E-COMMERCE'  
        #                 ELSE 'TIENDA' END AS CANAL
        #             from albventacab t1
        #             inner join albventalin t2 
        #                 on t1.NUMSERIE=t2.NUMSERIE
        #                 and t1.NUMALBARAN=T2.NUMALBARAN
        #             INNER JOIN FACTURASVENTACAMPOSLIBRES T3
        #                 ON T1.NUMSERIE=T3.NUMSERIE 
        #                 AND T1.NUMFAC=T3.NUMFACTURA
        #             LEFT JOIN ALBVENTACAMPOSLIBRES         T4  WITH(NOLOCK)  
        #             ON T4.NUMSERIE    = T1.NUMSERIE  
        #             AND T4.NUMALBARAN  = T1.NUMALBARAN  
        #             LEFT JOIN TESORERIA                    T5 
        #             ON T5.SERIE  = T1.NUMSERIE  
        #             AND T5.NUMERO = T1.NUMFAC  
        #             AND T5.CODFORMAPAGO = 15  

        #             where t1.tipodoc in (5,13,37,38)
        #             AND CAST(T1.FECHA AS DATE) BETWEEN :start_date AND :end_date
        #             --AND YEAR(t1.FECHA)=2025 AND MONTH(t1.FECHA)=1
        #             AND T2.UNIDADESTOTAL<>0
        #             and t2.CODALMACEN not in ('P01')
        #             --AND T1.NUMSERIE='BAKM' AND NUMFAC=0000006524
        #             GROUP BY 
        #             T1.FECHACREACION,
        #             T1.CODVENDEDOR,
        #             T1.CODCLIENTE,
        #             T1.NUMSERIE ,
        #             T1.NUMALBARAN , 
        #             T2.CODALMACEN,
        #             --T2.*,
        #             T2.CODARTICULO,
        #             T2.PRECIO,
        #             T2.DTO,
        #             T2.IVA,
        #             T3.TIPOFACT,
        #             CASE WHEN T3.CANAL_VENTA IN('CLICK & COLLECT','C&C')  THEN 'C&C'
        #                 WHEN T3.CANAL_VENTA IN('360','VENTA 360')        THEN '360'  
        #                 WHEN T3.CANAL_VENTA IN('E-COMMERCE','ECOMMERCE') THEN 'E-COMMERCE'  
        #                 WHEN T5.CODFORMAPAGO = '15'                      THEN 'RAPPI'
        #                 WHEN T3.CANAL_VENTA   = 'PYA'                    THEN 'PYA'
        #                 WHEN T1.TIPODOC IN (17,18) AND LEN(ISNULL(T3.NRO_PEDIDO,T4.PEDIDOVTEX)) > 0 AND ISNULL(T3.NRO_PEDIDO,T4.PEDIDOVTEX) COLLATE MODERN_SPANISH_CI_AS  = T2.ABONODE_NUMSERIE + '-' + RIGHT('0000000000' + CAST(T2.ABONODE_NUMALBARAN AS VARCHAR(10)), 10) THEN '360'  
        #                 WHEN T1.TIPODOC IN (17,18) AND LEN(ISNULL(T3.NRO_PEDIDO,T4.PEDIDOVTEX)) > 0 AND ISNULL(T3.NRO_PEDIDO,T4.PEDIDOVTEX) COLLATE MODERN_SPANISH_CI_AS != T2.ABONODE_NUMSERIE + '-' + RIGHT('0000000000' + CAST(T2.ABONODE_NUMALBARAN AS VARCHAR(10)), 10) THEN 'E-COMMERCE'  
        #                 ELSE 'TIENDA' END -- <--- Corregido: Agregado el 'END' y removido el 'AS CANAL'
        #             """)
        