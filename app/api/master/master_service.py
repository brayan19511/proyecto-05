

from re import search

from fastapi import HTTPException
from app.api.master.master_repository import MasterRepository
from app.api.master.master_schema import AreaCreateRequest, AreaUpdateRequest, CompanyCreateRequest, CompanyUpdateRequest, CurrencyCreateRequest, CurrencyUpdateRequest


class MasterService:
    def __init__(self, db):
        self.master_repository = MasterRepository(db)
    # company
    def get_companies(self, search: str | None = None):
        return self.master_repository.get_companies(search)
    def get_company_by_id(self, company_id: int):
        data=self.master_repository.get_company_by_id(company_id)
        if not data:
            raise HTTPException(status_code=404, detail="Company not found")
        return data
    def create_company(self, company_data: CompanyCreateRequest,current_user_id: int):
        if self.master_repository.get_companies(company_data.code):
            raise HTTPException(status_code=400, detail="Company code already exists")
        try:
            return self.master_repository.create_company(company_data, current_user_id)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    def update_company(self, company_id: int, company_data: CompanyUpdateRequest, current_user_id: int):
        data = self.master_repository.update_company(company_id, company_data, current_user_id)
        if not data:
            raise HTTPException(status_code=404, detail="Company not found")
        return data
    def delete_company(self, company_id: int, current_user_id: int):
        data = self.master_repository.delete_company(company_id, current_user_id)
        if not data:
            raise HTTPException(status_code=404, detail="Company not found")
        return data
    # area
    def get_areas(self, search: str | None = None):
        return self.master_repository.get_areas(search)
    def get_area_by_id(self, area_id: int):
        data = self.master_repository.get_area_by_id(area_id)
        if not data:
            raise HTTPException(status_code=404, detail="Area not found")
        return data
    def create_area(self, area_data: AreaCreateRequest, current_user_id: int):
        if self.master_repository.get_areas(area_data.code):
            raise HTTPException(status_code=400, detail="Area code already exists")
        try:
            return self.master_repository.create_area(area_data, current_user_id)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    def update_area(self, area_id: int, area_data: AreaUpdateRequest, current_user_id: int):
        data = self.master_repository.update_area(area_id, area_data, current_user_id)
        if not data:
            raise HTTPException(status_code=404, detail="Area not found")
        return data
    def delete_area(self, area_id: int, current_user_id: int):
        data = self.master_repository.delete_area(area_id, current_user_id)
        if not data:
            raise HTTPException(status_code=404, detail="Area not found")
        return data
    # Currency
    def get_currencies(self, search: str | None = None):
        return self.master_repository.get_currencies(search)
    def get_currency_by_id(self, currency_id: int):
        data = self.master_repository.get_currency_by_id(currency_id)
        if not data:
            raise HTTPException(status_code=404, detail="Currency not found")
        return data
    def create_currency(self, currency_data: CurrencyCreateRequest, current_user_id: int):
        if self.master_repository.get_currencies(currency_data.code):
            raise HTTPException(status_code=400, detail="Currency code already exists")
        try:
            return self.master_repository.create_currency(currency_data, current_user_id)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    def update_currency(self, currency_id: int, currency_data: CurrencyUpdateRequest, current_user_id: int):
        data = self.master_repository.update_currency(currency_id, currency_data, current_user_id)
        if not data:
            raise HTTPException(status_code=404, detail="Currency not found")
        return data
    def delete_currency(self, currency_id: int, current_user_id: int):
        data = self.master_repository.delete_currency(currency_id, current_user_id)
        if not data:
            raise HTTPException(status_code=404, detail="Currency not found")
        return data