from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.master.master_model import (
    Company,
    Area,
    Currency,
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
)
from app.core.db.integrity import raise_integrity_error
from app.core.exceptions import ConflictError, ValidationError, get_or_404


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

    def get_companies(self, search: str | None = None):
        return self.repository.get_companies(search)

    def get_company_by_id(self, company_id: int):
        return get_or_404(
            self.repository.get_company_by_id(company_id),
            "Company not found",
        )

    def create_company(
        self,
        request: CompanyCreateRequest,
        current_user_id: int|None,
    ):

        data = request.model_dump()
        data["code"] = data["code"].strip().upper()
        if self.repository.get_company_by_code(data["code"]):
            raise ConflictError("El codigo de empresa ya existe")

        company = Company(**data, created_by=current_user_id)
        self.repository.create_company(company)
        self._commit("companies_code_key", "El codigo de empresa ya existe")
        return company

    def update_company(
        self,
        company_id: int,
        request: CompanyUpdateRequest,
        current_user_id: int|None,
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

    def delete_company(
        self,
        company_id: int,
        current_user_id: int|None,
    ):

        company = self.get_company_by_id(company_id)

        company.active = False
        company.updated_by = current_user_id

        self.repository.commit()

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

    def get_currencies(self, search: str | None = None):
        return self.repository.get_currencies(search)

    def get_currency_by_id(self, currency_id: int):
        return get_or_404(
            self.repository.get_currency_by_id(currency_id),
            "Currency not found",
        )

    def create_currency(
        self,
        request: CurrencyCreateRequest,
        current_user_id: int|None,
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
        current_user_id: int|None,
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

    def delete_currency(
        self,
        currency_id: int,
        current_user_id: int|None,
    ):

        currency = self.get_currency_by_id(currency_id)

        currency.active = False
        currency.updated_by = current_user_id

        self.repository.commit()

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
        current_user_id: int | None,
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
        current_user_id: int | None,
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

    def delete_mailing_parameter(self, parameter_id: int, current_user_id: int | None):
        parameter = self.get_mailing_parameter_by_id(parameter_id)
        parameter.active = False
        parameter.updated_by = current_user_id
        self.repository.commit()
        return True

    # ==========================================
    # AREA
    # ==========================================

    def get_areas(self, search: str | None = None):
        return self.repository.get_areas(search)

    def get_area_by_id(self, area_id: int):
        return get_or_404(
            self.repository.get_area_by_id(area_id),
            "Area not found",
        )

    def create_area(
        self,
        request: AreaCreateRequest,
        current_user_id: int|None,
    ):

        data = request.model_dump()
        data["code"] = data["code"].strip().upper()
        if self.repository.get_area_by_code(data["code"]):
            raise ConflictError("El codigo de area ya existe")

        area = Area(**data, created_by=current_user_id)
        self.repository.create_area(area)
        self._commit("areas_code_key", "El codigo de area ya existe")
        return area

    def update_area(
        self,
        area_id: int,
        request: AreaUpdateRequest,
        current_user_id: int|None,
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
        current_user_id: int|None,
    ):

        area = self.get_area_by_id(area_id)

        area.active = False
        area.updated_by = current_user_id

        self.repository.commit()

        return True
