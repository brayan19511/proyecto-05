# app/api/master/master_router.py

from fastapi import APIRouter, Depends, Query

from app.core.access import require_any_permission
from app.core.db.db_postgres import get_db

from app.api.master.master_service import (
    MasterService,
)

from app.api.master.master_schema import (
    AreaCreateRequest,
    AreaResponse,
    AreaUpdateRequest,
    CompanyCreateRequest,
    CompanyResponse,
    CompanyUpdateRequest,
    CurrencyCreateRequest,
    CurrencyResponse,
    CurrencyUpdateRequest,
    MailingParameterCreateRequest,
    MailingParameterResponse,
    MailingParameterUpdateRequest,
    ModuleResponse,
    ModuleUpdateRequest,
)

router = APIRouter(prefix="/master", tags=["MASTER"])


def get_master_service(db=Depends(get_db)) -> MasterService:
    return MasterService(db)


@router.get("/company", response_model=list[CompanyResponse])
def get_companies(
    search: str | None = None,
    # active=None trae activas e inactivas (para la vista de mantenimiento).
    active: bool | None = Query(default=True),
    service: MasterService = Depends(get_master_service),
    current_user=Depends(
        require_any_permission("master.company.view", "master.data.edit"),
    ),
):

    return service.get_companies(search, active)


@router.get("/company/{company_id}", response_model=CompanyResponse)
def get_company_by_id(
    company_id: int,
    service: MasterService = Depends(get_master_service),
    current_user=Depends(
        require_any_permission("master.company.view", "master.data.edit"),
    ),
):

    return service.get_company_by_id(company_id)


@router.post("/company", response_model=CompanyResponse)
def create_company(
    request: CompanyCreateRequest,
    service: MasterService = Depends(get_master_service),
    current_user=Depends(
        require_any_permission("master.company.edit", "master.data.edit"),
    ),
):

    return service.create_company(request, current_user.id)


@router.put("/company/{company_id}", response_model=CompanyResponse)
def update_company(
    company_id: int,
    request: CompanyUpdateRequest,
    service: MasterService = Depends(get_master_service),
    current_user=Depends(
        require_any_permission("master.company.edit", "master.data.edit"),
    ),
):

    return service.update_company(company_id, request, current_user.id)


@router.post("/company/{company_id}/deactivate", response_model=CompanyResponse)
def deactivate_company(
    company_id: int,
    service: MasterService = Depends(get_master_service),
    current_user=Depends(
        require_any_permission("master.company.edit", "master.data.edit"),
    ),
):

    return service.set_company_active(company_id, False, current_user.id)


@router.post("/company/{company_id}/activate", response_model=CompanyResponse)
def activate_company(
    company_id: int,
    service: MasterService = Depends(get_master_service),
    current_user=Depends(
        require_any_permission("master.company.edit", "master.data.edit"),
    ),
):

    return service.set_company_active(company_id, True, current_user.id)


@router.delete(
    "/company/{company_id}",
    deprecated=True,
    summary="Desactivar empresa (usar /deactivate)",
)
def delete_company(
    company_id: int,
    service: MasterService = Depends(get_master_service),
    current_user=Depends(
        require_any_permission("master.company.edit", "master.data.edit"),
    ),
):
    # No existe borrado fisico: es un alias de /deactivate.
    return service.delete_company(company_id, current_user.id)


@router.get("/currency", response_model=list[CurrencyResponse])
def get_currency(
    search: str | None = None,
    active: bool | None = Query(default=True),
    service: MasterService = Depends(get_master_service),
    current_user=Depends(
        require_any_permission("master.currency.view", "master.data.edit"),
    ),
):
    return service.get_currencies(search, active)


@router.get("/currency/{currency_id}", response_model=CurrencyResponse)
def get_currency_by_id(
    currency_id: int,
    service: MasterService = Depends(get_master_service),
    current_user=Depends(
        require_any_permission("master.currency.view", "master.data.edit"),
    ),
):
    return service.get_currency_by_id(currency_id)


@router.post("/currency", response_model=CurrencyResponse)
def create_currency(
    currency: CurrencyCreateRequest,
    service: MasterService = Depends(get_master_service),
    current_user=Depends(
        require_any_permission("master.currency.edit", "master.data.edit"),
    ),
):
    return service.create_currency(currency, current_user.id)


@router.put("/currency/{currency_id}", response_model=CurrencyResponse)
def update_currency(
    currency_id: int,
    currency: CurrencyUpdateRequest,
    service: MasterService = Depends(get_master_service),
    current_user=Depends(
        require_any_permission("master.currency.edit", "master.data.edit"),
    ),
):
    return service.update_currency(currency_id, currency, current_user.id)


@router.post("/currency/{currency_id}/deactivate", response_model=CurrencyResponse)
def deactivate_currency(
    currency_id: int,
    service: MasterService = Depends(get_master_service),
    current_user=Depends(
        require_any_permission("master.currency.edit", "master.data.edit"),
    ),
):
    return service.set_currency_active(currency_id, False, current_user.id)


@router.post("/currency/{currency_id}/activate", response_model=CurrencyResponse)
def activate_currency(
    currency_id: int,
    service: MasterService = Depends(get_master_service),
    current_user=Depends(
        require_any_permission("master.currency.edit", "master.data.edit"),
    ),
):
    return service.set_currency_active(currency_id, True, current_user.id)


