# app/api/master/master_repository.py

from sqlalchemy.orm import Session
from app.api.master.master_schema import (
    AreaCreateRequest,
    AreaUpdateRequest,
    CompanyCreateRequest,
    CompanyUpdateRequest,
    CurrencyUpdateRequest,
    CurrencyUpdateRequest,
    CurrencyCreateRequest,
)
from app.models.master.master_model import Area, Company, Currency


class MasterRepository:
    def __init__(self, db: Session):
        self.db = db

    # company
  
    def get_companies(self, search: str | None = None):
        query = self.db.query(Company)

        if search:
            query = query.filter(Company.code.ilike(f"%{search}%"))

        return query.all()
    def get_company_by_id(self, company_id: int):
        return self.db.query(Company).filter(Company.id == company_id).first()

    def create_company(self, company_data: CompanyCreateRequest,current_user_id: int):
        new_company = Company(**company_data.model_dump(),created_by=current_user_id)
        self.db.add(new_company)
        self.db.commit()
        self.db.refresh(new_company)
        return new_company

    def update_company(self, company_id: int, company_data: CompanyUpdateRequest, current_user_id: int):
        company = self.get_company_by_id(company_id)
        if company:
            company.updated_by = current_user_id
            update_data = company_data.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                setattr(company, key, value)
            self.db.commit()
            self.db.refresh(company)
            return company
        return None

    def delete_company(self, company_id: int, current_user_id: int):
        company = self.get_company_by_id(company_id)
        if company:
            company.active = False
            self.db.commit()
            return True
        return False

    # area
    def get_areas(self, search: str | None = None):
        query = self.db.query(Area)

        if search:
            query = query.filter(Area.code.ilike(f"%{search}%"))

        return query.all()

    def get_area_by_id(self, area_id: int):
        return self.db.query(Area).filter(Area.id == area_id).first()

    def create_area(self, area_data: AreaCreateRequest, current_user_id: int):
        new_area = Area(**area_data.model_dump(), created_by=current_user_id)
        self.db.add(new_area)
        self.db.commit()
        self.db.refresh(new_area)
        return new_area

    def update_area(self, area_id: int, area_data: AreaUpdateRequest, current_user_id: int):
        area = self.get_area_by_id(area_id)
        if area:
            area.updated_by = current_user_id
            update_data = area_data.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                setattr(area, key, value)
            self.db.commit()
            self.db.refresh(area)
            return area
        return None

    def delete_area(self, area_id: int, current_user_id: int):
        area = self.get_area_by_id(area_id)
        if area:
            area.active = False
            area.updated_by = current_user_id
            self.db.commit()
            return True
        return False

    # currency
    def get_currencies(self, search: str | None = None):
        query = self.db.query(Currency)

        if search:
            query = query.filter(Currency.code.ilike(f"%{search}%"))

        return query.all()

    def get_currency_by_id(self, currency_id: int):
        return self.db.query(Currency).filter(Currency.id == currency_id).first()

    def create_currency(self, currency_data: CurrencyCreateRequest, current_user_id: int):
        new_currency = Currency(**currency_data.model_dump(), created_by=current_user_id)
        self.db.add(new_currency)
        self.db.commit()
        self.db.refresh(new_currency)
        return new_currency

    def update_currency(self, currency_id: int, currency_data: CurrencyUpdateRequest, current_user_id: int):
        currency = self.get_currency_by_id(currency_id)
        if currency:
            currency.updated_by = current_user_id
            update_data = currency_data.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                setattr(currency, key, value)
            self.db.commit()
            self.db.refresh(currency)
            return currency
        return None

    def delete_currency(self, currency_id: int, current_user_id: int):
        currency = self.get_currency_by_id(currency_id)
        if currency:
            currency.active = False
            currency.updated_by = current_user_id
            self.db.commit()
            return True
        return False
