# app/api/libro_mayor/libro_mayor_service.py

from datetime import date
from typing import Optional

import pandas as pd
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.api.finance.libro_mayor.constants import SUPPORTED_ACCOUNTS
from app.api.finance.libro_mayor.libro_mayor_schema import LibroMayorSap
from app.api.finance.libro_mayor.repository.libro_mayor_repository import (
    LibroMayorRepository,
)
from app.api.finance.libro_mayor.repository.sap_finance_repository import (
    SapRepository,
)
from app.api.finance.libro_mayor.service.libro_mayor_rules_service import (
    LibroMayorRulesService,
)
from app.models.finance.libro_mayor_model import LibroMayor


class LibroMayorService:

    def __init__(
        self,
        db_local: Session,
        db_sap: Session,
        company: str = "SBO_RASH_PRODUCCION",
        user_id: Optional[str] = None,
    ):
        self.user_id = user_id

        self.sap_repository = SapRepository(
            db_sap=db_sap,
            company=company,
        )

        self.libro_mayor_repository = LibroMayorRepository(db=db_local)

        self.rules_service = LibroMayorRulesService()

    def _validate_account(
        self,
        account: str,
    ):
        if account not in SUPPORTED_ACCOUNTS:
            raise HTTPException(
                status_code=400,
                detail=f"Cuenta no soportada: {account}",
            )

    def get_libro_mayor_by_sap(
        self,
        start_date: date,
        end_date: date,
        account: str,
    ) -> list[LibroMayorSap]:

        self._validate_account(account)

        return self.sap_repository.get_libro_mayor_by_account(
            start_date,
            end_date,
            account,
        )

    def get_libro_mayor_by_sap_delta(
        self,
        start_date: date,
        end_date: date | None,
        account: str,
    ):

        self._validate_account(account)

        return self.sap_repository.get_libro_mayor_delta(
            start_date=start_date,
            end_date=end_date,
            account=account,
        )

    def get_libro_mayor_by_account(
        self,
        start_date: date,
        end_date: date,
        account: str,
    ):

        self._validate_account(account)

        return self.libro_mayor_repository.get_libro_mayor_by_account(
            start_date,
            end_date,
            account,
        )

    def sync(
        self,
        start_date: date,
        end_date: date,
        account: str,
    ):
        data_sap = self.get_libro_mayor_by_sap(
            start_date,
            end_date,
            account,
        )
        reglas = self.libro_mayor_repository.get_reglas_activas()

        df = pd.DataFrame.from_records(data_sap)

        if df.empty:
            return {
                "procesados": 0,
                "clasificados": 0,
                "sin_clasificar": 0,
            }

        columnas_validas = {column.name for column in LibroMayor.__table__.columns}

        df = df[[c for c in df.columns if c in columnas_validas]]

        df = self.rules_service.aplicar(
            df=df,
            reglas=reglas,
            user_id=self.user_id,
        )

        resultado = self.libro_mayor_repository.upsert(df)

        return {
            "account": account,
            "registros_sap": len(df),
            "clasificados": int(df["tiene_regla"].sum()),
            "sin_clasificar": int((~df["tiene_regla"]).sum()),
            **resultado,
        }

    def sync_delta(
        self,
        start_date: date | None,
        end_date: date | None,
        account: str,
    ):

        self._validate_account(account)

        if not start_date:

            last_record = self.libro_mayor_repository.get_last_libro_mayor(account)

            if not last_record:
                return self.sync(
                    start_date=date(2026, 1, 1),
                    end_date=date.today(),
                    account=account,
                )

            start_date = last_record.fecha_actualizacion
            end_date = None

        data_sap = self.get_libro_mayor_by_sap_delta(
            start_date=start_date,
            end_date=end_date,
            account=account,
        )

        reglas = self.libro_mayor_repository.get_reglas_activas()

        df = pd.DataFrame.from_records(data_sap)

        if df.empty:
            return {
                "procesados": 0,
                "clasificados": 0,
                "sin_clasificar": 0,
            }

        columnas_validas = {column.name for column in LibroMayor.__table__.columns}

        df = df[[c for c in df.columns if c in columnas_validas]]

        df = self.rules_service.aplicar(
            df=df,
            reglas=reglas,
            user_id=self.user_id,
        )

        resultado = self.libro_mayor_repository.upsert(df)

        return {
            "account": account,
            "registros_sap": len(df),
            "clasificados": int(df["tiene_regla"].sum()),
            "sin_clasificar": int((~df["tiene_regla"]).sum()),
            **resultado,
        }

    def export_excel(
        self,
        start_date: date,
        end_date: date,
        account: str,
    ):

        return self.libro_mayor_repository.export_dataframe_by_account(
            start_date=start_date,
            end_date=end_date,
            account=account,
        )
