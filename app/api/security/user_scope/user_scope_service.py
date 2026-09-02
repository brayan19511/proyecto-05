# app/api/security/user_scope/user_scope_service.py

from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.master.master_service import MasterService
from app.api.security.auth.auth_repository import AuthRepository
from app.api.security.user_scope.user_scope_repository import UserScopeRepository
from app.api.security.user_scope.user_scope_schema import (
    AreaRefResponse,
    CompanyScopeResponse,
    UserAreaAccessRequest,
    UserScopeItemRequest,
    UserScopeResponse,
)
from app.core.access import is_admin
from app.core.exceptions import ConflictError, get_or_404
from app.models.auth.security_model import UserAreaAccess


class UserScopeService:
    """Gestiona a que areas de que empresas puede acceder cada usuario."""

    def __init__(self, db: Session):
        self.db = db
        self.repository = UserScopeRepository(db)
        self.auth_repository = AuthRepository(db)
        self.master_service = MasterService(db)

    # =====================================================
    # VALIDACIONES
    # =====================================================

    def _get_user_or_404(self, user_id: UUID):
        return get_or_404(
            self.auth_repository.get_by_id(user_id),
            "El usuario indicado no existe",
        )

    def _validate_target(self, company_id: int, area_id: int | None):
        """La empresa y el area deben existir y estar vigentes."""
        self.master_service.get_active_company_by_id(company_id)

        if area_id is not None:
            self.master_service.get_active_area_by_id(area_id)

    # =====================================================
    # CONSULTAS
    # =====================================================

    def get_accesses(
        self,
        user_id: UUID | None = None,
        company_id: int | None = None,
        area_id: int | None = None,
        active: bool | None = True,
    ):
        return self.repository.get_accesses(
            user_id=user_id,
            company_id=company_id,
            area_id=area_id,
            active=active,
        )

    def get_user_scope_detail(self, user, unrestricted: bool | None = None):
        """Devuelve el alcance del usuario agrupado como empresa > areas."""
        if unrestricted is None:
            unrestricted = is_admin(user)

        accesses = self.repository.get_accesses(user_id=user.id, active=True)

        companies: dict[int, CompanyScopeResponse] = {}

        for access in accesses:
            company = access.company

            # Ignora accesos que apunten a maestros dados de baja.
            if company is None or not company.active:
                continue

            entry = companies.get(company.id)
            if entry is None:
                entry = CompanyScopeResponse(
                    company_id=company.id,
                    company_code=company.code,
                    company_name=company.name,
                )
                companies[company.id] = entry

            if access.area_id is None:
                entry.all_areas = True
                continue

            area = access.area
            if area is None or not area.active:
                continue

            entry.areas.append(
                AreaRefResponse(id=area.id, code=area.code, name=area.name)
            )

        # Si cubre toda la empresa, se listan sus areas vigentes para que la
        # UI pueda pintar el arbol empresa > areas sin una llamada extra.
        all_areas_cache: list[AreaRefResponse] | None = None

        for entry in companies.values():
            if entry.all_areas:
                if all_areas_cache is None:
                    all_areas_cache = [
                        AreaRefResponse(id=area.id, code=area.code, name=area.name)
                        for area in self.master_service.get_areas()
                    ]
                entry.areas = list(all_areas_cache)
            else:
                entry.areas.sort(key=lambda area: area.code)

        return UserScopeResponse(
            user_id=user.id,
            unrestricted=unrestricted,
            companies=sorted(
                companies.values(),
                key=lambda entry: entry.company_code,
            ),
        )

    # =====================================================
    # ASIGNACION
    # =====================================================

    def assign_access(
        self,
        request: UserAreaAccessRequest,
        current_user_id: UUID | None,
    ):
        self._get_user_or_404(request.user_id)
        self._validate_target(request.company_id, request.area_id)

        existing = self.repository.get_access(
            request.user_id,
            request.company_id,
            request.area_id,
        )

        if existing:
            if existing.active:
                raise ConflictError("El usuario ya tiene asignado ese acceso")

            # Reactivar en vez de duplicar: el borrado es logico.
            existing.active = True
            existing.updated_by = current_user_id
            self._commit()
            return existing

        access = UserAreaAccess(
            user_id=request.user_id,
            company_id=request.company_id,
            area_id=request.area_id,
            created_by=current_user_id,
        )

        self.repository.create_access(access)
        self._commit()

        return access

    def replace_user_scope(
        self,
        user_id: UUID,
        items: list[UserScopeItemRequest],
        current_user_id: UUID | None,
    ):
        """Deja el alcance del usuario exactamente igual a la lista recibida.

        Lo que sale de la lista se desactiva, nunca se borra.
        """
        user = self._get_user_or_404(user_id)

        wanted: set[tuple[int, int | None]] = set()
        for item in items:
            key = (item.company_id, item.area_id)
            if key in wanted:
                raise ConflictError(
                    "No se puede repetir la misma combinacion de empresa y area"
                )
            self._validate_target(item.company_id, item.area_id)
            wanted.add(key)

        current = self.repository.get_accesses(user_id=user_id, active=None)
        by_key = {
            (access.company_id, access.area_id): access for access in current
        }

        for key, access in by_key.items():
            desired_active = key in wanted
            if access.active != desired_active:
                access.active = desired_active
                access.updated_by = current_user_id

        for key in wanted - set(by_key):
            company_id, area_id = key
            self.repository.create_access(
                UserAreaAccess(
                    user_id=user_id,
                    company_id=company_id,
                    area_id=area_id,
                    created_by=current_user_id,
                )
            )

        self._commit()

        return self.get_user_scope_detail(user)

    def set_access_active(
        self,
        access_id: int,
        active: bool,
        current_user_id: UUID | None,
    ):
        """Activa o desactiva el acceso (no hay borrado fisico)."""
        access = get_or_404(
            self.repository.get_access_by_id(access_id),
            "El acceso indicado no existe",
        )

        access.active = active
        access.updated_by = current_user_id

        self.repository.commit()

        return access

    # =====================================================
    # TRANSACCION
    # =====================================================

    def _commit(self):
        try:
            self.repository.commit()
        except IntegrityError:
            self.repository.rollback()
            raise ConflictError("El usuario ya tiene asignado ese acceso")
