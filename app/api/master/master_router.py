# app/api/master/master_router.py

from fastapi import APIRouter, Depends

from app.core.db.db_postgres import get_db

from app.core.security import (
    get_current_user,
    PermissionChecker,
)

from app.api.master.master_service import (
    MasterService,
)

from app.api.master.master_schema import (
    AreaCreateRequest,
    AreaUpdateRequest,
    CompanyCreateRequest,
    CompanyUpdateRequest,
    CurrencyCreateRequest,
    CurrencyUpdateRequest,
)

router = APIRouter(prefix="/master", tags=["Master"])


def get_master_service(db=Depends(get_db)) -> MasterService:
    return MasterService(db)


@router.get("/company")
def get_companies(
    search: str | None = None,
    service: MasterService = Depends(get_master_service),
    current_user=Depends(get_current_user),
):

    return service.get_companies(search)


@router.get("/company/{company_id}")
def get_company_by_id(
    company_id: int,
    service: MasterService = Depends(get_master_service),
    current_user=Depends(get_current_user),
):

    return service.get_company_by_id(company_id)


@router.post("/company")
def create_company(
    request: CompanyCreateRequest,
    service: MasterService = Depends(get_master_service),
    current_user=Depends(PermissionChecker("master.data.edit")),
):

    return service.create_company(request, current_user.id)


@router.put("/company/{company_id}")
def update_company(
    company_id: int,
    request: CompanyUpdateRequest,
    service: MasterService = Depends(get_master_service),
    current_user=Depends(PermissionChecker("master.data.edit")),
):

    return service.update_company(company_id, request, current_user.id)


@router.delete("/company/{company_id}")
def delete_company(
    company_id: int,
    service: MasterService = Depends(get_master_service),
    current_user=Depends(PermissionChecker("master.data.edit")),
):

    return service.delete_company(company_id, current_user.id)


@router.get("/currency")
def get_currency(
    search: str | None = None,
    service: MasterService = Depends(get_master_service),
    current_user=Depends(get_current_user),
):
    return service.get_currencies(search)


@router.get("/currency/{currency_id}")
def get_currency_by_id(
    currency_id: int, service: MasterService = Depends(get_master_service), current_user=Depends(get_current_user),
):
    return service.get_currency_by_id(currency_id)


@router.post("/currency")
def create_currency(
    currency: CurrencyCreateRequest,
    service: MasterService = Depends(get_master_service),
    current_user=Depends(PermissionChecker("master.data.edit")),
):
    return service.create_currency(currency, current_user.id)


@router.put(
    "/currency/{currency_id}",
)
def update_currency(
    currency_id: int,
    currency: CurrencyUpdateRequest,
    service: MasterService = Depends(get_master_service),
    current_user=Depends(PermissionChecker("master.data.edit")),
):
    return service.update_currency(currency_id, currency, current_user.id)


@router.delete("/currency/{currency_id}")
def delete_currency(
    currency_id: int,
    service: MasterService = Depends(get_master_service),
    current_user=Depends(PermissionChecker("master.data.edit")),
):
    return service.delete_currency(currency_id, current_user.id)


@router.get("/area")
def get_areas(
    search: str | None = None,
    service: MasterService = Depends(get_master_service),
    current_user=Depends(get_current_user),
):
    return service.get_areas(search)


@router.get("/area/{area_id}")
def get_area_by_id(
    area_id: int,
    service: MasterService = Depends(get_master_service),
    current_user=Depends(get_current_user),
):
    return service.get_area_by_id(area_id)


@router.post("/area")
def create_area(
    area: AreaCreateRequest,
    service: MasterService = Depends(get_master_service),
    current_user=Depends(PermissionChecker("master.data.edit")),
):
    return service.create_area(area, current_user.id)


@router.put("/area/{area_id}")
def update_area(
    area_id: int,
    area: AreaUpdateRequest,
    service: MasterService = Depends(get_master_service),
    current_user=Depends(PermissionChecker("master.data.edit")),
):
    return service.update_area(area_id, area, current_user.id)


@router.delete("/area/{area_id}")
def delete_area(
    area_id: int,
    service: MasterService = Depends(get_master_service),
    current_user=Depends(PermissionChecker("master.data.edit")),
):
    return service.delete_area(area_id, current_user.id)
