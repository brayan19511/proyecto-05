from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.attendance.permissions import ATTENDANCE_MARKS_VIEW_PERMISSION
from app.api.attendance.schemas import (
    AttendanceMarkPage,
    AttendanceMarkSearch,
)
from app.api.attendance.service import AttendanceService
from app.core.access import require_any_permission
from app.core.db.db_cic import get_db_cic
from app.core.modules import MODULE_ATTENDANCE, ModuleEnabled


router = APIRouter(
    prefix="/attendance",
    tags=["ATTENDANCE"],
    dependencies=[Depends(ModuleEnabled(MODULE_ATTENDANCE))],
)


def get_attendance_service(
    db: Session = Depends(get_db_cic),
) -> AttendanceService:
    return AttendanceService(db)


@router.get(
    "/marks",
    response_model=AttendanceMarkPage,
    summary="Consultar marcas de asistencia",
)
def get_attendance_marks(
    document_numbers: Annotated[
        list[int],
        Query(
            alias="document_number",
            description="Repeat the parameter to query multiple documents",
        ),
    ],
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = Query(default=1000, ge=1, le=5000),
    offset: int = Query(default=0, ge=0),
    service: AttendanceService = Depends(get_attendance_service),
    current_user=Depends(
        require_any_permission(ATTENDANCE_MARKS_VIEW_PERMISSION),
    ),
):
    return service.get_marks(
        document_numbers,
        date_from,
        date_to,
        limit,
        offset,
    )


@router.post(
    "/marks/search",
    response_model=AttendanceMarkPage,
    summary="Buscar marcas de varios colaboradores",
)
def search_attendance_marks(
    filters: AttendanceMarkSearch,
    service: AttendanceService = Depends(get_attendance_service),
    current_user=Depends(
        require_any_permission(ATTENDANCE_MARKS_VIEW_PERMISSION),
    ),
):
    """Use a request body when the UI needs to submit many documents."""
    return service.get_marks(
        filters.document_numbers,
        filters.date_from,
        filters.date_to,
        filters.limit,
        filters.offset,
    )
