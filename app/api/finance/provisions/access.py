from sqlalchemy.orm import Session

from app.core.access import has_permission
from app.core.scope import UserScope, get_user_scope


def can_view_all_provisions(user) -> bool:
    return has_permission(
        user,
        "provisions.view_all",
        "provisions.edit_all",
        "provisions.review",
    )


def can_edit_all_provisions(user) -> bool:
    return has_permission(user, "provisions.edit_all")


def resolve_provision_scope(db: Session, user) -> UserScope:
    """Alcance empresa/area del usuario para provisiones.

    Quien puede ver todo queda sin restriccion; el resto se limita a las
    areas que tenga asignadas en ``security.user_area_access``.
    """
    return get_user_scope(
        db,
        user,
        "provisions.view_all",
        "provisions.edit_all",
    )
