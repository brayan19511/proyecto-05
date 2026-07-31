from sqlalchemy.orm import Session

from app.api.finance.libro_mayor.repository.reglas_gastos_repository import (
    ReglasGastosRepository,
)
from app.api.finance.libro_mayor.service.libro_mayor_reproces_service import (
    LibroMayorReprocessService,
)
from app.models.finance.libro_mayor_model import ReglasGastos


class ReglasGastosService:

    def __init__(
        self,
        db: Session,
    ):
        self.repository = ReglasGastosRepository(db)

        self.reprocess_service = (
            LibroMayorReprocessService(
                db_local=db
            )
        )

    def get_all(
        self,
        account: str | None = None,
    ):
        if account:
            return self.repository.get_by_account(
                account
            )

        return self.repository.get_all()

    def get_by_id(
        self,
        rule_id: int,
    ):
        regla = self.repository.get_by_id(rule_id)

        if not regla:
            raise ValueError(
                "Regla no encontrada"
            )

        return regla

    def create(
        self,
        data,
        user_id: str,
    ):

        regla = self.repository.create(
            ReglasGastos(
                **data.model_dump()
            )
        )

        self.reprocess_service.user_id = user_id

        resultado = (
            self.reprocess_service
            .reprocess_rule(
                regla.id_regla
            )
        )

        return {
            "rule_id": regla.id_regla,
            "reprocesados": resultado["procesados"],
        }

    def update(
        self,
        rule_id: int,
        data,
        user_id: str,
    ):

        regla = self.repository.update(
            rule_id,
            data.model_dump(
                exclude_unset=True
            ),
        )

        if not regla:
            raise ValueError(
                "Regla no encontrada"
            )

        self.reprocess_service.user_id = user_id

        resultado = (
            self.reprocess_service
            .reprocess_rule(
                rule_id
            )
        )

        return {
            "rule_id": rule_id,
            "reprocesados": resultado["procesados"],
        }

    def delete(
        self,
        rule_id: int,
        user_id: str,
    ):

        regla = self.repository.get_by_id(
            rule_id
        )

        if not regla:
            raise ValueError(
                "Regla no encontrada"
            )

        self.reprocess_service.user_id = user_id

        registros_afectados = (
            self.reprocess_service
            .libro_mayor_repository
            .get_by_rule(rule_id)
        )

        eliminado = self.repository.delete(
            rule_id
        )

        if not eliminado:
            raise ValueError(
                "No se pudo eliminar la regla"
            )

        if registros_afectados:

            reglas_activas = (
                self.repository
                .get_all_active()
            )

            df = (
                self.reprocess_service
                .libro_mayor_repository
                .to_dataframe(
                    registros_afectados
                )
            )

            df = (
                self.reprocess_service
                .rules_service
                .reprocesar(
                    df=df,
                    reglas=reglas_activas,
                    user_id=user_id,
                )
            )

            resultado = (
                self.reprocess_service
                .libro_mayor_repository
                .update_classification(df)
            )

            reprocesados = resultado["procesados"]

        else:
            reprocesados = 0

        return {
            "eliminada": True,
            "reprocesados": reprocesados,
        }
