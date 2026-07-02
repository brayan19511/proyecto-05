from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.master.master_model import (
    Company,
    Area,
    Currency,
)

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
)
from app.core.db.integrity import raise_integrity_error
from app.core.exceptions import ConflictError


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

        company = self.repository.get_company_by_id(company_id)

        if not company:
            raise HTTPException(status_code=404, detail="Company not found")

        return company

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

        company = self.repository.get_company_by_id(company_id)
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")

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

        company = self.repository.get_company_by_id(company_id)

        if not company:
            raise HTTPException(status_code=404, detail="Company not found")

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
            raise HTTPException(
                status_code=400,
                detail="Currency exchange rate must be greater than zero",
            )

        return data

    def get_currencies(self, search: str | None = None):
        return self.repository.get_currencies(search)

    def get_currency_by_id(self, currency_id: int):
        curreny = self.repository.get_currency_by_id(currency_id)
        if not curreny:
            raise HTTPException(status_code=404, detail="Currency not found")
        return curreny

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

        currency = self.repository.get_currency_by_id(currency_id)

        if not currency:
            raise HTTPException(status_code=404, detail="Currency not found")

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

        currency = self.repository.get_currency_by_id(currency_id)

        if not currency:
            raise HTTPException(status_code=404, detail="Currency not found")

        currency.active = False
        currency.updated_by = current_user_id

        self.repository.commit()

        return True

    # ==========================================
    # AREA
    # ==========================================

    def get_areas(self, search: str | None = None):
        return self.repository.get_areas(search)

    def get_area_by_id(self, area_id: int):
        area = self.repository.get_area_by_id(area_id)
        if not area:
            raise HTTPException(status_code=404, detail="Area not found")
        return area

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

        area = self.repository.get_area_by_id(area_id)

        if not area:
            raise HTTPException(status_code=404, detail="Area not found")

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

        area = self.repository.get_area_by_id(area_id)

        if not area:
            raise HTTPException(status_code=404, detail="Area not found")

        area.active = False
        area.updated_by = current_user_id

        self.repository.commit()

        return True
