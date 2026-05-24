# app/api/master/master_repository.py

from sqlalchemy.orm import Session
from app.api.master.master_schema import AreaCreateRequest, AreaUpdateRequest, CompanyCreateRequest, CompanyUpdateRequest, CurrencyUpdateRequest, CurrencyUpdateRequest, CurrencyCreateRequest
from app.models.master.master_model import Area, Company, Currency


class MasterRepository:
    def __init__(self, db: Session):
        self.db = db
    # company
    def get_all_companies(self):
        return self.db.query(Company).all()
    def get_company_by_id(self, company_id: int):
        return self.db.query(Company).filter(Company.id == company_id).first()
    def get_company_by_code(self, code: str):
        return self.db.query(Company).filter(Company.code.like(f"%{code}%")).all()
    def create_company(self, company_data: CompanyCreateRequest):
        new_company = Company(**company_data.model_dump())
        self.db.add(new_company)
        self.db.commit()
        self.db.refresh(new_company)
        return new_company
    def update_company(self, company_id: int, company_data: CompanyUpdateRequest):
        company = self.get_company_by_id(company_id)
        if company:
            for key, value in company_data.model_dump().items():
                setattr(company, key, value)
            self.db.commit()
            self.db.refresh(company)
            return company
        return None
    def delete_company(self, company_id: int):
        company = self.get_company_by_id(company_id)
        if company:
            company.active = False
            self.db.commit()
            return True
        return False
    # area
    def get_all_areas(self):
        return self.db.query(Area).all()
    def get_area_by_id(self, area_id: int):
        return self.db.query(Area).filter(Area.id == area_id).first()
    def get_area_by_code(self, code: str):
        return self.db.query(Area).filter(Area.code.like(f"%{code}%")).all()
        # return self.db.query(Area).filter(Area.code == code).first()
    def create_area(self, area_data: AreaCreateRequest):
        new_area = Area(**area_data.model_dump())
        self.db.add(new_area)
        self.db.commit()
        self.db.refresh(new_area)
        return new_area
    def update_area(self, area_id: int, area_data: AreaUpdateRequest):
        area = self.get_area_by_id(area_id)
        if area:
            for key, value in area_data.model_dump().items():
                setattr(area, key, value)
            self.db.commit()
            self.db.refresh(area)
            return area
        return None
    def delete_area(self, area_id: int):
        area = self.get_area_by_id(area_id)
        if area:
            area.active = False
            self.db.commit()
            return True
        return False
    # currency
    def get_all_currencies(self):
        return self.db.query(Currency).all()
    def get_currency_by_id(self, currency_id: int):
        return self.db.query(Currency).filter(Currency.id == currency_id).first()
    def get_currency_by_code(self, code: str):
        return self.db.query(Currency).filter(Currency.code.like(f"%{code}%")).all()
    def create_currency(self, currency_data: CurrencyCreateRequest):
        new_currency = Currency(**currency_data.model_dump())
        self.db.add(new_currency)
        self.db.commit()
        self.db.refresh(new_currency)
        return new_currency
    def update_currency(self, currency_id: int, currency_data: CurrencyUpdateRequest):
        currency = self.get_currency_by_id(currency_id)
        if currency:
            for key, value in currency_data.model_dump().items():
                setattr(currency, key, value)
            self.db.commit()
            self.db.refresh(currency)
            return currency
        return None
    def delete_currency(self, currency_id: int):
        currency = self.get_currency_by_id(currency_id)
        if currency:
            currency.active = False
            self.db.commit()
            return True
        return False