from fastapi import HTTPException
from sqlalchemy.orm import Session
import pandas as pd

from app.api.libro_mayor.repository.libro_mayor_repository import LibroMayorRepository
from app.api.libro_mayor.repository.reglas_gasto_respository import ReglasGatosRepository
from app.api.libro_mayor.service.libro_mayor_rules_service import LibroMayorRulesService


SUPPORTED_ACCOUNTS = {"95", "97"}


class LibroMayorReprocessService:
    def __init__(self,  db_local: Session,):
        self.libro_mayor_repository = LibroMayorRepository(db=db_local)
        self.reglas_repository = ReglasGatosRepository(db=db_local)
        self.rules_service = LibroMayorRulesService()
        self.user_id = None

    def reprocess_rule(self, rule_id: int):

        regla = self.reglas_repository.get_by_id(rule_id)

        if not regla:
            raise ValueError(
                f"Regla {rule_id} no encontrada"
            )

        registros = (
            self.libro_mayor_repository
            .get_candidates_by_rule(regla)
        )

        df = self.libro_mayor_repository.to_dataframe(
            registros
        )

        df = self.rules_service.reprocesar(
            df=df,
            reglas=[regla],
            user_id=self.user_id
        )

        self.libro_mayor_repository.update_classification(df)

        return {
            "procesados": len(df)
        }

    def reprocess_account(
        self,
        account: str
    ):
        if account not in SUPPORTED_ACCOUNTS:
            raise HTTPException(
                status_code=400, detail=f"Cuenta no soportada: {account}"
            )
        registros = (
            self.libro_mayor_repository
            .get_by_tipo_cuenta(account)
        )

        reglas = (
            self.reglas_repository
            .get_all_active()
        )

        df = self.libro_mayor_repository.to_dataframe(
            registros
        )

        df = self.rules_service.reprocesar(
            df=df,
            reglas=reglas,
            user_id=self.user_id
        )

        self.libro_mayor_repository.update_classification(df)

        return {
            "procesados": len(df)
        }

    def reprocess_all(self):

        registros = (
            self.libro_mayor_repository
            .get_all()
        )

        reglas = (
            self.reglas_repository
            .get_all_active()
        )

        df = self.libro_mayor_repository.to_dataframe(
            registros
        )

        df = self.rules_service.reprocesar(
            df=df,
            reglas=reglas,
            user_id=self.user_id
        )

        self.libro_mayor_repository.update_classification(df)

        return {
            "procesados": len(df)
        }

    def reprocess_deleted_rule(
        self,
        rule_id: int
    ):

        registros = (
            self.libro_mayor_repository
            .get_by_rule(rule_id)
        )

        reglas = (
            self.reglas_repository
            .get_all_active()
        )

        df = self.libro_mayor_repository.to_dataframe(
            registros
        )

        df = self.rules_service.reprocesar(
            df=df,
            reglas=reglas,
            user_id=self.user_id
        )

        self.libro_mayor_repository.update_classification(df)

        return {
            "procesados": len(df)
        }
