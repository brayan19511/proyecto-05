# app\api\libro_mayor\libro_mayor_service.py
from datetime import date
from fastapi import HTTPException
import pandas as pd
from sqlalchemy.orm import Session
from typing import Optional
from app.api.libro_mayor.libro_mayor_schema import LibroMayorSap
from app.api.libro_mayor.repository.libro_mayor_repository import LibroMayorRepository
from app.api.libro_mayor.repository.sap_finance_repository import SapRepository
from app.api.libro_mayor.service.libro_mayor_rules_service import LibroMayorRulesService
from app.models.finance.libro_mayor_model import LibroMayor

SUPPORTED_ACCOUNTS = {"95", "97"}


class LibroMayorService:
    def __init__(
        self,
        db_local: Session,
        db_sap: Session,
        company: str = "SBO_RASH_PRODUCCION",
        user_id: Optional[str] = None,
    ):
        self.company = company
        self.user_id = user_id
        self.sap_repository = SapRepository(db_sap=db_sap, company=company)
        self.libro_mayor_repository = LibroMayorRepository(db=db_local)
        self.rules_service = LibroMayorRulesService()

    # obtener desde sap
    def get_libro_mayor_by_sap(
        self, start_date: date, end_date: date, account: str
    ) -> list[LibroMayorSap]:
        # obtener desde sap
        if account not in SUPPORTED_ACCOUNTS:
            raise HTTPException(
                status_code=400, detail=f"Cuenta no soportada: {account}"
            )
        data_sap = self.sap_repository.get_libro_mayor_by_account(
            start_date, end_date, account
        )
        return data_sap

    def get_libro_mayor_by_account(self, start_date: date, end_date: date, account: str):
        if account not in SUPPORTED_ACCOUNTS:
            raise HTTPException(
                status_code=400, detail=f"Cuenta no soportada: {account}"
            )
        return self.libro_mayor_repository.get_libro_mayor_by_account(
            start_date, end_date, account
        )

    # procesar lo que obtenenoms de sap y guardamos en local con lo que tenemos en gastos
    def sync(self, start_date, end_date, account):

        data_sap = self.get_libro_mayor_by_sap(start_date, end_date, account)

        reglas = self.libro_mayor_repository.get_reglas_activas()

        df = pd.DataFrame.from_records(data_sap)
        # limpiamos columnas no mapeadas
        columnas_validas = {column.name for column in LibroMayor.__table__.columns}
        df = df[[c for c in df.columns if c in columnas_validas]]

        df = self.rules_service.aplicar(df=df, reglas=reglas, user_id=self.user_id)

        resultado = self.libro_mayor_repository.upsert(df)

        return {
            "account": account,
            "registros_sap": len(df),
            "clasificados": int(df["tiene_regla"].sum()),
            "sin_clasificar": int((~df["tiene_regla"]).sum()),
            **resultado,
        }
