# app\api\sap\finance\sap_finance_repository.py
from sqlalchemy import text


class SapFinanceRepository:

    ALLOWED_COMPANIES = [
        "SBO_RASH_PRODUCCION",
        "SBO_RASH_PRUEBA_240425",
    ]

    def __init__(self, db, company: str):

        if company not in self.ALLOWED_COMPANIES:
            raise ValueError("Company not allowed")

        self.db = db
        self.company = company

    def get_libro_mayor_by_account(
        self,
        start_date,
        end_date,
        account: str
    ):

        sql = text(f"""
            SELECT *
            FROM {self.company}."VW_LIBRO_MAYOR_PERSONALIZADO_2"
            WHERE "fecha_contabilizacion"
                  BETWEEN :start_date AND :end_date
              AND "cuenta_asociada"
                  LIKE :account
        """)

        result = self.db.execute(
            sql,
            {
                "start_date": start_date,
                "end_date": end_date,
                "account": f"{account}%"
            }
        )

        return result.mappings().all()
    def get_reglas_by_account():
        pass