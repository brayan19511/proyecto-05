"""Alcance operativo (empresa / area) de un usuario.

Una fila de ``security.user_area_access`` significa "este usuario opera en el
area X de la empresa Y". Si ``area_id`` es NULL, cubre todas las areas de esa
empresa.

Este modulo centraliza la resolucion del alcance y su aplicacion como filtro
para que cualquier modulo (gastos, provisiones, ...) lo reutilice sin
reimplementar la logica.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import and_, false, or_
from sqlalchemy.orm import Session

from app.core.access import has_permission, is_admin
from app.core.exceptions import ForbiddenError
from app.models.auth.security_model import UserAreaAccess


@dataclass(frozen=True)
class UserScope:
    """Alcance resuelto de un usuario.

    - ``unrestricted``: ve todo (admin o permiso ``*_all``); se ignora el resto.
    - ``companies``: empresas donde tiene acceso a todas las areas.
    - ``pairs``: pares (company_id, area_id) explicitos.
    """

    unrestricted: bool = False
    companies: frozenset[int] = field(default_factory=frozenset)
    pairs: frozenset[tuple[int, int]] = field(default_factory=frozenset)

    @property
    def is_empty(self) -> bool:
        """True si el usuario no tiene ningun alcance asignado."""
        return not self.unrestricted and not self.companies and not self.pairs

    @property
    def company_ids(self) -> set[int]:
        """Todas las empresas alcanzadas, sea por empresa completa o por area."""
        return set(self.companies) | {company_id for company_id, _ in self.pairs}

    def area_ids(self, company_id: int | None = None) -> set[int]:
        """Areas explicitas del alcance, opcionalmente filtradas por empresa."""
        return {
            area_id
            for pair_company_id, area_id in self.pairs
            if company_id is None or pair_company_id == company_id
        }

    def allows(self, company_id: int | None, area_id: int | None) -> bool:
        """True si el par (empresa, area) cae dentro del alcance."""
        if self.unrestricted:
            return True

        if company_id is None:
            return False

        if company_id in self.companies:
            return True

        if area_id is None:
            return False

        return (company_id, area_id) in self.pairs


def get_user_scope(db: Session, user, *view_all_permissions: str) -> UserScope:
    """Resuelve el alcance del usuario a partir de sus accesos activos.

    Si es admin o tiene alguno de los ``view_all_permissions`` indicados, el
    alcance queda sin restriccion.
    """
    if is_admin(user) or (
        view_all_permissions and has_permission(user, *view_all_permissions)
    ):
        return UserScope(unrestricted=True)

    rows = (
        db.query(UserAreaAccess.company_id, UserAreaAccess.area_id)
        .filter(
            UserAreaAccess.user_id == user.id,
            UserAreaAccess.active.is_(True),
        )
        .all()
    )

    companies = {company_id for company_id, area_id in rows if area_id is None}
    pairs = {
        (company_id, area_id)
        for company_id, area_id in rows
        # Una empresa completa ya cubre sus areas: no repetir el par.
        if area_id is not None and company_id not in companies
    }

    return UserScope(
        unrestricted=False,
        companies=frozenset(companies),
        pairs=frozenset(pairs),
    )


def scope_condition(model, scope: UserScope):
    """Condicion SQL que limita ``model`` al alcance dado.

    Devuelve ``None`` cuando no hay que filtrar (alcance sin restriccion) y una
    condicion siempre falsa cuando el alcance esta vacio.
    """
    if scope.unrestricted:
        return None

    if scope.is_empty:
        return false()

    conditions = []

    if scope.companies:
        conditions.append(model.company_id.in_(sorted(scope.companies)))

    # Se expanden los pares en lugar de usar tuple_().in_() para no depender
    # del soporte de tuplas del motor.
    conditions.extend(
        and_(model.company_id == company_id, model.area_id == area_id)
        for company_id, area_id in sorted(scope.pairs)
    )

    return or_(*conditions)


def apply_scope_filter(query, model, scope: UserScope):
    """Aplica el alcance a un query de SQLAlchemy."""
    condition = scope_condition(model, scope)

    if condition is None:
        return query

    return query.filter(condition)


def assert_in_scope(
    scope: UserScope,
    company_id: int | None,
    area_id: int | None,
    message: str = "No tienes acceso a esa combinacion de empresa y area",
):
    """Valida que el par (empresa, area) este dentro del alcance del usuario.

    Un alcance vacio no bloquea: los usuarios que todavia no tienen accesos
    asignados siguen operando como antes. La restriccion aplica recien cuando
    se le configura un alcance explicito al usuario.
    """
    if scope.is_empty:
        return

    if not scope.allows(company_id, area_id):
        raise ForbiddenError(message)
