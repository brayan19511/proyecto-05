from decimal import Decimal
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.master.master_model import (
    Company,
    Area,
    Currency,
    Module,
)
from app.models.master.mailing_parameter_model import MailingParameter

from app.api.master.master_repository import (
    MasterRepository,
)

from app.api.master.master_schema import (
    CompanyCreateRequest,
    CompanyUpdateRequest,
    AreaCreateRequest,
    AreaUpdateRequest,
    CurrencyCreateRequest,
    CurrencyUpdateRequest,
    MailingParameterCreateRequest,
    MailingParameterUpdateRequest,
    ModuleResponse,
    ModuleUpdateRequest,
)
from app.core.config import settings
from app.core.db.integrity import raise_integrity_error
from app.core.modules import (
    ENVIRONMENT_DISABLED_REASON,
    MODULE_CATALOG,
)
from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    ValidationError,
    get_or_404,
)


class MasterService:

    def __init__(self, db: Session):

        self.repository = MasterRepository(db)

    def _commit(self, conflict_constraint: str, conflict_message: str):
        try:
            self.repository.commit()
        except IntegrityError as exc:
            self.repository.rollback()
            raise_integrity_error(
                exc,
                conflicts={conflict_constraint: conflict_message},
            )

    # ==========================================
    # COMPANY
    # ==========================================

    def get_companies(
        self,
        search: str | None = None,
        active: bool | None = True,
    ):
        return self.repository.get_companies(search, active)

    def get_company_by_id(self, company_id: int):
        return get_or_404(
            self.repository.get_company_by_id(company_id),
            "Company not found",
        )

    def get_active_company_by_id(self, company_id: int):
        """Valida contra empresas vigentes (no sirve una dada de baja)."""
        return get_or_404(
            self.repository.get_company_by_id(company_id, only_active=True),
            "La empresa indicada no existe o esta inactiva",
        )

    def create_company(
        self,
        request: CompanyCreateRequest,
        current_user_id: UUID | None,
    ):

        data = request.model_dump()
        data["code"] = data["code"].strip().upper()
        existing = self.repository.get_company_by_code(data["code"])
        if existing:
            # El borrado es logico, asi que el codigo sigue ocupado por el
            # registro inactivo: hay que reactivarlo, no crear otro.
            if not existing.active:
                raise ConflictError(
                    "Ya existe una empresa inactiva con este codigo, "
                    "reactivela en lugar de crear una nueva"
                )
            raise ConflictError("El codigo de empresa ya existe")

        company = Company(**data, created_by=current_user_id)
        self.repository.create_company(company)
        self._commit("companies_code_key", "El codigo de empresa ya existe")
        return company

    def update_company(
        self,
        company_id: int,
        request: CompanyUpdateRequest,
        current_user_id: UUID | None,
    ):

        company = self.get_company_by_id(company_id)

        data = request.model_dump(exclude_unset=True)
        if "code" in data and data["code"] is not None:
            data["code"] = data["code"].strip().upper()
            existing = self.repository.get_company_by_code(data["code"])
            if existing and existing.id != company_id:
                raise ConflictError("El codigo de empresa ya existe")

        for key, value in data.items():
            setattr(company, key, value)

        company.updated_by = current_user_id
        self._commit("companies_code_key", "El codigo de empresa ya existe")
        return company

    def set_company_active(
        self,
        company_id: int,
        active: bool,
        current_user_id: UUID | None,
    ):
        """Activa o desactiva la empresa (no hay borrado fisico)."""
        company = self.get_company_by_id(company_id)

        if not active and company.active:
            dependents = self.repository.count_company_dependents(company_id)
            if dependents:
                raise ConflictError(
                    "No se puede desactivar la empresa: tiene "
                    f"{dependents} registro(s) activo(s) asociado(s)"
                )

        company.active = active
        company.updated_by = current_user_id

        self.repository.commit()

        return company

    def delete_company(
        self,
        company_id: int,
        current_user_id: UUID | None,
    ):
        # Mantenido por compatibilidad: desactiva, nunca borra.
        self.set_company_active(company_id, False, current_user_id)

        return True

    # ==========================================
    # CURRENCY
    # ==========================================
    def _normalize_currency_data(self, data: dict):
        if data.get("is_base_currency"):
            data["exchange_rate_to_base"] = Decimal("1")

        exchange_rate = data.get("exchange_rate_to_base")
        if exchange_rate is not None and exchange_rate <= 0:
            raise ValidationError(
                "Currency exchange rate must be greater than zero",
            )

        return data

    def get_currencies(
        self,
        search: str | None = None,
        active: bool | None = True,
    ):
        return self.repository.get_currencies(search, active)

    def get_currency_by_id(self, currency_id: int):
        return get_or_404(
            self.repository.get_currency_by_id(currency_id),
            "Currency not found",
        )

    def create_currency(
        self,
        request: CurrencyCreateRequest,
        current_user_id: UUID | None,
    ):

        data = request.model_dump()
        data["code"] = data["code"].strip().upper()
        if self.repository.get_currency_by_code(data["code"]):
            raise ConflictError("El codigo de moneda ya existe")

        data = self._normalize_currency_data(data)
        currency = Currency(**data, created_by=current_user_id)
        self.repository.create_currency(currency)
        self._commit("currencies_code_key", "El codigo de moneda ya existe")
        return currency

    def update_currency(
        self,
        currency_id: int,
        request: CurrencyUpdateRequest,
        current_user_id: UUID | None,
    ):

        currency = self.get_currency_by_id(currency_id)

        data = self._normalize_currency_data(request.model_dump(exclude_unset=True))
        if "code" in data and data["code"] is not None:
            data["code"] = data["code"].strip().upper()
            existing = self.repository.get_currency_by_code(data["code"])
            if existing and existing.id != currency_id:
                raise ConflictError("El codigo de moneda ya existe")

        for key, value in data.items():
            setattr(currency, key, value)

        currency.updated_by = current_user_id

        self._commit("currencies_code_key", "El codigo de moneda ya existe")

        return currency

    def set_currency_active(
        self,
        currency_id: int,
        active: bool,
        current_user_id: UUID | None,
    ):
        """Activa o desactiva la moneda (no hay borrado fisico)."""
        currency = self.get_currency_by_id(currency_id)

        currency.active = active
        currency.updated_by = current_user_id

        self.repository.commit()

        return currency

    def delete_currency(
        self,
        currency_id: int,
        current_user_id: UUID | None,
    ):
        # Mantenido por compatibilidad: desactiva, nunca borra.
        self.set_currency_active(currency_id, False, current_user_id)

        return True

    # ==========================================
    # MAILING PARAMETERS
    # ==========================================

    def get_mailing_parameters(self, search: str | None = None):
        return self.repository.get_mailing_parameters(search)

    def get_mailing_parameter_by_id(self, parameter_id: int):
        return get_or_404(
            self.repository.get_mailing_parameter_by_id(parameter_id),
            "Mailing parameter not found",
        )

    def create_mailing_parameter(
        self,
        request: MailingParameterCreateRequest,
        current_user_id: UUID | None,
    ):
        data = request.model_dump()
        data["name"] = data["name"].strip()
        if self.repository.get_mailing_parameter_by_name(data["name"]):
            raise ConflictError("Ya existe un parametro de correo con este nombre")

        parameter = MailingParameter(**data, created_by=current_user_id)
        self.repository.create_mailing_parameter(parameter)
        self._commit(
            "uq_mailing_parameter_name",
            "Ya existe un parametro de correo con este nombre",
        )
        return parameter

    def update_mailing_parameter(
        self,
        parameter_id: int,
        request: MailingParameterUpdateRequest,
        current_user_id: UUID | None,
    ):
        parameter = self.get_mailing_parameter_by_id(parameter_id)
        data = request.model_dump(exclude_unset=True)
        if "name" in data and data["name"] is not None:
            data["name"] = data["name"].strip()
            existing = self.repository.get_mailing_parameter_by_name(data["name"])
            if existing and existing.id != parameter_id:
                raise ConflictError("Ya existe un parametro de correo con este nombre")

        for key, value in data.items():
            setattr(parameter, key, value)
        parameter.updated_by = current_user_id
        self._commit(
            "uq_mailing_parameter_name",
            "Ya existe un parametro de correo con este nombre",
        )
        return parameter

    def delete_mailing_parameter(self, parameter_id: int, current_user_id: UUID | None):
        parameter = self.get_mailing_parameter_by_id(parameter_id)
        parameter.active = False
        parameter.updated_by = current_user_id
        self.repository.commit()
        return True

    # ==========================================
    # AREA
    # ==========================================

    def get_areas(
        self,
        search: str | None = None,
        active: bool | None = True,
    ):
        return self.repository.get_areas(search, active)

    def get_area_by_id(self, area_id: int):
        return get_or_404(
            self.repository.get_area_by_id(area_id),
            "Area not found",
        )

    def get_active_area_by_id(self, area_id: int):
        """Valida contra areas vigentes (no sirve una dada de baja)."""
        return get_or_404(
            self.repository.get_area_by_id(area_id, only_active=True),
            "El area indicada no existe o esta inactiva",
        )

    def create_area(
        self,
        request: AreaCreateRequest,
        current_user_id: UUID | None,
    ):

        data = request.model_dump()
        data["code"] = data["code"].strip().upper()
        existing = self.repository.get_area_by_code(data["code"])
        if existing:
            # El borrado es logico: el codigo sigue ocupado por el inactivo.
            if not existing.active:
                raise ConflictError(
                    "Ya existe un area inactiva con este codigo, "
                    "reactivela en lugar de crear una nueva"
                )
            raise ConflictError("El codigo de area ya existe")

        area = Area(**data, created_by=current_user_id)
        self.repository.create_area(area)
        self._commit("areas_code_key", "El codigo de area ya existe")
        return area

    def update_area(
        self,
        area_id: int,
        request: AreaUpdateRequest,
        current_user_id: UUID | None,
    ):

        area = self.get_area_by_id(area_id)

        data = request.model_dump(exclude_unset=True)
        if "code" in data and data["code"] is not None:
            data["code"] = data["code"].strip().upper()
            existing = self.repository.get_area_by_code(data["code"])
            if existing and existing.id != area_id:
                raise ConflictError("El codigo de area ya existe")

        for key, value in data.items():
            setattr(area, key, value)

        area.updated_by = current_user_id

        self._commit("areas_code_key", "El codigo de area ya existe")

        return area

    def delete_area(
        self,
        area_id: int,
        current_user_id: UUID | None,
    ):

        area = self.get_area_by_id(area_id)

        area.active = False
        area.updated_by = current_user_id

        self.repository.commit()

        return True

    # ==========================================
    # MODULOS
    # ==========================================

    def get_modules(self) -> list[ModuleResponse]:
        """Catalogo completo con su estado, en el orden de MODULE_CATALOG.

        Se recorre el catalogo y no la tabla para que un modulo sin fila
        (seed no corrido) aparezca igual en el panel, como encendido.
        """
        rows = {row.code: row for row in self.repository.get_modules()}

        return [
            self._build_module_response(item, rows.get(item["code"]))
            for item in MODULE_CATALOG
        ]

    def set_module_enabled(
        self,
        code: str,
        request: ModuleUpdateRequest,
        current_user_id: UUID | None,
    ) -> ModuleResponse:
        item = next(
            (entry for entry in MODULE_CATALOG if entry["code"] == code),
            None,
        )
        if item is None:
            raise NotFoundError(f"No existe el modulo '{code}'")

        if code in settings.modules_disabled:
            raise ValidationError(
                f"El modulo '{item['name']}' esta apagado por configuracion "
                "del entorno (MODULES_DISABLED) y no se puede cambiar aqui"
            )

        module = self.repository.get_module_by_code(code)
        if module is None:
            # Primera vez que se toca un modulo que el seed aun no sembro.
            module = Module(
                code=code,
                name=item["name"],
                description=item["description"],
                enabled=True,
                created_by=current_user_id,
            )
            self.repository.create_module(module)

        module.enabled = request.enabled
        # Al prender se limpia el motivo para no dejar un texto viejo colgado.
        module.disabled_reason = None if request.enabled else request.disabled_reason
        module.updated_by = current_user_id

        self._commit(
            "uq_modules_code",
            "Ya existe un modulo con este codigo",
        )

        return self._build_module_response(item, module)

    @staticmethod
    def _build_module_response(item: dict, module: Module | None) -> ModuleResponse:
        locked = item["code"] in settings.modules_disabled

        if locked:
            reason = ENVIRONMENT_DISABLED_REASON
        elif module is not None and not module.enabled:
            reason = module.disabled_reason or "Desactivado por el administrador"
        else:
            reason = None

        return ModuleResponse(
            code=item["code"],
            name=module.name if module else item["name"],
            description=module.description if module else item["description"],
            enabled=reason is None,
            disabled_reason=reason,
            locked_by_environment=locked,
        )
