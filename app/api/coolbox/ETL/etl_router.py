from fastapi import APIRouter

from app.api.coolbox.ETL.router import ventas_router,tiendas_router

router = APIRouter()


router.include_router(prefix="/ventas", router=ventas_router.router)
router.include_router(prefix="/tiendas", router=tiendas_router.router)
router.include_router(prefix="/productos", router=ventas_router.router)
