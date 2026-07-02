# app\api\libro_mayor\repository\sap_finance_repository.py
from datetime import date
from typing import Optional
from sqlalchemy import text
from sqlalchemy.orm import Session

class SapRepository:
    ALLOWED_COMPANIES = [
        "SBO_RASH_PRODUCCION",
        "SBO_RASH_PRUEBA_240425",
    ]

    def __init__(self, db_sap: Session, company: str="SBO_RASH_PRODUCCION"):
        if company not in self.ALLOWED_COMPANIES:
            raise ValueError(f"Company '{company}' is not allowed for security reasons.")
        self.db = db_sap
        self.company = company

    def get_libro_mayor_by_account(self, start_date: date, end_date: date, account: str):
        """Consulta el libro mayor filtrando por rango de fechas y cuenta."""
        sql = text(f"""
            SELECT *
            FROM {self.company}."VW_LIBRO_MAYOR_PERSONALIZADO_2"
            WHERE "fecha_contabilizacion" BETWEEN :start_date AND :end_date
              AND "cuenta_asociada" LIKE :account
        """)
        
        result = self.db.execute(
            sql, 
            {"start_date": start_date, "end_date": end_date, "account": f"{account}%"}
        )
        return result.mappings().all()

    def get_libro_mayor_delta(self, account: str, start_date: date, end_date: Optional[date] = None):
        """
        Trae de SAP únicamente registros creados/modificados en un rango de fechas 
        o desde una fecha de inicio abierta, acotando las cuentas de manera segura.
        """
        # 1. Parámetros base para la query
        params = {
            "start_date": start_date,
            "account": f"{account}%",
        }
        
        # 2. Construcción de la condición de fechas dinámicamente
        # Condición por defecto (Filtro abierto hacia adelante)
        filtro_fechas = '( "fecha_creacion" >= :start_date OR "fecha_actualizacion" >= :start_date )'
        
        # Si el usuario envía una fecha fin, transformamos el filtro en un rango cerrado estricto
        if end_date:
            filtro_fechas = """(
                ("fecha_creacion" BETWEEN :start_date AND :end_date) 
                OR 
                ("fecha_actualizacion" BETWEEN :start_date AND :end_date)
            )"""
            params["end_date"] = end_date

        # 3. Armamos el SQL inyectando el bloque de fechas correspondiente
        sql = text(f"""
            SELECT * FROM {self.company}."VW_LIBRO_MAYOR_PERSONALIZADO_2"
            WHERE {filtro_fechas}
              AND "cuenta_asociada" LIKE :account
        """)
        
        result = self.db.execute(sql, params)
        
        return result.mappings().all()