@router.delete(
    "/currency/{currency_id}",
    deprecated=True,
    summary="Desactivar moneda (usar /deactivate)",
)
def delete_currency(
    currency_id: int,
    service: MasterService = Depends(get_master_service),
    current_user=Depends(
        require_any_permission("master.currency.edit", "master.data.edit"),
    ),
):
    # No existe borrado fisico: es un alias de /deactivate.
    return service.delete_currency(currency_id, current_user.id)


@router.get("/mailing-parameters", response_model=list[MailingParameterResponse])
def get_mailing_parameters(
    search: str | None = None,
    service: MasterService = Depends(get_master_service),
    current_user=Depends(
        require_any_permission("master.data.view", "master.data.edit"),
    ),
):
    return service.get_mailing_parameters(search)


@router.get(
    "/mailing-parameters/{parameter_id}",
    response_model=MailingParameterResponse,
)
def get_mailing_parameter_by_id(
    parameter_id: int,
    service: MasterService = Depends(get_master_service),
    current_user=Depends(
        require_any_permission("master.data.view", "master.data.edit"),
    ),
):
    return service.get_mailing_parameter_by_id(parameter_id)


@router.post("/mailing-parameters", response_model=MailingParameterResponse)
def create_mailing_parameter(
    request: MailingParameterCreateRequest,
    service: MasterService = Depends(get_master_service),
    current_user=Depends(require_any_permission("master.data.edit")),
):
    return service.create_mailing_parameter(request, current_user.id)


@router.patch(
    "/mailing-parameters/{parameter_id}",
    response_model=MailingParameterResponse,
)
def update_mailing_parameter(
    parameter_id: int,
    request: MailingParameterUpdateRequest,
    service: MasterService = Depends(get_master_service),
    current_user=Depends(require_any_permission("master.data.edit")),
):
    return service.update_mailing_parameter(parameter_id, request, current_user.id)


@router.delete("/mailing-parameters/{parameter_id}")
def delete_mailing_parameter(
    parameter_id: int,
    service: MasterService = Depends(get_master_service),
    current_user=Depends(require_any_permission("master.data.edit")),
):
    return service.delete_mailing_parameter(parameter_id, current_user.id)


@router.get("/area", response_model=list[AreaResponse])
def get_areas(
    search: str | None = None,
    active: bool | None = Query(default=True),
    service: MasterService = Depends(get_master_service),
    current_user=Depends(
        require_any_permission("master.area.view", "master.data.edit"),
    ),
):
    return service.get_areas(search, active)


@router.get("/area/{area_id}", response_model=AreaResponse)
def get_area_by_id(
    area_id: int,
    service: MasterService = Depends(get_master_service),
    current_user=Depends(
        require_any_permission("master.area.view", "master.data.edit"),
    ),
):
    return service.get_area_by_id(area_id)


@router.post("/area", response_model=AreaResponse)
def create_area(
    area: AreaCreateRequest,
    service: MasterService = Depends(get_master_service),
    current_user=Depends(
        require_any_permission("master.area.edit", "master.data.edit"),
    ),
):
    return service.create_area(area, current_user.id)


@router.put("/area/{area_id}", response_model=AreaResponse)
def update_area(
    area_id: int,
    area: AreaUpdateRequest,
    service: MasterService = Depends(get_master_service),
    current_user=Depends(
        require_any_permission("master.area.edit", "master.data.edit"),
    ),
):
    return service.update_area(area_id, area, current_user.id)


@router.post("/area/{area_id}/deactivate", response_model=AreaResponse)
def deactivate_area(
    area_id: int,
    service: MasterService = Depends(get_master_service),
    current_user=Depends(
        require_any_permission("master.area.edit", "master.data.edit"),
    ),
):
    return service.set_area_active(area_id, False, current_user.id)


@router.post("/area/{area_id}/activate", response_model=AreaResponse)
def activate_area(
    area_id: int,
    service: MasterService = Depends(get_master_service),
    current_user=Depends(
        require_any_permission("master.area.edit", "master.data.edit"),
    ),
):
    return service.set_area_active(area_id, True, current_user.id)


@router.delete(
    "/area/{area_id}",
    deprecated=True,
    summary="Desactivar area (usar /deactivate)",
)
def delete_area(
    area_id: int,
    service: MasterService = Depends(get_master_service),
    current_user=Depends(
        require_any_permission("master.area.edit", "master.data.edit"),
    ),
):
    # No existe borrado fisico: es un alias de /deactivate.
    return service.delete_area(area_id, current_user.id)


# =====================================================
# MODULOS
# =====================================================
# El panel de modulos es una vista de administracion: lista el catalogo
# completo con su estado. Para armar el menu, el front NO usa este endpoint
# sino enabled_modules de /security/auth/me, que ya trae permisos y alcance.
@router.get("/modules", response_model=list[ModuleResponse])
def get_modules(
    service: MasterService = Depends(get_master_service),
    current_user=Depends(
        require_any_permission("master.modules.view", "master.modules.edit"),
    ),
):
    return service.get_modules()


@router.patch("/modules/{code}", response_model=ModuleResponse)
def set_module_enabled(
    code: str,
    request: ModuleUpdateRequest,
    service: MasterService = Depends(get_master_service),
    current_user=Depends(require_any_permission("master.modules.edit")),
):
    # Queda en la auditoria por AuditMiddleware: quien apago que y cuando.
    return service.set_module_enabled(code, request, current_user.id)
