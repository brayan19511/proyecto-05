# app/api/master/master_service.py

from fastapi import HTTPException
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


class MasterService:

    def __init__(self, db: Session):

        self.repository = MasterRepository(db)

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

        if self.repository.get_company_by_code(request.code):
            raise HTTPException(status_code=400, detail="Company code already exists")

        try:

            company = Company(**request.model_dump(), created_by=current_user_id)

            self.repository.create_company(company)

            self.repository.commit()

            return company

        except Exception as e:

            self.repository.rollback()
            raise HTTPException(status_code=400, detail=str(e))

    def update_company(
        self,
        company_id: int,
        request: CompanyUpdateRequest,
        current_user_id: int|None,
    ):

        try:

            company = self.repository.get_company_by_id(company_id)

            if not company:
                raise HTTPException(status_code=404, detail="Company not found")

            for key, value in request.model_dump(exclude_unset=True).items():
                setattr(company, key, value)

            company.updated_by = current_user_id

            self.repository.commit()

            return company

        except Exception:
            self.repository.rollback()
            raise

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

        if self.repository.get_currency_by_code(request.code):
            raise HTTPException(status_code=400, detail="Currency code already exists")

        try:

            currency = Currency(**request.model_dump(), created_by=current_user_id)

            self.repository.create_currency(currency)

            self.repository.commit()

            return currency

        except Exception as e:

            self.repository.rollback()
            raise HTTPException(status_code=400, detail=str(e))

    def update_currency(
        self,
        currency_id: int,
        request: CurrencyUpdateRequest,
        current_user_id: int|None,
    ):

        currency = self.repository.get_currency_by_id(currency_id)

        if not currency:
            raise HTTPException(status_code=404, detail="Currency not found")

        for key, value in request.model_dump(exclude_unset=True).items():
            setattr(currency, key, value)

        currency.updated_by = current_user_id

        self.repository.commit()

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

        if self.repository.get_area_by_code(request.code):
            raise HTTPException(status_code=400, detail="Area code already exists")

        try:

            area = Area(**request.model_dump(), created_by=current_user_id)

            self.repository.create_area(area)

            self.repository.commit()

            return area

        except Exception as e:

            self.repository.rollback()
            raise HTTPException(status_code=400, detail=str(e))

    def update_area(
        self,
        area_id: int,
        request: AreaUpdateRequest,
        current_user_id: int|None,
    ):

        area = self.repository.get_area_by_id(area_id)

        if not area:
            raise HTTPException(status_code=404, detail="Area not found")

        for key, value in request.model_dump(exclude_unset=True).items():
            setattr(area, key, value)

        area.updated_by = current_user_id

        self.repository.commit()

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
