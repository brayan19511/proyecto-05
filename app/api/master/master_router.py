# api/master/master_router.py
from fastapi import APIRouter, Depends

from app.api.master.master_schema import AreaCreateRequest, CompanyCreateRequest, CompanyUpdateRequest, CurrencyUpdateRequest, CurrencyUpdateRequest, CurrencyCreateRequest
from app.api.master.master_service import MasterService
from app.core.db_postgres import get_db

router = APIRouter(   prefix="/master",tags=["Master"],)

# Company
@router.get("/company")
async def get_company(db=Depends(get_db)):
    master_service = MasterService(db)
    data = master_service.get_all_companies()
    return data
@router.get("/company/{company_id}")
async def get_company_by_id(company_id: int, db=Depends(get_db)):
    master_service = MasterService(db)
    data = master_service.get_company_by_id(company_id)
    return data
@router.get("/company/code/{code}")
async def get_company_by_code(code: str, db=Depends(get_db)):
    master_service = MasterService(db)
    data = master_service.get_company_by_code(code)
    return data
@router.post("/company")
async def create_company(company_data: CompanyCreateRequest, db=Depends(get_db)):
    master_service = MasterService(db)
    data = master_service.create_company(company_data)
    return data
@router.put("/company/{company_id}")
async def update_company(company_id: int, company_data: CompanyUpdateRequest, db=Depends(get_db)):
    master_service = MasterService(db)
    data = master_service.update_company(company_id, company_data)
    return data
@router.delete("/company/{company_id}")
async def delete_company(company_id: int, db=Depends(get_db)):
    master_service = MasterService(db)
    data = master_service.delete_company(company_id)
    return data
# Area
@router.get("/area")
async def get_area(db=Depends(get_db)):
    master_service = MasterService(db)
    data = master_service.get_all_areas()
    return data
@router.get("/area/{area_id}")
async def get_area_by_id(area_id: int, db=Depends(get_db)):
    master_service = MasterService(db)
    data = master_service.get_area_by_id(area_id)
    return data
@router.get("/area/code/{code}")
async def get_area_by_code(code: str, db=Depends(get_db)):
    master_service = MasterService(db)
    data = master_service.get_area_by_code(code)
    return data
@router.post("/area")
async def create_area(area_data: AreaCreateRequest, db=Depends(get_db)):
    master_service = MasterService(db)
    data = master_service.create_area(area_data)
    return data 
@router.put("/area/{area_id}")
async def update_area(area_id: int, area_data: AreaCreateRequest, db=Depends(get_db)):
    master_service = MasterService(db)
    data = master_service.update_area(area_id, area_data)
    return data
@router.delete("/area/{area_id}")
async def delete_area(area_id: int, db=Depends(get_db)):
    master_service = MasterService(db)
    data = master_service.delete_area(area_id)
    return data

# Currency
@router.get("/currency")
async def get_currency(search: str | None = None, db=Depends(get_db),):
    master_service = MasterService(db)
    return master_service.get_currencies(search)

@router.get("/currency/{currency_id}")
async def get_currency_by_id(currency_id: int, db=Depends(get_db)):
    master_service = MasterService(db)
    data = master_service.get_currency_by_id(currency_id)
    return data

@router.post("/currency")
async def create_currency(currency_data: CurrencyCreateRequest, db=Depends(get_db)):
    master_service = MasterService(db)
    data = master_service.create_currency(currency_data)
    return data
@router.put("/currency/{currency_id}")
async def update_currency(currency_id: int, currency_data: CurrencyUpdateRequest, db=Depends(get_db)):
    master_service = MasterService(db)
    data = master_service.update_currency(currency_id, currency_data)
    return data
@router.delete("/currency/{currency_id}")
async def delete_currency(currency_id: int, db=Depends(get_db)):
    master_service = MasterService(db)
    data = master_service.delete_currency(currency_id)
    return data
