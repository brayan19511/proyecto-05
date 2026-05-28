# api/master/master_router.py
from fastapi import APIRouter, Depends

from app.api.master.master_schema import AreaCreateRequest, CompanyCreateRequest, CompanyUpdateRequest, CurrencyUpdateRequest, CurrencyUpdateRequest, CurrencyCreateRequest
from app.api.master.master_service import MasterService
from app.core.db_postgres import get_db
from app.core.security import PermissionChecker, get_current_user

router = APIRouter(   prefix="/master",tags=["Master"],)

# Company
@router.get("/company")
async def get_company(search: str | None = None, db=Depends(get_db),current_user=Depends(get_current_user),):
    master_service = MasterService(db)
    data = master_service.get_companies(search)
    return data
@router.get("/company/{company_id}")
async def get_company_by_id(company_id: int, db=Depends(get_db),current_user=Depends(get_current_user),):
    master_service = MasterService(db)
    data = master_service.get_company_by_id(company_id)
    return data
@router.post("/company")
async def create_company(company_data: CompanyCreateRequest, db=Depends(get_db), current_user=Depends(PermissionChecker("master.data.edit"))):
    master_service = MasterService(db)
    data = master_service.create_company(company_data, current_user.id)
    return data
@router.put("/company/{company_id}")
async def update_company(company_id: int, company_data: CompanyUpdateRequest, db=Depends(get_db), current_user=Depends(PermissionChecker("master.data.edit"))):
    master_service = MasterService(db)
    data = master_service.update_company(company_id, company_data, current_user.id)
    return data
@router.delete("/company/{company_id}")
async def delete_company(company_id: int, db=Depends(get_db), current_user=Depends(PermissionChecker("master.data.edit"))):
    master_service = MasterService(db)
    data = master_service.delete_company(company_id, current_user.id)
    return data
# Area
@router.get("/area")
async def get_area(search: str | None = None, db=Depends(get_db),current_user=Depends(get_current_user),):
    master_service = MasterService(db)
    data = master_service.get_areas(search)
    return data
@router.get("/area/{area_id}")
async def get_area_by_id(area_id: int, db=Depends(get_db),current_user=Depends(get_current_user),):
    master_service = MasterService(db)
    data = master_service.get_area_by_id(area_id)
    return data
@router.post("/area")
async def create_area(area_data: AreaCreateRequest, db=Depends(get_db), current_user=Depends(PermissionChecker("master.data.edit"))):
    master_service = MasterService(db)
    data = master_service.create_area(area_data, current_user.id)
    return data 
@router.put("/area/{area_id}")
async def update_area(area_id: int, area_data: AreaCreateRequest, db=Depends(get_db), current_user=Depends(PermissionChecker("master.data.edit"))):
    master_service = MasterService(db)
    data = master_service.update_area(area_id, area_data, current_user.id)
    return data
@router.delete("/area/{area_id}")
async def delete_area(area_id: int, db=Depends(get_db), current_user=Depends(PermissionChecker("master.data.edit"))):
    master_service = MasterService(db)
    data = master_service.delete_area(area_id, current_user.id)
    return data

# Currency
@router.get("/currency")
async def get_currency(search: str | None = None, db=Depends(get_db),current_user=Depends(get_current_user),):
    master_service = MasterService(db)
    return master_service.get_currencies(search)

@router.get("/currency/{currency_id}")
async def get_currency_by_id(currency_id: int, db=Depends(get_db),current_user=Depends(get_current_user),):
    master_service = MasterService(db)
    data = master_service.get_currency_by_id(currency_id)
    return data

@router.post("/currency")
async def create_currency(currency_data: CurrencyCreateRequest, db=Depends(get_db), current_user=Depends(PermissionChecker("master.data.edit"))):
    master_service = MasterService(db)
    data = master_service.create_currency(currency_data, current_user.id)
    return data
@router.put("/currency/{currency_id}")
async def update_currency(currency_id: int, currency_data: CurrencyUpdateRequest, db=Depends(get_db), current_user=Depends(PermissionChecker("master.data.edit"))):
    master_service = MasterService(db)
    data = master_service.update_currency(currency_id, currency_data, current_user.id)
    return data
@router.delete("/currency/{currency_id}")
async def delete_currency(currency_id: int, db=Depends(get_db), current_user=Depends(PermissionChecker("master.data.edit")) ):
    master_service = MasterService(db)
    data = master_service.delete_currency(currency_id, current_user.id)
    return data
