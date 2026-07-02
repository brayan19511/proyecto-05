# app/api/libro_mayor/service/libro_mayor_reprocess_service.py

from datetime import date

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.api.libro_mayor.repository.libro_mayor_repository import (
    LibroMayorRepository,
)
from app.api.libro_mayor.repository.reglas_gastos_repository import (
    ReglasGastosRepository,
)
from app.api.libro_mayor.service.libro_mayor_rules_service import (
    LibroMayorRulesService,
)

SUPPORTED_ACCOUNTS = {"95", "97"}


class LibroMayorReprocessService:

    def __init__(
        self,
        db_local: Session,
        user_id: str | None = None,
    ):
        self.user_id = user_id

        self.libro_mayor_repository = (
            LibroMayorRepository(db=db_local)
        )

        self.reglas_repository = (
            ReglasGastosRepository(db=db_local)
        )

        self.rules_service = (
            LibroMayorRulesService()
        )

    def _validate_account(
        self,
        account: str,
    ):
        if account not in SUPPORTED_ACCOUNTS:
            raise HTTPException(
                status_code=400,
                detail=f"Cuenta no soportada: {account}",
            )

    def _get_active_rules(self):
        return (
            self.reglas_repository
            .get_all_active()
        )

    def reprocess_rule(
        self,
        rule_id: int,
    ):
        """
        Reprocesa únicamente los registros
        potencialmente afectados por una regla.
        """

        regla = (
            self.reglas_repository
            .get_by_id(rule_id)
        )

        if not regla:
            raise ValueError(
                f"Regla {rule_id} no encontrada"
            )

        registros = (
            self.libro_mayor_repository
            .get_candidates_by_rule(regla)
        )

        df = (
            self.libro_mayor_repository
            .to_dataframe(registros)
        )

        if df.empty:
            return {
                "procesados": 0,
                "rule_id": rule_id,
            }

        reglas = self._get_active_rules()

        df = self.rules_service.reprocesar(
            df=df,
            reglas=reglas,
            user_id=self.user_id,
        )

        resultado = (
            self.libro_mayor_repository
            .update_classification(df)
        )

        return {
            "rule_id": rule_id,
            **resultado,
        }

    def reprocess_account(
        self,
        account: str,
    ):
        """
        Reprocesa toda una cuenta.
        Ejemplo:
        95
        97
        """

        self._validate_account(account)

        registros = (
            self.libro_mayor_repository
            .get_by_tipo_cuenta(account)
        )

        reglas = self._get_active_rules()

        df = (
            self.libro_mayor_repository
            .to_dataframe(registros)
        )

        if df.empty:
            return {
                "procesados": 0,
                "account": account,
            }

        df = self.rules_service.reprocesar(
            df=df,
            reglas=reglas,
            user_id=self.user_id,
        )

        resultado = (
            self.libro_mayor_repository
            .update_classification(df)
        )

        return {
            "account": account,
            **resultado,
        }

    def reprocess_date_range(
        self,
        account: str,
        start_date: date,
        end_date: date,
    ):
        """
        Reprocesa un rango específico.
        Es el método recomendado para producción.
        """

        self._validate_account(account)

        registros = (
            self.libro_mayor_repository
            .get_by_account_and_date_range(
                account=account,
                start_date=start_date,
                end_date=end_date,
            )
        )

        reglas = self._get_active_rules()

        df = (
            self.libro_mayor_repository
            .to_dataframe(registros)
        )

        if df.empty:
            return {
                "procesados": 0,
                "account": account,
            }

        df = self.rules_service.reprocesar(
            df=df,
            reglas=reglas,
            user_id=self.user_id,
        )

        resultado = (
            self.libro_mayor_repository
            .update_classification(df)
        )

        return {
            "account": account,
            "start_date": start_date,
            "end_date": end_date,
            **resultado,
        }

    def reprocess_deleted_rule(
        self,
        rule_id: int,
    ):
        """
        Reprocesa registros clasificados anteriormente
        con una regla eliminada.
        """

        registros = (
            self.libro_mayor_repository
            .get_by_rule(rule_id)
        )

        reglas = self._get_active_rules()

        df = (
            self.libro_mayor_repository
            .to_dataframe(registros)
        )

        if df.empty:
            return {
                "procesados": 0,
                "rule_id": rule_id,
            }

        df = self.rules_service.reprocesar(
            df=df,
            reglas=reglas,
            user_id=self.user_id,
        )

        resultado = (
            self.libro_mayor_repository
            .update_classification(df)
        )

        return {
            "rule_id": rule_id,
            **resultado,
        }

    def reprocess_all(self):
        """
        Solo para mantenimiento.
        Evitar usar en producción.
        """

        registros = (
            self.libro_mayor_repository
            .get_all()
        )

        reglas = self._get_active_rules()

        df = (
            self.libro_mayor_repository
            .to_dataframe(registros)
        )

        if df.empty:
            return {
                "procesados": 0,
            }

        df = self.rules_service.reprocesar(
            df=df,
            reglas=reglas,
            user_id=self.user_id,
        )

        resultado = (
            self.libro_mayor_repository
            .update_classification(df)
        )

        return resultado
