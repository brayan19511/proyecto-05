from fastapi import APIRouter, Depends

from app.api.coolbox.ETL.router import productos_router, tiendas_router, ventas_router
from app.core.security import PermissionChecker

router = APIRouter(
    dependencies=[Depends(PermissionChecker("coolbox.etl.execute"))],
)


router.include_router(prefix="/ventas", router=ventas_router.router)
router.include_router(prefix="/tiendas", router=tiendas_router.router)
router.include_router(prefix="/productos", router=productos_router.router)
